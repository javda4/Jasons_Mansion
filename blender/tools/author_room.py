"""Bootstrap authoring of a game room — Blender → GLB → web.

    blender -b --factory-startup --python blender/tools/author_room.py -- <poker|blackjack|baccarat|roulette|slots>

Zone anchor: centre of the entrance threshold (the gallery door), floor level; the room runs along
Blender +Y (glTF −Z), width along X. Layouts, table ids and positions match the code-built rooms so
sessions, prompts and doors keep working.
"""
import itertools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import casino_props as C  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

zone_id = sys.argv[sys.argv.index("--") + 1]
kit.reset_scene()
T = 0.3
DOOR_W, DOOR_H = 2.2, 3.1
OUT = os.path.join(kit.ROOT, "blender", "rooms", zone_id, f"{zone_id}.blend")


def pilasters(lo, hi, bay=3.3):
    n = max(2, round((hi - lo) / bay))
    return [lo + i * (hi - lo) / n for i in range(n + 1)]


def shell(A, W, D, field, floor, windows_back=(), art=(), bays_side=None, back_art=True):
    """Floor, coffered ceiling and four dressed walls (entrance at y = 0 shares the gallery's jambs)."""
    M, hw = A.M, W / 2
    floor(A, hw, D)
    A.coffered_ceiling(-hw, hw, 0, D, spacing=2.4)
    side = pilasters(0, D, D / bays_side if bays_side else 3.3)
    back = pilasters(-hw, hw)
    if not back_art:  # a centrepiece owns the back wall: keep its middle bay clear of pilasters and sconces
        back = [p for p in back if abs(p) > 2.0 or abs(p) >= hw - 1e-6]
    front = [-hw, -DOOR_W / 2 - 0.45, DOOR_W / 2 + 0.45, hw]
    sconce_side = side[1:-1]
    a = itertools.cycle(art)
    mids = lambda p: [(p[i] + p[i + 1]) / 2 for i in range(len(p) - 1)]  # noqa: E731
    A.wall("Front", "x", 0, 1, -hw, hw, openings=[(0.0, DOOR_W, DOOR_H)], pilasters=front, jambs=False, field=field,
           sconces=[front[1] - 0.6, front[2] + 0.6])
    backs = [m for m in mids(back) if all(abs(m - w) > 0.5 for w in windows_back)]
    A.wall("Back", "x", D, -1, -hw, hw, pilasters=back, windows=list(windows_back), field=field,
           paintings=[(m, next(a)) for m in backs[:: max(1, len(backs) // 2)][:2]] if back_art else [], sconces=back[1:-1])
    lm = mids(side)
    A.wall("Left", "y", -hw, 1, 0, D, pilasters=side, field=field, sconces=sconce_side,
           paintings=[(m, next(a)) for m in lm[::2]])
    A.wall("Right", "y", hw, -1, 0, D, pilasters=side, field=field, sconces=sconce_side,
           paintings=[(m, next(a)) for m in lm[1::2]])


def carpet(key):
    def f(A, hw, D):
        M = A.M
        A.bordered_floor(-hw, hw, 0, D, M[key], M["gilt"], margin=M["walnut"], m=0.55, bw=0.05)
    return f


def marble(A, hw, D):
    A.bordered_floor(-hw, hw, 0, D, A.M["marble"], A.M["nero"])


def pendant(A, x, y, H, sx=1.6, candela=16):
    """Brass billiard-style pendant over a card table with a live light under the shade."""
    K, M = A.K, A.M
    K.cyl(K.name("PROP", "PendantRod"), 0.008, 0.008, H - 1.95, (x, y, (H + 1.95) / 2), M["brass"], segments=8)
    shade = K.lathe(K.name("PROP", "PendantShade"), [(0.55, 0), (0.5, 0.05), (0.3, 0.2), (0.14, 0.3), (0.05, 0.32), (0, 0.33)], (x, y, 1.72), M["brass"], segments=48)
    shade.scale = (sx, 1, 1)
    glow = K.cyl(K.name("PROP", "PendantGlow"), 0.48, 0.48, 0.01, (x, y, 1.73), M["shade"], segments=48)
    glow.scale = (sx, 1, 1)
    K.light(K.name("LIGHT", "Pendant"), "POINT", (x, y, 1.6), candela, rng=4.5)


def audio_table(A, x, y, sounds):
    for sound, gain, interval in sounds:
        A.audio(sound.capitalize(), (x, y, 0.9), sound, gain=gain, interval=interval)


# ============================================================================ rooms

def poker():
    W, D, H = 14, 12, 5.2
    K = kit.Zone("Poker")
    A = mansion.Mansion(K, height=H, thickness=T)
    shell(A, W, D, A.M["damask_green"], carpet("carpet"), art=(9, 4, 1, 7, 0, 10))  # red carpet on green walls (casino.png)
    for i, (x, y) in enumerate(((-3.4, 4.4), (3.4, 4.4), (-3.4, 8.9), (3.4, 8.9))):
        C.kr_poker_table(A, x, y, f"poker_{i + 1:02d}")
        pendant(A, x, y, H)
        audio_table(A, x, y, (("chips", 0.35, (4, 11)), ("cardFlick", 0.3, (3, 9))))
    A.lamp_table(-5.6, 1.8, candela=4)
    A.club_chair((-4.45, 1.8), -math.pi / 2)
    A.chandelier(0, 6.6, scale=0.7, drop=1.2, point_cd=30)
    return A, W, D, H


def blackjack():
    W, D, H = 14, 12, 5.6
    K = kit.Zone("Blackjack")
    A = mansion.Mansion(K, height=H, thickness=T, sea=mansion.sea_texture(os.path.join(kit.ROOT, "blender", "textures_src", "blackjack", "T_Blackjack_SeaView_Emissive.png"), seed=7, moon_x=0.7))
    shell(A, W, D, A.M["damask"], carpet("carpet"), windows_back=(-1.75, 1.75), art=(2, 6, 3, 8))
    for i, (x, y) in enumerate(((-3.6, 5.2), (3.6, 5.2), (-3.6, 9.6), (3.6, 9.6))):
        C.kr_blackjack_table(A, x, y, f"blackjack_{i + 1:02d}", rz=math.pi)  # players face the entrance
        audio_table(A, x, y, (("cardFlick", 0.3, (2.5, 7)), ("chips", 0.3, (5, 12))))
    A.chandelier(-3.6, 7.4, scale=0.75, drop=1.3, point_cd=36)
    A.chandelier(3.6, 7.4, scale=0.75, drop=1.3, point_cd=36, key=False)
    return A, W, D, H


def baccarat():
    W, D, H = 12, 12, 5.8
    K = kit.Zone("Baccarat")
    A = mansion.Mansion(K, height=H, thickness=T)
    shell(A, W, D, A.M["damask_gold"], marble, art=(5, 9, 0, 4), bays_side=3, back_art=False)  # the tapestry owns the back wall
    # the "tapestry": a grand landscape centred on the back wall
    P = lambda c, off, z: kit.Vector((c, D - off, z))  # noqa: E731
    A.painting("Tapestry", P, kit.Vector((0, -1, 0)), 0.0, 0, 3, max_w=3.4, max_h=2.4)
    C.baccarat_table(A, 0, 6.4, "baccarat_01")
    C.stanchions(A, 0, 6.4, 3.7, 2.6, 14, gap=(10, 11))
    audio_table(A, 0, 6.4, (("cardFlick", 0.3, (3, 8)), ("chips", 0.3, (6, 14))))
    for x in (-4.2, 4.2):
        A.lamp_table(x, 1.9, candela=4)
        A.club_chair((x, 3.0), 0)
    A.chandelier(0, 6.4, scale=1.0, drop=1.15, point_cd=64)
    return A, W, D, H


def roulette():
    W, D, H = 14, 12, 5.8
    K = kit.Zone("Roulette")
    A = mansion.Mansion(K, height=H, thickness=T)
    shell(A, W, D, A.M["damask"], carpet("carpet"), art=(6, 2, 10, 5, 3, 8))
    for i, (x, y) in enumerate(((-3.2, 4.4), (3.4, 4.4), (-3.2, 9.0), (3.4, 9.0))):
        C.kr_roulette_table(A, x, y, f"roulette_{i + 1:02d}", i + 1, rz=math.pi)  # players on the entrance side
        audio_table(A, x, y, (("rouletteBall", 0.35, (18, 40)), ("chips", 0.3, (5, 12))))
    A.chandelier(-3.2, 6.7, scale=0.7, drop=1.3, point_cd=32)
    A.chandelier(3.4, 6.7, scale=0.7, drop=1.3, point_cd=32, key=False)
    return A, W, D, H


def slots():
    W, D, H = 14, 14, 5.4
    K = kit.Zone("Slots")
    A = mansion.Mansion(K, height=H, thickness=T)
    shell(A, W, D, A.M["damask"], carpet("carpet"), art=(1, 7, 4, 0), bays_side=4)
    n = 0
    # Kraffing Slot_Machine_1 cabinets (0.85 m wide at real scale), back to back in two banks
    for bank_x in (-3.3, 3.3):
        for k in range(7):
            y = 3.4 + k * 0.9
            n += 1
            C.kr_slot_machine(A, bank_x - 0.47, y, math.pi / 2, f"slots_{n:02d}")    # faces −X
            n += 1
            C.kr_slot_machine(A, bank_x + 0.47, y, -math.pi / 2, f"slots_{n:02d}")   # faces +X
        A.audio(f"Chime{'L' if bank_x < 0 else 'R'}", (bank_x, 6.1, 1.5), "slotChime", gain=0.25, interval=(2, 6))
        A.K.light(A.K.name("LIGHT", "SlotGlow"), "POINT", (bank_x, 6.1, 1.6), 5, color=(1.0, 0.48, 0.23), rng=6)
    for k in range(12):
        n += 1
        C.kr_slot_machine(A, -4.95 + k * 0.9, D - 0.55, math.pi, f"slots_{n:02d}")  # back row faces the room
    # the pack's wheel-of-fortune machines as the hall's showpieces (not playable)
    C.kr_decor(A, "Lucky_Spin_Machine_2", "KrLuckySpinGrand", 0, 11.2, 0, pick=["Lucky_Spin_Machine_2_AllInOne"], collide=(1.1, 0.46, 3.0))
    for sx in (-1, 1):
        C.kr_decor(A, "Lucky_Spin_Machine_1", "KrLuckySpin", sx * 5.8, 1.6, -sx * math.pi / 2, collide=(0.6, 0.3, 2.4))
    A.chandelier(0, 7.0, scale=0.85, drop=1.4, point_cd=40)
    return A, W, D, H


A, W, D, H = {"poker": poker, "blackjack": blackjack, "baccarat": baccarat, "roulette": roulette, "slots": slots}[zone_id]()
A.logic(probe=(0, D / 2, 1.7), bounds=((-W / 2, 0.05, -1), (W / 2, D, H)))
mansion.save(OUT)
