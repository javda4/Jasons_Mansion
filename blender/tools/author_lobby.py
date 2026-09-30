"""Bootstrap authoring of the Grand Lobby at Phase 3/6 fidelity (Blender → GLB → web).

    blender -b --factory-startup --python blender/tools/author_lobby.py

Writes blender/rooms/lobby/lobby.blend (the editable source). Lighting is baked by
blender/tools/bake_lightmap.py into lobby_baked.blend + a lightmap, which is what gets exported.
Shared architecture (walls, doors, plaques, sconces, chandelier, paintings) comes from mansion.py;
this script keeps only what is unique to the lobby: the medallion floor, the staircase, the
Monte-Carlo columns and the rose centrepiece.

Coordinates: Blender Z-up, 1 unit = 1 m. The lobby is the mansion's reference zone, so its local
frame IS the world frame: glTF (x, y, z) = Blender (x, z, -y). Footprint and doorways match
src/rooms/shared/layout.ts (LOBBY, LOBBY_DOOR_Z) so the galleries connect.
"""
import math
import os
import sys

import bmesh
import bpy  # noqa: F401
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import flora  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

ROOT = kit.ROOT
TEX = os.path.join(ROOT, "blender", "textures_src", "lobby")
OUT = os.path.join(ROOT, "blender", "rooms", "lobby", "lobby.blend")
RNG = np.random.default_rng(1924)

# ---- layout (mirrors src/rooms/shared/layout.ts; Blender y = -glTF z)
X0, X1, Y0, Y1, H = -8.0, 8.0, -4.0, 20.0, 7.2
T = 0.3
LAND = 2.04
STAIR_Y0, RUN, RISE, STEPS, HALF = 12.0, 0.34, 0.17, 12, 2.6
STAIR_Y1 = STAIR_Y0 + STEPS * RUN                        # 16.08
BAY = (STAIR_Y1 - Y0) / 6                                # 3.3467
DOOR_Y = Y0 + 2.5 * BAY                                  # 4.3667 (= -LOBBY_DOOR_Z)
GAL_W, GAL_H = 2.6, 3.6
MED_Y = 5.0                                              # medallion + chandelier (glTF z = -5)
PILASTERS_Y = [Y0 + i * BAY for i in range(7)]           # -4 … 16.08
UPV = (0, 0, 1)
P_FRAME = mansion.P_FRAME
P_HANDRAIL = [(0, -0.06), (0.04, -0.06), (0.075, -0.045), (0.09, -0.02), (0.09, 0.02), (0.075, 0.045), (0.04, 0.06), (0, 0.06), (0, -0.06)]

kit.reset_scene()
K = kit.Zone("Lobby")
A = mansion.Mansion(K, height=H, thickness=T, sea=mansion.sea_texture(os.path.join(TEX, "T_Lobby_SeaView_Emissive.png"), seed=1924, moon_x=0.3))
M = A.M
K.material("petal", "MAT_Lobby_Rose", (0.42, 0.02, 0.04), 0.6, sheen=0.8)
K.material("leaf", "MAT_Lobby_Leaf", (0.03, 0.09, 0.03), 0.55)
W_, D_ = X1 - X0, Y1 - Y0
cy = (Y0 + Y1) / 2

# ============================================================================ build: floor & ceiling
import bmesh  # noqa: E402

# ---------------------------------------------------------------------------- floor (casino.png, Grand Lobby)
# Layers, bottom → top (1.5 mm apart): Calacatta slab · grout · 45° checker of Calacatta + Bardiglio tiles ·
# Nero cabochons · the Greek-key band · the compass-rose medallion.
K.material("grout", "MAT_Lobby_Grout", (0.06, 0.055, 0.05), 0.85)
K.box(K.name("ROOM", "Floor"), (W_, D_, 0.2), (0, cy, -0.1), M["marble"], lightmap=True)
K.collider("Floor", (X0 - 1, Y0 - 1, -0.5), (X1 + 1, Y1 + 1, 0))

MARGIN, BAND, GAP = 0.55, 0.36, 0.12
BY1 = STAIR_Y0 - 0.1                                       # the band stops at the foot of the stairs
band_o = (X0 + MARGIN, Y0 + MARGIN, X1 - MARGIN, BY1)
band_i = (band_o[0] + BAND, band_o[1] + BAND, band_o[2] - BAND, band_o[3] - BAND)
fld = (band_i[0] + GAP, band_i[1] + GAP, band_i[2] - GAP, band_i[3] - GAP)
Z_GROUT, Z_TILE, Z_CAB, Z_BAND, Z_KEY = 0.0008, 0.0016, 0.0024, 0.0016, 0.0024
MED_R = 3.4


def flat(name, polys, mat, z, lightmap=True, uv_jitter=None):
    """Flat faces at height z; UV0 in metres (optionally offset/rotated per face for vein variety)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    for k, poly in enumerate(polys):
        if len(poly) < 3:
            continue
        f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in poly])
        if f.normal.z < 0:
            f.normal_flip()
        ox, oy, rot = uv_jitter[k] if uv_jitter else (0, 0, 0)
        c, s_ = math.cos(rot), math.sin(rot)
        for loop in f.loops:
            x, y = loop.vert.co.x, loop.vert.co.y
            loop[uv].uv = (x * c - y * s_ + ox, x * s_ + y * c + oy)
    return K.obj(name, bm, mat, uv=None, lightmap=lightmap)


def clip(poly, rect):
    """Sutherland–Hodgman against an axis-aligned rectangle (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = rect
    for inside, cut in ((lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
                        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
                        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
                        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1))):
        out = []
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            if inside(b):
                if not inside(a):
                    out.append(cut(a, b))
                out.append(b)
            elif inside(a):
                out.append(cut(a, b))
        poly = out
        if not poly:
            break
    return poly


def rect_poly(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# grout bed under the checker
flat(K.name("ROOM", "FloorGrout"), [rect_poly(*fld)], M["grout"], Z_GROUT)

# 45° checker, symmetric about the medallion; 2 mm joints; each tile's veining offset/rotated
S, JOINT = 0.72, 0.001
r2 = math.sqrt(0.5)
tiles = {"marble": [], "bardiglio": []}
jit = {"marble": [], "bardiglio": []}
rngf = np.random.default_rng(7)
for i in range(-20, 21):
    for j in range(-20, 21):
        u0, u1, v0, v1 = i * S + JOINT, (i + 1) * S - JOINT, j * S + JOINT, (j + 1) * S - JOINT
        corners = [((u - v) * r2, MED_Y + (u + v) * r2) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
        cxy = (sum(p[0] for p in corners) / 4, sum(p[1] for p in corners) / 4)
        if math.hypot(cxy[0], cxy[1] - MED_Y) < MED_R - 0.6:
            continue                                          # hidden under the medallion
        poly = clip(corners, fld)
        if len(poly) < 3:
            continue
        key = "marble" if (i + j) % 2 == 0 else "bardiglio"
        tiles[key].append(poly)
        jit[key].append((rngf.random() * 4, rngf.random() * 4, rngf.integers(4) * math.pi / 2))
for key in tiles:
    flat(K.name("ROOM", f"FloorTile{key.capitalize()}"), tiles[key], M[key], Z_TILE, uv_jitter=jit[key])

# Nero cabochons at the checker's corners (instanced)
cab = K.prototype(K.box(K.name("PROP", "Cabochon"), (0.12, 0.12, 0.003), (0, 0, -30), M["nero"]))
for i in range(-20, 21):
    for j in range(-20, 21):
        u, v = i * S, j * S
        x, y = (u - v) * r2, MED_Y + (u + v) * r2
        if fld[0] + 0.1 < x < fld[2] - 0.1 and fld[1] + 0.1 < y < fld[3] - 0.1 and math.hypot(x, y - MED_Y) > MED_R + 0.1:
            K.linked(K.name("PROP", "Cabochon"), cab, (x, y, Z_CAB))

# Greek-key band: Nero ground, Calacatta meander, fillets both sides
ox0, oy0, ox1, oy1 = band_o
ix0, iy0, ix1, iy1 = band_i
flat(K.name("ROOM", "FloorBand"), [rect_poly(ox0, oy0, ox1, iy0), rect_poly(ox0, iy1, ox1, oy1),
                                   rect_poly(ox0, iy0, ix0, iy1), rect_poly(ix1, iy0, ox1, iy1)], M["nero"], Z_BAND)
LW, PAD = 0.03, 0.055
Hk = BAND - 2 * PAD                                          # key height across the band
Pk = Hk * 1.25                                               # one key per period


def key_run(a0, a1):
    """Meander segments in band-local (a along, b across) coords, as rectangles."""
    rects = [(a0, -LW / 2, a1, LW / 2), (a0, Hk - LW / 2, a1, Hk + LW / 2)]   # fillets
    n = int((a1 - a0) // Pk)
    start = a0 + ((a1 - a0) - n * Pk) / 2
    for k in range(n):
        a = start + k * Pk
        pts = [(a, 0), (a, Hk * 0.8), (a + Pk * 0.72, Hk * 0.8), (a + Pk * 0.72, Hk * 0.3), (a + Pk * 0.36, Hk * 0.3), (a + Pk * 0.36, Hk * 0.55)]
        for (p0, q0), (p1, q1) in zip(pts, pts[1:]):
            rects.append((min(p0, p1) - LW / 2, min(q0, q1) - LW / 2, max(p0, p1) + LW / 2, max(q0, q1) + LW / 2))
    return rects


key_polys = []
for side in ("front", "back", "left", "right"):
    if side in ("front", "back"):
        a0, a1 = ix0, ix1
        base = oy0 + PAD if side == "front" else oy1 - PAD
        sgn = 1 if side == "front" else -1
        for (pa0, pb0, pa1, pb1) in key_run(a0, a1):
            key_polys.append(rect_poly(pa0, base + sgn * pb0, pa1, base + sgn * pb1) if sgn > 0 else rect_poly(pa0, base - pb1, pa1, base - pb0))
    else:
        a0, a1 = iy0, iy1
        base = ox0 + PAD if side == "left" else ox1 - PAD
        sgn = 1 if side == "left" else -1
        for (pa0, pb0, pa1, pb1) in key_run(a0, a1):
            key_polys.append(rect_poly(base + pb0, pa0, base + pb1, pa1) if sgn > 0 else rect_poly(base - pb1, pa0, base - pb0, pa1))
# corner blocks: Calacatta square with a Nero lozenge
for cx_, cy_ in ((ox0 + BAND / 2, oy0 + BAND / 2), (ox1 - BAND / 2, oy0 + BAND / 2), (ox0 + BAND / 2, oy1 - BAND / 2), (ox1 - BAND / 2, oy1 - BAND / 2)):
    h_ = BAND / 2 - PAD / 2
    key_polys.append(rect_poly(cx_ - h_, cy_ - h_, cx_ + h_, cy_ + h_))
flat(K.name("ROOM", "FloorKey"), key_polys, M["marble"], Z_KEY)


# ---------------------------------------------------------------------------- compass-rose medallion
def disc(name, r, z, mat, seg=160):
    return flat(name, [[(r * math.cos(2 * math.pi * k / seg), MED_Y + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]], mat, z)


def ring(name, r0, r1, z, mat, seg=160):
    polys = []
    for k in range(seg):
        a, b = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        polys.append([(r0 * math.cos(a), MED_Y + r0 * math.sin(a)), (r1 * math.cos(a), MED_Y + r1 * math.sin(a)),
                      (r1 * math.cos(b), MED_Y + r1 * math.sin(b)), (r0 * math.cos(b), MED_Y + r0 * math.sin(b))])
    return flat(name, polys, mat, z)


zc = 0.003
disc(K.name("ROOM", "Medallion"), MED_R, zc, M["nero"])
ring(K.name("ROOM", "Medallion"), 2.93, 3.28, zc + 0.0008, M["rosso"])
teeth = []                                                   # sawtooth of Calacatta on the Rosso band
NT = 48
for k in range(NT):
    a0, a1, am = 2 * math.pi * k / NT, 2 * math.pi * (k + 1) / NT, 2 * math.pi * (k + 0.5) / NT
    teeth.append([(2.96 * math.cos(a0), MED_Y + 2.96 * math.sin(a0)), (2.96 * math.cos(a1), MED_Y + 2.96 * math.sin(a1)), (3.25 * math.cos(am), MED_Y + 3.25 * math.sin(am))])
flat(K.name("ROOM", "MedallionTeeth"), teeth, M["marble"], zc + 0.0016)
disc(K.name("ROOM", "Medallion"), 2.9, zc + 0.0016, M["marble"])
ring(K.name("ROOM", "MedallionLine"), 2.06, 2.12, zc + 0.0024, M["nero"])


def rays(n, r_tip, r_base, half_w, rot, z, mat_a, mat_b, tag):
    """Faceted compass rays: each ray is two triangles (left half mat_a, right half mat_b)."""
    left, right = [], []
    for k in range(n):
        a = rot + 2 * math.pi * k / n
        d = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-d.y, d.x, 0))
        tip = d * r_tip
        base = d * r_base
        c = (0.0, MED_Y)
        P = lambda v: (v.x + c[0], v.y + c[1])  # noqa: E731
        left.append([P(Vector((0, 0, 0)) + base * 0), P(tip), P(base + t * half_w)])
        right.append([P(Vector((0, 0, 0))), P(base - t * half_w), P(tip)])
    flat(K.name("ROOM", f"Medallion{tag}A"), left, mat_a, z)
    flat(K.name("ROOM", f"Medallion{tag}B"), right, mat_b, z)


rays(8, 2.1, 0.62, 0.3, math.pi / 8, zc + 0.0032, M["rosso"], M["nero"], "RayMinor")
rays(8, 2.82, 0.75, 0.38, 0.0, zc + 0.004, M["nero"], M["bardiglio"], "RayMajor")
ring(K.name("ROOM", "MedallionCore"), 0.62, 0.9, zc + 0.0048, M["rosso"])
disc(K.name("ROOM", "MedallionCore"), 0.62, zc + 0.0048, M["marble"])
rays(8, 0.56, 0.16, 0.12, math.pi / 8, zc + 0.0056, M["nero"], M["bardiglio"], "RayCore")
for R, r, z in ((3.29, 0.018, zc + 0.002), (2.92, 0.015, zc + 0.0024), (0.905, 0.014, zc + 0.0056), (0.62, 0.012, zc + 0.0064)):
    K.torus(K.name("ROOM", "MedallionRing"), R, r, (0, MED_Y, z - r * 0.7), M["gilt"], major=160, minor=6)


# coffered ceiling: slab, moulded beams, gilt rosettes, ceiling rose
K.box(K.name("ROOM", "Ceiling"), (W_, D_, 0.3), (0, cy, H + 0.15), M["ceiling"], lightmap=True)
beam_d = 0.36
xs = [X0 + 2 * i for i in range(1, 8)]
ys = [Y0 + 2 * i for i in range(1, 12)]
for x in xs:
    K.box(K.name("ROOM", "Beam"), (0.28, D_, beam_d), (x, cy, H - beam_d / 2), M["walnut"], lightmap=True)
    for s in (-1, 1):
        K.sweep(K.name("ROOM", "BeamMoulding"), [(x + s * 0.14, Y0, H - beam_d), (x + s * 0.14, Y1, H - beam_d)], (s, 0, 0),
                [(0, 0), (0, 0.02), (0.03, 0.04), (0.07, 0.05), (0.07, 0)], M["gilt"], n1_hint=UPV)
for y in ys:
    K.box(K.name("ROOM", "Beam"), (W_, 0.28, beam_d), (0, y, H - beam_d / 2 - 0.001), M["walnut"], lightmap=True)
rosette = K.prototype(K.lathe(K.name("PROP", "Rosette"), [(0, -0.07), (0.05, -0.065), (0.09, -0.04), (0.12, -0.02), (0.13, 0), (0, 0)], (0, 0, -30), M["gilt"], segments=16))
for x in xs:
    for y in ys:
        K.linked(K.name("PROP", "Rosette"), rosette, (x, y, H - beam_d - 0.001))
K.lathe(K.name("ROOM", "CeilingRose"), [(0, 0), (1.3, 0), (1.25, -0.05), (1.1, -0.08), (0.9, -0.1), (0.6, -0.12), (0.3, -0.16), (0.1, -0.2), (0, -0.2)],
        (0, MED_Y, H - beam_d), M["gilt"], segments=64, lightmap=False)

# ============================================================================ walls, doors, plaques
openW = (DOOR_Y, GAL_W, GAL_H)
A.wall("Left", "y", X0, 1, Y0, STAIR_Y1, openings=[openW], pilasters=PILASTERS_Y,
       paintings=[(Y0 + 1.5 * BAY, 3), (Y0 + 4.5 * BAY, 9)], sconces=PILASTERS_Y[1:6])
A.wall("Right", "y", X1, -1, Y0, STAIR_Y1, openings=[openW], pilasters=PILASTERS_Y,
       windows=[Y0 + 1.5 * BAY, Y0 + 4.5 * BAY], sconces=PILASTERS_Y[1:6])
A.wall("LeftUpper", "y", X0, 1, STAIR_Y1, Y1, base=LAND, pilasters=[STAIR_Y1, Y1])
A.wall("RightUpper", "y", X1, -1, STAIR_Y1, Y1, base=LAND, pilasters=[STAIR_Y1, Y1])
A.wall("Front", "x", Y0, 1, X0, X1, openings=[(0.0, 2.4, 3.6)], pilasters=[X0, X0 + 3.2, -1.6, 1.6, X1 - 3.2, X1],
       paintings=[(X0 + 1.6, 5), (X1 - 1.6, 8)], sconces=[-1.6, 1.6])
A.wall("Back", "x", Y1, -1, X0, X1, base=LAND, openings=[(0.0, 2.2, 3.3)], pilasters=[X0, X0 + 3.2, -1.5, 1.5, X1 - 3.2, X1],
       paintings=[(X0 + 1.6, 6), (X1 - 1.6, 2)], sconces=[-1.5, 1.5])

A.double_door("West", (X0, DOOR_Y, 0), (1, 0, 0), GAL_W, GAL_H, 0, "Enter the West Gallery", target="hall_west")
A.double_door("East", (X1, DOOR_Y, 0), (-1, 0, 0), GAL_W, GAL_H, 0, "Enter the East Gallery", target="hall_east")
A.double_door("Front", (0, Y0, 0), (0, 1, 0), 2.4, 3.6, 0, "The Front Doors — the terrace is closed tonight", locked=True)
A.double_door("Apartments", (0, Y1, 0), (0, -1, 0), 2.2, 3.3, LAND, "Private Apartments", locked=True)
A.plaque(["Poker · Blackjack · Baccarat", "Galerie Ouest"], (X0 + 0.14, DOOR_Y, GAL_H + 0.95), (1, 0, 0), width=2.4)
A.plaque(["Roulette · Machines à Sous", "Galerie Est"], (X1 - 0.14, DOOR_Y, GAL_H + 0.95), (-1, 0, 0), width=2.4)

# ============================================================================ staircase
tread_profile = [(0, 0), (0, 0.03), (-0.012, 0.042), (-0.03, 0.04), (-0.04, 0.022), (-0.04, 0)]  # a = up, b = out over the riser
rod = K.prototype(K.cyl(K.name("PROP", "StairRod"), 0.009, 0.009, 3.45, (0, 0, -30), M["brass"], segments=10, rot=(0, math.pi / 2, 0)))
for i in range(STEPS):
    top = (i + 1) * RISE
    y0, y1 = STAIR_Y0 + i * RUN, STAIR_Y0 + (i + 1) * RUN
    flare = max(0.0, 0.45 - i * 0.15)  # bottom steps flare out
    hw = HALF + flare
    K.box(K.name("ROOM", "Step"), (2 * hw, RUN, top), (0, (y0 + y1) / 2, top / 2), M["marble"], lightmap=True)
    if flare:
        for s in (-1, 1):
            K.cyl(K.name("ROOM", "StepEnd"), RUN / 2, RUN / 2, top, (s * hw, (y0 + y1) / 2, top / 2), M["marble"], segments=24, lightmap=True)
    K.sweep(K.name("ROOM", "StepNosing"), [(-hw, y0, top), (hw, y0, top)], (0, -1, 0), tread_profile, M["marble"], n1_hint=UPV)
    K.box(K.name("ROOM", "Runner"), (3.3, RUN + 0.02, 0.012), (0, (y0 + y1) / 2 + 0.01, top + 0.006), M["carpet"], lightmap=True)
    K.box(K.name("ROOM", "RunnerRiser"), (3.3, 0.012, RISE), (0, y0 + 0.025, top - RISE / 2), M["carpet"], lightmap=True)
    for s in (-1, 1):
        K.box(K.name("ROOM", "RunnerBorder"), (0.04, RUN + 0.02, 0.014), (s * 1.6, (y0 + y1) / 2 + 0.01, top + 0.007), M["gilt"])
    K.linked(K.name("PROP", "StairRod"), rod, (0, y0 + 0.04, top - RISE + 0.012), rot=(0, math.pi / 2, 0))
    K.collider(f"Step_{i + 1:02d}", (-hw, y0, 0), (hw, y1, top))

# landing, its panelled front face, stringers
land_d = Y1 - STAIR_Y1
K.box(K.name("ROOM", "Landing"), (W_, land_d, LAND - 0.04), (0, (STAIR_Y1 + Y1) / 2, (LAND - 0.04) / 2), M["walnut"], lightmap=True)
K.box(K.name("ROOM", "LandingFloor"), (W_, land_d + 0.06, 0.04), (0, (STAIR_Y1 + Y1) / 2 - 0.03, LAND - 0.02), M["marble"], lightmap=True)
K.box(K.name("ROOM", "LandingRunner"), (3.3, land_d, 0.012), (0, (STAIR_Y1 + Y1) / 2, LAND + 0.006), M["carpet"], lightmap=True)
K.collider("Landing", (X0, STAIR_Y1, 0), (X1, Y1, LAND))
for s in (-1, 1):
    cxs = s * (HALF + (X1 - HALF) / 2)
    wpan = X1 - HALF - 0.2
    K.box(K.name("ROOM", "LandingPanel"), (wpan - 0.3, 0.03, LAND - 0.6), (cxs, STAIR_Y1 - 0.015, LAND / 2), M["walnut_dark"], bevel=0.012, lightmap=True)
    K.frame(K.name("ROOM", "LandingPanelFrame"), (cxs, STAIR_Y1 - 0.03, LAND / 2), wpan - 0.26, LAND - 0.56, (0, -1, 0), P_FRAME, M["gilt"])
    K.box(K.name("ROOM", "Stringer"), (0.22, STAIR_Y1 - STAIR_Y0 + 0.1, LAND + 0.1), (s * (HALF + 0.11), (STAIR_Y0 + STAIR_Y1) / 2, (LAND + 0.1) / 2), M["walnut"], lightmap=True)

# balustrades: turned balusters (instanced), swept handrail, newels with lamps
baluster = K.prototype(K.lathe(K.name("PROP", "Baluster"), [(0, 0), (0.05, 0), (0.05, 0.06), (0.032, 0.09), (0.028, 0.18), (0.05, 0.34), (0.056, 0.42), (0.032, 0.56), (0.022, 0.66), (0.04, 0.7), (0.04, 0.84), (0, 0.84)], (0, 0, -30), M["gilt"], segments=14))
rail_h = 0.95


def balustrade(p0, p1, tag):
    p0, p1 = Vector(p0), Vector(p1)
    run = p1 - p0
    horiz = Vector((run.x, run.y, 0))
    n_ = max(2, int(horiz.length / 0.16))
    for k in range(n_ + 1):
        p = p0 + run * (k / n_)
        K.linked(K.name("PROP", "Baluster"), baluster, (p.x, p.y, p.z + 0.04))
    side = Vector((0, 0, 1)).cross(horiz.normalized())
    K.sweep(K.name("PROP", f"{tag}Handrail"), [p0 + Vector((0, 0, rail_h)), p1 + Vector((0, 0, rail_h))], side, P_HANDRAIL, M["walnut"], n1_hint=UPV)
    K.sweep(K.name("PROP", f"{tag}BaseRail"), [p0, p1], side, [(0, -0.05), (0.04, -0.05), (0.04, 0.05), (0, 0.05), (0, -0.05)], M["walnut"], n1_hint=UPV)


newel_top = K.prototype(K.lathe(K.name("PROP", "NewelCap"), [(0, 0), (0.2, 0), (0.2, 0.05), (0.15, 0.08), (0.08, 0.14), (0.05, 0.2), (0, 0.22)], (0, 0, -30), M["gilt"], segments=24))
for s in (-1, 1):
    balustrade((s * (HALF + 0.11), STAIR_Y0 + 0.1, 0.18), (s * (HALF + 0.11), STAIR_Y1 + 0.12, LAND), f"Stair{'L' if s < 0 else 'R'}")
    balustrade((s * (HALF + 0.25), STAIR_Y1 + 0.12, LAND), (s * (X1 - 0.35), STAIR_Y1 + 0.12, LAND), f"Landing{'L' if s < 0 else 'R'}")
    K.collider(f"BalustradeStair_{'L' if s < 0 else 'R'}", (s * HALF - (0.22 if s < 0 else 0), STAIR_Y0, 0), (s * HALF + (0.22 if s > 0 else 0), STAIR_Y1 + 0.2, LAND + 1.1))
    K.collider(f"BalustradeLanding_{'L' if s < 0 else 'R'}", (min(s * (HALF + 0.2), s * X1), STAIR_Y1, LAND), (max(s * (HALF + 0.2), s * X1), STAIR_Y1 + 0.22, LAND + 1.1))
    for (y, z) in ((STAIR_Y0 - 0.15, 0.0), (STAIR_Y1 + 0.12, LAND)):
        x = s * (HALF + 0.15)
        K.box(K.name("ROOM", "Newel"), (0.34, 0.34, 1.2), (x, y, z + 0.6), M["walnut"], bevel=0.015, segments=3)
        for f_ in range(4):
            a = f_ * math.pi / 2
            K.box(K.name("ROOM", "NewelPanel"), (0.22, 0.012, 0.8) if f_ % 2 == 0 else (0.012, 0.22, 0.8),
                  (x + 0.172 * math.sin(a), y - 0.172 * math.cos(a), z + 0.6), M["walnut_dark"], bevel=0.004)
        K.linked(K.name("PROP", "NewelCap"), newel_top, (x, y, z + 1.2))
        K.collider(f"Newel_{K.idx('newel')}", (x - 0.18, y - 0.18, z), (x + 0.18, y + 0.18, z + 1.3))
        if z == 0.0:
            K.lathe(K.name("PROP", "NewelLamp"), [(0, 0), (0.03, 0), (0.02, 0.3), (0.05, 0.36), (0.02, 0.4), (0, 0.4)], (x, y, 1.42), M["brass"], segments=16)
            K.lathe(K.name("PROP", "NewelGlobe"), [(0, 0), (0.1, 0.02), (0.14, 0.14), (0.12, 0.28), (0.05, 0.34), (0, 0.34)], (x, y, 1.8), M["shade"], segments=24)
            K.light(K.name("LIGHT", "Newel"), "POINT", (x, y, 1.97), 8, rng=7, bake_only=True)

# ============================================================================ columns (Monte-Carlo marble)
for (x, y, z0) in ((-3.8, 11.0, 0.0), (3.8, 11.0, 0.0), (-3.8, 17.2, LAND), (3.8, 17.2, LAND)):
    top = H - beam_d
    K.box(K.name("ROOM", "ColumnPlinth"), (0.78, 0.78, 0.36), (x, y, z0 + 0.18), M["nero"], bevel=0.02, segments=3, lightmap=True)
    K.lathe(K.name("ROOM", "ColumnBase"), [(0, 0), (0.36, 0), (0.36, 0.05), (0.33, 0.1), (0.31, 0.12), (0.3, 0.18), (0, 0.18)], (x, y, z0 + 0.36), M["gilt"], segments=48)
    shaft_h = top - (z0 + 0.54) - 0.72
    K.fluted_shaft(K.name("ROOM", "ColumnShaft"), 0.28, shaft_h, (x, y, z0 + 0.54), M["marble"], flutes=18, lightmap=True)
    K.lathe(K.name("ROOM", "ColumnCapital"), [(0, 0), (0.27, 0), (0.29, 0.06), (0.33, 0.24), (0.38, 0.42), (0.42, 0.52), (0, 0.52)], (x, y, z0 + 0.54 + shaft_h), M["gilt"], segments=48)
    K.box(K.name("ROOM", "ColumnAbacus"), (0.94, 0.94, 0.2), (x, y, top - 0.1), M["walnut"], bevel=0.02, segments=3, lightmap=True)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        K.torus(K.name("PROP", "CapitalVolute"), 0.07, 0.02, (x + 0.38 * math.cos(a), y + 0.38 * math.sin(a), top - 0.3), M["gilt"],
                major=20, minor=6, rot=(math.pi / 2, 0, a + math.pi / 2))
    K.collider(f"Column_{K.idx('col')}", (x - 0.4, y - 0.4, z0), (x + 0.4, y + 0.4, top))

# ============================================================================ chandelier + furniture
A.chandelier(0, MED_Y, scale=1.0, drop=1.6, point_cd=90, key_cd=150)
A.audio("Chandelier", (0, MED_Y, 4.6), "crystal", gain=0.3, interval=(9, 22))

# centre table with a grand floral arrangement (flora.py: modelled roses, leaves, greenery)
K.lathe(K.name("TABLE", "Centre"), [(0, 0), (0.5, 0), (0.48, 0.06), (0.16, 0.16), (0.1, 0.36), (0.15, 0.6), (0.2, 0.74), (0, 0.74)], (0, MED_Y, 0), M["walnut"], segments=48)
K.cyl(K.name("TABLE", "CentreTop"), 0.95, 0.95, 0.05, (0, MED_Y, 0.765), M["nero"], segments=72, bevel=0.012)
K.torus(K.name("TABLE", "CentreRim"), 0.95, 0.02, (0, MED_Y, 0.765), M["gilt"], major=72, minor=6)
K.lathe(K.name("PROP", "Urn"), [(0, 0), (0.17, 0), (0.18, 0.035), (0.1, 0.12), (0.12, 0.21), (0.29, 0.42), (0.31, 0.58), (0.23, 0.7), (0.28, 0.79), (0.29, 0.84), (0, 0.84)],
        (0, MED_Y, 0.79), M["gilt"], segments=48)
K.collider("CentreTable", (-0.98, MED_Y - 0.98, 0), (0.98, MED_Y + 0.98, 0.9))
flora.arrangement(K, (0, MED_Y), 0.79 + 0.84, radius=0.55, height=0.58, reds=95, ivories=70, leaves=200, sprays=22)

# ---------------------------------------------------------------------------- furnishing (photoscanned, CC0)
# Poly Haven models imported as instanced prototypes (mansion.prop / place; scripts/fetch-models.mjs).
A.prop("sofa_02", "Chesterfield")
A.prop("Sofa_01", "LouisSofa", tint={"Sofa": (0.62, 0.5, 0.36)})             # cream silk → antique gold
A.prop("gothic_coffee_table", "CoffeeTable", scale=0.72, decimate=0.45)
A.prop("ClassicConsole_01", "Console")
A.prop("ornate_mirror_01", "Mirror", scale=2.1, origin="back")
A.prop("brass_candleholders", "Candelabra", pick=["candleholder_03"], decimate=0.4)
A.prop("antique_ceramic_vase_01", "Vase")
A.prop("mantel_clock_01", "MantelClock", decimate=0.4)
A.prop("marble_bust_01", "Bust", decimate=0.6)
A.prop("horse_statue_01", "Horse", scale=4.2, decimate=0.6)
A.prop("vintage_grandfather_clock_01", "GrandfatherClock")
A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.3)       # its terracotta pot → our jardinière


def seating(cx_, cy_, face, sofa):
    """A conversation group on an antique rug (face = -1 west side, +1 east side): the sofa against the
    wall facing into the room, two bergères opposite angled in, a carved coffee table between, oil lamps
    on pedestals at the sofa's ends."""
    A.rug(f"SeatRug{K.idx('seatrug')}", cx_, cy_, 3.3, 3.3 / 1.1469, math.pi / 2, "Rug_Kazak", fringe=True)
    sx = cx_ + face * 1.65
    A.place(sofa, (sx, cy_, 0.011), face * math.pi / 2, collide=(0.9, 0.42, 0.8))
    A.place("CoffeeTable", (cx_ + face * 0.2, cy_, 0.011), 0, collide=(0.52, 0.52, 0.42))
    for dy in (-0.8, 0.8):
        A.club_chair((cx_ - face * 1.05, cy_ + dy), -face * math.pi / 2 + face * (dy / 0.8) * 0.4)
    for dy in (-1.3, 1.3):
        A.lamp_table(sx + face * 0.05, cy_ + dy, candela=6)


seating(-5.6, 0.35, -1, "Chesterfield")
seating(5.6, 0.35, 1, "Chesterfield")
seating(-5.6, 8.55, -1, "LouisSofa")
seating(5.6, 8.55, 1, "LouisSofa")


def console_group(wx, wy, rz, z0=0.0, clock=False):
    """Carved gilt console against the wall point (wx, wy) (rz: 0 = facing +Y), an ornate mirror above,
    candelabra and a chinoiserie vase or mantel clock on top."""
    n = Vector((-math.sin(rz), math.cos(rz), 0))                 # into the room
    t = Vector((math.cos(rz), math.sin(rz), 0))                  # along the wall
    base = Vector((wx, wy, z0))
    A.place("Console", tuple(base + n * 0.42), rz, collide=(0.78, 0.32, 0.95))
    A.place("Mirror", tuple(base + n * 0.07 + Vector((0, 0, 1.98))), rz)
    A.place("Candelabra", tuple(base + n * 0.4 + t * 0.48 + Vector((0, 0, 0.95))), rz)
    A.place("MantelClock" if clock else "Vase", tuple(base + n * 0.4 - t * 0.42 + Vector((0, 0, 0.95))), rz)
    K.light(K.name("LIGHT", "Candelabra"), "POINT", tuple(base + n * 0.4 + t * 0.48 + Vector((0, 0, 1.85))), 5, rng=5, bake_only=True)


console_group(-3.2, Y0, 0, clock=False)          # front wall, either side of the entrance
console_group(3.2, Y0, 0, clock=True)
console_group(-3.15, Y1, math.pi, LAND, clock=True)   # landing, either side of the apartments door
console_group(3.15, Y1, math.pi, LAND, clock=False)


def pedestal(x, y, top_mat="nero"):
    """Marble pedestal (plinth, fluted-look shaft, moulded cap) for a bust or statue; top at 1.12 m."""
    K.box(K.name("PROP", "PedestalBase"), (0.5, 0.5, 0.14), (x, y, 0.07), M["nero"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalShaft"), (0.36, 0.36, 0.84), (x, y, 0.14 + 0.42), M["marble"], bevel=0.01, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalCap"), (0.48, 0.48, 0.12), (x, y, 0.98 + 0.06), M[top_mat], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalCap"), (0.42, 0.42, 0.04), (x, y, 1.1), M["gilt"], bevel=0.006)
    K.collider(f"BustPedestal_{K.idx('ped')}", (x - 0.26, y - 0.26, 0), (x + 0.26, y + 0.26, 1.7))


# busts flanking both gallery doors, looking into the room
for sx in (-1, 1):
    for dy in (-1.95, 1.95):
        px_, py_ = sx * (X1 - 0.5), DOOR_Y + dy
        pedestal(px_, py_)
        A.place("Bust", (px_, py_, 1.12), -sx * math.pi / 2)

# porcelain horses on plinths at the foot of the stair (casino.png: statues flank the staircase)
for sx in (-1, 1):
    x_, y_ = sx * 3.55, STAIR_Y0 + 0.35
    K.box(K.name("PROP", "StatuePlinth"), (0.62, 0.62, 0.18), (x_, y_, 0.09), M["nero"], bevel=0.015, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.5, 0.5, 0.72), (x_, y_, 0.18 + 0.36), M["rosso"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.6, 0.6, 0.08), (x_, y_, 0.94), M["nero"], bevel=0.012, segments=2, lightmap=True)
    A.place("Horse", (x_, y_, 0.98), sx * math.pi / 2 + math.pi)
    K.collider(f"Statue_{K.idx('statue')}", (x_ - 0.32, y_ - 0.32, 0), (x_ + 0.32, y_ + 0.32, 2.0))

# the long-case clock beside the stair
A.place("GrandfatherClock", (X0 + 0.45, 13.6, 0), -math.pi / 2, collide=(0.32, 0.25, 2.2))


def jardiniere_plant(x, y, z=0.0):
    """A leafy plant in a brass jardinière (the scan's terracotta pot is replaced)."""
    K.lathe(K.name("PROP", "Jardiniere"), [(0, 0), (0.16, 0), (0.17, 0.03), (0.12, 0.08), (0.2, 0.2), (0.3, 0.36), (0.32, 0.46), (0.3, 0.48), (0, 0.48)],
            (x, y, z), M["brass"], segments=40)
    A.place("Plant", (x, y, z + 0.2), 0)
    K.collider(f"Plant_{K.idx('plant')}", (x - 0.34, y - 0.34, z), (x + 0.34, y + 0.34, z + 1.3))


for x_, y_ in ((X0 + 0.55, Y0 + 0.55), (X1 - 0.55, Y0 + 0.55), (X1 - 0.55, 13.6), (-6.2, STAIR_Y0 + 0.4), (6.2, STAIR_Y0 + 0.4)):
    jardiniere_plant(x_, y_)
for x_ in (X0 + 0.6, X1 - 0.6):
    jardiniere_plant(x_, Y1 - 0.6, LAND)

# two lesser chandeliers over the seating groups
for x_ in (-5.6, 5.6):
    A.chandelier(x_, 4.45, scale=0.62, drop=1.4, point_cd=26, key=False, tiers=2)

# moonlight through the east windows (bake-only)
K.light("LIGHT_Lobby_Moon_01", "SPOT", (X1 + 3, 3.0, 5.0), 25, color=(0.55, 0.63, 0.85), rng=30, bake_only=True,
        angle=math.radians(80), blend=1.0, rot=(0, math.radians(-62), 0))

A.logic(spawn=((0, -2.2, 0), (-math.pi / 2, 0, 0)), probe=(0, 4.0, 1.7), bounds=((X0, Y0, -1), (X1, Y1, H)))
mansion.save(OUT)
