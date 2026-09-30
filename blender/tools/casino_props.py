"""Game furniture for the Blender-authored rooms (Layer 1). Visual + the `INTERACT_` contract only:
every table/machine carries an invisible INTERACT_ volume with `casinoTable` extras
(src/interaction/schema.ts); rules live in src/games (§9).

Printing on felt is real geometry (flat Cinzel lettering), the roulette rotor is modelled pocket
by pocket and joined into one node the runtime spins, and slot reels are physical drums.
"""
import math

import bmesh
from mathutils import Matrix, Vector

import kit

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
PROMPTS = {"poker": "Play Texas Hold'em", "blackjack": "Play Blackjack", "baccarat": "Play Baccarat", "roulette": "Play Roulette", "slots": "Play the Slot"}


def casino_materials(A):
    K = A.K
    m = K.mat
    if "print" not in m:
        K.material("print", f"MAT_{K.zone}_FeltPrint", (0.78, 0.66, 0.4), 0.7)
        K.material("chip_red", f"MAT_{K.zone}_ChipRed", (0.5, 0.04, 0.04), 0.35, coat=0.6)
        K.material("chip_black", f"MAT_{K.zone}_ChipBlack", (0.02, 0.02, 0.02), 0.35, coat=0.6)
        K.material("chip_ivory", f"MAT_{K.zone}_ChipIvory", (0.85, 0.8, 0.68), 0.35, coat=0.6)
    return m


def interact(A, table_id, game, center, size, rz=0.0):
    """Invisible INTERACT_ volume with casinoTable extras (no material: never rendered)."""
    K = A.K
    pascal = "".join(p.capitalize() for p in table_id.split("_"))
    ob = K.obj(f"INTERACT_{K.zone}_{pascal}", kit.cube_bm(*size), None, coll="LOGIC", loc=center, rot=(0, 0, rz), uv=None)
    ob.display_type = "WIRE"
    ob.hide_render = True
    ob["interactable"] = True
    ob["interactionType"] = "casinoTable"
    ob["interactionPrompt"] = PROMPTS[game]
    ob["gameType"] = game
    ob["tableId"] = table_id
    return ob


def xf(x, y, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lambda dx, dy, dz=0.0: (x + dx * c - dy * s, y + dx * s + dy * c, dz)


def flat_text(A, text, loc, rz, size, mat=None):
    """Lettering lying flat on a surface (reads along local +X after rz; tops toward local +Y)."""
    K = A.K
    return K.text(K.name("PROP", "FeltPrint"), text, size, mat or K.mat["print"], extrude=0.0, loc=loc, rot=(0, 0, rz))


def arc_text(A, text, cx, cy, z, radius, a_mid, size, mat=None, spacing=0.72):
    """Characters placed one by one along an arc, tops toward the centre (read from outside the arc)."""
    step = size * spacing / radius
    a0 = a_mid - step * (len(text) - 1) / 2
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        a = a0 + step * i
        flat_text(A, ch, (cx + radius * math.cos(a), cy + radius * math.sin(a), z), a + math.pi / 2, size, mat)


def outline(A, center, w, h, rz, z, width=0.012):
    """Printed rectangular outline (betting box) lying flat on the felt."""
    K = A.K
    c, s = math.cos(rz), math.sin(rz)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append((center[0] + dx * c - dy * s, center[1] + dx * s + dy * c, z))
    return K.sweep(K.name("PROP", "FeltLine"), pts, (0, 0, 1), [(0, 0), (0, 0.001), (width, 0.001), (width, 0)], K.mat["print"], closed=True)


def ellipse_bm(rx, ry, depth, segments=72):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=1, radius2=1, depth=depth)
    for v in bm.verts:
        v.co.x *= rx
        v.co.y *= ry
    return bm


def chip_stack(A, loc, n, key):
    K = A.K
    proto = A._dining.get(f"chip_{key}")
    if proto is None:
        proto = A._dining[f"chip_{key}"] = K.prototype(K.cyl(K.name("PROP", "Chip"), 0.02, 0.02, 0.004, (0, 0, -30), K.mat[f"chip_{key}"], segments=16))
    for i in range(n):
        K.linked(K.name("PROP", "Chip"), proto, (loc[0] + (i % 3) * 0.0015, loc[1], loc[2] + 0.002 + i * 0.0042))


# ============================================================================ tables

def poker_table(A, x, y, table_id, rz=0.0):
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    sx, R = 1.75, 0.78
    K.obj(K.name("TABLE", "PokerFelt"), ellipse_bm(R * sx, R, 0.04), M["felt"], loc=T(0, 0, 0.78), rot=(0, 0, rz), smooth_angle=30)
    K.obj(K.name("TABLE", "PokerApron"), ellipse_bm((R + 0.05) * sx, R + 0.05, 0.16), M["walnut"], loc=T(0, 0, 0.68), rot=(0, 0, rz), bevel=0.02, segments=3)
    rail = K.torus(K.name("TABLE", "PokerRail"), R + 0.06, 0.07, T(0, 0, 0.8), M["leather"], major=96, minor=14)
    rail.scale = ((R * sx + 0.06) / (R + 0.06), 1, 1)
    rail.rotation_euler = (0, 0, rz)
    line = K.torus(K.name("TABLE", "PokerLine"), R - 0.14, 0.006, T(0, 0, 0.801), M["gilt"], major=96, minor=4)
    line.scale = ((R * sx - 0.14) / (R - 0.14), 1, 1)
    line.rotation_euler = (0, 0, rz)
    K.lathe(K.name("TABLE", "PokerBase"), [(0, 0), (0.55, 0), (0.5, 0.06), (0.22, 0.14), (0.18, 0.5), (0.3, 0.62), (0, 0.62)], T(0, 0, 0), M["walnut_dark"], segments=40)
    flat_text(A, "LE GRAND RIVIERA", T(0, 0.02, 0.8005), rz, 0.07)
    for i in range(8):
        a = (i / 8) * 2 * math.pi + math.pi / 8
        px, py = math.cos(a) * (R * sx + 0.55), math.sin(a) * (R + 0.58)
        A.dining_chair(T(px, py), rz + math.atan2(-px, -py) - math.pi, collide=False)
        chip_stack(A, T(math.cos(a) * R * sx * 0.72, math.sin(a) * R * 0.66, 0.8), 3 + i % 4, ("red", "black", "ivory")[i % 3])
    chip_stack(A, T(0.12, -0.05, 0.8), 9, "red")
    chip_stack(A, T(-0.1, -0.08, 0.8), 6, "black")
    K.collider(f"Table_{K.idx('table')}", (x - R * sx - 0.1, y - R - 0.1, 0), (x + R * sx + 0.1, y + R + 0.1, 0.9))
    interact(A, table_id, "poker", (x, y, 0.55), (2 * R * sx + 0.3, 2 * R + 0.3, 1.1), rz)


def blackjack_table(A, x, y, table_id, rz=0.0):
    """Half-moon table: flat dealer side toward local -Y, players around the arc (+Y)."""
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    R = 1.25
    # half-disc felt: fan of the upper half circle, extruded
    bm = bmesh.new()
    seg = 64
    ring = [bm.verts.new((R * math.cos(math.pi * i / seg), R * math.sin(math.pi * i / seg), 0)) for i in range(seg + 1)]
    face = bm.faces.new(ring)
    bmesh.ops.solidify(bm, geom=[face], thickness=0.04)
    K.obj(K.name("TABLE", "BlackjackFelt"), bm, M["felt"], loc=T(0, 0, 0.8), rot=(0, 0, rz), smooth_angle=30)
    bm = bmesh.new()
    ring = [bm.verts.new(((R + 0.03) * math.cos(math.pi * i / seg), (R + 0.03) * math.sin(math.pi * i / seg), 0)) for i in range(seg + 1)]
    face = bm.faces.new(ring)
    bmesh.ops.solidify(bm, geom=[face], thickness=0.16)
    K.obj(K.name("TABLE", "BlackjackApron"), bm, M["walnut"], loc=T(0, 0, 0.76), rot=(0, 0, rz), bevel=0.02)
    K.torus(K.name("TABLE", "BlackjackRail"), R + 0.03, 0.055, T(0, 0, 0.8), M["leather"], major=64, minor=12, arc=math.pi, rot=(0, 0, rz))
    K.box(K.name("TABLE", "BlackjackBack"), (2 * R + 0.12, 0.18, 0.2), T(0, -0.06, 0.7), M["walnut"], bevel=0.015, rot=(0, 0, rz))
    K.lathe(K.name("TABLE", "BlackjackBase"), [(0, 0), (0.45, 0), (0.4, 0.06), (0.2, 0.14), (0.16, 0.5), (0.28, 0.62), (0, 0.62)], T(0, 0.35, 0), M["walnut_dark"], segments=32)
    z = 0.8005
    arc_text(A, "BLACKJACK PAYS 3 TO 2", *T(0, 0)[:2], z, 0.86, rz + math.pi / 2, 0.075)
    arc_text(A, "DEALER MUST DRAW TO 16 AND STAND ON ALL 17S", *T(0, 0)[:2], z, 0.64, rz + math.pi / 2, 0.032)
    for i in range(5):
        a = math.pi * (0.1 + (i + 0.5) * 0.16)
        bx, by = math.cos(a) * 1.02, math.sin(a) * 1.02
        outline(A, T(bx, by, 0), 0.16, 0.11, rz + a - math.pi / 2, z)
        A.dining_chair(T(math.cos(a) * (R + 0.55), math.sin(a) * (R + 0.55)), rz + a - math.pi / 2 + math.pi, collide=False)
    # chip rack and shoe on the dealer side
    K.box(K.name("TABLE", "ChipRack"), (0.9, 0.2, 0.05), T(0, 0.16, 0.825), M["walnut_dark"], bevel=0.01, rot=(0, 0, rz))
    for i in range(10):
        chip_stack(A, T(-0.38 + i * 0.085, 0.16, 0.85), 8, ("red", "black", "ivory")[i % 3])
    K.box(K.name("TABLE", "Shoe"), (0.16, 0.3, 0.1), T(0.8, 0.22, 0.85), M["walnut_dark"], bevel=0.015, rot=(0, 0, rz + 0.3))
    a_, b_ = T(-R - 0.05, -0.2)[:2], T(R + 0.05, R + 0.05)[:2]
    K.collider(f"Table_{K.idx('table')}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), 0.9))
    interact(A, table_id, "blackjack", T(0, R / 2, 0.55), (2 * R + 0.3, R + 0.5, 1.1), rz)


def baccarat_table(A, x, y, table_id, rz=0.0):
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    sx, R = 2.1, 0.95
    K.obj(K.name("TABLE", "BaccaratFelt"), ellipse_bm(R * sx, R, 0.04), M["felt"], loc=T(0, 0, 0.78), rot=(0, 0, rz), smooth_angle=30)
    K.obj(K.name("TABLE", "BaccaratApron"), ellipse_bm((R + 0.05) * sx, R + 0.05, 0.16), M["walnut"], loc=T(0, 0, 0.68), rot=(0, 0, rz), bevel=0.02, segments=3)
    rail = K.torus(K.name("TABLE", "BaccaratRail"), R + 0.06, 0.07, T(0, 0, 0.8), M["leather"], major=96, minor=14)
    rail.scale = ((R * sx + 0.06) / (R + 0.06), 1, 1)
    rail.rotation_euler = (0, 0, rz)
    for i, (r_, label) in enumerate(((0.55, "BANQUE"), (0.78, "JOUEUR"))):
        line = K.torus(K.name("TABLE", "BaccaratLine"), r_, 0.006, T(0, 0, 0.801), M["print"], major=96, minor=4)
        line.scale = ((r_ * sx * 0.9) / r_, 1, 1)
        line.rotation_euler = (0, 0, rz)
        for side in (-1, 1):
            flat_text(A, label, T(0, side * (r_ - 0.08), 0.8005), rz + (0 if side > 0 else math.pi), 0.075)
    flat_text(A, "BACCARAT", T(0, 0, 0.8005), rz, 0.09)
    for lx in (-0.9, 0.9):
        K.lathe(K.name("TABLE", "BaccaratBase"), [(0, 0), (0.45, 0), (0.4, 0.06), (0.2, 0.14), (0.16, 0.5), (0.28, 0.62), (0, 0.62)], T(lx, 0, 0), M["walnut_dark"], segments=32)
    for i in range(12):
        a = (i / 12) * 2 * math.pi + math.pi / 12
        if math.sin(a) < -0.9:
            continue  # croupier's place
        px, py = math.cos(a) * (R * sx + 0.52), math.sin(a) * (R + 0.6)
        A.dining_chair(T(px, py), rz + math.atan2(-px, -py) - math.pi, collide=False)
    K.collider(f"Table_{K.idx('table')}", (x - R * sx - 0.1, y - R - 0.1, 0), (x + R * sx + 0.1, y + R + 0.1, 0.9))
    interact(A, table_id, "baccarat", (x, y, 0.55), (2 * R * sx + 0.3, 2 * R + 0.3, 1.1), rz)


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


def roulette_table(A, x, y, table_id, index, rz=0.0):
    """Cabinet with printed layout along local +X and a modelled wheel at the -X end.
    The rotor is one node `PROP_<Zone>_Rotor_NN` with extras {rotor: tableId} (spun at runtime)."""
    K, M = A.K, casino_materials(A)
    T = xf(x, y, rz)
    L, W = 3.2, 1.35
    if "red" not in M:
        K.material("red", f"MAT_{K.zone}_LayoutRed", (0.42, 0.03, 0.03), 0.8)
        K.material("black", f"MAT_{K.zone}_LayoutBlack", (0.015, 0.012, 0.01), 0.8)
        K.material("zero", f"MAT_{K.zone}_LayoutGreen", (0.02, 0.2, 0.08), 0.8)
        K.material("pocket_red", f"MAT_{K.zone}_PocketRed", (0.42, 0.03, 0.03), 0.3, coat=1)
        K.material("pocket_black", f"MAT_{K.zone}_PocketBlack", (0.02, 0.018, 0.015), 0.3, coat=1)
        K.material("pocket_green", f"MAT_{K.zone}_PocketGreen", (0.02, 0.24, 0.09), 0.3, coat=1)
    K.box(K.name("TABLE", "RouletteTop"), (L, W, 0.1), T(0.2, 0, 0.73), M["walnut"], bevel=0.02, rot=(0, 0, rz))
    K.box(K.name("TABLE", "RouletteBody"), (L - 0.3, W - 0.35, 0.62), T(0.2, 0, 0.36), M["walnut_dark"], bevel=0.02, rot=(0, 0, rz))
    K.box(K.name("TABLE", "RouletteRail"), (L + 0.08, W + 0.08, 0.06), T(0.2, 0, 0.81), M["leather"], bevel=0.025, segments=3, rot=(0, 0, rz))
    # layout: felt with number grid, zero and outside bets
    lx0 = 0.2 - L / 2 + 1.22
    K.box(K.name("TABLE", "RouletteFelt"), (L - 1.3, W - 0.2, 0.01), T(0.75, 0, 0.84), M["felt"], rot=(0, 0, rz))
    cw, ch = 0.13, 0.22
    z = 0.8455
    for col in range(12):
        for row in range(3):
            n_ = col * 3 + (3 - row)
            cx_, cy_ = lx0 + 0.18 + col * cw, 0.33 - row * ch
            K.box(K.name("PROP", "RouletteCell"), (cw - 0.012, ch - 0.012, 0.002), T(cx_, cy_, z), M["red"] if n_ in RED_NUMBERS else M["black"], rot=(0, 0, rz))
            flat_text(A, str(n_), T(cx_, cy_ - 0.03, z + 0.0015), rz + math.pi / 2, 0.06)
    K.box(K.name("PROP", "RouletteCell"), (0.14, 3 * ch - 0.012, 0.002), T(lx0 + 0.18 - 0.14, 0.33 - ch, z), M["zero"], rot=(0, 0, rz))
    flat_text(A, "0", T(lx0 + 0.18 - 0.14, 0.33 - ch - 0.03, z + 0.0015), rz + math.pi / 2, 0.07)
    for i, label in enumerate(("1-12", "13-24", "25-36")):
        cx_ = lx0 + 0.18 + (i * 4 + 1.5) * cw
        outline(A, T(cx_, -0.25, 0), 4 * cw - 0.012, 0.1, rz, z)
        flat_text(A, label, T(cx_, -0.27, z + 0.0015), rz, 0.045)
    for i, label in enumerate(("MANQUE", "PAIR", "ROUGE", "NOIR", "IMPAIR", "PASSE")):
        cx_ = lx0 + 0.18 + (i * 2 + 0.5) * cw
        outline(A, T(cx_, -0.37, 0), 2 * cw - 0.012, 0.1, rz, z)
        flat_text(A, label, T(cx_, -0.385, z + 0.0015), rz, 0.03)
    # wheel bowl
    wx = 0.2 - L / 2 + 0.55
    K.lathe(K.name("TABLE", "RouletteBowl"), [(0, 0), (0.5, 0), (0.56, 0.06), (0.56, 0.14), (0.52, 0.16), (0.44, 0.12), (0.36, 0.1), (0, 0.1)], T(wx, 0, 0.78), M["walnut"], segments=64)
    K.torus(K.name("TABLE", "RouletteBowlRim"), 0.54, 0.018, T(wx, 0, 0.94), M["gilt"], major=64, minor=8)
    # rotor: pockets, frets, numbers, cone and turret joined into one spinning node
    cxw, cyw = T(wx, 0)[:2]
    center = Vector((cxw, cyw, 0.88))
    cone = K.lathe(f"PROP_{K.zone}_Rotor_{index:02d}", [(0, 0.08), (0.3, 0.02), (0.3, 0.0), (0, 0.0)], tuple(center), M["walnut"], segments=48)
    parts = []
    for i, num in enumerate(WHEEL_ORDER):
        a0, a1 = 2 * math.pi * i / 37, 2 * math.pi * (i + 1) / 37
        bm = bmesh.new()
        vs = [bm.verts.new((r * math.cos(a), r * math.sin(a), 0)) for r, a in ((0.3, a0), (0.4, a0), (0.4, a1), (0.3, a1))]
        f = bm.faces.new(vs)
        bmesh.ops.solidify(bm, geom=[f], thickness=0.015)
        mat = M["pocket_green"] if num == 0 else (M["pocket_red"] if num in RED_NUMBERS else M["pocket_black"])
        parts.append(K.obj(K.name("PROP", "RotorPocket"), bm, mat, loc=tuple(center), uv="box"))
        parts.append(K.box(K.name("PROP", "RotorFret"), (0.1, 0.006, 0.03), tuple(center + Vector((0.35 * math.cos(a0), 0.35 * math.sin(a0), 0.015))), M["gilt"], rot=(0, 0, a0)))
        am = (a0 + a1) / 2
        parts.append(flat_text(A, str(num), tuple(center + Vector((0.42 * math.cos(am), 0.42 * math.sin(am), 0.002))), am - math.pi / 2, 0.022))
    parts.append(K.lathe(K.name("PROP", "RotorTurret"), [(0, 0), (0.05, 0), (0.03, 0.06), (0.012, 0.12), (0.03, 0.14), (0, 0.17)], tuple(center + Vector((0, 0, 0.07))), M["gilt"], segments=16))
    for k in range(4):
        a = k * math.pi / 2
        parts.append(K.box(K.name("PROP", "RotorSpoke"), (0.24, 0.012, 0.012), tuple(center + Vector((0.13 * math.cos(a), 0.13 * math.sin(a), 0.07))), M["gilt"], rot=(0, 0, a)))
    K.join_into(cone, parts)
    cone["rotor"] = table_id  # extras: keeps it a separate node the runtime can spin
    for i in range(4):
        A.dining_chair(T(-0.2 + i * 0.62, W / 2 + 0.55), rz + math.pi, collide=False)
    a_, b_ = T(0.2 - L / 2 - 0.05, -W / 2 - 0.05)[:2], T(0.2 + L / 2 + 0.05, W / 2 + 0.05)[:2]
    K.collider(f"Table_{K.idx('table')}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), 0.95))
    interact(A, table_id, "roulette", T(0.2, 0, 0.55), (L + 0.3, W + 0.3, 1.1), rz)


# ============================================================================ slot machines

SLOT = {}


def slot_protos(A):
    K, M = A.K, A.M
    if SLOT:
        return SLOT
    if "glass" not in M:
        K.material("glass", f"MAT_{K.zone}_Glass", (0.02, 0.02, 0.025), 0.05, coat=1, coat_rough=0.01, alpha=0.18)
        K.material("reel", f"MAT_{K.zone}_ReelStrip", (0.9, 0.86, 0.76), 0.5, emis_color=(1, 0.93, 0.8), emis_strength=0.6)
        K.material("sym_red", f"MAT_{K.zone}_SymbolRed", (0.6, 0.03, 0.03), 0.4, emis_color=(0.9, 0.08, 0.05), emis_strength=0.5)
        K.material("sym_gold", f"MAT_{K.zone}_SymbolGold", (0.7, 0.5, 0.1), 0.3, metal=1)
        K.material("lights", "MAT_Slots_Lights", (0, 0, 0), 0.4, emis_color=(1.0, 0.7, 0.25), emis_strength=6)
    P = SLOT
    P["base"] = K.prototype(K.box(K.name("SLOT", "MachineBase"), (0.62, 0.6, 1.05), (0, 0, -30), M["walnut_dark"], bevel=0.02))
    P["cabinet"] = K.prototype(K.box(K.name("SLOT", "MachineCabinet"), (0.6, 0.33, 0.85), (0, 0, -30), M["walnut"], bevel=0.03, segments=3))
    # gilt shadow box around the reel window (0.46 × 0.32 opening, 0.16 deep): the reels sit inside it
    bars = [((0.04, 0.16, 0.6), (-0.25, 0, 0)), ((0.04, 0.16, 0.6), (0.25, 0, 0)),
            ((0.46, 0.16, 0.14), (0, 0, 0.23)), ((0.46, 0.16, 0.14), (0, 0, -0.23))]
    parts = [K.box(K.name("SLOT", "MachineBezel"), size, (d[0], d[1], -30 + d[2]), M["gilt"], bevel=0.01) for size, d in bars]
    K.join_into(parts[0], parts[1:])
    parts[0].data.transform(Matrix.Translation((-0.25, 0, 0)))  # re-centre the joined mesh on the window
    parts[0].location.x = 0
    P["bezel"] = K.prototype(parts[0])
    P["glass"] = K.prototype(K.box(K.name("SLOT", "MachineGlass"), (0.46, 0.01, 0.32), (0, 0, -30), M["glass"]))
    # a reel drum with raised symbols around it (axis along X)
    drum = K.cyl(K.name("SLOT", "MachineReel"), 0.12, 0.12, 0.12, (0, 0, -30), M["reel"], segments=32, rot=(0, math.pi / 2, 0))
    drum.data.transform(drum.rotation_euler.to_matrix().to_4x4())  # bake the axis (X) into the mesh so
    drum.rotation_euler = (0, 0, 0)                                # instances can spin about it
    syms = []
    for k, (ch, mat) in enumerate((("7", "sym_red"), ("BAR", "sym_gold"), ("7", "sym_gold"), ("$", "sym_red"), ("BAR", "sym_red"), ("$", "sym_gold"))):
        a = 2 * math.pi * k / 6
        loc = Vector((0, -0.121 * math.cos(a), -30 + 0.121 * math.sin(a)))
        t = K.text(K.name("SLOT", "ReelSymbol"), ch, 0.07 if ch != "BAR" else 0.045, M[mat], extrude=0.0, resolution=2, loc=tuple(loc), rot=(math.pi / 2 - a, 0, 0))
        syms.append(t)
    K.join_into(drum, syms)
    P["reel"] = K.prototype(drum)
    P["topper"] = K.prototype(K.cyl(K.name("SLOT", "MachineTopper"), 0.3, 0.3, 0.16, (0, 0, -30), M["gilt"], segments=32, rot=(math.pi / 2, 0, 0)))
    P["lights"] = K.prototype(K.torus(K.name("SLOT", "MachineLights"), 0.3, 0.02, (0, 0, -30), M["lights"], major=32, minor=6, arc=math.pi, rot=(math.pi / 2, 0, 0)))
    P["panel"] = K.prototype(K.box(K.name("SLOT", "MachinePanel"), (0.6, 0.26, 0.06), (0, 0, -30), M["leather"], bevel=0.015))
    P["button"] = K.prototype(K.cyl(K.name("SLOT", "MachineButton"), 0.022, 0.022, 0.02, (0, 0, -30), M["lights"], segments=12))
    P["lever"] = K.prototype(K.cyl(K.name("SLOT", "MachineLever"), 0.012, 0.012, 0.42, (0, 0, -30), M["brass"], segments=8))
    P["knob"] = K.prototype(K.lathe(K.name("SLOT", "MachineKnob"), [(0, 0), (0.04, 0.02), (0.04, 0.06), (0, 0.08)], (0, 0, -30), M["rosso"], segments=16))
    P["stool"] = K.prototype(K.cyl(K.name("SLOT", "Stool"), 0.2, 0.2, 0.1, (0, 0, -30), M["velvet"], segments=24, subsurf=1))
    P["stoolstem"] = K.prototype(K.lathe(K.name("SLOT", "StoolStem"), [(0, 0), (0.2, 0), (0.18, 0.03), (0.04, 0.08), (0.03, 0.6), (0, 0.6)], (0, 0, -30), M["brass"], segments=20))
    return P


def slot_machine(A, x, y, rz, table_id, stool=True):
    """Modular machine (Base / Cabinet / Screen / Lights / Panel, §6) built from linked parts; faces local +Y."""
    K = A.K
    P = slot_protos(A)
    T = xf(x, y, rz)
    link = lambda key, d, rot=(0, 0, 0): K.linked(K.name("SLOT", P[key].name.split("_")[2]), P[key], T(*d), rot=(rot[0], rot[1], rz + rot[2]))  # noqa: E731
    link("base", (0, 0, 0.525))
    link("cabinet", (0, -0.165, 1.475))   # front face at y = 0; the reel window projects forward of it
    link("bezel", (0, 0.08, 1.5))
    seed = sum(map(ord, table_id))  # deterministic per machine (Python's hash() is salted per run)
    for i, dx in enumerate((-0.14, 0, 0.14)):
        link("reel", (dx, 0.03, 1.5), rot=((seed * (i + 3)) % 6 * math.pi / 3, 0, 0))
    link("glass", (0, 0.155, 1.5))
    link("topper", (0, -0.08, 1.9))
    link("lights", (0, 0.0, 1.9))
    link("panel", (0, 0.2, 1.07), rot=(0.25, 0, 0))
    link("button", (0.18, 0.24, 1.11), rot=(0.25, 0, 0))
    link("lever", (0.36, 0, 1.3))
    link("knob", (0.36, 0, 1.51))
    if stool:
        link("stool", (0, 0.95, 0.66))
        link("stoolstem", (0, 0.95, 0))
    a_, b_ = T(-0.34, -0.32)[:2], T(0.34, 0.34)[:2]
    K.collider(f"Slot_{K.idx('slot')}", (min(a_[0], b_[0]), min(a_[1], b_[1]), 0), (max(a_[0], b_[0]), max(a_[1], b_[1]), 2.0))
    interact(A, table_id, "slots", T(0, 0.02, 1.0), (0.66, 0.7, 2.0), rz)
