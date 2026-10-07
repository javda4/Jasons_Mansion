"""Bootstrap authoring of the Grand Ballroom (Blender → GLB → web). docs/mansion-plan.md, M3 (rebuilt 2026-10-07).

    npm run author:ballroom         (blender -b --factory-startup --python blender/tools/author_ballroom.py)

The villa's showpiece, through the Grand Salon's enfilade door: 18 × 30 m and 9 m high. From the door the eye runs
down the whole length:
- **Dance floor:** a marble-banded parquet with an inlaid compass rose, under four great crystal chandeliers
  (kept low: the room glows rather than blazes).
- **Long walls:** giant fluted marble columns. Between them, on the sea side, six tall French windows open onto
  the night with pleated velvet drapes; on the other side six arched mirrors answer them (a galerie des glaces).
- **Grand stage:** at the far end, behind a gilt proscenium with swagged velvet theatre curtains, footlights and a
  painted backdrop. An orchestra is set out on it: a grand piano, a harp, music stands and gilt chairs round a
  conductor's podium.
- **Ceiling and walls:** a painted ceiling panel in a gilt frame; a musicians' gallery over the entrance; gilt
  torchères, velvet banquettes, gilt chairs, palms and porcelain horses.

Roulette is here to be played but stays out of the way: two tables in the bays either side of the entrance.

Zone anchor: the centre of the doorway from the Grand Salon (its back wall, world x = -26.3, y = 15). The room runs
along local +Y (world west) and local +X points north (the sea), like the salon.
"""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(__file__))
import casino_props as C  # noqa: E402
import floors  # noqa: E402
import furniture as F  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

OUT = os.path.join(kit.ROOT, "blender", "rooms", "ballroom", "ballroom.blend")
TEX = os.path.join(kit.ROOT, "blender", "textures_src", "ballroom")
W, D, H, T = 18.0, 30.0, 9.0, 0.3
X0, X1 = -W / 2, W / 2                 # X0 = south (the mirrors), X1 = north (the windows, the sea)
DOOR_W, DOOR_H = 2.4, 3.2
BAYS = [3.6, 7.2, 10.8, 14.4, 18.0, 21.6]          # window / mirror centres along the long walls
PIERS = [1.8, 5.4, 9.0, 12.6, 16.2, 19.8, 23.4]    # the columns stand in front of these
STAGE_Y, STAGE_H = 24.2, 1.1                        # the stage's front edge and floor height
PROS = (-6.6, 6.6, 7.6)                             # proscenium opening x0, x1 and its crown height
COL_X = W / 2 - 0.75                                # column centres, off the long walls
TABLES = ((-5.2, 4.0), (5.2, 4.0))                  # roulette, in the bays either side of the entrance
DIM = 0.6                                           # the room's lights, turned down

kit.reset_scene()
K = kit.Zone("Ballroom")
M0 = mansion.library_materials(K)
A = mansion.Mansion(K, height=H, thickness=T, trim=M0["paint"], panel=M0["paint"], ceiling=M0["paint"],
                    sea=mansion.sea_texture(os.path.join(TEX, "T_Ballroom_SeaView_Emissive.png"), seed=1925, moon_x=0.35))
A.win_sill, A.win_w = 0.55, 2.0                      # tall French windows (and mirrors to match)
M = A.M
FIELD = M["damask_gold"]
K.material("grout", "MAT_Ballroom_Grout", (0.06, 0.055, 0.05), 0.85)

# ============================================================================ floor
K.box(K.name("ROOM", "Floor"), (W, D, 0.2), (0, D / 2, -0.1), M["parquet"], lightmap=True)
K.collider("Floor", (X0 - 0.5, -0.5, -0.5), (X1 + 0.5, D + 0.5, 0))
# a Nero-and-Calacatta border round the dance floor, and the compass rose at its heart
band_o = (X0 + 1.4, 0.9, X1 - 1.4, STAGE_Y - 1.6)
band_i = (band_o[0] + 0.42, band_o[1] + 0.42, band_o[2] - 0.42, band_o[3] - 0.42)
floors.key_band(K, M, band_o, band_i)
floors.medallion(K, M, (0.0, 12.0), R=3.2)

# ============================================================================ walls
A.wall("Front", "x", 0, 1, X0, X1, openings=[(0.0, DOOR_W, DOOR_H)], jambs=False, field=FIELD,
       pilasters=[X0, -6.0, -2.4, -1.65, 1.65, 2.4, 6.0, X1], sconces=[-6.0, 6.0])        # the musicians' gallery spans this wall
A.wall("North", "y", X1, -1, 0, D, field=FIELD, pilasters=[0.0] + PIERS + [D], windows=BAYS)
A.wall("South", "y", X0, 1, 0, D, field=FIELD, pilasters=[0.0] + PIERS + [D], mirrors=BAYS)
A.wall("Back", "x", D, -1, X0, X1, field=FIELD, pilasters=[X0, X1])
A.outside("NorthOut", "y", X1, -1, 0, D, extend=0.15)          # the sea terrace beyond the French windows
A.coffered_ceiling(X0, X1, 0, D, spacing=3.0)

# giant marble columns before every pier
for y in PIERS:
    for s in (-1, 1):
        F.column(A, (s * COL_X, y), A.field_top - 0.05, r=0.3)

# the painted ceiling: a great canvas in a gilt frame between the chandeliers
art, aspect = A.art_material(3)
cw = 10.0
ch = cw / aspect
cz = H - 0.37
bm = bmesh.new()
uv = bm.loops.layers.uv.verify()
f = bm.faces.new([bm.verts.new((x, 12.0 + y, cz)) for x, y in ((-cw / 2, -ch / 2), (cw / 2, -ch / 2), (cw / 2, ch / 2), (-cw / 2, ch / 2))])
for loop, q in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    loop[uv].uv = q
if f.normal.z > 0:
    f.normal_flip()
K.obj(K.name("PROP", "CeilingPainting"), bm, art, uv=None)
K.sweep(K.name("ROOM", "CeilingPaintingFrame"), [(-cw / 2, 12 - ch / 2, cz), (cw / 2, 12 - ch / 2, cz), (cw / 2, 12 + ch / 2, cz), (-cw / 2, 12 + ch / 2, cz)], (0, 0, -1),
        [(0, 0), (0, 0.05), (0.08, 0.1), (0.2, 0.12), (0.34, 0.08), (0.4, 0)], M["gilt"], closed=True)

# ============================================================================ the grand stage
sx0, sx1, sz = PROS
K.box(K.name("ROOM", "Stage"), (W, D - STAGE_Y, STAGE_H), (0, (STAGE_Y + D) / 2, STAGE_H / 2), M["walnut"], lightmap=True)
K.box(K.name("ROOM", "StageApron"), (W, 0.06, STAGE_H), (0, STAGE_Y - 0.03, STAGE_H / 2), M["walnut_dark"], lightmap=True)
K.box(K.name("ROOM", "StageNosing"), (W, 0.1, 0.08), (0, STAGE_Y - 0.03, STAGE_H - 0.04), M["gilt"], bevel=0.015)
K.collider("Stage", (X0, STAGE_Y, 0), (X1, D, STAGE_H))
# a broad flight up to the stage in the centre
for k in range(5):
    z = STAGE_H * (k + 1) / 5
    y0 = STAGE_Y - 0.36 * (5 - k)
    K.box(K.name("ROOM", "StageStep"), (5.2 - k * 0.2, 0.36, z), (0, y0 + 0.18, z / 2), M["marble"], bevel=0.01, lightmap=True)
    K.box(K.name("PROP", "StageStepRunner"), (3.0, 0.38, 0.012), (0, y0 + 0.19, z + 0.006), M["carpet"])
    K.collider(f"StageStep_{k + 1:02d}", (-2.6 + k * 0.1, y0, 0), (2.6 - k * 0.1, y0 + 0.36, z))
# footlights: brass shells along the apron, glowing up at the curtain
shell = K.prototype(K.lathe(K.name("PROP", "Footlight"), [(0, 0), (0.08, 0.0), (0.09, 0.03), (0.06, 0.06), (0, 0.06)], (0, 0, -30), M["brass"], segments=12))
glow = K.prototype(K.cyl(K.name("PROP", "FootlightGlow"), 0.05, 0.05, 0.012, (0, 0, -30), M["shade"], segments=12))
for x in [sx0 + 0.6 + k * 0.8 for k in range(int((sx1 - sx0 - 1.0) / 0.8) + 1)]:
    if abs(x) < 2.8:
        continue
    K.linked(K.name("PROP", "Footlight"), shell, (x, STAGE_Y + 0.18, STAGE_H))
    K.linked(K.name("PROP", "FootlightGlow"), glow, (x, STAGE_Y + 0.18, STAGE_H + 0.055))
for x in (-5.0, -3.4, 3.4, 5.0):
    K.light(K.name("LIGHT", "Footlight"), "POINT", (x, STAGE_Y + 0.3, STAGE_H + 0.15), 3 * DIM * 2, color=(1.0, 0.72, 0.42), rng=5, bake_only=True)
# the proscenium: a wall across the room with an arched opening, gilt mouldings and a crowning cartouche
PY = STAGE_Y + 0.6
spring = sz - 1.2
outline = [(sx0, STAGE_H), (sx0, spring)] + [(sx0 + (sx1 - sx0) * (0.5 - 0.5 * math.cos(math.pi * k / 24)), spring + 1.2 * math.sin(math.pi * k / 24)) for k in range(1, 24)] + [(sx1, spring), (sx1, STAGE_H)]
for side in (-1, 1):   # the piers either side of the opening
    xa, xb = (X0, sx0) if side < 0 else (sx1, X1)
    K.box(K.name("ROOM", "Proscenium"), (xb - xa, 0.6, H - STAGE_H), ((xa + xb) / 2, PY, (H + STAGE_H) / 2), M["paint"], lightmap=True)
K.box(K.name("ROOM", "Proscenium"), (sx1 - sx0, 0.6, H - sz), (0, PY, (H + sz) / 2), M["paint"], lightmap=True)
for sgn in (-1, 1):    # spandrels over the arch
    poly = [(sgn * (sx1 - sx0) / 2, spring)] + [(sgn * (sx1 - sx0) / 2 * math.cos(math.pi * k / 24), spring + 1.2 * math.sin(math.pi * k / 24)) for k in range(1, 13)] + [(0, sz), (sgn * (sx1 - sx0) / 2, sz)]
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x, PY - 0.3, z)) for x, z in poly])
    if face.normal.y > 0:
        face.normal_flip()
    K.obj(K.name("ROOM", "ProsceniumSpandrel"), bm, M["paint"], lightmap=True)
K.sweep(K.name("ROOM", "ProsceniumFrame"), [(x, PY - 0.3, z) for x, z in outline], (0, -1, 0),
        [(0, 0), (0, 0.06), (0.1, 0.12), (0.28, 0.14), (0.42, 0.1), (0.5, 0)], M["gilt"], n1_hint=(1, 0, 0))
K.sweep(K.name("ROOM", "ProsceniumFrame"), [(x, PY - 0.3, z) for x, z in outline], (0, -1, 0),
        [(0.62, 0), (0.62, 0.03), (0.68, 0.05), (0.72, 0)], M["gilt"], n1_hint=(1, 0, 0))
K.lathe(K.name("PROP", "ProsceniumCartouche"), [(0, 0), (0.6, 0.0), (0.7, 0.06), (0.55, 0.14), (0.25, 0.2), (0, 0.22)], (0, PY - 0.31, sz + 0.55), M["gilt"],
        segments=32, rot=(math.pi / 2, 0, 0))
for s in (-1, 1):
    K.collider(f"Proscenium_{'W' if s < 0 else 'E'}", (min(s * X1, s * sx1), PY - 0.3, 0), (max(s * X1, s * sx1), PY + 0.3, H))
    F.column(A, (s * (sx1 + 0.6), STAGE_Y - 0.55), H - 1.2, r=0.32)                    # flanking the stage front
F.theatre_curtains(A, sx0 + 0.05, sx1 - 0.05, PY + 0.05, STAGE_H, sz - 0.05, tie_z=STAGE_H + 1.7, valance=1.1)
# the painted backdrop behind the orchestra
art2, aspect2 = A.art_material(2)
bw = 11.0
bh = min(bw / aspect2, H - STAGE_H - 0.4)
bm = bmesh.new()
uv = bm.loops.layers.uv.verify()
f = bm.faces.new([bm.verts.new((x, D - 0.32, z)) for x, z in ((-bw / 2, STAGE_H + 0.3), (bw / 2, STAGE_H + 0.3), (bw / 2, STAGE_H + 0.3 + bh), (-bw / 2, STAGE_H + 0.3 + bh))])
for loop, q in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    loop[uv].uv = q
if f.normal.y > 0:
    f.normal_flip()
K.obj(K.name("PROP", "Backdrop"), bm, art2, uv=None)
# the orchestra
F.grand_piano(A, (-4.8, 26.8), -math.pi / 2 + 0.25, z0=STAGE_H)
F.harp(A, (4.4, 27.4), math.pi + 0.6, z0=STAGE_H)
for k in range(7):
    a = math.radians(-60 + k * 20)
    x, y = 3.4 * math.sin(a), 28.6 - 2.4 * math.cos(a)
    if x < -1.6:
        continue
    F.gilt_chair(A, (x, y), math.pi + a * 0.6, z0=STAGE_H)
    F.music_stand(A, (x + 0.55 * math.sin(a), y - 0.6), math.pi + a * 0.6 + math.pi, z0=STAGE_H)
K.box(K.name("PROP", "Podium"), (0.9, 0.9, 0.22), (0.4, 25.6, STAGE_H + 0.11), M["velvet"], bevel=0.02)
K.collider("Podium", (-0.05, 25.15, STAGE_H), (0.85, 26.05, STAGE_H + 0.25))
F.music_stand(A, (0.4, 25.95), 0.0, z0=STAGE_H + 0.22)
for x in (-4.6, 4.6):
    K.light(K.name("LIGHT", "StageWash"), "SPOT", (x * 0.4, 15.0, H - 0.6), 40 * DIM, color=(1.0, 0.8, 0.58), rng=20, bake_only=True,
            angle=math.radians(40), blend=0.7, rot=(math.radians(58), 0, math.radians(-x * 2)))

# ============================================================================ the musicians' gallery over the entrance
F.gallery_walk(A, (X0 + 0.9, 0.0), (X1 - 0.9, 0.0), (0, 1), 4.6, depth=1.4)

# ============================================================================ light: four great chandeliers, turned low
for i, y in enumerate((5.0, 10.0, 15.0, 20.0)):
    A.chandelier(0, y, scale=1.45, drop=1.8, point_cd=36 * DIM, key=(i == 1), key_cd=55)
A.audio("Chandelier", (0, 12, 6.0), "crystal", gain=0.28, interval=(9, 20))
K.light("LIGHT_Ballroom_Moon_01", "SPOT", (X1 + 4.0, 12.0, 7.0), 26, color=(0.55, 0.63, 0.85), rng=30, bake_only=True,
        angle=math.radians(85), blend=1.0, rot=(0, math.radians(56), 0))

# ============================================================================ round the walls
A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.15)
A.prop("horse_statue_01", "Horse", scale=4.2, decimate=0.6)


def jardiniere(x, y, z=0.0):
    K.lathe(K.name("PROP", "Jardiniere"), [(0, 0), (0.16, 0), (0.17, 0.03), (0.12, 0.08), (0.2, 0.2), (0.3, 0.36), (0.32, 0.46), (0.3, 0.48), (0, 0.48)],
            (x, y, z), M["brass"], segments=40)
    A.place("Plant", (x, y, z + 0.2), 0)
    K.collider(f"Plant_{K.idx('plant')}", (x - 0.34, y - 0.34, z), (x + 0.34, y + 0.34, z + 1.3))


for b in BAYS[2:]:
    F.banquette(A, (X0 + 0.45, b), -math.pi / 2, length=1.9)       # under the mirrors
for b in BAYS[1:]:
    for s in (-1, 1):
        F.gilt_chair(A, (X1 - 1.2, b + s * 0.36), math.pi / 2)              # before the windows, between the drapes
for y in (PIERS[1], PIERS[3], PIERS[5]):
    for s in (-1, 1):
        F.torchere(A, (s * (COL_X - 0.95), y), candela=3)
for s in (-1, 1):
    F.torchere(A, (s * 3.0, STAGE_Y - 2.2), candela=4)
    jardiniere(s * 6.2, STAGE_Y - 0.8)
    jardiniere(s * (X1 - 0.7), 0.7)
# porcelain horses on plinths either side of the door from the salon
for s in (-1, 1):
    x_, y_ = s * 2.0, 1.0
    K.box(K.name("PROP", "StatuePlinth"), (0.62, 0.62, 0.18), (x_, y_, 0.09), M["nero"], bevel=0.015, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.5, 0.5, 0.72), (x_, y_, 0.18 + 0.36), M["rosso"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.6, 0.6, 0.08), (x_, y_, 0.94), M["nero"], bevel=0.012, segments=2, lightmap=True)
    A.place("Horse", (x_, y_, 0.98), -s * math.pi / 2)
    K.collider(f"Statue_{K.idx('statue')}", (x_ - 0.32, y_ - 0.32, 0), (x_ + 0.32, y_ + 0.32, 2.0))

# ============================================================================ roulette, in the bays by the entrance
for i, (x, y) in enumerate(TABLES):
    C.roulette_table(A, x, y, f"roulette_{i + 1:02d}", i + 1, rz=math.pi)   # players face the room's length
    for sound, gain, interval in (("rouletteBall", 0.3, (18, 40)), ("chips", 0.25, (5, 12))):
        A.audio(sound.capitalize(), (x, y, 0.9), sound, gain=gain, interval=interval)

# ============================================================================ logic
A.logic(probe=(0, 12.0, 1.7), bounds=((X0, 0.05, -1), (X1, D, H)))
mansion.save(OUT)
