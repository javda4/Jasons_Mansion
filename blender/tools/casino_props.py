"""Game furniture for the Blender-authored rooms (Layer 1) — built to read as real casino equipment.

- Felts carry printed layouts (scripts/make-game-textures.mjs → textures_src/games/T_Felt<Game>_BaseColor):
  the felt's UV0 is its plan bounding box, matching the texture's plan coordinates.
- Padded leather armrests are lofted along the table outline; walnut aprons with a brass band; pedestal
  bases; chip trays filled with real chips (chip atlas, instanced) and a card shoe.
- The roulette rotor is one textured node with brass frets and a turret (extras {rotor: tableId}, spun at
  runtime); the ball track, deflectors and bowl are static.
- Slot machines are art-deco cabinets: back-lit marquee under a bulb arch, chrome-bezelled reel window,
  back-lit pay-table glass, button deck, coin tray and side lever. The reels themselves are runtime
  geometry (src/tables) placed on ANCHOR_ empties so they can spin to the engine's result.

Contracts: INTERACT_ volumes with `casinoTable` extras (src/interaction/schema.ts) and ANCHOR_ empties
(extras {anchor, tableId, index, …}; roles in conventions.ANCHOR_ROLES) that the runtime presenters use.
An anchor's local +Y (Blender) points to the *top* of cards laid there, i.e. away from the seated player.
"""
import json
import math
import os

import bmesh
from mathutils import Matrix, Vector

import kit

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
PROMPTS = {"poker": "Play Texas Hold'em", "blackjack": "Play Blackjack", "baccarat": "Play Baccarat", "roulette": "Play Roulette", "slots": "Play the Slot"}
GAMES = os.path.join(kit.ROOT, "blender", "textures_src", "games")
LAYOUT = json.load(open(os.path.join(GAMES, "layout.json")))
WHEEL_ORDER = LAYOUT["WHEEL_ORDER"]
FELT_Z = 0.8                      # playing surface height
SEAT_EYE = 1.2                    # seated eye height


# ----------------------------------------------------------------------------- materials
def casino_materials(A):
    K, m = A.K, A.K.mat
    if "cardstock" not in m:
        K.material("cardstock", f"MAT_{K.zone}_CardStock", (0.9, 0.87, 0.8), 0.6)
        K.material("chips", f"MAT_{K.zone}_Chips", (1, 1, 1), 0.42, coat=0.35, coat_rough=0.3, base_tex=os.path.join(GAMES, "T_Chip_Atlas_BaseColor.png"))
        K.material("lacquer_black", f"MAT_{K.zone}_BlackLacquer", (0.012, 0.011, 0.01), 0.35, coat=0.5, coat_rough=0.2)
    return m


def felt(A, game):
    K, M = A.K, A.K.mat
    key = f"felt_{game}"
    if key not in M:
        m = K.material(key, f"MAT_{K.zone}_Felt{game.capitalize()}", (1, 1, 1), 1.0, sheen=0.15, sheen_tint=(0.05, 0.13, 0.08),   # matte wool
                       base_tex=os.path.join(GAMES, f"T_Felt{game.capitalize()}_BaseColor.png"), extension="EXTEND")
    return M[key]


# ----------------------------------------------------------------------------- contracts
def pascal(table_id):
    return "".join(p.capitalize() for p in table_id.split("_"))


def interact(A, table_id, game, center, size, rz=0.0):
    """Invisible INTERACT_ volume with casinoTable extras (no material: never rendered)."""
    K = A.K
    ob = K.obj(f"INTERACT_{K.zone}_{pascal(table_id)}", kit.cube_bm(*size), None, coll="LOGIC", loc=center, rot=(0, 0, rz), uv=None)
    ob.display_type = "WIRE"
    ob.hide_render = True
    ob["interactable"] = True
    ob["interactionType"] = "casinoTable"
    ob["interactionPrompt"] = PROMPTS[game]
    ob["gameType"] = game
    ob["tableId"] = table_id
    return ob


def anchor(A, table_id, role, loc, rz=0.0, index=None, **extras):
    """ANCHOR_<Zone>_<Table><Role>[_NN] empty: a pose the runtime presenter builds on."""
    K = A.K
    name = f"ANCHOR_{K.zone}_{pascal(table_id)}{role[0].upper()}{role[1:]}" + (f"_{index + 1:02d}" if index is not None else "")
    e = K.empty(name, loc, rot=(0, 0, rz), kind="ARROWS", size=0.08)
    e["anchor"] = role
    e["tableId"] = table_id
    e["index"] = index or 0
    for k, v in extras.items():
        e[k] = v
    return e


def xf(x, y, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lambda dx, dy, dz=0.0: (x + dx * c - dy * s, y + dx * s + dy * c, dz)


# ----------------------------------------------------------------------------- geometry helpers
def outline_ellipse(a, b, n=96):
    pts, nrm = [], []
    for i in range(n):
        t = 2 * math.pi * i / n
        pts.append(Vector((a * math.cos(t), b * math.sin(t), 0)))
        nrm.append(Vector((math.cos(t) / a, math.sin(t) / b, 0)).normalized())
    return pts, nrm


def outline_halfmoon(R, n=72):
    pts, nrm = [], []
    for i in range(n + 1):
        t = math.pi * i / n
        pts.append(Vector((R * math.cos(t), R * math.sin(t), 0)))
        nrm.append(Vector((math.cos(t), math.sin(t), 0)))
    return pts, nrm


def loft(K, name, pts, nrm, profile, mat, T, rz, closed=True, lightmap=False, smooth=60, caps=False):
    """Sweep `profile` [(out, z), …] along a plan outline (pts with outward normals), in table space."""
    bm = bmesh.new()
    rings = []
    for p, n in zip(pts, nrm):
        rings.append([bm.verts.new(Vector(T(p.x + n.x * d, p.y + n.y * d, z))) for d, z in profile])
    m = len(rings)
    for i in range(m if closed else m - 1):
        r0, r1 = rings[i], rings[(i + 1) % m]
        for j in range(len(profile) - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    if caps and not closed:
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return K.obj(name, bm, mat, smooth_angle=smooth, lightmap=lightmap)


def felt_top(K, name, pts, mat, T, z, bbox):
    """Flat felt with UV0 = its plan bounding box (x0, y0, x1, y1) — the printed layout's frame."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    x0, y0, x1, y1 = bbox
    f = bm.faces.new([bm.verts.new(Vector(T(p.x, p.y, z))) for p in pts])
    for loop, p in zip(f.loops, pts):
        loop[uv].uv = ((p.x - x0) / (x1 - x0), (p.y - y0) / (y1 - y0))
    if f.normal.z < 0:
        f.normal_flip()
    # not lightmapped: a table-sized island gets too few texels (blotchy) — felt is lit live by the pendants
    return K.obj(name, bm, mat, uv=None)


RAIL = [(-0.012, -0.004), (-0.012, 0.028), (-0.004, 0.05), (0.018, 0.066), (0.05, 0.072), (0.082, 0.064), (0.105, 0.045),
        (0.118, 0.018), (0.118, -0.01), (0.1, -0.03)]      # padded leather armrest (in, up)
APRON = [(0.095, -0.03), (0.105, -0.06), (0.105, -0.16), (0.07, -0.19), (0.0, -0.2)]
BRASS_BAND = [(0.107, -0.075), (0.112, -0.078), (0.112, -0.09), (0.107, -0.093)]


def pedestal(A, loc, top_z, r=0.2):
    K, M = A.K, A.M
    K.lathe(K.name("TABLE", "Pedestal"), [(0, 0), (r + 0.26, 0), (r + 0.24, 0.05), (r + 0.06, 0.1), (r - 0.06, 0.16), (r - 0.1, 0.3),
                                           (r - 0.1, top_z - 0.3), (r - 0.04, top_z - 0.2), (r + 0.06, top_z - 0.12), (0, top_z - 0.12)],
            loc, M["walnut_dark"], segments=40, lightmap=False)
    K.lathe(K.name("TABLE", "PedestalFoot"), [(r + 0.235, 0.0), (r + 0.265, 0.0), (r + 0.265, 0.022), (r + 0.235, 0.022)], loc, M["brass"], segments=40)


# ----------------------------------------------------------------------------- chips & cards
CHIP_R, CHIP_H = 0.0195, 0.0034
DENOMS = ("10", "25", "100", "500")


def chip_mesh(K, name, k, mat, seg=20):
    """A chip whose faces and edge map into the 2 × 2 chip atlas (the edge takes the rim band → stripes)."""
    cu, cv = (k % 2) * 0.5 + 0.25, 1 - ((k // 2) * 0.5 + 0.25)
    RU = 0.244
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    top, bot = [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        top.append(bm.verts.new((CHIP_R * math.cos(t), CHIP_R * math.sin(t), CHIP_H)))
        bot.append(bm.verts.new((CHIP_R * math.cos(t), CHIP_R * math.sin(t), 0)))
    ft = bm.faces.new(top)
    fb = bm.faces.new(list(reversed(bot)))
    for f, flip in ((ft, 1), (fb, -1)):
        for loop in f.loops:
            p = loop.vert.co
            loop[uv].uv = (cu + RU * p.x / CHIP_R, cv + RU * flip * p.y / CHIP_R)
    for i in range(seg):
        j = (i + 1) % seg
        f = bm.faces.new((bot[i], bot[j], top[j], top[i]))
        for loop, (t, r) in zip(f.loops, ((i, 0.235), (j + (seg if j == 0 else 0), 0.235), (j + (seg if j == 0 else 0), RU), (i, RU))):
            a = 2 * math.pi * t / seg
            loop[uv].uv = (cu + r * math.cos(a), cv + r * math.sin(a))
    return K.obj(name, bm, mat, uv=None, smooth_angle=35)


def chip_protos(A):
    K = A.K
    P = A._dining
    if "chip_0" not in P:
        mat = casino_materials(A)["chips"]
        for k in range(4):
            P[f"chip_{k}"] = K.prototype(chip_mesh(K, K.name("PROP", f"Chip{DENOMS[k]}"), k, mat))
    return P


def chip_stack(A, loc, n, k, jitter=0.0012, seed=0):
    """A neat stack of n chips of denomination index k (instanced)."""
    K, P = A.K, chip_protos(A)
    for i in range(n):
        dx = math.sin(seed * 7.1 + i * 2.3) * jitter
        dy = math.cos(seed * 3.7 + i * 1.9) * jitter
        K.linked(K.name("PROP", f"Chip{DENOMS[k]}"), P[f"chip_{k}"], (loc[0] + dx, loc[1] + dy, loc[2] + i * CHIP_H), rot=(0, 0, (i * 0.9 + seed) % 6.28))


def chip_tray(A, T, rz, cx, cy, width=0.84, depth=0.16):
    """Dealer's walnut float tray: channels of chips lying in rows (their striped edges up)."""
    K, M = A.K, A.M
    P = chip_protos(A)
    K.box(K.name("TABLE", "ChipTray"), (width, depth, 0.03), T(cx, cy, FELT_Z + 0.004), M["walnut_dark"], bevel=0.008, rot=(0, 0, rz))
    K.box(K.name("TABLE", "ChipTrayLip"), (width + 0.02, 0.012, 0.022), T(cx, cy + depth / 2, FELT_Z + 0.02), M["brass"], rot=(0, 0, rz))
    rows = 10
    for r in range(rows):
        k = (3, 2, 1, 1, 0, 0, 1, 1, 2, 3)[r]
        x = cx - width / 2 + (r + 0.5) * width / rows
        n = 30 - (r * 7) % 11
        for i in range(n):
            y = cy - depth / 2 + 0.01 + i * CHIP_H * 1.02
            # a chip on edge: rotate so its axis runs along the channel (+Y)
            K.linked(K.name("PROP", f"Chip{DENOMS[k]}"), P[f"chip_{k}"], T(x, y, FELT_Z + 0.019), rot=(math.pi / 2, 0, rz))


def card_shoe(A, T, rz, x, y, facing, fz=FELT_Z):
    """Walnut card shoe with a brass face plate; the deck shows its ivory edges. `fz` = the felt height."""
    K, M = A.K, casino_materials(A)
    a = rz + facing
    K.box(K.name("TABLE", "Shoe"), (0.15, 0.32, 0.09), T(x, y, fz + 0.045), M["walnut_dark"], bevel=0.012, segments=2, rot=(0, 0, a))
    K.box(K.name("TABLE", "ShoeDeck"), (0.11, 0.24, 0.07), T(x, y, fz + 0.07), M["cardstock"], rot=(0.12, 0, a))
    c, s = math.cos(a), math.sin(a)
    fx, fy = T(x, y)[:2]
    K.box(K.name("TABLE", "ShoePlate"), (0.15, 0.012, 0.06), (fx - s * 0.16, fy + c * 0.16, fz + 0.04), M["brass"], rot=(0.35, 0, a))


# ============================================================================ tables

def poker_table(A, x, y, table_id, rz=0.0):
    """Oval Hold'em table; the guest sits at local −Y facing +Y, three house players around the far side."""
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    a, b = LAYOUT["PK"]["a"], LAYOUT["PK"]["b"]
    pts, nrm = outline_ellipse(a, b)
    felt_top(K, K.name("TABLE", "PokerFelt"), pts, felt(A, "poker"), T, FELT_Z, (-a, -b, a, b))
    loft(K, K.name("TABLE", "PokerRail"), pts, nrm, [(d, FELT_Z + z) for d, z in RAIL], M["leather"], T, rz)
    loft(K, K.name("TABLE", "PokerApron"), pts, nrm, [(d, FELT_Z + z) for d, z in APRON], M["walnut"], T, rz, lightmap=True)
    loft(K, K.name("TABLE", "PokerBand"), pts, nrm, [(d, FELT_Z + z) for d, z in BRASS_BAND], M["brass"], T, rz)
    for px in (-0.65, 0.65):
        pedestal(A, T(px, 0, 0), FELT_Z - 0.2)
    # chairs round the table (the guest's at −Y)
    for i in range(8):
        t = (i / 8) * 2 * math.pi + math.pi / 8 + math.pi / 8
        px, py = math.cos(t) * (a + 0.55), math.sin(t) * (b + 0.6)
        A.dining_chair(T(px, py), rz + math.atan2(px, -py), collide=False)   # local +Y → the table centre
    # house players' stacks, dealer button
    bots = [(-a + 0.38, 0.05, -math.pi / 2), (0.0, b - 0.3, math.pi), (a - 0.38, 0.05, math.pi / 2)]
    for i, (bx, by, face) in enumerate(bots):
        for j, k in enumerate((1, 2, 0)):
            chip_stack(A, T(bx + 0.06 * (j - 1), by + (0.12 if by < 0.5 else -0.12), FELT_Z), 6 + (i * 5 + j * 3) % 9, k, seed=i * 3 + j)
        anchor(A, table_id, "botCards", T(bx, by, FELT_Z + 0.001), rz + face, index=i, name=("Comtesse", "Baron", "Signor")[i])
    K.cyl(K.name("PROP", "DealerButton"), 0.028, 0.028, 0.008, T(0.42, -0.28, FELT_Z + 0.004), M["cardstock"], segments=24)
    for j, k in enumerate((1, 2, 0, 3)):
        chip_stack(A, T(-0.12 + j * 0.05, -b + 0.22, FELT_Z), 5 + j * 3, k, seed=20 + j)
    # presentation anchors
    anchor(A, table_id, "seat", T(0, -1.05, 1.65), rz)          # leaning in: hole cards, board and pot all in view
    anchor(A, table_id, "focus", T(0, -0.24, FELT_Z), rz)
    anchor(A, table_id, "playerCards", T(0, -b + 0.36, FELT_Z + 0.001), rz)
    anchor(A, table_id, "board", T(0, 0.04, FELT_Z + 0.001), rz)
    anchor(A, table_id, "pot", T(0, 0.3, FELT_Z), rz)
    anchor(A, table_id, "bet", T(0.2, -b + 0.36, FELT_Z), rz)
    anchor(A, table_id, "shoe", T(0.0, b - 0.15, FELT_Z + 0.05), rz)
    ha, hb = (a, b) if abs(math.sin(rz)) < 0.5 else (b, a)
    K.collider(f"Table_{K.idx('table')}", (x - ha - 0.1, y - hb - 0.1, 0), (x + ha + 0.1, y + hb + 0.1, 0.9))
    interact(A, table_id, "poker", (x, y, 0.55), (2 * a + 0.3, 2 * b + 0.3, 1.1), rz)


def blackjack_table(A, x, y, table_id, rz=0.0):
    """Half-moon table: dealer on the flat side (local −Y), players around the arc (+Y); the guest takes
    the centre spot."""
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    R = LAYOUT["BJ"]["R"]
    pts, nrm = outline_halfmoon(R)
    felt_top(K, K.name("TABLE", "BlackjackFelt"), pts, felt(A, "blackjack"), T, FELT_Z, (-R, -R, R, R))
    loft(K, K.name("TABLE", "BlackjackRail"), pts, nrm, [(d, FELT_Z + z) for d, z in RAIL], M["leather"], T, rz, closed=False, caps=True)
    loft(K, K.name("TABLE", "BlackjackApron"), pts, nrm, [(d, FELT_Z + z) for d, z in APRON], M["walnut"], T, rz, closed=False, lightmap=True)
    loft(K, K.name("TABLE", "BlackjackBand"), pts, nrm, [(d, FELT_Z + z) for d, z in BRASS_BAND], M["brass"], T, rz, closed=False)
    # dealer's edge: walnut bumper with a brass inlay, and the cabinet under it
    K.box(K.name("TABLE", "BlackjackEdge"), (2 * R + 0.24, 0.07, 0.07), T(0, -0.035, FELT_Z - 0.015), M["walnut"], bevel=0.012, segments=2, rot=(0, 0, rz), lightmap=True)
    K.box(K.name("TABLE", "BlackjackEdgeInlay"), (2 * R + 0.2, 0.006, 0.012), T(0, -0.071, FELT_Z - 0.01), M["brass"], rot=(0, 0, rz))
    K.box(K.name("TABLE", "BlackjackCabinet"), (2 * R - 0.2, 0.5, 0.58), T(0, 0.22, 0.33), M["walnut_dark"], bevel=0.015, rot=(0, 0, rz), lightmap=True)
    for px in (-0.6, 0.6):
        pedestal(A, T(px, 0.55, 0), FELT_Z - 0.2, r=0.16)
    spots = LAYOUT["BJ"]["spots"]
    for i, t in enumerate(spots):
        A.dining_chair(T(math.cos(t) * (R + 0.55), math.sin(t) * (R + 0.55)), rz + t - math.pi / 2 + math.pi, collide=False)
    chip_tray(A, T, rz, 0, 0.1)
    card_shoe(A, T, rz, 0.86, 0.26, 0.5)
    K.box(K.name("TABLE", "Discard"), (0.1, 0.14, 0.05), T(-0.86, 0.24, FELT_Z + 0.025), M["walnut_dark"], bevel=0.008, rot=(0, 0, rz - 0.5))
    # presentation anchors (card tops point to the dealer: local −Y → rz + π)
    face = rz + math.pi
    anchor(A, table_id, "seat", T(0, 1.45, 1.62), rz)            # over the rail, looking down ~45° at both hands
    anchor(A, table_id, "focus", T(0, 0.6, FELT_Z), rz)
    anchor(A, table_id, "bet", T(0, LAYOUT["BJ"]["spotR"], FELT_Z), face)
    anchor(A, table_id, "playerCards", T(0, 0.78, FELT_Z + 0.001), face)
    anchor(A, table_id, "dealerCards", T(0, 0.36, FELT_Z + 0.001), face)
    anchor(A, table_id, "shoe", T(0.86, 0.26, FELT_Z + 0.06), face)
    anchor(A, table_id, "discard", T(-0.86, 0.24, FELT_Z + 0.05), face)
    anchor(A, table_id, "chipTray", T(0, 0.1, FELT_Z + 0.03), face)
    a_, b_ = T(-R - 0.1, -0.2)[:2], T(R + 0.1, R + 0.1)[:2]
    K.collider(f"Table_{K.idx('table')}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), 0.9))
    interact(A, table_id, "blackjack", T(0, R / 2, 0.55), (2 * R + 0.3, R + 0.5, 1.1), rz)


def baccarat_table(A, x, y, table_id, rz=0.0):
    """Grand oval punto-banco table; the croupier stands at local −Y, the guest sits at +Y centre."""
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    a, b = LAYOUT["BC"]["a"], LAYOUT["BC"]["b"]
    pts, nrm = outline_ellipse(a, b, 120)
    felt_top(K, K.name("TABLE", "BaccaratFelt"), pts, felt(A, "baccarat"), T, FELT_Z, (-a, -b, a, b))
    loft(K, K.name("TABLE", "BaccaratRail"), pts, nrm, [(d, FELT_Z + z) for d, z in RAIL], M["leather"], T, rz)
    loft(K, K.name("TABLE", "BaccaratApron"), pts, nrm, [(d, FELT_Z + z) for d, z in APRON], M["walnut"], T, rz, lightmap=True)
    loft(K, K.name("TABLE", "BaccaratBand"), pts, nrm, [(d, FELT_Z + z) for d, z in BRASS_BAND], M["brass"], T, rz)
    for lx in (-0.95, 0.95):
        pedestal(A, T(lx, 0, 0), FELT_Z - 0.2, r=0.22)
    for i in range(12):
        t = (i / 12) * 2 * math.pi + math.pi / 12
        if math.sin(t) < -0.9:
            continue  # croupier's place
        px, py = math.cos(t) * (a + 0.52), math.sin(t) * (b + 0.6)
        A.dining_chair(T(px, py), rz + math.atan2(px, -py), collide=False)   # local +Y → the table centre
    chip_tray(A, T, rz, 0, -b + 0.2, width=0.9)
    card_shoe(A, T, rz, 0.95, -0.58, -0.4)
    face = rz + math.pi
    anchor(A, table_id, "seat", T(0, 0.9, 1.78), rz)             # leaning over the rail: the coup and your bet both in view
    anchor(A, table_id, "focus", T(0, 0.1, FELT_Z), rz)
    anchor(A, table_id, "playerCards", T(-0.3, -0.2, FELT_Z + 0.001), face)
    anchor(A, table_id, "bankerCards", T(0.3, -0.2, FELT_Z + 0.001), face)
    for side, yy in (("banker", 0.62), ("player", 0.44), ("tie", 0.3)):
        anchor(A, table_id, "bet", T(0.34, yy, FELT_Z), face, index=("banker", "player", "tie").index(side), side=side)
    anchor(A, table_id, "shoe", T(0.95, -0.58, FELT_Z + 0.06), face)
    anchor(A, table_id, "chipTray", T(0, -b + 0.2, FELT_Z + 0.03), face)
    K.collider(f"Table_{K.idx('table')}", (x - a - 0.1, y - b - 0.1, 0), (x + a + 0.1, y + b + 0.1, 0.9))
    interact(A, table_id, "baccarat", (x, y, 0.55), (2 * a + 0.3, 2 * b + 0.3, 1.1), rz)


def stanchions(A, cx, cy, rx, ry, count, gap=(3, 4)):
    """Brass stanchions on an ellipse joined by sagging velvet ropes (curve tubes)."""
    K, M = A.K, A.M
    post = A._dining.get("stanchion")
    if post is None:
        post = A._dining["stanchion"] = K.prototype(K.lathe(K.name("PROP", "Stanchion"), [(0, 0), (0.16, 0), (0.15, 0.03), (0.04, 0.06), (0.025, 0.1), (0.025, 0.9), (0.04, 0.93), (0.035, 0.98), (0, 1.0)], (0, 0, -30), M["brass"], segments=16))
    pts = [(cx + rx * math.cos(2 * math.pi * i / count), cy + ry * math.sin(2 * math.pi * i / count)) for i in range(count)]
    for i, (px, py) in enumerate(pts):
        if i in gap:
            continue
        K.linked(K.name("PROP", "Stanchion"), post, (px, py, 0))
        j = (i + 1) % count
        if j in gap:
            continue
        nx, ny = pts[j]
        mid = ((px + nx) / 2, (py + ny) / 2, 0.72)
        K.tube(K.name("PROP", "VelvetRope"), [Vector((px, py, 0.9)), Vector(mid), Vector((nx, ny, 0.9))], 0.018, M["velvet"])


# ============================================================================ roulette

def roulette_table(A, x, y, table_id, index, rz=0.0):
    """Cabinet with the printed layout along local +X and the wheel at the −X end; players sit along +Y.
    The rotor is one node `PROP_<Zone>_Rotor_NN` with extras {rotor: tableId} (spun at runtime); the wheel
    anchor carries the ball-track geometry and the pocket order for the ball animation."""
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    L, W = 3.2, 1.35
    RL = LAYOUT["RL"]
    if "wheeltop" not in M:
        K.material("wheeltop", f"MAT_{K.zone}_WheelTop", (1, 1, 1), 0.28, coat=0.8, coat_rough=0.08, base_tex=os.path.join(GAMES, "T_WheelTop_BaseColor.png"))
    # cabinet: walnut top with an apron, padded rail, plinth
    K.box(K.name("TABLE", "RouletteTop"), (L, W, 0.08), T(0.2, 0, FELT_Z - 0.01), M["walnut"], bevel=0.02, segments=3, rot=(0, 0, rz), lightmap=True)
    K.box(K.name("TABLE", "RouletteBody"), (L - 0.3, W - 0.35, 0.6), T(0.2, 0, 0.36), M["walnut_dark"], bevel=0.02, rot=(0, 0, rz), lightmap=True)
    K.box(K.name("TABLE", "RoulettePlinth"), (L - 0.2, W - 0.25, 0.06), T(0.2, 0, 0.03), M["walnut_dark"], bevel=0.01, rot=(0, 0, rz))
    K.box(K.name("TABLE", "RouletteBand"), (L - 0.28, W - 0.33, 0.014), T(0.2, 0, 0.64), M["brass"], rot=(0, 0, rz))
    rect = [Vector(p) for p in ((-L / 2 + 0.2, -W / 2, 0), (L / 2 + 0.2, -W / 2, 0), (L / 2 + 0.2, W / 2, 0), (-L / 2 + 0.2, W / 2, 0))]
    rpts, rnrm = [], []
    for i in range(4):   # rounded-corner outline for the rail
        c0 = rect[i]
        cx_ = c0.x - math.copysign(0.12, c0.x - 0.2)
        cy_ = c0.y - math.copysign(0.12, c0.y)
        a0 = math.atan2(c0.y - cy_, c0.x - cx_) - math.pi / 4
        for k in range(7):
            t = a0 + (math.pi / 2) * k / 6
            rpts.append(Vector((cx_ + 0.12 * math.cos(t), cy_ + 0.12 * math.sin(t), 0)))
            rnrm.append(Vector((math.cos(t), math.sin(t), 0)))
    loft(K, K.name("TABLE", "RouletteRail"), rpts, rnrm, [(d - 0.1, FELT_Z + 0.03 + z) for d, z in RAIL], M["leather"], T, rz)
    # printed layout
    fx = 0.75
    lw, lh = RL["w"], RL["h"]
    felt_top(K, K.name("TABLE", "RouletteFelt"), [Vector((fx - lw / 2, -lh / 2, 0)), Vector((fx + lw / 2, -lh / 2, 0)), Vector((fx + lw / 2, lh / 2, 0)), Vector((fx - lw / 2, lh / 2, 0))],
             felt(A, "roulette"), lambda px, py, pz=0.0: T(px, py, pz), FELT_Z + 0.032, (fx - lw / 2, -lh / 2, fx + lw / 2, lh / 2))
    boxes = LAYOUT["rouletteBoxes"]
    anchor(A, table_id, "layout", T(fx, 0, FELT_Z + 0.033), rz,
           numbers=[boxes["numbers"][str(n)] for n in range(37)], dozens=boxes["dozens"],
           outside=[boxes["outside"][k] for k in ("low", "even", "red", "black", "odd", "high")], outsideKeys=["low", "even", "red", "black", "odd", "high"])
    # wheel: bowl with a polished ball track and brass deflectors
    wx = 0.2 - L / 2 + 0.58
    cz = FELT_Z + 0.045
    K.lathe(K.name("TABLE", "RouletteBowl"), [(0, 0), (0.6, 0), (0.62, 0.05), (0.62, 0.15), (0.6, 0.17), (0.56, 0.165), (0.5, 0.125), (0.47, 0.11), (0.455, 0.07), (0, 0.07)],
            T(wx, 0, FELT_Z - 0.03), M["walnut"], segments=96)
    K.torus(K.name("TABLE", "RouletteBowlRim"), 0.61, 0.016, T(wx, 0, FELT_Z + 0.14), M["gilt"], major=96, minor=8)
    for k in range(8):
        t = k * math.pi / 4 + math.pi / 8
        K.box(K.name("PROP", "RouletteDeflector"), (0.022, 0.012, 0.012), T(wx + 0.52 * math.cos(t), 0.52 * math.sin(t), FELT_Z + 0.108), M["brass"], rot=(0, 0.35, rz + t))
    center = Vector(T(wx, 0, cz))
    rotor = K.lathe(f"PROP_{K.zone}_Rotor_{index:02d}", [(0, 0.1), (0.1, 0.075), (0.29, 0.03), (0.3, 0.01), (0, 0.01)], tuple(center), M["walnut"], segments=64)
    # textured pocket + number ring (UV0 = plan disc of radius 0.45)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    seg = 111
    rings = [(0.3, 0.004), (0.4, 0.004), (0.45, 0.012)]
    vs = [[bm.verts.new(center + Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)] for r, z in rings]
    for a_, b_ in zip(vs, vs[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            f = bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
            for loop in f.loops:
                p = loop.vert.co - center
                loop[uv].uv = (0.5 + p.x / 0.9, 0.5 + p.y / 0.9)
    parts = [K.obj(K.name("PROP", "RotorTop"), bm, M["wheeltop"], uv=None)]
    for i in range(37):   # brass frets between pockets
        t = 2 * math.pi * i / 37
        parts.append(K.box(K.name("PROP", "RotorFret"), (0.1, 0.004, 0.018), tuple(center + Vector((0.35 * math.cos(t), 0.35 * math.sin(t), 0.012))), M["brass"], rot=(0, 0, t)))
    parts.append(K.lathe(K.name("PROP", "RotorTurret"), [(0, 0), (0.05, 0), (0.03, 0.05), (0.012, 0.11), (0.028, 0.13), (0.02, 0.15), (0, 0.16)], tuple(center + Vector((0, 0, 0.1))), M["gilt"], segments=24))
    for k in range(4):
        t = k * math.pi / 2
        parts.append(K.lathe(K.name("PROP", "RotorSpoke"), [(0, 0), (0.008, 0), (0.008, 0.2), (0, 0.2)], tuple(center + Vector((0, 0, 0.19))), M["gilt"], segments=8, rot=(0, math.pi / 2, t)))
        parts.append(K.box(K.name("PROP", "RotorKnob"), (0.018, 0.018, 0.018), tuple(center + Vector((0.2 * math.cos(t), 0.2 * math.sin(t), 0.19))), M["gilt"], bevel=0.006))
    K.join_into(rotor, parts)
    rotor["rotor"] = table_id
    anchor(A, table_id, "wheel", tuple(center), rz, trackRadius=0.52, trackZ=0.075, pocketRadius=0.352, pocketZ=0.012, order=WHEEL_ORDER)
    for i in range(4):
        A.dining_chair(T(-0.2 + i * 0.62, W / 2 + 0.55), rz + math.pi, collide=False)
    # roulette is played standing at the rail: a higher, closer view over layout and wheel
    anchor(A, table_id, "seat", T(-0.05, 0.62, 3.0), rz)         # near top-down: the whole layout + the spinning wheel
    anchor(A, table_id, "focus", T(-0.05, 0.02, FELT_Z), rz)
    anchor(A, table_id, "chipTray", T(wx + 0.1, -0.5, FELT_Z + 0.05), rz)
    a_, b_ = T(0.2 - L / 2 - 0.05, -W / 2 - 0.05)[:2], T(0.2 + L / 2 + 0.05, W / 2 + 0.05)[:2]
    K.collider(f"Table_{K.idx('table')}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), 0.95))
    interact(A, table_id, "roulette", T(0.2, 0, 0.55), (L + 0.3, W + 0.3, 1.1), rz)


# ============================================================================ slot machines

SLOT = {}
REEL_R, REEL_W, REEL_Z, REEL_Y = 0.115, 0.125, 1.34, 0.02
REEL_X = (0.145, 0.0, -0.145)     # reel 1, 2, 3 from the PLAYER's left (local −X is their right hand)


def slot_protos(A):
    """Art-deco cabinet parts, built once per zone as prototypes (every machine is instanced)."""
    K, M = A.K, A.M
    if SLOT:
        return SLOT
    casino_materials(A)
    if "glass" not in M:
        K.material("glass", f"MAT_{K.zone}_Glass", (0.02, 0.02, 0.025), 0.03, coat=1, coat_rough=0.01, alpha=0.12)
        K.material("lights", "MAT_Slots_Lights", (0, 0, 0), 0.4, emis_color=(1.0, 0.7, 0.25), emis_strength=6)
        K.material("marquee", f"MAT_{K.zone}_SlotMarquee", (0.05, 0.02, 0.02), 0.3, emis_tex=os.path.join(GAMES, "T_SlotMarquee_Emissive.png"), emis_strength=1.3)
        K.material("payglass", f"MAT_{K.zone}_SlotPayGlass", (0.02, 0.01, 0.01), 0.15, coat=1, coat_rough=0.02, emis_tex=os.path.join(GAMES, "T_SlotPayGlass_Emissive.png"), emis_strength=0.55)
        K.material("chrome", f"MAT_{K.zone}_Chrome", (0.85, 0.85, 0.86), 0.12, metal=1)
        K.material("knob", f"MAT_{K.zone}_LeverKnob", (0.5, 0.02, 0.03), 0.18, coat=1, coat_rough=0.05)
        K.material("reel_lamp", f"MAT_{K.zone}_ReelLamp", (0, 0, 0), 0.5, emis_color=(1, 0.86, 0.62), emis_strength=4)
    P = SLOT

    def proto(key, ob):
        P[key] = K.prototype(ob)

    def textured_quad(name, w, h, mat):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.verify()
        f = bm.faces.new([bm.verts.new((x, 0, z)) for x, z in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))])
        for loop, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = c
        if f.normal.y > 0:
            f.normal_flip()   # faces −Y in the mesh; rotated to face the player (+Y) below
        ob = K.obj(name, bm, mat, uv=None)
        ob.data.transform(Matrix.Rotation(math.pi, 4, "Z"))
        return ob

    # lower cabinet with a rounded front, brass kick plate, belly door + back-lit pay glass
    proto("base", K.box(K.name("SLOT", "MachineBase"), (0.66, 0.56, 0.9), (0, 0, -30), M["walnut_dark"], bevel=0.03, segments=4))
    proto("kick", K.box(K.name("SLOT", "MachineKick"), (0.62, 0.02, 0.08), (0, 0, -30), M["brass"], bevel=0.004))
    proto("belly", K.box(K.name("SLOT", "MachineBelly"), (0.54, 0.02, 0.44), (0, 0, -30), M["walnut"], bevel=0.01, segments=2))
    proto("payglass", textured_quad(K.name("SLOT", "MachinePayGlass"), 0.46, 0.23, M["payglass"]))
    frame = [K.box(K.name("SLOT", "MachinePayFrame"), s_, (d[0], d[1], -30 + d[2]), M["chrome"], bevel=0.003)
             for s_, d in (((0.5, 0.015, 0.02), (0, 0, 0.125)), ((0.5, 0.015, 0.02), (0, 0, -0.125)), ((0.02, 0.015, 0.25), (-0.24, 0, 0)), ((0.02, 0.015, 0.25), (0.24, 0, 0)))]
    K.join_into(frame[0], frame[1:])
    frame[0].data.transform(Matrix.Translation((0, 0, 0.125)))   # re-centre on the join target's offset
    frame[0].location.z = -30
    proto("payframe", frame[0])
    # button deck (sloped), coin slot, buttons, coin tray
    proto("deck", K.box(K.name("SLOT", "MachineDeck"), (0.66, 0.24, 0.05), (0, 0, -30), M["leather"], bevel=0.012, segments=2))
    proto("button", K.cyl(K.name("SLOT", "MachineButton"), 0.02, 0.02, 0.014, (0, 0, -30), M["lights"], segments=16))
    proto("coinplate", K.box(K.name("SLOT", "MachineCoinPlate"), (0.07, 0.05, 0.006), (0, 0, -30), M["brass"], bevel=0.003))
    proto("tray", K.box(K.name("SLOT", "MachineTray"), (0.4, 0.12, 0.05), (0, 0, -30), M["chrome"], bevel=0.01, segments=2))
    # upper cabinet with the reel window (black lacquer shadow box, chrome bezel, glass, lamp strip)
    # upper cabinet = a frame round the reel window: back block, side cheeks, pieces above and below
    #   (local to the cabinet centre at y = -0.06, z = 1.33; window 0.47 × 0.29 at z = REEL_Z)
    wz = REEL_Z - 1.33
    pieces = [((0.64, 0.2, 0.74), (0, -0.12, 0)), ((0.085, 0.24, 0.74), (-0.2775, 0.1, 0)), ((0.085, 0.24, 0.74), (0.2775, 0.1, 0)),
              ((0.47, 0.24, 0.37 + wz - 0.145), (0, 0.1, (-0.37 + wz - 0.145) / 2)), ((0.47, 0.24, 0.37 - wz - 0.145), (0, 0.1, (0.37 + wz + 0.145) / 2))]
    cab = [K.box(K.name("SLOT", "MachineCabinet"), size, (d[0], d[1], -30 + d[2]), M["walnut"], bevel=0.012, segments=2) for size, d in pieces]
    K.join_into(cab[0], cab[1:])
    cab[0].data.transform(Matrix.Translation((0, -0.12, 0)))
    cab[0].location.y = 0
    proto("cabinet", cab[0])
    # open-fronted black lacquer shadow box the reels turn in
    bm = kit.cube_bm(0.466, 0.234, 0.286)   # a hair inside the cabinet frame (no coplanar faces)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.y > 0.5], context="FACES")
    bmesh.ops.reverse_faces(bm, faces=bm.faces)   # seen from inside
    proto("reelbox", K.obj(K.name("SLOT", "MachineReelBox"), bm, M["lacquer_black"], loc=(0, 0, -30)))
    bez = [K.box(K.name("SLOT", "MachineBezel"), s_, (d[0], d[1], -30 + d[2]), M["chrome"], bevel=0.006, segments=2)
           for s_, d in (((0.53, 0.03, 0.035), (0, 0, 0.16)), ((0.53, 0.03, 0.035), (0, 0, -0.16)), ((0.035, 0.03, 0.29), (-0.25, 0, 0)), ((0.035, 0.03, 0.29), (0.25, 0, 0)))]
    K.join_into(bez[0], bez[1:])
    bez[0].data.transform(Matrix.Translation((0, 0, 0.16)))
    bez[0].location.z = -30
    proto("bezel", bez[0])
    proto("glass", K.box(K.name("SLOT", "MachineGlass"), (0.47, 0.004, 0.29), (0, 0, -30), M["glass"]))
    proto("lamp", K.box(K.name("SLOT", "MachineReelLamp"), (0.44, 0.012, 0.01), (0, 0, -30), M["reel_lamp"]))
    # topper: back-lit marquee under a gilt arch lined with bulbs
    proto("topbox", K.box(K.name("SLOT", "MachineTopBox"), (0.64, 0.3, 0.3), (0, 0, -30), M["walnut_dark"], bevel=0.025, segments=3))
    proto("marquee", textured_quad(K.name("SLOT", "MachineMarquee"), 0.54, 0.27, M["marquee"]))
    proto("arch", K.torus(K.name("SLOT", "MachineArch"), 0.3, 0.018, (0, 0, -30), M["gilt"], major=40, minor=8, arc=math.pi, rot=(math.pi / 2, 0, 0)))
    proto("bulb", K.cyl(K.name("SLOT", "MachineBulb"), 0.012, 0.012, 0.014, (0, 0, -30), M["lights"], segments=10, rot=(math.pi / 2, 0, 0)))
    # lever
    proto("hub", K.cyl(K.name("SLOT", "MachineLeverHub"), 0.045, 0.045, 0.05, (0, 0, -30), M["chrome"], segments=24, rot=(0, math.pi / 2, 0)))
    proto("lever", K.cyl(K.name("SLOT", "MachineLever"), 0.011, 0.011, 0.36, (0, 0, -30), M["chrome"], segments=10))
    proto("knob", K.lathe(K.name("SLOT", "MachineKnob"), [(0, 0), (0.028, 0.004), (0.036, 0.03), (0.03, 0.058), (0, 0.064)], (0, 0, -30), M["knob"], segments=20))
    # stool
    proto("stool", K.cyl(K.name("SLOT", "Stool"), 0.2, 0.2, 0.1, (0, 0, -30), M["velvet"], segments=24, subsurf=1))
    proto("stoolstem", K.lathe(K.name("SLOT", "StoolStem"), [(0, 0), (0.2, 0), (0.18, 0.03), (0.04, 0.08), (0.03, 0.6), (0, 0.6)], (0, 0, -30), M["brass"], segments=20))
    return P


def slot_machine(A, x, y, rz, table_id, stool=True):
    """An art-deco slot machine facing local +Y (the reels are runtime geometry on ANCHOR_ reel empties)."""
    K = A.K
    P = slot_protos(A)
    T = xf(x, y, rz)

    def link(key, d, rot=(0, 0, 0)):
        K.linked(K.name("SLOT", P[key].name.split("_")[2]), P[key], T(*d), rot=(rot[0], rot[1], rz + rot[2]))
    link("base", (0, 0, 0.45))
    link("kick", (0, 0.275, 0.06))
    link("belly", (0, 0.275, 0.52))
    link("payframe", (0, 0.287, 0.52))
    link("payglass", (0, 0.29, 0.52))
    link("deck", (0, 0.2, 0.93), rot=(-0.32, 0, 0))
    for bx in (-0.12, 0.0, 0.12):
        link("button", (bx, 0.27, 0.955), rot=(-0.32, 0, 0))
    link("coinplate", (0.24, 0.24, 0.96), rot=(-0.32, 0, 0))
    link("tray", (0, 0.29, 0.83))
    link("cabinet", (0, -0.06, 1.33))
    link("reelbox", (0, 0.042, REEL_Z))
    link("bezel", (0, 0.17, REEL_Z))
    link("glass", (0, 0.165, REEL_Z))
    link("lamp", (0, 0.14, REEL_Z + 0.135))
    link("topbox", (0, -0.03, 1.85))
    link("marquee", (0, 0.125, 1.86))
    link("arch", (0, 0.13, 1.86))
    for k in range(13):
        t = math.pi * k / 12
        link("bulb", (0.3 * math.cos(t), 0.14, 1.86 + 0.3 * math.sin(t)))
    link("hub", (-0.345, -0.02, 1.18))          # on the player's right (local −X faces their right hand)
    link("lever", (-0.37, -0.02, 1.36))
    link("knob", (-0.37, -0.02, 1.54))
    if stool:
        link("stool", (0, 0.95, 0.66))
        link("stoolstem", (0, 0.95, 0))
    for i, rx in enumerate(REEL_X):
        anchor(A, table_id, "reel", T(rx, REEL_Y, REEL_Z), rz, index=i, radius=REEL_R, width=REEL_W)
    anchor(A, table_id, "seat", T(0, 0.9, 1.3), rz)
    anchor(A, table_id, "focus", T(0, 0.05, REEL_Z - 0.04), rz)
    a_, b_ = T(-0.36, -0.32)[:2], T(0.36, 0.34)[:2]
    K.collider(f"Slot_{K.idx('slot')}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), 2.1))
    interact(A, table_id, "slots", T(0, 0.02, 1.0), (0.7, 0.7, 2.0), rz)


# ============================================================================ Kraffing Casino Pack V1
# Licensed game-ready models (blender/props/kraffing/, git-ignored source). Each is imported once per zone as
# an instanced prototype (kit.import_pack), scaled to real size and turned to our player-side convention;
# the anchors below are calibrated to the pack's printed felts, measured on orthographic top renders of the
# original models (pack metres; px → m noted per table). The pack's bar stools, loose coins and cards are
# dropped: guests sit on our red velvet tub chairs and the runtime deals real cards and chips.

KRAFFING = os.path.join(kit.ROOT, "blender", "props", "kraffing")
PACK_SCALE = 0.86                 # the pack is ~16 % oversize: felts at 0.89–0.92 m → a real ~0.77–0.79 m


def pack_proto(A, name, key, pick, rz=0.0, scale=PACK_SCALE):
    if key not in A._props:
        A._props[key] = A.K.import_pack(os.path.join(KRAFFING, f"{name}.glb"), key, pick=pick, scale=scale, rz=rz)
    return A._props[key]


def _face(rz_local, flip):
    """Pack → proto-local: the proto was turned by π when `flip` (player side −Y → +Y) and scaled."""
    s = PACK_SCALE
    return (lambda px, py: (-px * s, -py * s)) if flip else (lambda px, py: (px * s, py * s))


def _facing(cx, cy, tx, ty):
    """Local rotation that points a chair's (or anchor's) local +Y from (cx, cy) at (tx, ty)."""
    return math.atan2(-(tx - cx), ty - cy)


def _aabb_collider(K, T, lo, hi, top, tag="Table"):
    a_, b_ = T(*lo)[:2], T(*hi)[:2]
    K.collider(f"{tag}_{K.idx(tag.lower())}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), top))


def kr_blackjack_table(A, x, y, table_id, rz=0.0):
    """Kraffing Blackjack_Table_1: dealer + chip rack on the flat side (proto −Y), five boxes on the arc (+Y);
    the guest takes the centre box. Top render: 0.0022833 m/px, centre (0, −0.084) at px (800, 500)."""
    K = A.K
    proto = pack_proto(A, "Blackjack_Table_1", "KrBlackjack", ["Blackjack_Table_1_1"], rz=math.pi)
    K.linked(K.name("TABLE", "KrBlackjack"), proto, (x, y, 0), rot=(0, 0, rz))
    T, P = xf(x, y, rz), _face(0, True)
    px = lambda u, v: P((u - 800) * 0.0022833, -0.084 - (v - 500) * 0.0022833)   # noqa: E731
    fz = 0.9202 * PACK_SCALE
    # tub chairs behind the five printed boxes, on rays from the arc's centre (pack (0, 0.263), rail R 1.43)
    cx0, cy0 = P(0, 0.263)
    for u, v in ((463, 675), (628, 750), (805, 765), (980, 750), (1145, 675)):
        bx, by = px(u, v)
        d = math.hypot(bx - cx0, by - cy0)
        r = 1.43 * PACK_SCALE + 0.5
        chx, chy = cx0 + (bx - cx0) / d * r, cy0 + (by - cy0) / d * r
        A.dining_chair(T(chx, chy), rz + _facing(chx, chy, cx0, cy0), collide=False)
    sx, sy = px(420, 300)
    card_shoe(A, T, rz, -sx, sy, 0.5, fz=fz)
    face = rz + math.pi                                                  # card tops toward the dealer
    anchor(A, table_id, "seat", T(0, 1.5, 1.72), rz)                   # back over the rail: your box and the dealer's cards
    anchor(A, table_id, "focus", T(0, 0.3, fz), rz)
    anchor(A, table_id, "bet", T(*px(805, 850), fz), face)
    anchor(A, table_id, "playerCards", T(*px(805, 770), fz + 0.001), face)
    anchor(A, table_id, "dealerCards", T(*px(805, 330), fz + 0.001), face)
    anchor(A, table_id, "shoe", T(-sx, sy, fz + 0.06), face)
    anchor(A, table_id, "discard", T(sx, sy, fz + 0.05), face)
    anchor(A, table_id, "chipTray", T(*px(805, 140), fz + 0.03), face)
    _aabb_collider(K, T, P(-1.45, -1.2), P(1.45, 1.04), 0.95)
    interact(A, table_id, "blackjack", T(0, 0.1, 0.55), (2.6, 2.1, 1.1), rz)


# seat labels printed round the poker felt (px): 1, 2, 3, crown, 5, 6, 7, 8, 9, 10
PK_SEATS = ((1210, 325), (1340, 440), (1300, 620), (1150, 712), (930, 700), (678, 700), (452, 700), (300, 600), (275, 440), (400, 322))


def kr_poker_table(A, x, y, table_id, rz=0.0):
    """Kraffing Poker_Table_1: dealer + chip rack at proto +Y, ten numbered seats; the guest has seat 5
    (proto −Y), the house players 9, 2 and 7. Top render: 0.0023511 m/px, centre (−0.0044, −0.0001)."""
    K = A.K
    proto = pack_proto(A, "Poker_Table_1", "KrPoker", ["Poker_Table_1_1"])
    K.linked(K.name("TABLE", "KrPoker"), proto, (x, y, 0), rot=(0, 0, rz))
    T, P = xf(x, y, rz), _face(0, False)
    px = lambda u, v: P(-0.0044 + (u - 800) * 0.0023511, -0.0001 - (v - 500) * 0.0023511)   # noqa: E731
    fz = 0.8943 * PACK_SCALE
    a, b = 1.85 * PACK_SCALE, 1.07 * PACK_SCALE
    for u, v in PK_SEATS:
        sx, sy = px(u, v)
        t = math.atan2(sy / b, sx / a)
        chx, chy = (a + 0.42) * math.cos(t), (b + 0.46) * math.sin(t)
        A.dining_chair(T(chx, chy), rz + _facing(chx, chy, 0, 0), collide=False)
    # house players: cards and stacks at seats 9, 2 and 7, tops toward the table centre
    for i, (u, v) in enumerate((PK_SEATS[8], PK_SEATS[1], PK_SEATS[6])):
        bx, by = px(u, v)
        bx, by = bx * 0.8, by * 0.8                                   # in from the rail, onto the felt
        f = _facing(bx, by, 0, 0)
        for j, k in enumerate((1, 2, 0)):
            ox, oy = -math.sin(f) * -0.1 + math.cos(f) * 0.06 * (j - 1), math.cos(f) * -0.1 + math.sin(f) * 0.06 * (j - 1)
            chip_stack(A, T(bx + ox, by + oy, fz), 6 + (i * 5 + j * 3) % 9, k, seed=i * 3 + j)
        anchor(A, table_id, "botCards", T(bx, by, fz + 0.001), rz + f, index=i, name=("Comtesse", "Baron", "Signor")[i])
    gx, gy = px(930, 700)
    for j, k in enumerate((1, 2, 0, 3)):
        chip_stack(A, T(gx - 0.2 + j * 0.05, gy - 0.12, fz), 5 + j * 3, k, seed=20 + j)
    K.cyl(K.name("PROP", "DealerButton"), 0.028, 0.028, 0.008, T(gx + 0.22, gy + 0.1, fz + 0.004), casino_materials(A)["cardstock"], segments=24)
    shx, shy = px(1040, 250)
    card_shoe(A, T, rz, shx, shy, math.pi, fz=fz)
    anchor(A, table_id, "seat", T(gx * 0.85, -1.2, 1.75), rz)
    anchor(A, table_id, "focus", T(gx * 0.45, -0.1, fz), rz)
    anchor(A, table_id, "playerCards", T(gx, gy + 0.03, fz + 0.001), rz)
    anchor(A, table_id, "bet", T(gx, gy + 0.22, fz), rz)
    anchor(A, table_id, "board", T(*px(805, 505), fz + 0.001), rz, spacing=0.176 * PACK_SCALE)
    anchor(A, table_id, "pot", T(*px(805, 400), fz), rz)
    anchor(A, table_id, "shoe", T(shx, shy, fz + 0.05), rz)
    _aabb_collider(K, T, (-a - 0.05, -b - 0.05), (a + 0.05, b + 0.05), 0.95)
    interact(A, table_id, "poker", T(0, 0, 0.55), (2 * a + 0.3, 2 * b + 0.3, 1.1), rz)


# the pack wheel's pockets, counter-clockwise from 0 (its numbers run clockwise in the European order)
KR_WHEEL_CCW = [0, 26, 3, 35, 12, 28, 7, 29, 18, 22, 9, 31, 14, 20, 1, 33, 16, 24, 5, 10, 23, 8, 30, 11, 36,
                13, 27, 6, 34, 17, 25, 2, 21, 4, 19, 15, 32]


def kr_roulette_table(A, x, y, table_id, index, rz=0.0):
    """Kraffing Roulette_Table_1: its wheel is a separate node, spun as the rotor (a unique mesh per table so
    the build can't batch the four wheels into one instanced draw). The player stands at proto +Y; the
    printed layout drives click-to-bet and chip placement. Top render: 0.0025323 m/px, centre (0, −0.0156);
    wheel close-up: 0 pocket at 14.0° (pack frame), ball track r 0.43 m, pocket bed r 0.25 m."""
    K = A.K
    s = PACK_SCALE
    table = pack_proto(A, "Roulette_Table_1", "KrRoulette", ["Roulette_Table_1_1"], rz=math.pi)
    wheel = pack_proto(A, "Roulette_Table_1", "KrRouletteWheel", ["RLT_Asset"], rz=math.pi)
    K.linked(K.name("TABLE", "KrRoulette"), table, (x, y, 0), rot=(0, 0, rz))
    rotor = bpy_object_copy(K, f"PROP_{K.zone}_Rotor_{index:02d}", wheel, (x, y, 0), rz)
    rotor["rotor"] = table_id
    T, P = xf(x, y, rz), _face(0, True)
    ps = 0.0025323
    px = lambda u, v: P((u - 800) * ps, -0.0156 - (v - 500) * ps)   # noqa: E731
    fz = 0.8388 * s
    col_w, row_h = 802 / 12, 230 / 3
    numbers = [list(px(554, 512))]
    for v in range(1, 37):
        c, r = (v - 1) // 3, {0: 0, 2: 1, 1: 2}[v % 3]
        numbers.append(list(px(588 + (c + 0.5) * col_w, 397 + (r + 0.5) * row_h)))
    dozens = [list(px(588 + (d + 0.5) * 802 / 3, 666)) for d in range(3)]
    outside = [list(px(588 + (k + 0.5) * 802 / 6, 742)) for k in range(6)]
    half = lambda w, h: [w * ps * s, h * ps * s]   # noqa: E731
    anchor(A, table_id, "layout", T(0, 0, fz + 0.002), rz, numbers=numbers, dozens=dozens, outside=outside,
           outsideKeys=["low", "even", "red", "black", "odd", "high"],
           cell=half(col_w / 2, row_h / 2), zero=half(34, 115), dozen=half(802 / 6, 39), out=half(802 / 12, 38))
    wx, wy = P(-1.385, -0.43)
    offset = rz + math.radians(14.0) + math.pi - math.pi / 37      # pocket 0's centre, in the zone frame
    anchor(A, table_id, "wheel", T(wx, wy, 0.92 * s), rz, trackRadius=0.43 * s, trackZ=0.026 * s,
           pocketRadius=0.25 * s, pocketZ=0.006 * s, order=KR_WHEEL_CCW, offset=offset)
    for i in range(4):                                                  # standing guests' tub chairs along the layout
        cx_, cy_ = -1.25 + i * 0.6, 1.02 * s + 0.45
        A.dining_chair(T(cx_, cy_), rz + math.pi, collide=False)
    anchor(A, table_id, "seat", T(0.0, 0.55, 3.0), rz)                 # near top-down: layout + the spinning wheel
    anchor(A, table_id, "focus", T(0.0, 0.0, fz), rz)
    anchor(A, table_id, "chipTray", T(wx - 0.35, wy - 0.25, fz + 0.03), rz)
    _aabb_collider(K, T, P(-1.99, -1.04), P(1.99, 1.01), 0.95)
    interact(A, table_id, "roulette", T(0, 0, 0.55), (3.5, 1.9, 1.1), rz)


def bpy_object_copy(K, name, proto, loc, rz):
    """A single-user copy of a prototype (not a linked duplicate): nodes that move on their own at runtime."""
    import bpy
    ob = bpy.data.objects.new(name, proto.data.copy())
    ob.data.name = name
    ob.location, ob.rotation_euler = loc, (0, 0, rz)
    K.coll["VISUAL"].objects.link(ob)
    return ob


def kr_slot_machine(A, x, y, rz, table_id):
    """Kraffing Slot_Machine_1 facing proto +Y; its three reel drums are replaced by our runtime reels on
    ANCHOR_ reel empties at the same centres (pack reels: x −0.12/0/0.12, centre y −0.105, z 1.625, r 0.19)."""
    K = A.K
    s = PACK_SCALE
    proto = pack_proto(A, "Slot_Machine_1", "KrSlot", ["Slot_Machine_1_1", "Slot_Machine_1_Lever"], rz=math.pi)
    K.linked(K.name("SLOT", "KrSlot"), proto, (x, y, 0), rot=(0, 0, rz))
    T = xf(x, y, rz)
    P = slot_protos(A)
    K.linked(K.name("SLOT", "Stool"), P["stool"], T(0, 1.15, 0.66), rot=(0, 0, rz))
    K.linked(K.name("SLOT", "StoolStem"), P["stoolstem"], T(0, 1.15, 0), rot=(0, 0, rz))
    rz_ = 1.625 * s
    for i, rx in enumerate((0.12, 0.0, -0.12)):                        # reel 1 on the player's left (proto +X)
        anchor(A, table_id, "reel", T(rx * s, 0.105 * s, rz_), rz, index=i, radius=0.186 * s, width=0.078 * s)
    anchor(A, table_id, "seat", T(0, 1.55, rz_ + 0.12), rz)            # the whole cabinet, reels at eye level
    anchor(A, table_id, "focus", T(0, 0.09, rz_ - 0.03), rz)
    _aabb_collider(K, T, (-0.44, -0.44), (0.44, 0.52), 2.1, tag="Slot")
    interact(A, table_id, "slots", T(0, 0.05, 1.0), (0.85, 0.95, 2.0), rz)


def kr_decor(A, name, key, x, y, rz, pick=None, collide=None, scale=PACK_SCALE):
    """A non-playable pack piece (lucky-spin wheels, pool table, jukebox); `collide` = (half-x, half-y, h)."""
    K = A.K
    proto = pack_proto(A, name, key, pick, scale=scale)
    K.linked(K.name("PROP", key), proto, (x, y, 0), rot=(0, 0, rz))
    if collide:
        hx, hy, h = collide
        if abs(math.sin(rz)) > 0.7:
            hx, hy = hy, hx
        K.collider(f"{key}_{K.idx('c' + key)}", (x - hx, y - hy, 0), (x + hx, y + hy, h))
