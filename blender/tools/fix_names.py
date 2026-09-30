"""One-off migration for .blend files authored before the V2 naming fix (run on *_baked.blend so the
lightmap bake is kept):  blender -b <file.blend> --python blender/tools/fix_names.py

- imported-prop materials  MAT_<Zone>_<Key>_<Part>  →  MAT_<Key>_<Part>   (§6: MAT_<Surface>_<Variant>)
- lobby bust-pedestal colliders that collided with the lamp pedestals' names (.001)
"""
import re

import bpy

ZONE_MAT = re.compile(r"^MAT_([A-Z][A-Za-z0-9]*)_([A-Z][A-Za-z0-9]*)_([A-Za-z0-9]+)$")
n = 0
for m in bpy.data.materials:
    mm = ZONE_MAT.match(m.name)
    if mm:
        part = mm.group(3)
        m.name = f"MAT_{mm.group(2)}_{'Main' + part if part[0].isdigit() else part}"
        n += 1
k = 0
for o in list(bpy.data.objects):
    mo = re.match(r"^COLLIDER_(\w+?)_Pedestal_(\d\d)\.\d{3}$", o.name)
    if mo:
        o.name = f"COLLIDER_{mo.group(1)}_BustPedestal_{mo.group(2)}"
        k += 1
bpy.ops.wm.save_mainfile()
print(f"[fix_names] {bpy.data.filepath}: {n} materials, {k} colliders renamed")
