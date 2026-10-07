"""Bootstrap authoring of the Stair Hall and its Vestibule (Blender → GLB → web). docs/mansion-plan.md, M1.

    npm run author:stair_hall       (blender -b --factory-startup --python blender/tools/author_stair_hall.py)

Writes blender/rooms/stair_hall/stair_hall.blend. Lighting is baked by bake_lightmap.py (npm run bake -- stair_hall).

The hall is the house's reference zone, so its local frame IS the world frame: glTF (x, y, z) = Blender (x, z, -y).
Blender +Y points north, to the sea. The origin is the centre of the arch between Vestibule and hall, at floor level.

    y = -6        front doors (forecourt)
    y = -6 … 0    Vestibule, 8 m wide, 5 m high
    y =  0 … 22   Stair Hall, 20 m wide, double height (upper floor at 5 m, ceiling at 10 m). A gallery runs round
                  three sides on fluted columns, and a landing spans the back. A laylight sits over the centre.
    stair         a horseshoe: two marble flights curve up around a fountain and meet at a balcony that projects
                  from the landing. The loggia under the landing opens onto the terrace doors.
    doors         ground floor: West Gallery (west, y 3.6), Grand Salon (west, y 15), East Gallery and Library
                  (east), Terrace (north). Upper floor: four apartment doors. Doors to unbuilt rooms are locked.
"""
import math
import os
import sys

import bmesh
import bpy  # noqa: F401
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import floors  # noqa: E402
import flora  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

ROOT = kit.ROOT
TEX = os.path.join(ROOT, "blender", "textures_src", "stair_hall")
OUT = os.path.join(ROOT, "blender", "rooms", "stair_hall", "stair_hall.blend")
UPV = Vector((0, 0, 1))

# ---------------------------------------------------------------- layout
X0, X1, Y0, Y1 = -10.0, 10.0, 0.0, 22.0
FL, HT, T, SLAB = 5.0, 10.0, 0.3, 0.4         # upper floor, hall ceiling, wall thickness, gallery slab
GX, GY = 8.0, 2.0                              # gallery inner edges: |x| = GX (sides), y = GY (front)
VX, VY0 = 4.0, -6.0                            # vestibule half-width, front wall
ARCH_W, ARCH_H = 3.2, 3.2                      # ground-storey openings stay under the frieze (field top 3.7 m)
DOOR_W, DOOR_H = 2.4, 3.2
DOOR_Y = (3.6, 15.0)                           # side doors: gallery (south row), sea-front room (north row)
BUILT = {"Salon": "grand_salon", "Library": "library"}               # side doors whose rooms exist (blender/zones.json); the rest stay locked
UP_W, UP_H = 1.9, 3.1                          # apartment doors
SC = Vector((0.0, 12.5))                       # staircase centre = fountain
R_C, SW = 5.4, 2.2
RI, RO = R_C - SW / 2, R_C + SW / 2            # 4.3 … 6.5
N = 28
RISE = FL / N
TH0, TH1 = math.radians(210), math.radians(114)   # the west flight climbs clockwise from 210° to 114°
DTH = (TH0 - TH1) / N
TH_RAIL = TH1 + 2 * DTH                        # the outer rail stops where the flight meets the landing
LY = SC.y + RO * math.sin(TH_RAIL)             # landing front edge (straight parts), ≈ 18.07
LX = -RO * math.cos(TH_RAIL)                   # … from |x| = LX outwards, ≈ 3.35
MED = (0.0, 5.6)                               # medallion, centre table, main chandelier
LAYLIGHT = (-3.0, 2.6, 3.0, 8.6)
COLUMNS = [(s * GX, y) for s in (-1, 1) for y in (GY, 6.0, 10.0, 14.0, LY)] + [(s * 4.0, GY) for s in (-1, 1)] \
    + [(s * 5.6, LY) for s in (-1, 1)] + [(s * RO * math.cos(math.radians(80)), SC.y + RO * math.sin(math.radians(80))) for s in (-1, 1)]

kit.reset_scene()
K = kit.Zone("StairHall")
A = mansion.Mansion(K, height=FL, thickness=T, sea=mansion.sea_texture(os.path.join(TEX, "T_StairHall_SeaView_Emissive.png"), seed=1907, moon_x=0.62))
A2 = mansion.Mansion(K, height=HT, thickness=T)              # the upper storey (walls from FL to HT)
A2._props, A2._sconce, A2._art_mats, A2._chair, A2._dining = A._props, A._sconce, A._art_mats, A._chair, A._dining
M = A.M
K.material("grout", "MAT_StairHall_Grout", (0.06, 0.055, 0.05), 0.85)
K.material("water", "MAT_StairHall_Water", (0.015, 0.035, 0.04), 0.03, coat=1.0, coat_rough=0.02)
K.material("veil", "MAT_StairHall_WaterVeil", (0.6, 0.7, 0.72), 0.05, alpha=0.18)
K.material("laylight", "MAT_StairHall_Laylight", (0.02, 0.03, 0.05), 0.08, emis_color=(0.3, 0.38, 0.6), emis_strength=0.25)


def P2(r, th, s, z=0.0):
    """A point on the staircase circle at radius r, angle th; s = -1 west flight, +1 east flight (mirrored)."""
    x = r * math.cos(th)
    return Vector((x if s < 0 else -x, SC.y + r * math.sin(th), z))


def face(bm, verts, normal):
    f = bm.faces.new(verts)
    f.normal_update()
    if f.normal.dot(normal) < 0:
        f.normal_flip()
    return f


def extrude_poly(name, poly, z0, z1, mats, lightmap=True):
    """A slab from a plan polygon: top (mats[0]), soffit (mats[1]) and edge (mats[2]) as three objects."""
    out = []
    for part, mat in zip(("Top", "Soffit", "Edge"), mats):
        bm = bmesh.new()
        if part == "Top":
            face(bm, [bm.verts.new((x, y, z1)) for x, y in poly], UPV)
        elif part == "Soffit":
            face(bm, [bm.verts.new((x, y, z0)) for x, y in poly], -UPV)
        else:
            ccw = sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1] for k in range(len(poly))) > 0
            for k in range(len(poly)):
                a, b = poly[k], poly[(k + 1) % len(poly)]
                ed = Vector((b[0] - a[0], b[1] - a[1], 0))
                face(bm, [bm.verts.new(p) for p in ((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1))],
                     Vector((ed.y, -ed.x, 0)) if ccw else Vector((-ed.y, ed.x, 0)))
        out.append(K.obj(K.name("ROOM", f"{name}{part}"), bm, mat, lightmap=lightmap))
    return out


def arc(r, a0, a1, s, n):
    return [P2(r, a0 + (a1 - a0) * k / n, s) for k in range(n + 1)]


# ============================================================================ floors
K.box(K.name("ROOM", "Floor"), (X1 - X0, Y1 - Y0, 0.2), (0, (Y0 + Y1) / 2, -0.1), M["marble"], lightmap=True)
K.collider("HallFloor", (X0 - 1, Y0 - 0.3, -0.5), (X1 + 1, Y1 + 1, 0))


def under_stair(x, y):
    d = Vector((x, y)) - SC
    r = d.length
    if r < 2.5:                                            # fountain basin
        return True
    if not (RI - 0.15 < r < RO + 0.15):
        return False
    th = math.atan2(d.y, -abs(x))                          # fold onto the west flight
    th = th if th > 0 else th + 2 * math.pi
    return TH1 - 0.02 <= th <= TH0 + 0.02


MARGIN, BAND, GAP = 0.55, 0.36, 0.12
band_o = (X0 + MARGIN, Y0 + MARGIN, X1 - MARGIN, Y1 - MARGIN)
band_i = (band_o[0] + BAND, band_o[1] + BAND, band_o[2] - BAND, band_o[3] - BAND)
fld = (band_i[0] + GAP, band_i[1] + GAP, band_i[2] - GAP, band_i[3] - GAP)
floors.checker(K, M, fld, MED, hole_r=3.0, skip=under_stair)
floors.key_band(K, M, band_o, band_i)
floors.medallion(K, M, MED, R=3.0)

# vestibule: Calacatta field in a Nero band; Persian runner from the front doors to the arch
A.bordered_floor(-VX, VX, VY0, -T, M["marble"], M["nero"], m=0.45, bw=0.22)
A.rug("VestRunner", 0, (VY0 - T) / 2 + 0.15, 4.9, 4.9 / 2.9977, 0, "Runner_PalmTrees", fringe=True)

# ============================================================================ walls — ground storey (A, 0 … FL)
gal_open = lambda y: (y, DOOR_W, DOOR_H)  # noqa: E731
SIDE_P = [0.0, 2.15, 5.05, 7.6, 11.0, 13.55, 16.45, 19.3, 22.0]
A.wall("Front", "x", Y0, 1, X0, X1, openings=[(0.0, ARCH_W, ARCH_H)], pilasters=[X0, -8.9, -4.3, -2.25, 2.25, 4.3, 8.9, X1],
       paintings=[(-6.6, 2), (6.6, 6)], sconces=[-8.9, -4.3, 4.3, 8.9])
A.wall("Left", "y", X0, 1, Y0, Y1, openings=[gal_open(y) for y in DOOR_Y], pilasters=SIDE_P,
       paintings=[(9.3, 0), (20.65, 1)], sconces=[2.15, 5.05, 7.6, 11.0, 13.55, 16.45, 19.3])
A.wall("Right", "y", X1, -1, Y0, Y1, openings=[gal_open(y) for y in DOOR_Y], pilasters=SIDE_P,
       paintings=[(9.3, 3), (20.65, 10)], sconces=[2.15, 5.05, 7.6, 11.0, 13.55, 16.45, 19.3])
A.wall("Back", "x", Y1, -1, X0, X1, openings=[(0.0, 2.2, DOOR_H)], windows=[-5.0, 5.0], pilasters=[X0, -6.4, -3.6, -1.55, 1.55, 3.6, 6.4, X1],
       sconces=[-6.4, -1.55, 1.55, 6.4])
# vestibule (its back wall is the hall's front wall seen from the other side)
A.wall("VestLeft", "y", -VX, 1, VY0, -T, pilasters=[VY0, -4.45, -1.85, -T], sconces=[-4.45, -1.85])
A.wall("VestRight", "y", VX, -1, VY0, -T, pilasters=[VY0, -4.45, -1.85, -T], sconces=[-4.45, -1.85])
A.wall("VestFront", "x", VY0, 1, -VX, VX, openings=[(0.0, 2.4, DOOR_H)], pilasters=[-VX, -1.65, 1.65, VX], sconces=[-1.65, 1.65],
       paintings=[(-2.85, 8), (2.85, 9)])
A.wall("VestBack", "x", -T, -1, -VX, VX, openings=[(0.0, ARCH_W, ARCH_H)], pilasters=[-VX, -2.3, 2.3, VX], mass=False, jambs=False)
A.coffered_ceiling(-VX, VX, VY0, -T, spacing=2.0)

for s, side in ((-1, "W"), (1, "E")):
    x = s * X1
    names = (("Gallery" + side, "West Gallery" if s < 0 else "East Gallery"), ("Salon" if s < 0 else "Library", "Grand Salon" if s < 0 else "Library"))
    for y, (did, title) in zip(DOOR_Y, names):
        target = BUILT.get(did)
        A.double_door(did, (x, y, 0), (-s, 0, 0), DOOR_W, DOOR_H, 0, f"Enter the {title}" if target else f"{title} — not yet open",
                      target=target, locked=not target)
A.double_door("Terrace", (0, Y1, 0), (0, -1, 0), 2.2, DOOR_H, 0, "The terrace — closed for the night", locked=True)
A.double_door("Front", (0, VY0, 0), (0, 1, 0), 2.4, DOOR_H, 0, "The front doors", locked=True)


# ============================================================================ walls — upper storey (A2, FL … HT)
UP_P = [0.0, 2.2, 5.0, 7.6, 11.0, 13.6, 16.4, 19.3, 22.0]
A2.wall("UpperFront", "x", Y0, 1, X0, X1, base=FL, pilasters=[X0, -6.0, -2.0, 2.0, 6.0, X1],
        paintings=[(-4.0, 0), (0.0, 5), (4.0, 3)], sconces=[-6.0, -2.0, 2.0, 6.0])
A2.wall("UpperLeft", "y", X0, 1, Y0, Y1, base=FL, openings=[(y, UP_W, UP_H) for y in DOOR_Y], pilasters=UP_P,
        paintings=[(6.3, 8), (9.3, 2), (12.3, 4), (20.65, 6)], sconces=UP_P[1:-1])
A2.wall("UpperRight", "y", X1, -1, Y0, Y1, base=FL, openings=[(y, UP_W, UP_H) for y in DOOR_Y], pilasters=UP_P,
        paintings=[(6.3, 9), (9.3, 1), (12.3, 7), (20.65, 5)], sconces=UP_P[1:-1])
A2.wall("UpperBack", "x", Y1, -1, X0, X1, base=FL, windows=[-4.5, 0.0, 4.5], pilasters=[X0, -6.75, -2.25, 2.25, 6.75, X1],
        paintings=[(-8.4, 10), (8.4, 2)], sconces=[-6.75, -2.25, 2.25, 6.75])
for s in (-1, 1):
    for y in DOOR_Y:
        A2.double_door(f"Apartment{'W' if s < 0 else 'E'}{K.idx('apt')}", (s * X1, y, 0), (-s, 0, 0), UP_W, UP_H, FL, "Private apartments", locked=True)

# ============================================================================ ceiling with the laylight
lx0, ly0, lx1, ly1 = LAYLIGHT
for (a, b, c, d) in ((X0, Y0, X1, ly0), (X0, ly1, X1, Y1), (X0, ly0, lx0, ly1), (lx1, ly0, X1, ly1)):
    K.box(K.name("ROOM", "Ceiling"), (c - a, d - b, 0.3), ((a + c) / 2, (b + d) / 2, HT + 0.15), M["ceiling"], lightmap=True)
BEAM_D = 0.36
xs = [X0 + 2.5 * i for i in range(1, 8)]
ys = [Y0 + 2.2 * i for i in range(1, 10)]


def beam(x0_, y0_, x1_, y1_):
    if x1_ - x0_ < 0.05 or y1_ - y0_ < 0.05:
        return
    K.box(K.name("ROOM", "Beam"), (max(0.28, x1_ - x0_), max(0.28, y1_ - y0_), BEAM_D), ((x0_ + x1_) / 2, (y0_ + y1_) / 2, HT - BEAM_D / 2), M["walnut"], lightmap=True)


for x in xs:
    if lx0 - 0.2 < x < lx1 + 0.2:
        beam(x, Y0, x, ly0 - 0.2)
        beam(x, ly1 + 0.2, x, Y1)
    else:
        beam(x, Y0, x, Y1)
for y in ys:
    if ly0 - 0.2 < y < ly1 + 0.2:
        beam(X0, y, lx0 - 0.2, y)
        beam(lx1 + 0.2, y, X1, y)
    else:
        beam(X0, y, X1, y)
rosette = K.prototype(K.lathe(K.name("PROP", "Rosette"), [(0, -0.07), (0.05, -0.065), (0.09, -0.04), (0.12, -0.02), (0.13, 0), (0, 0)], (0, 0, -30), M["gilt"], segments=16))
for x in xs:
    for y in ys:
        if not (lx0 - 0.2 < x < lx1 + 0.2 and ly0 - 0.2 < y < ly1 + 0.2):
            K.linked(K.name("PROP", "Rosette"), rosette, (x, y, HT - BEAM_D - 0.001))
# the laylight: a shaft lined in walnut, a gilt frame, glazing bars over moonlit glass
LL_D = 0.7
for size, (cx_, cy_) in (((lx1 - lx0, 0.06), ((lx0 + lx1) / 2, ly0)), ((lx1 - lx0, 0.06), ((lx0 + lx1) / 2, ly1)),
                         ((0.06, ly1 - ly0), (lx0, (ly0 + ly1) / 2)), ((0.06, ly1 - ly0), (lx1, (ly0 + ly1) / 2))):
    K.box(K.name("ROOM", "LaylightShaft"), (*size, LL_D), (cx_, cy_, HT + LL_D / 2), M["walnut"], lightmap=True)
K.box(K.name("PROP", "LaylightGlass"), (lx1 - lx0, ly1 - ly0, 0.02), ((lx0 + lx1) / 2, (ly0 + ly1) / 2, HT + LL_D - 0.05), M["laylight"])
for k in range(1, 6):
    K.box(K.name("PROP", "LaylightBar"), (0.05, ly1 - ly0, 0.08), (lx0 + k * (lx1 - lx0) / 6, (ly0 + ly1) / 2, HT + LL_D - 0.1), M["brass"])
    K.box(K.name("PROP", "LaylightBar"), (lx1 - lx0, 0.05, 0.08), ((lx0 + lx1) / 2, ly0 + k * (ly1 - ly0) / 6, HT + LL_D - 0.1), M["brass"])
K.sweep(K.name("ROOM", "LaylightFrame"), [(lx0, ly0, HT), (lx1, ly0, HT), (lx1, ly1, HT), (lx0, ly1, HT)], (0, 0, -1),
        [(0, 0), (0, 0.04), (0.06, 0.08), (0.16, 0.1), (0.26, 0.06), (0.3, 0)], M["gilt"], closed=True)

# ============================================================================ galleries, landing, balcony (FL)
# plan polygons; the landing wraps the balcony that projects over the fountain between the flights' tops
land = [(X0, Y1), (X1, Y1), (X1, LY)]
land += [(p.x, p.y) for p in arc(RO, TH_RAIL, TH1, 1, 3)]                     # east flight's outer rim, top
land += [(p.x, p.y) for p in arc(RI, TH1, math.pi / 2, 1, 8)]                 # balcony front, east half
land += [(p.x, p.y) for p in arc(RI, math.pi / 2, TH1, -1, 8)[1:]]            # … west half
land += [(p.x, p.y) for p in arc(RO, TH1, TH_RAIL, -1, 3)]
land += [(X0, LY)]
land = [(x, y) for i, (x, y) in enumerate(land) if i == 0 or (abs(x - land[i - 1][0]) > 1e-4 or abs(y - land[i - 1][1]) > 1e-4)]
slab_mats = (M["marble"], M["ceiling"], M["walnut"])
extrude_poly("Landing", land, FL - SLAB, FL, slab_mats)
for s in (-1, 1):
    extrude_poly("SideGallery", [(s * GX, Y0), (s * X1, Y0), (s * X1, LY), (s * GX, LY)], FL - SLAB, FL, slab_mats)
extrude_poly("FrontGallery", [(-GX, Y0), (GX, Y0), (GX, GY), (-GX, GY)], FL - SLAB, FL, slab_mats)
# colliders (axis-aligned, conservative around the curves)
K.collider("Landing_Back", (X0, SC.y + RO * math.sin(TH1), FL - SLAB), (X1, Y1, FL))
for s in (-1, 1):
    K.collider(f"Landing_{'W' if s < 0 else 'E'}", (min(s * LX, s * X1), LY, FL - SLAB), (max(s * LX, s * X1), Y1, FL))
    K.collider(f"Gallery_{'W' if s < 0 else 'E'}", (min(s * GX, s * X1), Y0, FL - SLAB), (max(s * GX, s * X1), LY, FL))
K.collider("Gallery_Front", (-GX, Y0, FL - SLAB), (GX, GY, FL))
for k in range(8):                                                             # the balcony, in 6° slices
    a0, a1 = TH1 - k * (TH1 - math.pi / 2) / 4 * 0.5, TH1 - (k + 1) * (TH1 - math.pi / 2) / 4 * 0.5
    pts = [P2(r, a, -1) for r in (RI + 0.05, RO) for a in (a0, a1)]
    K.collider(f"Balcony_{k + 1:02d}", (min(p.x for p in pts), min(p.y for p in pts), FL - SLAB), (max(p.x for p in pts), max(p.y for p in pts), FL))
    pts = [Vector((-p.x, p.y, 0)) for p in pts]
    K.collider(f"Balcony_{k + 9:02d}", (min(p.x for p in pts), min(p.y for p in pts), FL - SLAB), (max(p.x for p in pts), max(p.y for p in pts), FL))

# gilt fillet and dentils along the gallery fascia
FASCIA = [(-GX, LY), (-GX, GY), (GX, GY), (GX, LY)]
K.sweep(K.name("ROOM", "FasciaGilt"), [(x, y, FL - 0.06) for x, y in FASCIA], (0, 0, 1), [(0, 0), (0.025, 0.01), (0.03, 0.035), (0, 0.045)], M["gilt"])
for s in (-1, 1):
    K.sweep(K.name("ROOM", "FasciaGilt"), [(s * GX, LY, FL - 0.06), (s * LX, LY, FL - 0.06)], (0, 0, 1), [(0, 0), (0.025, 0.01), (0.03, 0.035), (0, 0.045)], M["gilt"], n1_hint=(0, -1, 0))

# ============================================================================ columns (fluted Calacatta on Nero plinths)
for (x, y) in COLUMNS:
    top = FL - SLAB
    K.box(K.name("ROOM", "ColumnPlinth"), (0.7, 0.7, 0.32), (x, y, 0.16), M["nero"], bevel=0.02, segments=3, lightmap=True)
    K.lathe(K.name("ROOM", "ColumnBase"), [(0, 0), (0.33, 0), (0.33, 0.05), (0.3, 0.1), (0.28, 0.12), (0.27, 0.16), (0, 0.16)], (x, y, 0.32), M["gilt"], segments=40)
    shaft_h = top - 0.48 - 0.62
    K.fluted_shaft(K.name("ROOM", "ColumnShaft"), 0.25, shaft_h, (x, y, 0.48), M["marble"], flutes=18, lightmap=True)
    K.lathe(K.name("ROOM", "ColumnCapital"), [(0, 0), (0.24, 0), (0.26, 0.05), (0.3, 0.2), (0.34, 0.36), (0.38, 0.44), (0, 0.44)], (x, y, 0.48 + shaft_h), M["gilt"], segments=40)
    K.box(K.name("ROOM", "ColumnAbacus"), (0.84, 0.84, 0.18), (x, y, top - 0.09), M["walnut"], bevel=0.02, segments=3, lightmap=True)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        K.torus(K.name("PROP", "CapitalVolute"), 0.06, 0.018, (x + 0.34 * math.cos(a), y + 0.34 * math.sin(a), top - 0.26), M["gilt"],
                major=16, minor=6, rot=(math.pi / 2, 0, a + math.pi / 2))
    K.collider(f"Column_{K.idx('col')}", (x - 0.36, y - 0.36, 0), (x + 0.36, y + 0.36, top))

# ============================================================================ the horseshoe staircase
P_HANDRAIL = [(0, -0.06), (0.04, -0.06), (0.075, -0.045), (0.09, -0.02), (0.09, 0.02), (0.075, 0.045), (0.04, 0.06), (0, 0.06), (0, -0.06)]
baluster = K.prototype(K.lathe(K.name("PROP", "Baluster"), [(0, 0), (0.05, 0), (0.05, 0.06), (0.032, 0.09), (0.028, 0.18), (0.05, 0.34), (0.056, 0.42), (0.032, 0.56), (0.022, 0.66), (0.04, 0.7), (0.04, 0.84), (0, 0.84)], (0, 0, -30), M["gilt"], segments=8))
rod = K.prototype(K.cyl(K.name("PROP", "StairRod"), 0.009, 0.009, 1.62, (0, 0, -30), M["brass"], segments=10, rot=(0, math.pi / 2, 0)))
RAIL_H = 0.92
SUB = 3                                                # arc subdivisions per step


def tread_top(i):
    return (i + 1) * RISE


def flight(s):
    tag = "W" if s < 0 else "E"
    side_n = lambda th, out: Vector(((1 if out else -1) * (math.cos(th) if s < 0 else -math.cos(th)), (1 if out else -1) * math.sin(th), 0))  # noqa: E731
    up_dir = lambda th: Vector(((math.sin(th) if s < 0 else -math.sin(th)), -math.cos(th), 0))   # noqa: E731  (towards higher steps)
    body, treads, strings = bmesh.new(), bmesh.new(), bmesh.new()
    run = bmesh.new()
    for i in range(N):
        ta, tb = TH0 - i * DTH, TH0 - (i + 1) * DTH
        z0, z1 = (tread_top(i - 1) if i else 0.0), tread_top(i)
        angs = [ta + (tb - ta) * k / SUB for k in range(SUB + 1)]
        # tread (and the flight's top face)
        verts = [treads.verts.new(P2(RI, a, s, z1)) for a in angs] + [treads.verts.new(P2(RO, a, s, z1)) for a in reversed(angs)]
        face(treads, verts, UPV)
        # riser
        face(body, [body.verts.new(v) for v in (P2(RI, ta, s, z0), P2(RO, ta, s, z0), P2(RO, ta, s, z1), P2(RI, ta, s, z1))], -up_dir(ta))
        # the string walls under the step, inner and outer, down to the floor
        for r, out in ((RI, False), (RO, True)):
            for a, b in zip(angs, angs[1:]):
                face(strings, [strings.verts.new(v) for v in (P2(r, a, s, 0), P2(r, b, s, 0), P2(r, b, s, z1), P2(r, a, s, z1))], side_n((a + b) / 2, out))
        # runner: carpet over the middle 1.5 m of tread and riser
        r0, r1 = R_C - 0.75, R_C + 0.75
        verts = [run.verts.new(P2(r0, a, s, z1 + 0.008)) for a in angs] + [run.verts.new(P2(r1, a, s, z1 + 0.008)) for a in reversed(angs)]
        face(run, verts, UPV)
        n_r = -up_dir(ta) * 0.012
        face(run, [run.verts.new(v + n_r) for v in (P2(r0, ta, s, z0 + 0.008), P2(r1, ta, s, z0 + 0.008), P2(r1, ta, s, z1 + 0.008), P2(r0, ta, s, z1 + 0.008))], -up_dir(ta))
        # nosing, brass stair rod at the foot of the riser
        K.sweep(K.name("ROOM", f"Nosing{tag}"), [P2(RI, ta, s, z1), P2(RO, ta, s, z1)], -up_dir(ta),
                [(0, 0), (0, 0.03), (-0.012, 0.042), (-0.03, 0.04), (-0.04, 0.022), (-0.04, 0)], M["marble"], n1_hint=UPV)
        radial = (P2(1, ta, s) - P2(0, ta, s)).normalized()
        K.linked(K.name("PROP", "StairRod"), rod, tuple(P2(R_C, ta, s, z0 + 0.012) + up_dir(ta) * 0.035), rot=(0, math.pi / 2, math.atan2(radial.y, radial.x)))
        # balusters: two per tread on each edge
        for r, out in ((RI + 0.07, False), (RO - 0.07, True)):
            if out and ta < TH_RAIL + 1e-6:
                continue
            for u in (0.28, 0.78):
                K.linked(K.name("PROP", "Baluster"), baluster, tuple(P2(r, ta + (tb - ta) * u, s, z1 + 0.02)))
        # colliders: the solid step in four radial slices, and the rails
        for k in range(4):
            ra, rb = RI + SW * k / 4, RI + SW * (k + 1) / 4
            pts = [P2(r, a, s) for r in (ra, rb) for a in (ta, tb, (ta + tb) / 2)]
            K.collider(f"Step{tag}_{i + 1:02d}_{k + 1:02d}", (min(p.x for p in pts), min(p.y for p in pts), 0), (max(p.x for p in pts), max(p.y for p in pts), z1))
        for r, out in ((RI + 0.05, False), (RO - 0.05, True)):
            if out and ta < TH_RAIL + 1e-6:
                continue
            pts = [P2(r, a, s) for a in (ta, tb)]
            K.collider(f"Rail{tag}{'O' if out else 'I'}_{i + 1:02d}", (min(p.x for p in pts) - 0.05, min(p.y for p in pts) - 0.05, z1), (max(p.x for p in pts) + 0.05, max(p.y for p in pts) + 0.05, z1 + 1.1))
    # the end wall under the balcony (θ = TH1), floor to landing
    face(body, [body.verts.new(v) for v in (P2(RI, TH1, s, 0), P2(RO, TH1, s, 0), P2(RO, TH1, s, FL), P2(RI, TH1, s, FL))], up_dir(TH1))
    K.obj(K.name("ROOM", f"Flight{tag}Risers"), body, M["marble"], lightmap=True)
    K.obj(K.name("ROOM", f"Flight{tag}Treads"), treads, M["marble"], lightmap=True)
    K.obj(K.name("ROOM", f"Flight{tag}Strings"), strings, M["marble"], lightmap=True)
    K.obj(K.name("ROOM", f"Flight{tag}Runner"), run, M["carpet"], lightmap=True)
    # outer handrail (stops where the flight meets the landing) and a gilt string course on both edges
    n_out = int(round((TH0 - TH_RAIL) / DTH))
    pts = [P2(RO - 0.07, TH0 - (i + 0.5) * DTH, s, tread_top(i) + RAIL_H) for i in range(n_out)]
    K.tube(K.name("PROP", f"Handrail{tag}O"), pts, 0.04, M["walnut"])
    for r, k_ in ((RI - 0.012, "I"), (RO + 0.012, "O")):
        pts = [P2(r, TH0 - (i + 0.5) * DTH, s, tread_top(i) - 0.09) for i in range(N)]
        K.tube(K.name("PROP", f"String{tag}{k_}"), pts, 0.022, M["gilt"])
    # the string walls are dressed like the house's walls: a Nero plinth and gilt-framed panels under the stair line
    line = lambda th: (TH0 - th) / DTH * RISE  # noqa: E731
    for r, out in ((RI, False), (RO, True)):
        off = 0.012 if out else -0.012
        band = bmesh.new()
        angs = [TH0 - (TH0 - TH1) * k / (N * 2) for k in range(N * 2 + 1)]
        for a, b in zip(angs, angs[1:]):
            face(band, [band.verts.new(v) for v in (P2(r + off, a, s, 0), P2(r + off, b, s, 0), P2(r + off, b, s, 0.24), P2(r + off, a, s, 0.24))],
                 side_n((a + b) / 2, out))
        K.obj(K.name("ROOM", f"StringPlinth{tag}"), band, M["nero"], lightmap=True)
        for j0 in range(2, N - 1, 4):
            a0, a1 = TH0 - (j0 + 0.15) * DTH, TH0 - (j0 + 3.85) * DTH
            if line(a0) - 0.5 - 0.42 < 0.55:
                continue
            arcs = [a0 + (a1 - a0) * k / 8 for k in range(9)]
            loop = [P2(r + off * 1.5, a, s, 0.42) for a in arcs] + [P2(r + off * 1.5, a, s, line(a) - 0.5) for a in reversed(arcs)]
            K.tube(K.name("PROP", f"StringPanel{tag}"), loop + [loop[0]], 0.014, M["gilt"], bezier=False)


flight(-1)
flight(1)
# inner handrail: one continuous rail down the west flight's inner edge, round the balcony, down the east flight
pts = [P2(RI + 0.07, TH0 - (i + 0.5) * DTH, -1, tread_top(i) + RAIL_H) for i in range(N)]
pts += [P2(RI + 0.07, a, -1, FL + RAIL_H) for a in [TH1 - (TH1 - math.pi / 2) * k / 6 for k in range(1, 7)]]
pts += [P2(RI + 0.07, a, 1, FL + RAIL_H) for a in [math.pi / 2 + (TH1 - math.pi / 2) * k / 6 for k in range(1, 7)]]
pts += [P2(RI + 0.07, TH0 - (i + 0.5) * DTH, 1, tread_top(i) + RAIL_H) for i in reversed(range(N))]
K.tube(K.name("PROP", "HandrailInner"), pts, 0.04, M["walnut"], resolution=4)
# balcony balusters and rail collider
n_b = int(RI * (TH1 - math.pi / 2) * 2 / 0.15)
for k in range(n_b + 1):
    a = TH1 - (TH1 - (math.pi - TH1)) * k / n_b
    K.linked(K.name("PROP", "Baluster"), baluster, tuple(P2(RI + 0.07, a, -1, FL + 0.02)))
for k in range(8):
    a0, a1 = TH1 - k * (TH1 - (math.pi - TH1)) / 8, TH1 - (k + 1) * (TH1 - (math.pi - TH1)) / 8
    pts = [P2(RI + 0.07, a, -1) for a in (a0, a1)]
    K.collider(f"BalconyRail_{k + 1:02d}", (min(p.x for p in pts) - 0.06, min(p.y for p in pts) - 0.06, FL), (max(p.x for p in pts) + 0.06, max(p.y for p in pts) + 0.06, FL + 1.1))

# newels: at both feet of each flight (lamp standards on the outer ones) and where the outer rail meets the landing
newel_cap = K.prototype(K.lathe(K.name("PROP", "NewelCap"), [(0, 0), (0.2, 0), (0.2, 0.05), (0.15, 0.08), (0.08, 0.14), (0.05, 0.2), (0, 0.22)], (0, 0, -30), M["gilt"], segments=24))


def newel(p, z, lamp=False):
    K.box(K.name("ROOM", "Newel"), (0.34, 0.34, 1.2), (p.x, p.y, z + 0.6), M["walnut"], bevel=0.015, segments=3)
    K.linked(K.name("PROP", "NewelCap"), newel_cap, (p.x, p.y, z + 1.2))
    K.collider(f"Newel_{K.idx('newel')}", (p.x - 0.18, p.y - 0.18, z), (p.x + 0.18, p.y + 0.18, z + 1.3))
    if lamp:   # a bronze lamp standard with three globes
        K.lathe(K.name("PROP", "NewelLamp"), [(0, 0), (0.05, 0), (0.03, 0.2), (0.025, 0.7), (0.06, 0.78), (0.02, 0.86), (0, 0.86)], (p.x, p.y, z + 1.42), M["brass"], segments=16)
        for k in range(3):
            a = k * 2 * math.pi / 3
            g = Vector((p.x + 0.2 * math.cos(a), p.y + 0.2 * math.sin(a), z + 2.3))
            K.tube(K.name("PROP", "NewelLampArm"), [Vector((p.x, p.y, z + 2.1)), Vector((p.x + 0.12 * math.cos(a), p.y + 0.12 * math.sin(a), z + 2.12)), g], 0.012, M["brass"])
            K.lathe(K.name("PROP", "NewelGlobe"), [(0, 0), (0.07, 0.015), (0.1, 0.1), (0.085, 0.2), (0.035, 0.24), (0, 0.24)], tuple(g), M["shade"], segments=20)
        K.lathe(K.name("PROP", "NewelGlobe"), [(0, 0), (0.08, 0.02), (0.12, 0.12), (0.1, 0.24), (0.04, 0.28), (0, 0.28)], (p.x, p.y, z + 2.28), M["shade"], segments=20)
        K.light(K.name("LIGHT", "Newel"), "POINT", (p.x, p.y, z + 2.45), 10, rng=8, bake_only=True)


for s in (-1, 1):
    newel(P2(RO + 0.05, TH0 + 0.02, s), 0.0, lamp=True)
    newel(P2(RI - 0.05, TH0 + 0.02, s), 0.0)
    newel(P2(RO + 0.05, TH_RAIL, s), FL)

# ============================================================================ gallery balustrades
P_BASE = [(0, -0.05), (0.04, -0.05), (0.04, 0.05), (0, 0.05), (0, -0.05)]


def balustrade(p0, p1, tag, inward):
    """Gilt balusters, a walnut handrail and base rail on a gallery edge at FL; collider on the edge."""
    p0, p1 = Vector((*p0, FL)), Vector((*p1, FL))
    run_ = p1 - p0
    n_ = max(2, int(run_.length / 0.16))
    for k in range(n_ + 1):
        p = p0 + run_ * (k / n_)
        K.linked(K.name("PROP", "Baluster"), baluster, (p.x, p.y, FL + 0.04))
    side = UPV.cross(run_.normalized())
    K.sweep(K.name("PROP", f"{tag}Handrail"), [p0 + UPV * (RAIL_H + 0.04), p1 + UPV * (RAIL_H + 0.04)], side, P_HANDRAIL, M["walnut"], n1_hint=UPV)
    K.sweep(K.name("PROP", f"{tag}BaseRail"), [p0, p1], side, P_BASE, M["walnut"], n1_hint=UPV)
    lo, hi = Vector((min(p0.x, p1.x), min(p0.y, p1.y))), Vector((max(p0.x, p1.x), max(p0.y, p1.y)))
    K.collider(f"Balustrade{tag}_{K.idx('bal' + tag)}", (lo.x - 0.1, lo.y - 0.1, FL), (hi.x + 0.1, hi.y + 0.1, FL + 1.1))


E = 0.12
for s in (-1, 1):
    tag = "W" if s < 0 else "E"
    balustrade((s * (GX + E), GY - E), (s * (GX + E), LY + E), f"Side{tag}", (-s, 0))
    balustrade((s * (GX + E), LY + E), (s * (LX + 0.1), LY + E), f"Landing{tag}", (0, -1))
balustrade((-(GX + E), GY - E), (GX + E, GY - E), "Front", (0, 1))

# ============================================================================ the fountain: basin, tazza, bronze figure
basin = [(2.2, 0), (2.25, 0.04), (2.25, 0.12), (2.18, 0.16), (2.18, 0.4), (2.26, 0.44), (2.28, 0.5), (2.24, 0.54), (2.1, 0.55), (2.06, 0.5), (2.06, 0.12), (0, 0.12)]
K.lathe(K.name("ROOM", "FountainBasin"), basin, (SC.x, SC.y, 0), M["rosso"], segments=96, lightmap=True)
K.cyl(K.name("PROP", "FountainWater"), 2.06, 2.06, 0.01, (SC.x, SC.y, 0.42), M["water"], segments=96)
ped = [(0.62, 0), (0.62, 0.08), (0.5, 0.14), (0.36, 0.3), (0.3, 0.62), (0.36, 0.78), (0.32, 0.86), (0.2, 0.92), (0.16, 1.02), (0, 1.02)]
K.lathe(K.name("ROOM", "FountainPedestal"), ped, (SC.x, SC.y, 0.12), M["marble"], segments=48, lightmap=True)
tazza = [(0.16, 0), (0.3, 0.05), (0.6, 0.14), (0.8, 0.22), (0.84, 0.28), (0.8, 0.3), (0.6, 0.22), (0.3, 0.16), (0, 0.15)]
K.lathe(K.name("PROP", "FountainTazza"), tazza, (SC.x, SC.y, 1.1), M["marble"], segments=64)
K.cyl(K.name("PROP", "FountainWater"), 0.62, 0.62, 0.008, (SC.x, SC.y, 1.36), M["water"], segments=64)
K.lathe(K.name("PROP", "FountainVeil"), [(0.81, 0), (0.86, -0.08), (0.9, -0.35), (0.93, -0.94)], (SC.x, SC.y, 1.38), M["veil"], segments=64)
for r, z in ((2.27, 0.47), (0.84, 1.37)):
    K.torus(K.name("PROP", "FountainRing"), r, 0.012, (SC.x, SC.y, z), M["gilt"], major=96, minor=6)
K.lathe(K.name("PROP", "FountainPlinth"), [(0.3, 0), (0.3, 0.06), (0.24, 0.1), (0.22, 0.28), (0.28, 0.32), (0.28, 0.36), (0, 0.36)], (SC.x, SC.y, 1.3), M["nero"], segments=32)
A.prop("gothic_statue", "Statue", scale=0.95, decimate=0.35)
A.place("Statue", (SC.x, SC.y, 1.66), math.pi)                       # faces the entrance
for hx, hy in ((2.28, 0.96), (0.96, 2.28), (1.65, 1.65)):
    K.collider(f"Fountain_{K.idx('fountain')}", (SC.x - hx, SC.y - hy, 0), (SC.x + hx, SC.y + hy, 3.4))
A.audio("Fountain", (SC.x, SC.y, 0.8), "fountain", gain=0.5, mode="loop")

# ============================================================================ chandeliers & light
A2.chandelier(MED[0], MED[1], scale=1.5, drop=2.6, point_cd=120, key_cd=200)
A2.chandelier(SC.x, SC.y, scale=1.05, drop=2.4, point_cd=55, key=False, tiers=2)
A.audio("Chandelier", (MED[0], MED[1], 5.5), "crystal", gain=0.3, interval=(9, 22))
lantern = A.prop("Chandelier_03", "CandleChandelier", decimate=0.3)
lh = lantern["dims"][2]


def hang(x, y, ceil, cd=9):
    A.place("CandleChandelier", (x, y, ceil - lh), 0)
    K.light(K.name("LIGHT", "CandleChandelier"), "POINT", (x, y, ceil - 0.6), cd, rng=7, bake_only=True)


for s in (-1, 1):
    hang(s * 9.0, 9.3, FL - SLAB)                 # over the bergère niches
    hang(s * 7.2, 20.3, FL - SLAB)                # the loggia
    hang(s * 6.6, 1.0, FL - SLAB, cd=7)           # over the settees
hang(0.0, 20.6, FL - SLAB)
hang(0.0, VY0 / 2 - 0.15, FL, cd=12)               # vestibule
# moonlight through the sea windows (bake-only): over the landing and down into the hall
K.light("LIGHT_StairHall_Moon_01", "SPOT", (0.0, Y1 + 4.0, 9.5), 30, color=(0.55, 0.63, 0.85), rng=30, bake_only=True,
        angle=math.radians(70), blend=1.0, rot=(math.radians(-58), 0, 0))
K.light("LIGHT_StairHall_Moon_02", "SPOT", (0.0, Y1 + 4.0, 4.4), 14, color=(0.55, 0.63, 0.85), rng=20, bake_only=True,
        angle=math.radians(70), blend=1.0, rot=(math.radians(-70), 0, 0))

# ============================================================================ furnishing (photoscanned, CC0)
A.prop("Sofa_01", "LouisSofa", tint={"Sofa": (0.62, 0.5, 0.36)}, scale=1.15)
A.prop("gothic_coffee_table", "CoffeeTable", scale=0.72, decimate=0.45)
A.prop("ClassicConsole_01", "Console", decimate=0.5)
A.prop("ornate_mirror_01", "Mirror", scale=2.1, origin="back", decimate=0.4)
A.prop("brass_candleholders", "Candelabra", pick=["candleholder_03"], decimate=0.2)
A.prop("antique_ceramic_vase_01", "Vase")
A.prop("brass_vase_01", "BrassVase", scale=0.8, decimate=0.15)
A.prop("mantel_clock_01", "MantelClock", decimate=0.2)
A.prop("marble_bust_01", "Bust", decimate=0.3)
A.prop("horse_statue_01", "Horse", scale=4.2, decimate=0.6)
A.prop("lion_head", "Lion", scale=1.7, decimate=0.25)
A.prop("vintage_grandfather_clock_01", "GrandfatherClock")
A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.15)


def console_group(wx, wy, rz, z0=0.0, clock=False, mirror=True):
    """Carved console against the wall point (wx, wy) (rz: 0 = facing +Y), ornate mirror above, candelabra and a
    vase or mantel clock on top."""
    n = Vector((-math.sin(rz), math.cos(rz), 0))
    t = Vector((math.cos(rz), math.sin(rz), 0))
    base = Vector((wx, wy, z0))
    A.place("Console", tuple(base + n * 0.42), rz, collide=(0.78, 0.32, 0.95))
    if mirror:
        A.place("Mirror", tuple(base + n * 0.07 + Vector((0, 0, 1.98))), rz)
    A.place("Candelabra", tuple(base + n * 0.4 + t * 0.48 + Vector((0, 0, 0.95))), rz)
    A.place("MantelClock" if clock else "BrassVase", tuple(base + n * 0.4 - t * 0.42 + Vector((0, 0, 0.95))), rz)
    K.light(K.name("LIGHT", "Candelabra"), "POINT", tuple(base + n * 0.4 + t * 0.48 + Vector((0, 0, 1.85))), 4, rng=5, bake_only=True)


def pedestal(x, y, z0=0.0, h=1.12):
    K.box(K.name("PROP", "PedestalBase"), (0.5, 0.5, 0.14), (x, y, z0 + 0.07), M["nero"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalShaft"), (0.36, 0.36, h - 0.28), (x, y, z0 + 0.14 + (h - 0.28) / 2), M["marble"], bevel=0.01, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalCap"), (0.48, 0.48, 0.12), (x, y, z0 + h - 0.08), M["nero"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalCap"), (0.42, 0.42, 0.04), (x, y, z0 + h - 0.02), M["gilt"], bevel=0.006)
    K.collider(f"BustPedestal_{K.idx('ped')}", (x - 0.26, y - 0.26, z0), (x + 0.26, y + 0.26, z0 + h + 0.6))


def jardiniere_plant(x, y, z=0.0):
    K.lathe(K.name("PROP", "Jardiniere"), [(0, 0), (0.16, 0), (0.17, 0.03), (0.12, 0.08), (0.2, 0.2), (0.3, 0.36), (0.32, 0.46), (0.3, 0.48), (0, 0.48)],
            (x, y, z), M["brass"], segments=40)
    A.place("Plant", (x, y, z + 0.2), 0)
    K.collider(f"Plant_{K.idx('plant')}", (x - 0.34, y - 0.34, z), (x + 0.34, y + 0.34, z + 1.3))


def chair_pair(x, y, rz, gap=1.5, z0=0.0, lamp=True):
    """Two velvet bergères (the house's comfort chair) angled towards each other, a lamp table between."""
    t = Vector((math.cos(rz), math.sin(rz), 0))
    for k in (-1, 1):
        p = Vector((x, y, 0)) + t * (k * gap / 2)
        A.club_chair((p.x, p.y), rz + k * 0.32, z=z0)
    if lamp:
        A.lamp_table(x, y, candela=5)


# --- vestibule: consoles with mirrors, bergères by the doors, palms, an umbrella stand
for s in (-1, 1):
    console_group(s * VX, -3.15, s * math.pi / 2, clock=s > 0)
    jardiniere_plant(s * (VX - 0.5), VY0 + 0.5)
    A.club_chair((s * 2.55, VY0 + 0.75), 0.0 if s < 0 else 0.0)
K.lathe(K.name("PROP", "UmbrellaStand"), [(0, 0), (0.13, 0), (0.14, 0.02), (0.12, 0.05), (0.12, 0.52), (0.14, 0.56), (0, 0.56)], (-VX + 0.5, -1.0, 0), M["brass"], segments=24)
for k, (dx, dy, tilt) in enumerate(((0.03, 0.02, 0.06), (-0.04, 0.03, -0.08), (0.0, -0.05, 0.1))):
    K.cyl(K.name("PROP", "WalkingCane"), 0.012, 0.012, 0.92, (-VX + 0.5 + dx, -1.0 + dy, 0.47), M["walnut_dark"], segments=8, rot=(tilt, -tilt, 0))
K.collider("UmbrellaStand", (-VX + 0.35, -1.15, 0), (-VX + 0.65, -0.85, 1.0))

# --- hall, entrance side: consoles flank the arch; Louis settees with bergères at the front corners
for s in (-1, 1):
    console_group(s * 3.275, Y0, 0.0, clock=s > 0)
    cx = s * 6.6
    A.rug(f"SettleRug{K.idx('rug')}", cx, 2.05, 3.0, 3.0 / 1.1469, math.pi / 2, "Rug_Kazak", fringe=True)
    A.place("LouisSofa", (cx, 0.62, 0.011), 0.0, collide=(0.95, 0.4, 0.8))
    A.place("CoffeeTable", (cx, 1.85, 0.011), 0.0, collide=(0.5, 0.5, 0.42))
    for k in (-1, 1):
        A.club_chair((cx + k * 0.95, 2.95), math.pi - k * 0.45)
    for k in (-1, 1):
        A.lamp_table(cx + k * 1.3, 0.45, candela=5)

# --- centre table with a grand floral arrangement under the main chandelier
K.lathe(K.name("TABLE", "Centre"), [(0, 0), (0.5, 0), (0.48, 0.06), (0.16, 0.16), (0.1, 0.36), (0.15, 0.6), (0.2, 0.74), (0, 0.74)], (MED[0], MED[1], 0), M["walnut"], segments=48)
K.cyl(K.name("TABLE", "CentreTop"), 0.95, 0.95, 0.05, (MED[0], MED[1], 0.765), M["nero"], segments=72, bevel=0.012)
K.torus(K.name("TABLE", "CentreRim"), 0.95, 0.02, (MED[0], MED[1], 0.765), M["gilt"], major=72, minor=6)
K.lathe(K.name("PROP", "Urn"), [(0, 0), (0.17, 0), (0.18, 0.035), (0.1, 0.12), (0.12, 0.21), (0.29, 0.42), (0.31, 0.58), (0.23, 0.7), (0.28, 0.79), (0.29, 0.84), (0, 0.84)],
        (MED[0], MED[1], 0.79), M["gilt"], segments=48)
K.collider("CentreTable", (MED[0] - 0.98, MED[1] - 0.98, 0), (MED[0] + 0.98, MED[1] + 0.98, 0.9))
flora.arrangement(K, MED, 0.79 + 0.84, radius=0.55, height=0.58, reds=95, ivories=70, leaves=200, sprays=22)

# --- porcelain horses on plinths at the feet of the flights
for s in (-1, 1):
    p = P2(RO + 0.9, TH0 + 0.12, s)
    K.box(K.name("PROP", "StatuePlinth"), (0.62, 0.62, 0.18), (p.x, p.y, 0.09), M["nero"], bevel=0.015, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.5, 0.5, 0.72), (p.x, p.y, 0.18 + 0.36), M["rosso"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.6, 0.6, 0.08), (p.x, p.y, 0.94), M["nero"], bevel=0.012, segments=2, lightmap=True)
    A.place("Horse", (p.x, p.y, 0.98), (math.pi / 2 if s < 0 else -math.pi / 2) + math.pi)
    K.collider(f"Statue_{K.idx('statue')}", (p.x - 0.32, p.y - 0.32, 0), (p.x + 0.32, p.y + 0.32, 2.0))

# --- side aisles: busts flank every door, a pair of bergères in the middle bay, clock and console in the loggia
for s in (-1, 1):
    wx = s * X1
    for y in DOOR_Y:
        for dy in (-1.95, 1.95):
            pedestal(wx - s * 0.5, y + dy)
            A.place("Bust", (wx - s * 0.5, y + dy, 1.12), s * math.pi / 2)    # faces local +Y like every prop: looks into the hall
    chair_pair(wx - s * 0.62, 9.3, s * math.pi / 2)
    jardiniere_plant(wx - s * 0.55, Y0 + 0.55)
A.place("GrandfatherClock", (X0 + 0.45, 17.95, 0), -math.pi / 2, collide=(0.32, 0.25, 2.2))
console_group(X1, 17.95, math.pi / 2, clock=True)

# --- loggia: bronze lions flank the terrace doors; window seats under the sea windows
for s in (-1, 1):
    pedestal(s * 1.95, Y1 - 0.55)
    A.place("Lion", (s * 1.95, Y1 - 0.55, 1.12), math.pi)
    chair_pair(s * 5.0, Y1 - 0.75, math.pi, gap=1.7)
    jardiniere_plant(s * (X1 - 0.55), Y1 - 0.55)

# --- the landing and galleries (FL): settee under the centre window, chairs at the side windows, consoles, busts
A.rug("LandingRunner", 0.0, 20.05, 5.4, 5.4 / 2.9977, math.pi / 2, "Runner_PalmTrees", fringe=True, z0=FL)
A.place("LouisSofa", (0.0, Y1 - 0.6, FL + 0.011), math.pi, collide=(0.95, 0.4, 0.8))
for s in (-1, 1):
    chair_pair(s * 4.5, Y1 - 0.75, math.pi, gap=1.7, z0=FL, lamp=False)
    K.lathe(K.name("PROP", "Gueridon"), [(0, 0), (0.22, 0), (0.2, 0.03), (0.04, 0.08), (0.03, 0.66), (0.28, 0.68), (0.28, 0.72), (0, 0.72)],
            (s * 4.5, Y1 - 0.6, FL), M["walnut"], segments=32)
    A.place("BrassVase", (s * 4.5, Y1 - 0.6, FL + 0.72), 0)
    K.collider(f"Gueridon_{K.idx('gue')}", (s * 4.5 - 0.3, Y1 - 0.9, FL), (s * 4.5 + 0.3, Y1 - 0.3, FL + 0.9))
    console_group(s * X1, 20.65, s * math.pi / 2, z0=FL, clock=s < 0, mirror=False)
    jardiniere_plant(s * (X1 - 0.55), Y1 - 0.55, FL)
    jardiniere_plant(s * (X1 - 0.55), Y0 + 0.55, FL)
    console_group(s * X1, 9.3, s * math.pi / 2, z0=FL, clock=s > 0, mirror=False)
    for y in DOOR_Y:
        for dy in (-1.55, 1.55):
            pedestal(s * (X1 - 0.45), y + dy, FL)
            A.place("Bust", (s * (X1 - 0.45), y + dy, FL + 1.12), s * math.pi / 2)
    for y in (5.85, 9.65, 13.45):
        A.rug(f"GalleryRunner{K.idx('grun')}", s * 8.85, y, 3.6, 3.6 / 3.8109, 0, "Runner_Mamluk", fringe=False, z0=FL)
    A.place("LouisSofa", (s * 4.0, Y0 + 0.6, FL + 0.011), 0.0, collide=(0.95, 0.4, 0.8))

# ============================================================================ logic
A.logic(spawn=((0, VY0 + 1.5, 0), (-math.pi / 2, 0, 0)), probe=(0, 8.0, 2.2), bounds=((X0, VY0, -1), (X1, Y1, HT + 1)))
mansion.save(OUT)
