"""Bootstrap authoring of the Ballroom, the Salon de Musique (Blender → GLB → web). docs/mansion-plan.md, M3.

    npm run author:ballroom         (blender -b --factory-startup --python blender/tools/author_ballroom.py)

The villa's ballroom, through the Grand Salon's enfilade door on the sea front:
- **Architecture:** ivory-and-gilt boiserie, seven metres high. Five arched windows onto the night sea face an
  arcade of five arched mirrors (a galerie des glaces). Point-de-Hongrie parquet, three crystal chandeliers.
- **Musicians' dais:** at the far end, with a grand piano, a harp, music stands and gilt chairs for a quartet.
- **Round the walls:** gilt chairs in pairs, velvet banquettes under the mirrors, palms in brass jardinières, and
  porcelain horses at the door.
- **Game:** two roulette tables on the dance floor under the chandeliers, Monte-Carlo style.

Zone anchor: the centre of the doorway from the Grand Salon (its back wall, world x = -26.3, y = 15). The room runs
along local +Y (world west) and local +X points north (the sea), like the salon.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import casino_props as C  # noqa: E402
import furniture as F  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

OUT = os.path.join(kit.ROOT, "blender", "rooms", "ballroom", "ballroom.blend")
TEX = os.path.join(kit.ROOT, "blender", "textures_src", "ballroom")
W, D, H, T = 14.0, 20.0, 7.0, 0.3
X0, X1 = -W / 2, W / 2                 # X0 = south (the mirrors), X1 = north (the windows, the sea)
DOOR_W, DOOR_H = 2.4, 3.2
BAYS = [2.8, 6.4, 10.0, 13.6, 17.2]    # window / mirror centres along the long walls
PIERS = [0.0, 1.6, 4.0, 5.2, 7.6, 8.8, 11.2, 12.4, 14.8, 16.0, 18.4, D]
TABLES = ((0.0, 6.2), (0.0, 12.0))     # roulette, under the first two chandeliers
DAIS = (-4.2, 4.2, 16.6, D, 0.42)      # x0, x1, y0, y1, height

kit.reset_scene()
K = kit.Zone("Ballroom")
M0 = mansion.library_materials(K)
A = mansion.Mansion(K, height=H, thickness=T, trim=M0["paint"], panel=M0["paint"], ceiling=M0["paint"],
                    sea=mansion.sea_texture(os.path.join(TEX, "T_Ballroom_SeaView_Emissive.png"), seed=1925, moon_x=0.35))
M = A.M
FIELD = M["damask_gold"]

# ============================================================================ floor, walls, ceiling
K.box(K.name("ROOM", "Floor"), (W, D, 0.2), (0, D / 2, -0.1), M["parquet"], lightmap=True)
K.collider("Floor", (X0 - 0.5, -0.5, -0.5), (X1 + 0.5, D + 0.5, 0))
A.wall("Front", "x", 0, 1, X0, X1, openings=[(0.0, DOOR_W, DOOR_H)], jambs=False, field=FIELD,
       pilasters=[X0, -4.4, -1.65, 1.65, 4.4, X1], paintings=[(-5.7, 0), (5.7, 3)], sconces=[-4.4, -1.65, 1.65, 4.4])
A.wall("Back", "x", D, -1, X0, X1, field=FIELD, pilasters=[X0, -4.4, -2.0, 2.0, 4.4, X1], paintings=[(0.0, 5), (-5.7, 6), (5.7, 2)],
       sconces=[-4.4, -2.0, 2.0, 4.4])
A.wall("North", "y", X1, -1, 0, D, field=FIELD, pilasters=PIERS, windows=BAYS, sconces=[1.6, 4.6, 8.2, 11.8, 15.4, 18.4])
A.wall("South", "y", X0, 1, 0, D, field=FIELD, pilasters=PIERS, mirrors=BAYS, sconces=[1.6, 4.6, 8.2, 11.8, 15.4, 18.4])
A.coffered_ceiling(X0, X1, 0, D, spacing=2.5)
for y in (6.2, 12.0, 17.6):
    K.lathe(K.name("ROOM", "CeilingRose"), [(0, 0), (1.3, 0), (1.25, -0.04), (1.05, -0.08), (0.8, -0.1), (0.5, -0.12), (0.22, -0.16), (0, -0.18)],
            (0, y, H - 0.34), M["gilt"], segments=64)

# ============================================================================ light
A.chandelier(0, TABLES[0][1], scale=1.15, drop=1.5, point_cd=60, key=False)
A.chandelier(0, TABLES[1][1], scale=1.15, drop=1.5, point_cd=60)
A.chandelier(0, 17.6, scale=1.0, drop=1.6, point_cd=44, key=False, tiers=2)
A.audio("Chandelier", (0, 10, 5.2), "crystal", gain=0.28, interval=(9, 20))
K.light("LIGHT_Ballroom_Moon_01", "SPOT", (X1 + 4.0, 10.0, 6.0), 26, color=(0.55, 0.63, 0.85), rng=26, bake_only=True,
        angle=math.radians(85), blend=1.0, rot=(0, math.radians(56), 0))

# ============================================================================ the musicians' dais
x0, x1, y0, y1, dh = DAIS
K.box(K.name("ROOM", "Dais"), (x1 - x0, y1 - y0, dh), ((x0 + x1) / 2, (y0 + y1) / 2, dh / 2), M["parquet"], lightmap=True)
K.box(K.name("ROOM", "DaisNosing"), (x1 - x0 + 0.04, 0.06, 0.05), ((x0 + x1) / 2, y0 - 0.01, dh - 0.025), M["gilt"], bevel=0.01)
K.box(K.name("ROOM", "DaisStep"), (2.4, 0.32, dh / 2), (0, y0 - 0.16, dh / 4), M["parquet"], lightmap=True)
K.collider("Dais", (x0, y0, 0), (x1, y1, dh))
K.collider("DaisStep", (-1.2, y0 - 0.32, 0), (1.2, y0, dh / 2))
F.grand_piano(A, (-3.2, 18.2), -math.pi / 2, z0=dh)          # the pianist faces the quartet; the lid opens to the room
for k, (x, y, rz) in enumerate(((0.6, 17.6, math.pi + 0.3), (1.6, 17.9, math.pi), (2.6, 17.6, math.pi - 0.3))):
    F.gilt_chair(A, (x, y), rz, z0=dh)
    F.music_stand(A, (x - 0.1, y - 0.75), rz + math.pi, z0=dh)
F.harp(A, (3.5, 18.9), math.pi + 0.5, z0=dh)

# ============================================================================ round the walls
A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.15)
A.prop("horse_statue_01", "Horse", scale=4.2, decimate=0.6)


def jardiniere(x, y, z=0.0):
    K.lathe(K.name("PROP", "Jardiniere"), [(0, 0), (0.16, 0), (0.17, 0.03), (0.12, 0.08), (0.2, 0.2), (0.3, 0.36), (0.32, 0.46), (0.3, 0.48), (0, 0.48)],
            (x, y, z), M["brass"], segments=40)
    A.place("Plant", (x, y, z + 0.2), 0)
    K.collider(f"Plant_{K.idx('plant')}", (x - 0.34, y - 0.34, z), (x + 0.34, y + 0.34, z + 1.3))


# gilt chairs in pairs on the window piers; velvet banquettes under the mirrors
for (a, b) in zip(BAYS, BAYS[1:]):
    pier = (a + b) / 2
    for s in (-1, 1):
        F.gilt_chair(A, (X1 - 0.45, pier + s * 0.3), math.pi / 2)
for b in BAYS:
    F.banquette(A, (X0 + 0.45, b), -math.pi / 2)
for (a, b) in zip(BAYS, BAYS[1:]):
    pier = (a + b) / 2
    F.gilt_chair(A, (X0 + 0.45, pier), -math.pi / 2)
for (x, y) in ((X1 - 0.6, 0.65), (X0 + 0.6, 0.65), (X1 - 0.6, D - 0.6), (X0 + 0.6, D - 0.6), (x0 - 0.6, y0 + 0.3), (x1 + 0.6, y0 + 0.3)):
    jardiniere(x, y)
# porcelain horses on plinths either side of the door from the salon
for s in (-1, 1):
    x_, y_ = s * 2.3, 0.75
    K.box(K.name("PROP", "StatuePlinth"), (0.62, 0.62, 0.18), (x_, y_, 0.09), M["nero"], bevel=0.015, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.5, 0.5, 0.72), (x_, y_, 0.18 + 0.36), M["rosso"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "StatuePlinth"), (0.6, 0.6, 0.08), (x_, y_, 0.94), M["nero"], bevel=0.012, segments=2, lightmap=True)
    A.place("Horse", (x_, y_, 0.98), -s * math.pi / 2)
    K.collider(f"Statue_{K.idx('statue')}", (x_ - 0.32, y_ - 0.32, 0), (x_ + 0.32, y_ + 0.32, 2.0))

# ============================================================================ roulette on the dance floor
for i, (x, y) in enumerate(TABLES):
    C.roulette_table(A, x, y, f"roulette_{i + 1:02d}", i + 1, rz=math.pi)   # players on the entrance side
    for sound, gain, interval in (("rouletteBall", 0.35, (18, 40)), ("chips", 0.3, (5, 12))):
        A.audio(sound.capitalize(), (x, y, 0.9), sound, gain=gain, interval=interval)

# ============================================================================ logic
A.logic(probe=(0, D / 2, 1.7), bounds=((X0, 0.05, -1), (X1, D, H)))
mansion.save(OUT)
