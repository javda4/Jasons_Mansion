"""Migration: only open flames flicker. Clears the `flicker` custom property from every light whose name
doesn't contain "Fire" (electric chandeliers/sconces were flagged in V1).
    blender -b <file.blend> --python blender/tools/fix_flicker.py"""
import bpy

n = 0
for o in bpy.data.objects:
    if o.type == "LIGHT" and "flicker" in o.keys() and "Fire" not in o.name:
        del o["flicker"]
        n += 1
bpy.ops.wm.save_mainfile()
print(f"[fix_flicker] {bpy.data.filepath}: {n} lights now steady")
