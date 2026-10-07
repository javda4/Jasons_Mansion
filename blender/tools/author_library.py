"""Bootstrap authoring of the Library (Blender → GLB → web). docs/mansion-plan.md, M3.

    npm run author:library          (blender -b --factory-startup --python blender/tools/author_library.py)

The villa's library, on the sea front east of the Stair Hall:
- **Bookcases:** walnut cases in two tiers, thousands of leather-bound volumes (furniture.book_atlas), a gallery
  walkway on three walls reached by a spiral stair, a library ladder on its brass rail, classical busts on the
  cornices.
- **Hearth corner:** a marble fireplace with a Chesterfield and green velvet bergères.
- **Furniture:** a long reading table under banker's lamps, a globe, a bureau plat at the sea window, a window
  reading corner.
- **Game:** a poker table under a brass billiard pendant, the gentlemen's game in the gentlemen's room.

Zone anchor: the centre of the doorway from the Stair Hall (the hall's east door, world y = 15), at floor level.
The room runs along local +Y (world east), and local -X points north (the sea). blender/zones.json places it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import casino_props as C  # noqa: E402
import furniture as F  # noqa: E402
import kit  # noqa: E402
import mansion  # noqa: E402

OUT = os.path.join(kit.ROOT, "blender", "rooms", "library", "library.blend")
TEX = os.path.join(kit.ROOT, "blender", "textures_src", "library")
W, D, H, T = 14.0, 14.0, 6.0, 0.3
X0, X1 = -W / 2, W / 2                 # X0 = north (the sea), X1 = south
DOOR_W, DOOR_H = 2.4, 3.2
GZ = 3.4                               # gallery walkway
LOW, UP = (0.0, 3.3), (3.45, 5.75)     # the two tiers of cases
CD = 0.38                              # case depth
POKER = (-1.4, 10.6)
GREEN = (0.1, 0.24, 0.12)              # the bergères in forest-green velvet

kit.reset_scene()
K = kit.Zone("Library")
A = mansion.Mansion(K, height=H, thickness=T, sea=mansion.sea_texture(os.path.join(TEX, "T_Library_SeaView_Emissive.png"), seed=1931, moon_x=0.55))
M = A.M
books = K.material("books", "MAT_Library_Books", (1, 1, 1), 0.72, base_tex=F.book_atlas(os.path.join(TEX, "T_Library_Books_BaseColor.png")))

# ============================================================================ floor, walls, ceiling
K.box(K.name("ROOM", "Floor"), (W, D, 0.2), (0, D / 2, -0.1), M["parquet"], lightmap=True)
K.collider("Floor", (X0 - 0.5, -0.5, -0.5), (X1 + 0.5, D + 0.5, 0))
field = M["damask_green"]
A.wall("Front", "x", 0, 1, X0, X1, openings=[(0.0, DOOR_W, DOOR_H)], jambs=False, field=field, pilasters=[X0, -1.65, 1.65, X1])
A.wall("Back", "x", D, -1, X0, X1, field=field, pilasters=[X0, X1])
A.wall("North", "y", X0, 1, 0, D, field=field, pilasters=[0.0, 2.6, 5.0, 9.0, 11.4, D], windows=[3.8, 10.2], sconces=[2.6, 5.0, 9.0, 11.4])
A.wall("South", "y", X1, -1, 0, D, field=field, pilasters=[0.0, D])
A.outside("NorthOut", "y", X0, 1, 0, D, extend=0.15)           # the sea terrace beyond the windows
A.coffered_ceiling(X0, X1, 0, D, spacing=2.35)

# ============================================================================ the cases, the gallery, the stair and ladder
n_books = 0
for (p0, p1, n, z, shelves) in (
    ((X0, 0), (-1.75, 0), (0, 1), LOW, 9), ((1.75, 0), (X1, 0), (0, 1), LOW, 9),          # front, either side of the door
    ((X0, 0), (X1, 0), (0, 1), UP, 6),                                                     # front, upper tier over the door
    ((-4.9, D), (X1, D), (0, -1), LOW, 9), ((X0, D), (X1, D), (0, -1), UP, 6),            # back
    ((X1, CD), (X1, 5.6), (-1, 0), LOW, 9), ((X1, 8.4), (X1, D - CD), (-1, 0), LOW, 9),   # south, either side of the hearth
    ((X1, CD), (X1, D - CD), (-1, 0), UP, 6),
    ((X0, CD), (X0, 2.45), (1, 0), LOW, 9), ((X0, 5.15), (X0, 8.85), (1, 0), LOW, 9),     # north, between the windows
):
    n_books += F.bookcase(A, p0, p1, n, z[0], z[1], shelves, depth=CD, seed=len(K._n) + int(p0[0] * 7 + p0[1] * 13), books_mat=books)
print(f"[library] {n_books} books")
F.gallery_walk(A, (X0, CD), (X1 - CD, CD), (0, 1), GZ)
F.gallery_walk(A, (X1 - CD, CD), (X1 - CD, D - CD), (-1, 0), GZ)
F.gallery_walk(A, (X1 - CD, D - CD), (X0, D - CD), (0, -1), GZ)
F.spiral_stair(A, (-5.9, 12.85), GZ, start=-math.pi / 2)
F.library_ladder(A, (-4.9, D), (X1, D), (0, -1), 3.05, at=0.55)

# ============================================================================ light
lantern = A.prop("Chandelier_03", "CandleChandelier", decimate=0.3)
for (x, y) in ((-0.6, 4.6), (3.0, 10.4)):
    A.place("CandleChandelier", (x, y, H - lantern["dims"][2]), 0)
    K.light(K.name("LIGHT", "CandleChandelier"), "POINT", (x, y, H - 0.7), 14, rng=9)
F.pendant_lamp(A, POKER[0], POKER[1], H)
K.light("LIGHT_Library_Moon_01", "SPOT", (X0 - 4.0, 7.0, 4.8), 18, color=(0.55, 0.63, 0.85), rng=22, bake_only=True,
        angle=math.radians(80), blend=1.0, rot=(0, math.radians(-58), 0))
A.audio("Clock", (X1 - 0.5, 7.0, 1.5), "crystal", gain=0.12, interval=(14, 30))

# ============================================================================ furnishing
A.prop("sofa_02", "Chesterfield")
A.prop("gothic_coffee_table", "CoffeeTable", scale=0.72, decimate=0.45)
A.prop("brass_candleholders", "Candelabra", pick=["candleholder_03"], decimate=0.2)
A.prop("antique_ceramic_vase_01", "Vase")
A.prop("mantel_clock_01", "MantelClock", decimate=0.2)
A.prop("marble_bust_01", "Bust", decimate=0.3)
A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.15)
A.prop("tea_set_01", "TeaSet", decimate=0.4)


def bergere(xy, rz):
    A.club_chair(xy, rz, tint=GREEN, key="BergereGreen")


# --- the hearth corner: green bergères either side, a Chesterfield facing the fire
F.fireplace(A, (X1, 7.0), math.pi / 2, width=2.1)
A.rug("HearthRug", 4.5, 7.0, 3.3, 3.3 / 1.1469, 0, "Rug_Kazak", fringe=True)
bergere((5.65, 5.5), 0.35)
bergere((5.65, 8.5), math.pi - 0.35)
A.place("Chesterfield", (2.95, 7.0, 0.011), -math.pi / 2, collide=(0.95, 0.45, 0.8))
A.place("CoffeeTable", (4.35, 7.0, 0.011), 0.0, collide=(0.5, 0.5, 0.42))
A.place("TeaSet", (4.35, 7.0, 0.43), 0.2)
for dy in (-1.3, 1.3):
    A.lamp_table(2.9, 7.0 + dy, candela=5)

# --- the reading table under banker's lamps, four bergères; a Mamluk runner beneath
A.rug("TableRunner", -0.6, 4.6, 4.2, 4.2 / 3.8109, math.pi / 2, "Runner_Mamluk", fringe=True)
F.library_table(A, (-0.6, 4.6), 0.0)
for dx in (-0.7, 0.7):
    bergere((-0.6 + dx, 3.62), 0.0)
    bergere((-0.6 + dx, 5.58), math.pi)
F.globe(A, (2.7, 2.2))

# --- the bureau plat at the first sea window; a reading corner at the second
F.bureau_plat(A, (-5.4, 3.8), math.pi / 2, chair=False)
bergere((-4.68, 3.8), math.pi / 2)
top = F.gueridon(A, (-5.85, 10.2), r=0.3)
A.place("Candelabra", (-5.85, 10.2, top), 0.0)
bergere((-5.75, 9.35), 0.25)
bergere((-5.75, 11.05), math.pi - 0.25)

# --- busts on the cornices of the upper cases, looking into the room
for x in (-4.6, -1.2, 2.4, 5.4):
    A.place("Bust", (x, 0.22, UP[1]), 0.0)
    A.place("Bust", (x, D - 0.22, UP[1]), math.pi)
for y in (3.0, 11.0):
    A.place("Bust", (X1 - 0.22, y, UP[1]), math.pi / 2)
for (x, y) in ((X0 + 0.75, 1.0), (X0 + 0.75, 9.3)):
    K.lathe(K.name("PROP", "Jardiniere"), [(0, 0), (0.16, 0), (0.17, 0.03), (0.12, 0.08), (0.2, 0.2), (0.3, 0.36), (0.32, 0.46), (0.3, 0.48), (0, 0.48)],
            (x, y, 0), M["brass"], segments=40)
    A.place("Plant", (x, y, 0.2), 0)
    K.collider(f"Plant_{K.idx('plant')}", (x - 0.34, y - 0.34, 0), (x + 0.34, y + 0.34, 1.3))

# ============================================================================ poker, under the billiard pendant
C.poker_table(A, POKER[0], POKER[1], "poker_01")
for sound, gain, interval in (("chips", 0.35, (4, 11)), ("cardFlick", 0.3, (3, 9))):
    A.audio(sound.capitalize(), (POKER[0], POKER[1], 0.9), sound, gain=gain, interval=interval)

# ============================================================================ logic
A.logic(probe=(0, D / 2, 1.7), bounds=((X0, 0.05, -1), (X1, D, H)))
mansion.save(OUT)
