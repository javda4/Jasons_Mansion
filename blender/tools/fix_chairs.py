"""Turn every table chair to face its own table (poker, baccarat). casino_props.py placed them with a
mirrored angle — atan2(-x, -y) - π instead of atan2(x, -y) — so the chairs at the table ends faced away.

    blender -b blender/rooms/<zone>/<zone>[_baked].blend --python blender/tools/fix_chairs.py

Each chair is several linked parts (back, body, plinth, cushion, legs) around one centre; the whole group is
rotated about that centre so its local +Y points at the centre of the nearest felt.
"""
import math

import bpy
from mathutils import Matrix, Vector

felts = []
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("TABLE_") and "Felt" in o.name and o.users_collection[0].name.startswith("VISUAL"):
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        felts.append(sum(pts, Vector()) / 8)
parts = [o for o in bpy.data.objects if o.name.startswith("CHAIR_") and not o.users_collection[0].name.startswith("_WIP")]
backs = [o for o in parts if "TubBack" in o.name]
n = 0
for back in backs:
    c = back.location.copy()
    centre = min(felts, key=lambda f: (f.xy - c.xy).length)
    d = centre.xy - c.xy
    want = math.atan2(-d.x, d.y)                 # R(θ)·(0, 1) = d̂
    delta = want - back.rotation_euler.z
    delta = math.atan2(math.sin(delta), math.cos(delta))
    if abs(delta) < 1e-3:
        continue
    R = Matrix.Rotation(delta, 3, "Z")
    for p in parts:
        if (p.location.xy - c.xy).length < 0.45:
            p.location = c + R @ (p.location - c)
            p.rotation_euler.z += delta
    n += 1
bpy.ops.wm.save_mainfile()
print("[fix_chairs]", bpy.path.basename(bpy.data.filepath), "felts", len(felts), "chairs", len(backs), "turned", n)
