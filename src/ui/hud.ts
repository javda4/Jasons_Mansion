import type { EventBus, QualityTier } from '../core/events';

/** Minimal, diegetic-first HUD (§8 UI): brand, reticle, interaction prompt, curtain, pause menu. */
export class Hud {
  private curtain = document.getElementById('curtain')!;
  private status = document.getElementById('curtain-status')!;
  private enterBtn = document.getElementById('enter-btn') as HTMLButtonElement;
  private menu = document.getElementById('menu')!;
  private prompt = document.getElementById('hud-prompt')!;
  private promptText = document.getElementById('hud-prompt-text')!;
  private entered = false;
  private inGame = false;
  private toast = document.getElementById('hud-toast')!;
  private toastTimer = 0;

  constructor(
    private readonly bus: EventBus,
    handlers: {
      requestLock: () => void;
      setQuality: (t: QualityTier) => void;
      setSensitivity: (v: number) => void;
      setFov: (v: number) => void;
      setVolume: (v: number) => void;
    },
    initialTier: QualityTier,
  ) {
    this.enterBtn.addEventListener('click', () => { this.entered = true; handlers.requestLock(); });
    document.getElementById('resume-btn')!.addEventListener('click', () => handlers.requestLock());

    const q = document.getElementById('quality-select') as HTMLSelectElement;
    q.value = initialTier;
    q.addEventListener('change', () => handlers.setQuality(q.value as QualityTier));
    const sens = document.getElementById('sensitivity') as HTMLInputElement;
    sens.addEventListener('input', () => handlers.setSensitivity(Number(sens.value)));
    const vol = document.getElementById('volume') as HTMLInputElement;
    vol.addEventListener('input', () => handlers.setVolume(Number(vol.value)));
    const fov = document.getElementById('fov') as HTMLInputElement;
    fov.addEventListener('input', () => handlers.setFov(Number(fov.value)));

    bus.on('ui:toast', ({ text }) => {
      this.toast.textContent = text;
      this.toast.dataset.show = 'true';
      clearTimeout(this.toastTimer);
      this.toastTimer = window.setTimeout(() => (this.toast.dataset.show = 'false'), 2600);
    });
    bus.on('interaction:focus', (f) => {
      this.prompt.hidden = !f;
      if (f) this.promptText.textContent = f.prompt;
    });
  }

  setStatus(text: string): void { this.status.textContent = text; }

  ready(): void {
    this.setStatus('The doors are open.');
    this.enterBtn.disabled = false;
    this.enterBtn.focus();
  }

  /** Seated at a table: the game view owns the screen, so no pause menu or prompt. */
  setInGame(inGame: boolean): void {
    this.inGame = inGame;
    this.prompt.hidden = true;
    if (inGame) this.menu.hidden = true;
  }

  /** Reflects pointer-lock state: locked = playing, unlocked after entry = paused menu. */
  setLocked(locked: boolean): void {
    if (locked) {
      this.curtain.dataset.hidden = 'true';
      this.menu.hidden = true;
    } else if (this.entered && !this.inGame) {
      this.menu.hidden = false;
    }
    this.bus.emit('app:paused', { paused: !locked });
  }
}
