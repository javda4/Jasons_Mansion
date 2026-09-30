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

# floor: bordered marble field
m, band = 0.7, 0.35
W_, D_ = X1 - X0, Y1 - Y0
cx, cy = 0, (Y0 + Y1) / 2
slabs = [
    ((W_, m), (cx, Y0 + m / 2), "marble"), ((W_, m), (cx, Y1 - m / 2), "marble"),
    ((m, D_ - 2 * m), (X0 + m / 2, cy), "marble"), ((m, D_ - 2 * m), (X1 - m / 2, cy), "marble"),
    ((W_ - 2 * m, band), (cx, Y0 + m + band / 2), "nero"), ((W_ - 2 * m, band), (cx, Y1 - m - band / 2), "nero"),
    ((band, D_ - 2 * m - 2 * band), (X0 + m + band / 2, cy), "nero"), ((band, D_ - 2 * m - 2 * band), (X1 - m - band / 2, cy), "nero"),
    ((W_ - 2 * m - 2 * band, D_ - 2 * m - 2 * band), (cx, cy), "marble"),
]
for (sx, sy), (px, py), key in slabs:
    K.box(K.name("ROOM", "Floor"), (sx, sy, 0.2), (px, py, -0.1), M[key], lightmap=True)
K.collider("Floor", (X0 - 1, Y0 - 1, -0.5), (X1 + 1, Y1 + 1, 0))

# nero cabochons at the tile grid (instanced), avoiding the medallion and stair
cab = K.prototype(K.box(K.name("PROP", "Cabochon"), (0.16, 0.16, 0.004), (0, 0, -30), M["nero"]))
for gx in np.arange(X0 + 1.4, X1 - 1.3, 1.2):
    for gy in np.arange(Y0 + 1.4, STAIR_Y0 - 0.3, 1.2):
        if math.hypot(gx, gy - MED_Y) < 3.3:
            continue
        K.linked(K.name("PROP", "Cabochon"), cab, (gx, gy, 0.002), rot=(0, 0, math.pi / 4))

# medallion: stacked inlays (1–2 mm apart), compass rose
for r, z, key in ((3.0, 0.001, "nero"), (2.7, 0.0022, "rosso"), (2.3, 0.0034, "marble"), (0.3, 0.007, "marble")):
    K.cyl(K.name("ROOM", "Medallion"), r, r, 0.002, (0, MED_Y, z), M[key], segments=128, smooth_angle=None, lightmap=True)
for R, r, z in ((2.82, 0.04, 0.0025), (1.15, 0.03, 0.0046), (0.32, 0.02, 0.0081)):
    K.torus(K.name("ROOM", "MedallionRing"), R, r, (0, MED_Y, z - r * 0.8), M["gilt"], major=128, minor=6)


def star(name, outer, inner, points, rot, z, mat):
    bm = bmesh.new()
    verts = []
    for i in range(points * 2):
        rr = outer if i % 2 == 0 else inner
        a = i / (points * 2) * 2 * math.pi + rot
        verts.append(bm.verts.new((rr * math.cos(a), MED_Y + rr * math.sin(a), z)))
    bm.faces.new(verts)
    return K.obj(name, bm, mat, lightmap=True)


star(K.name("ROOM", "MedallionStar"), 2.2, 0.55, 8, math.pi / 8, 0.0048, M["nero"])
star(K.name("ROOM", "MedallionStar"), 2.0, 0.4, 4, 0, 0.006, M["rosso"])

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

# centre table with a floral arrangement
K.lathe(K.name("TABLE", "Centre"), [(0, 0), (0.42, 0), (0.4, 0.05), (0.12, 0.14), (0.08, 0.35), (0.12, 0.6), (0.16, 0.74), (0, 0.74)], (0, MED_Y, 0), M["walnut"], segments=40)
K.cyl(K.name("TABLE", "CentreTop"), 0.78, 0.78, 0.05, (0, MED_Y, 0.765), M["nero"], segments=64, bevel=0.012)
K.torus(K.name("TABLE", "CentreRim"), 0.78, 0.018, (0, MED_Y, 0.765), M["gilt"], major=64, minor=6)
K.lathe(K.name("PROP", "Urn"), [(0, 0), (0.14, 0), (0.15, 0.03), (0.08, 0.1), (0.1, 0.18), (0.24, 0.36), (0.26, 0.5), (0.19, 0.6), (0.23, 0.68), (0.24, 0.72), (0, 0.72)],
        (0, MED_Y, 0.79), M["gilt"], segments=40)
K.collider("CentreTable", (-0.8, MED_Y - 0.8, 0), (0.8, MED_Y + 0.8, 0.9))
rose = K.prototype(K.lathe(K.name("PROP", "Rose"), [(0, 0), (0.035, 0.01), (0.045, 0.035), (0.03, 0.06), (0, 0.055)], (0, 0, -30), M["petal"], segments=10))
leaf = K.prototype(K.lathe(K.name("PROP", "Leaf"), [(0, 0), (0.03, 0.05), (0, 0.16)], (0, 0, -30), M["leaf"], segments=4, smooth_angle=None))
for k in range(90):
    # dome of roses
    u, v = RNG.random(), RNG.random()
    th, ph = 2 * math.pi * u, math.acos(1 - v * 0.95)
    r = 0.42
    p = (r * math.sin(ph) * math.cos(th), MED_Y + r * math.sin(ph) * math.sin(th), 1.45 + r * math.cos(ph) * 0.8)
    K.linked(K.name("PROP", "Rose"), rose, p, rot=(ph * math.cos(th), ph * math.sin(th), RNG.random() * 6))
for k in range(60):
    th = 2 * math.pi * k / 60 + RNG.random() * 0.1
    tilt = 0.9 + RNG.random() * 0.5
    K.linked(K.name("PROP", "Leaf"), leaf, (0.3 * math.cos(th), MED_Y + 0.3 * math.sin(th), 1.35 + RNG.random() * 0.1),
             rot=(tilt * math.sin(th) * -1, tilt * math.cos(th), 0))


for (gx, gy, face) in ((5.9, -0.4, 1), (-5.9, 9.6, -1), (5.9, 9.6, 1)):
    A.lamp_table(gx, gy)
    A.club_chair((gx, gy - 1.25), 0)
    A.club_chair((gx - face * 1.25, gy + 0.2), -face * math.pi / 2)
    A.club_chair((gx, gy + 1.3), math.pi)
A.console(-6.9, -1.4, math.pi / 2)

# moonlight through the east windows (bake-only)
K.light("LIGHT_Lobby_Moon_01", "SPOT", (X1 + 3, 3.0, 5.0), 25, color=(0.55, 0.63, 0.85), rng=30, bake_only=True,
        angle=math.radians(80), blend=1.0, rot=(0, math.radians(-62), 0))

A.logic(spawn=((0, -2.2, 0), (-math.pi / 2, 0, 0)), probe=(0, 4.0, 1.7), bounds=((X0, Y0, -1), (X1, Y1, H)))
mansion.save(OUT)
