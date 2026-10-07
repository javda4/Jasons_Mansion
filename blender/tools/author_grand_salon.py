"""Bootstrap authoring of the Grand Salon (Blender → GLB → web). docs/mansion-plan.md, M2.

    npm run author:grand_salon      (blender -b --factory-startup --python blender/tools/author_grand_salon.py)

The villa's drawing room, on the sea front west of the Stair Hall: ivory-and-gilt Louis XV boiserie with gold
silk damask panels, an oak point-de-Hongrie floor, three French windows onto the night sea, two crystal
chandeliers. It is dressed as a lived-in salon:
- a lit marble fireplace with a trumeau mirror and a seating group round it;
- the main salon group under the first chandelier; a grand piano at the windows; a bureau plat;
- two vitrines of porcelain, pier glasses between the windows, a chess corner, busts, paintings, flowers, palms.
Baccarat, the aristocrat's game, is one table at the far end, roped off under the second chandelier.

Zone anchor: the centre of the doorway from the Stair Hall (the hall's west door, world y = 15), at floor level.
The room runs along local +Y (world west) and local +X points north (the sea). blender/zones.json places it.
"""
import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import casino_props as C  # noqa: E402
import flora  # noqa: E402
import furniture as F  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

OUT = os.path.join(kit.ROOT, "blender", "rooms", "grand_salon", "grand_salon.blend")
TEX = os.path.join(kit.ROOT, "blender", "textures_src", "grand_salon")
W, D, H, T = 14.0, 16.0, 6.0, 0.3
X0, X1 = -W / 2, W / 2
DOOR_W, DOOR_H = 2.4, 3.2
TABLE = (0.0, 12.0)              # baccarat, under the second chandelier
SALON = (0.0, 4.2)               # the main seating group, under the first

kit.reset_scene()
K = kit.Zone("GrandSalon")
M0 = mansion.library_materials(K)
A = mansion.Mansion(K, height=H, thickness=T, trim=M0["paint"], panel=M0["paint"], ceiling=M0["paint"],
                    sea=mansion.sea_texture(os.path.join(TEX, "T_GrandSalon_SeaView_Emissive.png"), seed=1911, moon_x=0.42))
M = A.M
FIELD = M["damask_gold"]

# ============================================================================ floor, walls, ceiling
K.box(K.name("ROOM", "Floor"), (W, D, 0.2), (0, D / 2, -0.1), M["parquet"], lightmap=True)
K.collider("Floor", (X0 - 0.5, -0.5, -0.5), (X1 + 0.5, D + 0.5, 0))
A.wall("Front", "x", 0, 1, X0, X1, openings=[(0.0, DOOR_W, DOOR_H)], jambs=False, mass=False,   # the Stair Hall's wall is the mass (its upper doors stand in it)
       field=FIELD,
       pilasters=[X0, -4.6, -1.65, 1.65, 4.6, X1], paintings=[(-5.8, 2)], sconces=[-4.6, -1.65, 1.65, 4.6])
A.wall("Back", "x", D, -1, X0, X1, openings=[(0.0, DOOR_W, DOOR_H)], field=FIELD,
       pilasters=[X0, -4.6, -1.65, 1.65, 4.6, X1], paintings=[(5.8, 6)], sconces=[-4.6, -1.65, 1.65, 4.6])
NORTH_P = [0.0, 1.6, 4.8, 6.4, 9.6, 11.2, 14.4, D]
A.wall("North", "y", X1, -1, 0, D, field=FIELD, pilasters=NORTH_P, windows=[3.2, 8.0, 12.8], sconces=[1.6, 14.4])
A.wall("South", "y", X0, 1, 0, D, field=FIELD, pilasters=[0.0, 2.8, 6.2, 9.8, 13.2, D],
       paintings=[(4.5, 8), (11.5, 9), (14.6, 1), (1.4, 4)], sconces=[2.8, 6.2, 9.8, 13.2])
A.coffered_ceiling(X0, X1, 0, D, spacing=2.7)
A.double_door("Ballroom", (0, D, 0), (0, -1, 0), DOOR_W, DOOR_H, 0, "Enter the Ballroom", target="ballroom")
# ceiling roses over the chandeliers
for (x, y) in (SALON, TABLE):
    K.lathe(K.name("ROOM", "CeilingRose"), [(0, 0), (1.1, 0), (1.05, -0.04), (0.9, -0.07), (0.7, -0.09), (0.45, -0.1), (0.2, -0.14), (0, -0.16)],
            (x, y, H - 0.34), M["gilt"], segments=64)

# ============================================================================ light
A.chandelier(SALON[0], SALON[1], scale=1.0, drop=1.3, point_cd=58, key=False)
A.chandelier(TABLE[0], TABLE[1], scale=1.0, drop=1.2, point_cd=60)
A.audio("Chandelier", (0, 8, 4.5), "crystal", gain=0.25, interval=(10, 24))
K.light("LIGHT_GrandSalon_Moon_01", "SPOT", (X1 + 4.0, 8.0, 5.2), 22, color=(0.55, 0.63, 0.85), rng=24, bake_only=True,
        angle=math.radians(80), blend=1.0, rot=(0, math.radians(58), 0))

# ============================================================================ furnishing
A.prop("Sofa_01", "LouisSofa", tint={"Sofa": (0.62, 0.5, 0.36)}, scale=1.15)
A.prop("gothic_coffee_table", "CoffeeTable", scale=0.72, decimate=0.45)
A.prop("ClassicConsole_01", "Console", decimate=0.5)
A.prop("ornate_mirror_01", "Mirror", scale=2.1, origin="back", decimate=0.4)
A.prop("brass_candleholders", "Candelabra", pick=["candleholder_03"], decimate=0.2)
A.prop("antique_ceramic_vase_01", "Vase")
A.prop("mantel_clock_01", "MantelClock", decimate=0.2)
A.prop("marble_bust_01", "Bust", decimate=0.3)
A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.15)
A.prop("tea_set_01", "TeaSet", decimate=0.4)
A.prop("chess_set", "Chess", decimate=0.4)


def console_group(wx, wy, rz, clock=False):
    """A pier table: carved console, a tall mirror above, candelabra and a vase or clock."""
    n = Vector((-math.sin(rz), math.cos(rz), 0))
    t = Vector((math.cos(rz), math.sin(rz), 0))
    base = Vector((wx, wy, 0))
    A.place("Console", tuple(base + n * 0.42), rz, collide=(0.78, 0.32, 0.95))
    A.place("Mirror", tuple(base + n * 0.07 + Vector((0, 0, 1.98))), rz)
    A.place("Candelabra", tuple(base + n * 0.4 + t * 0.48 + Vector((0, 0, 0.95))), rz)
    A.place("MantelClock" if clock else "Vase", tuple(base + n * 0.4 - t * 0.42 + Vector((0, 0, 0.95))), rz)
    K.light(K.name("LIGHT", "Candelabra"), "POINT", tuple(base + n * 0.4 + t * 0.48 + Vector((0, 0, 1.85))), 4, rng=5, bake_only=True)


def jardiniere_plant(x, y):
    K.lathe(K.name("PROP", "Jardiniere"), [(0, 0), (0.16, 0), (0.17, 0.03), (0.12, 0.08), (0.2, 0.2), (0.3, 0.36), (0.32, 0.46), (0.3, 0.48), (0, 0.48)],
            (x, y, 0), M["brass"], segments=40)
    A.place("Plant", (x, y, 0.2), 0)
    K.collider(f"Plant_{K.idx('plant')}", (x - 0.34, y - 0.34, 0), (x + 0.34, y + 0.34, 1.3))


def pedestal_bust(x, y, rz):
    K.box(K.name("PROP", "PedestalBase"), (0.5, 0.5, 0.14), (x, y, 0.07), M["nero"], bevel=0.012, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalShaft"), (0.36, 0.36, 0.84), (x, y, 0.56), M["marble"], bevel=0.01, segments=2, lightmap=True)
    K.box(K.name("PROP", "PedestalCap"), (0.48, 0.48, 0.12), (x, y, 1.04), M["nero"], bevel=0.012, segments=2, lightmap=True)
    A.place("Bust", (x, y, 1.12), rz)
    K.collider(f"BustPedestal_{K.idx('ped')}", (x - 0.26, y - 0.26, 0), (x + 0.26, y + 0.26, 1.72))


# --- the hearth (south wall) and its seating: bergères either side facing in, a settee facing the fire
F.fireplace(A, (X0, 8.0), -math.pi / 2, width=2.2)
A.rug("HearthRug", -4.4, 8.0, 3.3, 3.3 / 1.1469, 0, "Rug_Kazak", fringe=True)
A.club_chair((-5.55, 6.55), -0.35)
A.club_chair((-5.55, 9.45), math.pi + 0.35)
A.place("LouisSofa", (-2.75, 8.0, 0.011), math.pi / 2, collide=(0.95, 0.4, 0.8))
A.place("CoffeeTable", (-4.3, 8.0, 0.011), 0.0, collide=(0.5, 0.5, 0.42))
A.place("TeaSet", (-4.3, 8.0, 0.43), 0.3)

# --- the main salon group: two settees face each other across a low table, bergères at the ends
A.rug("SalonRug", SALON[0], SALON[1], 4.6, 4.6 / 1.1469, math.pi / 2, "Rug_Kazak", fringe=True)
for s in (-1, 1):
    A.place("LouisSofa", (s * 1.95, SALON[1], 0.011), s * math.pi / 2, collide=(0.95, 0.4, 0.8))
    A.club_chair((SALON[0], SALON[1] + s * 1.75), (math.pi if s > 0 else 0.0))
    A.lamp_table(s * 1.95, SALON[1] + 1.25, candela=5)
A.place("CoffeeTable", (SALON[0], SALON[1], 0.011), 0.0, collide=(0.5, 0.5, 0.42))
flora.arrangement(K, SALON, 0.43 + 0.04, radius=0.32, height=0.34, reds=40, ivories=34, leaves=90, sprays=10, seed=1911)

# --- the grand piano at the middle window, its lid open to the room
F.grand_piano(A, (3.4, 7.4), -math.pi / 2)

# --- writing table in the south-front corner; vitrines in the north-front and south-back corners
F.bureau_plat(A, (-4.6, 2.4), 0.0)
F.vitrine(A, (5.8, 0.0), 0.0)
F.vitrine(A, (-5.8, D), math.pi)

# --- pier glasses between the windows; palms in the corners
console_group(X1, 5.6, math.pi / 2, clock=True)
console_group(X1, 10.4, math.pi / 2)
for (x, y) in ((X1 - 0.55, 1.35), (X1 - 0.55, D - 0.6), (X0 + 0.55, 0.6), (X0 + 0.6, 12.9)):
    jardiniere_plant(x, y)

# --- a chess corner by the far window
top = F.gueridon(A, (4.6, 14.4), r=0.34)
A.place("Chess", (4.6, 14.4, top), 0.6)
A.club_chair((3.85, 14.4), -math.pi / 2)
A.club_chair((5.35, 14.4), math.pi / 2)

# --- busts flank the enfilade door to the Ballroom
for s in (-1, 1):
    pedestal_bust(s * 2.05, D - 0.5, math.pi)      # faces into the salon, away from the Ballroom door

# ============================================================================ baccarat, roped off at the far end
C.baccarat_table(A, TABLE[0], TABLE[1], "baccarat_01", rz=math.pi)   # croupier at the far end, facing the entrance
C.stanchions(A, TABLE[0], TABLE[1], 3.7, 2.6, 14, gap=(10, 11))
for sound, gain, interval in (("cardFlick", 0.3, (3, 8)), ("chips", 0.3, (6, 14))):
    A.audio(sound.capitalize(), (TABLE[0], TABLE[1], 0.9), sound, gain=gain, interval=interval)

# ============================================================================ logic
A.logic(probe=(0, D / 2, 1.7), bounds=((X0, 0.05, -1), (X1, D, H)))
mansion.save(OUT)
