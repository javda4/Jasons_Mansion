"""Migration: tint the sheen of rug / fringe / petal zone materials (Blender's default sheen tint is white,
which exported as a white film). Run on source and *_baked.blend files; the bake is unaffected.
    blender -b <file.blend> --python blender/tools/fix_sheen.py"""
import re

import bpy

n = 0
for m in bpy.data.materials:
    b = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if b is None:
        continue
    if re.match(r"^MAT_\w+_(Rug[A-Z]\w*|Runner\w+)$", m.name) and "Fringe" not in m.name:
        b.inputs["Sheen Weight"].default_value = 0.3
        b.inputs["Sheen Tint"].default_value = (0.42, 0.12, 0.08, 1)
    elif m.name.endswith("_RugFringe"):
        b.inputs["Sheen Weight"].default_value = 0.2
        b.inputs["Base Color"].default_value = (0.5, 0.44, 0.33, 1)
        b.inputs["Sheen Tint"].default_value = (0.5, 0.44, 0.33, 1)
    elif m.name.endswith(("_RoseRed", "_RoseIvory")):
        b.inputs["Sheen Weight"].default_value = 0.2
        b.inputs["Roughness"].default_value = 0.78
        b.inputs["Sheen Tint"].default_value = (0.46, 0.022, 0.045, 1) if m.name.endswith("Red") else (0.82, 0.77, 0.66, 1)
    else:
        continue
    n += 1
bpy.ops.wm.save_mainfile()
print(f"[fix_sheen] {bpy.data.filepath}: {n} materials")
