"""Bootstrap authoring of a gallery hallway (West or East) — Blender → GLB → web.

    blender -b --factory-startup --python blender/tools/author_hallway.py -- hall_west
    blender -b --factory-startup --python blender/tools/author_hallway.py -- hall_east

Zone anchor: centre of the lobby doorway on the lobby wall's inner face, floor level; the gallery
runs along Blender +Y (glTF −Z). Rooms attach at the slots in src/rooms/shared/layout.ts (HALL_SLOTS):
side doors at y = 10.15 on x = ±1.9, the end door at y = 20.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import mansion  # noqa: E402

zone_id = sys.argv[sys.argv.index("--") + 1]
CONFIG = {
    "hall_west": ("HallWest", {
        "left": ("poker", "Enter the Poker Room", ["Salon de Poker", "Texas Hold'em"]),
        "right": ("blackjack", "Enter the Blackjack Room", ["Salon Blackjack", "Vingt-et-Un"]),
        "end": ("baccarat", "Enter the Baccarat Room", ["Salon Baccarat", "Chemin de Fer"]),
    }, (0, 2, 5, 9)),
    "hall_east": ("HallEast", {
        "left": ("roulette", "Enter the Roulette Room", ["Salon de Roulette", "Faites vos jeux"]),
        "right": ("slots", "Enter the Slot Room", ["Machines à Sous", "Salle des Jackpots"]),
        "end": ("vip", "Enter the Salon Privé", ["Salon Privé", "Réservé aux membres"]),
    }, (3, 6, 10, 1)),
}
ZONE, LINKS, ART = CONFIG[zone_id]
W, L, H, T = 3.8, 20.0, 4.9, 0.3
hw = W / 2
BAYS = 5
BAY = (L - T) / BAYS
SIDE_Y = T + 2.5 * BAY               # 10.15 (= -HALL_SIDE_DOOR_Z)
PIL = [T + i * BAY for i in range(BAYS + 1)]
DOOR_W, DOOR_H = 2.2, 3.1
OUT = os.path.join(kit.ROOT, "blender", "rooms", zone_id, f"{zone_id}.blend")

kit.reset_scene()
K = kit.Zone(ZONE)
A = mansion.Mansion(K, height=H, thickness=T)
M = A.M

# floor: polished walnut with a Nero band, crimson runner with gilt borders
A.bordered_floor(-hw, hw, 0, L, M["walnut"], M["nero"], margin=M["walnut_dark"], m=0.25, bw=0.12)
K.box(K.name("ROOM", "Runner"), (2.0, L - T - 0.45, 0.012), (0, (T + L - 0.4) / 2 + 0.05, 0.006), M["carpet"], lightmap=True)
for s in (-1, 1):
    K.box(K.name("ROOM", "RunnerBorder"), (0.04, L - T - 0.45, 0.014), (s * 0.88, (T + L - 0.4) / 2 + 0.05, 0.007), M["gilt"])
A.coffered_ceiling(-hw, hw, T, L, spacing=1.9, beam_d=0.3)

# walls
A.wall("Entrance", "x", T, 1, -hw, hw, openings=[(0.0, 2.6, 3.6)], pilasters=[-hw, hw], mass=False, jambs=False)
side = dict(pilasters=PIL, sconces=PIL[1:-1])
A.wall("Left", "y", -hw, 1, T, L, openings=[(SIDE_Y, DOOR_W, DOOR_H)], paintings=[(T + 1.5 * BAY, ART[0]), (T + 3.5 * BAY, ART[1])], **side)
A.wall("Right", "y", hw, -1, T, L, openings=[(SIDE_Y, DOOR_W, DOOR_H)], paintings=[(T + 1.5 * BAY, ART[2]), (T + 3.5 * BAY, ART[3])], **side)
A.wall("End", "x", L, -1, -hw, hw, openings=[(0.0, DOOR_W, DOOR_H)], pilasters=[-hw, hw])

# doors the gallery owns (they swing into the rooms) + plaques on the overdoors
for did, (target, prompt, plaque), centre, normal in (
    ("Left", LINKS["left"], (-hw, SIDE_Y, 0), (1, 0, 0)),
    ("Right", LINKS["right"], (hw, SIDE_Y, 0), (-1, 0, 0)),
    ("End", LINKS["end"], (0, L, 0), (0, -1, 0)),
):
    A.double_door(did, centre, normal, DOOR_W, DOOR_H, 0, prompt, target=target)
    n = kit.Vector(normal)
    A.plaque(plaque, tuple(kit.Vector(centre) + n * 0.15 + kit.Vector((0, 0, DOOR_H + 0.34))), normal, width=1.7, height=0.24)

# arched ribs across the gallery at every interior pilaster
r = hw - 0.12
for y in PIL[1:-1]:
    rib = K.torus(K.name("ROOM", "Rib"), r, 0.07, (0, y, H - r - 0.02), M["walnut"], major=40, minor=10, arc=math.pi, rot=(math.pi / 2, 0, 0))
    rib.data.transform(kit.Matrix.Diagonal((1, 1, 2.6, 1)))  # flat rib; scale applied to the mesh (§6)
    K.torus(K.name("PROP", "RibGilt"), r - 0.07, 0.018, (0, y, H - r - 0.02), M["gilt"], major=40, minor=6, arc=math.pi, rot=(math.pi / 2, 0, 0))

# consoles with lamps near the far end, two small chandeliers
A.console(-hw + 0.25, T + 4.5 * BAY, math.pi / 2)
A.console(hw - 0.25, T + 4.5 * BAY, -math.pi / 2)
A.chandelier(0, T + 1.5 * BAY, scale=0.45, drop=0.9, point_cd=22, key=True, tiers=2)
A.chandelier(0, T + 3.5 * BAY, scale=0.45, drop=0.9, point_cd=22, key=False, tiers=2)

A.logic(probe=(0, L / 2, 1.7), bounds=((-hw, 0, -1), (hw, L, H)))
mansion.save(OUT)
