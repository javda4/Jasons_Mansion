"""Salon Privé: replace the box-built leather sofas with the lobby's photoscanned Louis sofa
(Poly Haven Sofa_01, upholstered silk tinted antique gold — the same prototype as the Grand Lobby).

    blender -b blender/rooms/vip/vip.blend --python blender/tools/vip_sofas.py

vip.blend is the zone's source of truth after its bootstrap (author_vip.py), so this edits it in place.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402

SOFAS = [((-1.85, 6.2, 0.0), -math.pi / 2), ((1.85, 6.2, 0.0), math.pi / 2)]   # against the side walls, facing the hearth

for o in [o for o in bpy.data.objects if o.name.startswith(("PROP_Vip_Sofa_", "PROP_Vip_LouisSofa"))]:
    bpy.data.objects.remove(o, do_unlink=True)
for me in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(me)
for m in [m for m in bpy.data.materials if m.users == 0]:
    bpy.data.materials.remove(m)

# a kit.Zone bound to the existing collections (kit.Zone() would create new ones)
K = kit.Zone.__new__(kit.Zone)
K.zone, K.mat, K._n = "Vip", {}, {}
K.coll = {c: bpy.data.collections[f"{c}_Vip"] for c in ("VISUAL", "COLLISION", "LOGIC", "LIGHTS", "PROBES")}
K.wip = bpy.data.collections.get("_WIP_Vip_Notes")

proto = K.import_prop("Sofa_01", "LouisSofa", tint={"Sofa": (0.62, 0.5, 0.36)}, scale=1.25)   # ≈ 1.75 m settee
sx, sy, sz = proto["dims"]
for i, (loc, rz) in enumerate(SOFAS):
    K.linked(K.name("PROP", "LouisSofa"), proto, loc, rot=(0, 0, rz))       # instances; the prototype stays in _WIP
    c = bpy.data.objects[f"COLLIDER_Vip_Sofa_{i + 1:02d}"]                  # fitted to the new footprint
    c.scale = (1, 1, 1)
    c.dimensions = (sy + 0.04, sx + 0.04, c.dimensions.z)
    c.data.transform(Matrix.Diagonal((*c.scale, 1.0)))                       # colliders keep scale 1 (§6)
    c.scale = (1, 1, 1)
    c.location.x = loc[0]
print("[vip_sofas] dims", tuple(round(v, 2) for v in (sx, sy, sz)))
bpy.ops.wm.save_mainfile()
