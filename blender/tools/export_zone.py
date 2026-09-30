"""Validate and export one zone to raw GLB (Layer 2 input; optimised later by scripts/build-assets).

Usage (headless):
    blender -b blender/rooms/<zone>/<zone>.blend --python blender/tools/export_zone.py -- <zoneId> <Zone> <out.glb>
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import validate_zone as V  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) != 3:
    sys.exit("usage: ... --python export_zone.py -- <zoneId> <Zone> <out.glb>")
zone_id, zone, out = argv

if not V.report(zone):
    sys.exit(1)

# Select exactly the exportable objects (excludes _WIP / _REF collections)
bpy.ops.object.select_all(action="DESELECT") if bpy.context.view_layer.objects else None
keep = set(V.exported_objects())
for o in bpy.context.view_layer.objects:
    o.select_set(o in keep)

os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=os.path.abspath(out),
    export_format="GLB",
    use_selection=True,
    export_yup=True,                     # Blender Z-up → glTF Y-up (never pre-rotate)
    export_apply=True,                   # bevels / subdivision baked into the mesh
    export_extras=True,                  # custom properties → glTF extras → runtime userData
    export_lights=True,                  # LIGHT_ → KHR_lights_punctual
    export_import_convert_lighting_mode="SPEC",  # physical: candela = W / 4π × 683
    export_cameras=False,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_attributes=False,
    export_meshopt_compression_enable=False,  # compression happens in the optimise step
    export_draco_mesh_compression_enable=False,
)
print(f"[export] {zone_id} → {out} ({os.path.getsize(out) / 1024:.0f} KiB)")
