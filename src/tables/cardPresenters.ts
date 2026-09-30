import { Quaternion, Vector3, type Group, type Object3D } from 'three/webgpu';
import type { BaccaratState } from '../games/baccarat/baccarat';
import type { BlackjackState } from '../games/blackjack/blackjack';
import type { PokerState } from '../games/poker/poker';
import type { GameEvent } from '../games/shared/types';
import type { AnchorDef, ZoneInstance } from '../world/roomBuilder';
import { CARD_W } from './assets';
import { CardTable, chipPile, movePile, TableAnchors, type CardView } from './table';

/**
 * 3D presentation for the card tables (§9): each presenter reconciles what lies on the felt with the
 * engine's latest state snapshot and animates the difference — cards leave the shoe, turn over, get
 * swept; chips are staked, paid and collected. Nothing here decides an outcome.
 */
export interface Presenter {
  update(state: unknown | null, events: GameEvent[]): Promise<void>;
  tick(time: number): void;
  dispose(): void;
}

const TOWARD_PLAYER = new Vector3(0, 0, 0.28);   // anchor-local: +Z points at the guest (−Z = card tops)

abstract class CardTablePresenter implements Presenter {
  protected t: CardTable;
  protected chips: Group[] = [];
  constructor(protected a: TableAnchors) { this.t = new CardTable(a); }
  abstract update(state: unknown | null, events: GameEvent[]): Promise<void>;
  tick(time: number): void { this.t.tw.update(time); }

  protected stake(amount: number, at: Object3D, delay: number, offset = new Vector3()): { pile: Group; done: Promise<void> } {
    const pile = chipPile(amount);
    at.add(pile);
    pile.position.copy(offset).add(TOWARD_PLAYER);
    pile.visible = false;
    this.chips.push(pile);
    const done = this.t.tw.add(delay, 1e-3, () => { pile.visible = true; }).then(() => movePile(this.t.tw, pile, at, offset, 0, 0.45));
    return { pile, done };
  }

  /** Winnings: the dealer pushes chips from the tray next to the stake, then both slide back to the guest. */
  protected async settle(net: number, stake: Group | undefined, at: Object3D, delay: number): Promise<void> {
    const tray = this.a.get('chipTray') ?? at;
    const tw = this.t.tw;
    if (!stake) return;
    if (net < 0) {                     // the house collects
      await movePile(tw, stake, tray, new Vector3(0, 0.03, 0), delay, 0.5);
      this.drop(stake);
      return;
    }
    if (net > 0) {
      const win = chipPile(net);
      tray.add(win);
      win.position.set(0, 0.03, 0);
      this.chips.push(win);
      await movePile(tw, win, at, new Vector3(CARD_W * 0.9, 0, 0), delay, 0.55);
      delay = 0.35;
      await Promise.all([movePile(tw, win, at, TOWARD_PLAYER.clone().add(new Vector3(0.05, 0, 0.1)), delay, 0.5).then(() => this.drop(win)),
        movePile(tw, stake, at, TOWARD_PLAYER.clone().add(new Vector3(-0.02, 0, 0.1)), delay, 0.5).then(() => this.drop(stake))]);
      return;
    }
    await movePile(tw, stake, at, TOWARD_PLAYER.clone().add(new Vector3(0, 0, 0.1)), delay + 0.3, 0.5);   // push: stake back
    this.drop(stake);
  }

  protected drop(pile: Group): void {
    pile.removeFromParent();
    this.chips = this.chips.filter((c) => c !== pile);
  }

  protected clearChips(): void {
    for (const c of this.chips) c.removeFromParent();
    this.chips = [];
  }

  dispose(): void {
    this.t.dispose();
    this.clearChips();
  }
}

// ---------------------------------------------------------------- blackjack
class BlackjackPresenter extends CardTablePresenter {
  private player: CardView[] = [];
  private dealer: CardView[] = [];
  private stakePile?: Group;
  private settled = false;

  async update(s: BlackjackState | null, events: GameEvent[]): Promise<void> {
    if (!s) { this.reset(); return; }
    const P = this.a.get('playerCards'), D = this.a.get('dealerCards'), B = this.a.get('bet');
    if (!P || !D || !B) return;
    const jobs: Promise<void>[] = [];
    let d = 0;
    if (events.some((e) => e.type === 'dealt')) {
      if (this.t.count) { jobs.push(this.t.sweep()); d = 0.55; }
      this.player = []; this.dealer = []; this.settled = false;
      this.clearChips();
      const st = this.stake(s.bet, B, d); this.stakePile = st.pile; jobs.push(st.done); d += 0.45;
      const order: ['p' | 'd', number][] = [['p', 0], ['d', 0], ['p', 1], ['d', 1]];
      for (const [who, i] of order) {
        const hand = who === 'p' ? s.player : s.dealer;
        if (!hand[i]) continue;
        const hidden = who === 'd' && i === 1 && s.dealerHidden;
        const r = this.t.deal(hidden ? null : hand[i], !hidden, who === 'p' ? P : D, this.t.handPose(i, !hidden), d);
        (who === 'p' ? this.player : this.dealer).push(r.view);
        jobs.push(r.done); d += 0.34;
      }
    }
    for (let i = this.player.length; i < s.player.length; i++) {
      const r = this.t.deal(s.player[i], true, P, this.t.handPose(i, true), d);
      this.player.push(r.view); jobs.push(r.done); d += 0.36;
    }
    if (!s.dealerHidden && this.dealer[1] && !this.dealer[1].faceUp) {
      jobs.push(this.t.flip(this.dealer[1], s.dealer[1], d)); d += 0.45;
    }
    for (let i = this.dealer.length; i < s.dealer.length; i++) {
      const r = this.t.deal(s.dealer[i], true, D, this.t.handPose(i, true), d);
      this.dealer.push(r.view); jobs.push(r.done); d += 0.4;
    }
    await Promise.all(jobs);
    if (s.phase === 'settled' && !this.settled) {
      this.settled = true;
      await this.settle(s.payout, this.stakePile, B, 0.25);
      this.stakePile = undefined;
    }
  }

  private reset(): void {
    this.dispose();
    this.player = []; this.dealer = []; this.stakePile = undefined; this.settled = false;
  }
}

// ---------------------------------------------------------------- baccarat
const SIDE_INDEX = { banker: 0, player: 1, tie: 2 } as const;

class BaccaratPresenter extends CardTablePresenter {
  async update(s: BaccaratState | null, events: GameEvent[]): Promise<void> {
    if (!s) { this.dispose(); return; }
    if (!events.some((e) => e.type === 'coup') || !s.bet) return;
    const P = this.a.get('playerCards'), Bk = this.a.get('bankerCards'), bet = this.a.get('bet', SIDE_INDEX[s.bet.on]);
    if (!P || !Bk || !bet) return;
    const jobs: Promise<void>[] = [];
    let d = 0;
    if (this.t.count) { jobs.push(this.t.sweep()); d = 0.55; }
    this.clearChips();
    const st = this.stake(s.bet.amount, bet, d);
    jobs.push(st.done); d += 0.5;
    // punto banco order: P, B, P, B, then any third cards — laid sideways, as croupiers do
    const order: ['p' | 'b', number][] = [['p', 0], ['b', 0], ['p', 1], ['b', 1], ['p', 2], ['b', 2]];
    for (const [who, i] of order) {
      const hand = who === 'p' ? s.player : s.banker;
      if (!hand[i]) continue;
      const pose = this.t.handPose(Math.min(i, 1), true, 0.9);
      if (i === 2) {
        pose.pos.set(0, 0.0012, CARD_W * 0.95);
        pose.q.setFromAxisAngle(new Vector3(0, 1, 0), Math.PI / 2);
      }
      const r = this.t.deal(hand[i], true, who === 'p' ? P : Bk, pose, d);
      jobs.push(r.done); d += 0.38;
    }
    await Promise.all(jobs);
    await this.settle(s.payout, st.pile, bet, 0.5);
  }
}

// ---------------------------------------------------------------- poker
class PokerPresenter extends CardTablePresenter {
  private mine: CardView[] = [];
  private bots: CardView[][] = [[], [], []];
  private board: CardView[] = [];
  private pot?: Group;
  private potAmount = 0;
  private done = false;

  /** Community-card pitch: the board anchor's printed boxes (extras.spacing), else a tight real-table spread. */
  private boardSpacing(): number {
    return Number(this.a.extras('board').spacing ?? CARD_W * 1.12);
  }

  async update(s: PokerState | null, events: GameEvent[]): Promise<void> {
    if (!s) { this.dispose(); this.mine = []; this.bots = [[], [], []]; this.board = []; this.pot = undefined; this.potAmount = 0; return; }
    const me = this.a.get('playerCards'), boardA = this.a.get('board'), potA = this.a.get('pot');
    if (!me || !boardA || !potA) return;
    const botAnchors = this.a.all('botCards');
    const jobs: Promise<void>[] = [];
    let d = 0;
    if (events.some((e) => e.type === 'dealt')) {
      if (this.t.count) { jobs.push(this.t.sweep()); d = 0.55; }
      this.clearChips();
      this.mine = []; this.bots = [[], [], []]; this.board = []; this.pot = undefined; this.potAmount = 0; this.done = false;
      const bots = s.seats.filter((x) => !x.isPlayer);
      for (let round = 0; round < 2; round++) {
        const r = this.t.deal(s.seats.find((x) => x.isPlayer)!.hole[round], true, me, this.t.handPose(round, true), d);
        this.mine.push(r.view); jobs.push(r.done); d += 0.22;
        bots.forEach((_, i) => {
          const a = botAnchors[i]?.node;
          if (!a) return;
          const v = this.t.deal(null, false, a, this.t.handPose(round, false), d);
          this.bots[i].push(v.view); jobs.push(v.done); d += 0.22;
        });
      }
    }
    // folded house players toss their cards in
    s.seats.filter((x) => !x.isPlayer).forEach((b, i) => {
      if (b.folded && this.bots[i].length) { jobs.push(this.muck(this.bots[i], potA, d)); this.bots[i] = []; }
    });
    if (s.seats.find((x) => x.isPlayer)?.folded && this.mine.length) { jobs.push(this.muck(this.mine, potA, d)); this.mine = []; }
    // community cards
    for (let i = this.board.length; i < s.board.length; i++) {
      const r = this.t.deal(s.board[i], true, boardA, { pos: new Vector3((i - 2) * this.boardSpacing(), 0.0004, 0), q: new Quaternion() }, d);
      this.board.push(r.view); jobs.push(r.done); d += 0.3;
    }
    // the pot grows as chips go in
    if (s.pot !== this.potAmount) {
      const old = this.pot;
      const pile = chipPile(s.pot);
      potA.add(pile);
      pile.visible = false;
      this.chips.push(pile);
      this.pot = pile;
      this.potAmount = s.pot;
      jobs.push(this.t.tw.add(d, 1e-3, () => { pile.visible = true; if (old) this.drop(old); }));
    }
    await Promise.all(jobs);
    if (s.street === 'showdown' && !this.done) {
      this.done = true;
      const flips: Promise<void>[] = [];
      s.seats.filter((x) => !x.isPlayer).forEach((b, i) => {
        this.bots[i].forEach((v, k) => { if (b.hole[k]?.rank) flips.push(this.t.flip(v, b.hole[k], 0.1 + i * 0.2 + k * 0.08)); });
      });
      await Promise.all(flips);
      const winnerSeat = s.seats.findIndex((x) => s.winners.includes(x.name));
      const winner = s.seats[winnerSeat];
      if (this.pot) {
        const bi = s.seats.filter((x) => !x.isPlayer).indexOf(winner);
        const to = winner?.isPlayer ? me : botAnchors[bi]?.node ?? potA;
        await movePile(this.t.tw, this.pot, to, new Vector3(0, 0, winner?.isPlayer ? 0.2 : 0.12), 0.4, 0.7);
      }
    }
  }

  /** Folded cards slide face down into the muck beside the pot. */
  private muck(views: CardView[], potA: Object3D, delay: number): Promise<void> {
    const down = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI);
    return Promise.all(views.map((v, i) => {
      let from: Vector3, fq: Quaternion;
      const to = new Vector3(0.18 + i * 0.01, 0.001 + i * 0.0004, -0.12);
      return this.t.tw.add(delay + i * 0.05, 0.4, (k) => {
        v.mesh.position.lerpVectors(from, to, k);
        v.mesh.quaternion.slerpQuaternions(fq, down, k);
      }, undefined, () => { potA.attach(v.mesh); from = v.mesh.position.clone(); fq = v.mesh.quaternion.clone(); });
    })).then(() => {});
  }
}

// ---------------------------------------------------------------- wiring
const MAKERS: Record<string, (a: TableAnchors) => Presenter> = {
  blackjack: (a) => new BlackjackPresenter(a),
  baccarat: (a) => new BaccaratPresenter(a),
  poker: (a) => new PokerPresenter(a),
};

/** Give a zone's card tables 3D presenters (called from the room runtime modules). */
export function attachCardTables(inst: ZoneInstance, game: 'blackjack' | 'baccarat' | 'poker'): void {
  const byTable = new Map<string, AnchorDef[]>();
  for (const a of inst.anchors ?? []) (byTable.get(a.tableId) ?? byTable.set(a.tableId, []).get(a.tableId)!).push(a);
  const presenters = new Map<string, Presenter>();
  inst.animate.push((t) => { for (const p of presenters.values()) p.tick(t); });
  inst.onGameState = (tableId, state, events) => {
    const anchors = byTable.get(tableId);
    if (!anchors) return;
    let p = presenters.get(tableId);
    if (!p) presenters.set(tableId, (p = MAKERS[game](new TableAnchors(anchors))));
    return p.update(state, events);
  };
}
