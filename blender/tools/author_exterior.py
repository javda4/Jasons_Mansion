"""Bootstrap authoring of the Exterior: the sea terrace and the night beyond every window (Blender → GLB → web).

    npm run author:exterior         (blender -b --factory-startup --python blender/tools/author_exterior.py)

One zone for the whole sea front, always loaded and drawn (zones.json `always`), so every window in every room looks
out on the same continuous terrace and night:
- **Terrace:** one stone terrace along the north facade. It runs 6 m deep before the Stair Hall, salon and library
  (facade at y 22.3) and 4 m before the Ballroom wing, which steps forward (y 24.3). A single balustrade of turned
  stone balusters runs along y = 28.4 with returns at both ends, with urns of plants and lit lanterns on its piers
  and olive trees in stone planters at the ends.
- **Moonlight:** baked from a low directional moon at the sky photograph's moon direction.
- **Backdrop:** an open box beyond everything: far, sides, top and bottom. Its `MAT_Exterior_SeaView` material is
  swapped at runtime for the live night (src/render/nightView.ts: sky photograph, animated sea far below the cliff,
  the coast's lights), so no window, at any angle, can see past it.

The zone's frame is the world frame (like the Stair Hall). Its bounds lie far off, so the player is never "in" it.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import mansion  # noqa: E402

OUT = os.path.join(kit.ROOT, "blender", "rooms", "exterior", "exterior.blend")
TEX = os.path.join(kit.ROOT, "blender", "textures_src", "exterior")
X_W, X_E = -58.0, 26.0              # the terrace's ends (the Ballroom wing's west wall is at x -56.9)
FACADE, WING_FACADE, WING_X = 22.3, 24.3, -26.6
EDGE = 28.4                         # the balustrade line
Z0 = 0.0                            # terrace level = the ground floor

kit.reset_scene()
K = kit.Zone("Exterior")
A = mansion.Mansion(K, height=6.0, sea=mansion.sea_texture(os.path.join(TEX, "T_Exterior_SeaView_Emissive.png"), seed=1907, moon_x=0.62))
M = A.M
K.material("stone", "MAT_Exterior_TerraceStone", (0.5, 0.46, 0.39), 0.88)
K.material("terracotta", "MAT_Exterior_Terracotta", (0.42, 0.2, 0.12), 0.8)

# ============================================================================ the terrace
for (x0, x1, y0) in ((WING_X, X_E, FACADE), (X_W, WING_X, WING_FACADE)):
    K.box(K.name("ROOM", "Terrace"), (x1 - x0, EDGE + 0.4 - y0, 0.25), ((x0 + x1) / 2, (y0 + EDGE + 0.4) / 2, Z0 - 0.125), M["stone"], lightmap=True)
K.collider("Terrace", (X_W, FACADE, -0.5), (X_E, EDGE + 0.7, 0.0))           # ready for when the terrace doors open
K.collider("Balustrade", (X_W - 0.3, EDGE - 0.3, 0.0), (X_E + 0.3, EDGE + 0.3, 1.1))
K.box(K.name("ROOM", "TerraceCoping"), (X_E - X_W + 0.4, 0.3, 0.7), ((X_W + X_E) / 2, EDGE + 0.55, Z0 - 0.33), M["stone"], lightmap=True)

bal = K.prototype(K.lathe(K.name("PROP", "StoneBaluster"), [(0, 0), (0.07, 0), (0.07, 0.05), (0.045, 0.09), (0.04, 0.2), (0.075, 0.4),
                                                             (0.08, 0.46), (0.045, 0.6), (0.035, 0.63), (0.06, 0.66), (0.06, 0.68), (0, 0.68)], (0, 0, -30), M["stone"], segments=10))


def balustrade(p0, p1, piers_every=4.2):
    """A stone balustrade from p0 to p1 (plan points): plinth, balusters, rail, piers with urns and lanterns."""
    p0, p1 = Vector((*p0, Z0)), Vector((*p1, Z0))
    t = (p1 - p0).normalized()
    L = (p1 - p0).length
    rz = math.atan2(t.y, t.x)
    mid = (p0 + p1) / 2
    K.box(K.name("ROOM", "BalustradePlinth"), (L, 0.3, 0.18), tuple(mid + Vector((0, 0, 0.09))), M["stone"], rot=(0, 0, rz), lightmap=True)
    K.box(K.name("ROOM", "BalustradeRail"), (L, 0.38, 0.14), tuple(mid + Vector((0, 0, 0.93))), M["stone"], rot=(0, 0, rz), bevel=0.02, lightmap=True)
    n = max(1, round(L / piers_every))
    piers = [p0 + t * (L * k / n) for k in range(n + 1)]
    s = 0.12
    while s < L:
        p = p0 + t * s
        if all((p - q).length > 0.32 for q in piers):
            K.linked(K.name("PROP", "StoneBaluster"), bal, tuple(p + Vector((0, 0, 0.18))))
        s += 0.22
    for k, q in enumerate(piers):
        K.box(K.name("ROOM", "BalustradePier"), (0.5, 0.5, 1.06), tuple(q + Vector((0, 0, 0.53))), M["stone"], rot=(0, 0, rz), bevel=0.02, lightmap=True)
        top = Z0 + 1.06
        if k % 2:
            K.lathe(K.name("PROP", "TerraceUrn"), [(0, 0), (0.13, 0), (0.14, 0.04), (0.09, 0.1), (0.12, 0.2), (0.24, 0.4), (0.27, 0.52), (0.2, 0.6), (0.25, 0.66), (0, 0.66)],
                    (q.x, q.y, top), M["terracotta"], segments=24)
            A.place("Plant", (q.x, q.y, top + 0.42), k * 0.7)
        else:
            K.lathe(K.name("PROP", "TerraceLantern"), [(0, 0), (0.08, 0), (0.06, 0.04), (0.1, 0.1), (0.1, 0.38), (0.12, 0.42), (0.05, 0.5), (0, 0.55)],
                    (q.x, q.y, top), M["brass"], segments=8)
            K.cyl(K.name("PROP", "TerraceLanternGlow"), 0.085, 0.085, 0.26, (q.x, q.y, top + 0.24), M["shade"], segments=12)
            K.light(K.name("LIGHT", "TerraceLantern"), "POINT", (q.x, q.y, top + 0.26), 6, color=(1.0, 0.72, 0.42), rng=8, bake_only=True)


A.prop("potted_plant_02", "Plant", pick=["leaves", "dirt"], scale=1.45, decimate=0.15)
balustrade((X_W, EDGE), (X_E, EDGE))
balustrade((X_W, WING_FACADE), (X_W, EDGE))          # returns at both ends
balustrade((X_E, FACADE), (X_E, EDGE))
# olive trees in stone planters at the terrace's ends and either side of the hall's terrace doors
A.prop("island_tree_02", "Olive", scale=0.42, decimate=0.02)    # a dense scan: ~21k triangles each
for (x, y) in ((X_W + 2.2, EDGE - 1.6), (X_E - 2.2, EDGE - 1.6), (-4.2, EDGE - 1.4), (4.2, EDGE - 1.4)):
    K.box(K.name("PROP", "Planter"), (1.1, 1.1, 0.7), (x, y, Z0 + 0.35), M["stone"], bevel=0.04, segments=2, lightmap=True)
    A.place("Olive", (x, y, Z0 + 0.66), (x * 13) % 6.28)

# ============================================================================ moonlight
env = json.load(open(os.path.join(kit.ROOT, "blender", "textures_src", "env", "T_NightSky.json")))
az, el = env["moon"]["az"], env["moon"]["el"]
to_moon = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))     # Blender frame: north = +Y
moon = bpy.data.lights.new("LIGHT_Exterior_Moon_01", "SUN")
moon.energy = 0.06
moon.color = (0.6, 0.68, 0.9)
moon.angle = math.radians(0.6)
ob = bpy.data.objects.new("LIGHT_Exterior_Moon_01", moon)
ob.rotation_euler = (-to_moon).to_track_quat("-Z", "Y").to_euler()
ob["bakeOnly"] = True
K.coll["LIGHTS"].objects.link(ob)

# ============================================================================ the backdrop for the live night: an open box beyond everything
BX0, BX1, BY0, BY1, BZ0, BZ1 = -75.0, 45.0, 20.0, 52.0, -38.0, 38.0   # well inside the camera's reach from every window
faces = (
    ((BX0, BY1, BZ0), (BX1, BY1, BZ0), (BX1, BY1, BZ1), (BX0, BY1, BZ1)),      # far
    ((BX0, BY0, BZ0), (BX0, BY1, BZ0), (BX0, BY1, BZ1), (BX0, BY0, BZ1)),      # west
    ((BX1, BY1, BZ0), (BX1, BY0, BZ0), (BX1, BY0, BZ1), (BX1, BY1, BZ1)),      # east
    ((BX0, BY0, BZ1), (BX0, BY1, BZ1), (BX1, BY1, BZ1), (BX1, BY0, BZ1)),      # top
    ((BX0, BY1, BZ0), (BX0, BY0, BZ0), (BX1, BY0, BZ0), (BX1, BY1, BZ0)),      # bottom
)
bm = bmesh.new()
centre = Vector(((BX0 + BX1) / 2, (BY0 + BY1) / 2, (BZ0 + BZ1) / 2))
for quad in faces:
    f = bm.faces.new([bm.verts.new(v) for v in quad])
    f.normal_update()
    if f.normal.dot(centre - f.calc_center_median()) < 0:       # facing inwards, towards the house
        f.normal_flip()
K.obj(K.name("PROP", "NightView"), bm, M["sea"])

# ============================================================================ logic: bounds far away (the player is never "in" the exterior)
A.logic(probe=(0, 25.5, 1.7), bounds=((400, 400, -1), (401, 401, 1)))
mansion.save(OUT)
