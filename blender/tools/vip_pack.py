"""Salon Privé: the Kraffing pack's billiard table and jukebox (licensed; blender/props/kraffing, git-ignored).

    blender -b blender/rooms/vip/vip.blend --python blender/tools/vip_pack.py

Idempotent. The pool table (balls racked, cue laid on the cloth) stands in the front half of the room, left of
the path from the door to the hearth; the jukebox in the front-right corner, facing into the room.
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402

PACK = os.path.join(kit.ROOT, "blender", "props", "kraffing")
OLD = ("PROP_Vip_KrPool", "PROP_Vip_KrJukebox", "COLLIDER_Vip_KrPool", "COLLIDER_Vip_KrJukebox")
for o in [o for o in bpy.data.objects if o.name.startswith(OLD)]:
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for d in [d for d in coll if d.users == 0]:
        coll.remove(d)

K = kit.Zone.__new__(kit.Zone)
K.zone, K.mat, K._n = "Vip", {}, {}
K.coll = {c: bpy.data.collections[f"{c}_Vip"] for c in ("VISUAL", "COLLISION", "LOGIC", "LIGHTS", "PROBES")}
K.wip = bpy.data.collections.get("_WIP_Vip_Notes")

# (file, key, scale, location, rz, collider half-extents x/y + height after rotation)
PIECES = [
    ("Pool_Table_1", "KrPool", 0.8, (-2.6, 1.95, 0), 0.0, (1.38, 0.79, 0.85)),     # 9-ft table, 0.82 m bed
    ("Jukebox_1", "KrJukebox", 1.0, (4.5, 1.3, 0), -math.pi / 2, (0.42, 0.62, 1.45)),  # faces −X, into the room
]
for name, key, scale, loc, rz, (hx, hy, h) in PIECES:
    proto = K.import_pack(os.path.join(PACK, f"{name}.glb"), key, scale=scale)
    K.linked(K.name("PROP", key), proto, loc, rot=(0, 0, rz))
    K.collider(key, (loc[0] - hx, loc[1] - hy, 0), (loc[0] + hx, loc[1] + hy, h))

bpy.ops.wm.save_mainfile()
print("[vip_pack] placed", [p[1] for p in PIECES])
