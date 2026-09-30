"""Bake a zone's lightmap with Cycles (Layer 1). Hybrid lighting, CLAUDE.md §8 / architecture.md §F.

    blender -b blender/rooms/<zone>/<zone>.blend --python blender/tools/bake_lightmap.py -- <zone> <Zone> [size] [samples]

What gets baked into one atlas on UV1 ("Lightmap") of every object flagged `lightmap`:
  • INDIRECT diffuse light from *all* lights and emissive surfaces (bounce light, colour bleed,
    soft occlusion) — the runtime has no GI, so this is the realism workhorse;
  • DIRECT diffuse light from lights marked `bakeOnly` (sconces, lamps…). Those lights are skipped
    at runtime, freeing the LightPool for the few dynamic hero lights (chandelier + its shadow key),
    whose direct light stays real-time so it isn't counted twice.

Units: the runtime treats a lightmap texel as irradiance (three.js adds it to `irradiance`, then
multiplies by albedo/π). Cycles' diffuse-light pass is irradiance/π, and exported lights are
W = 4π·cd/683, so during the bake light power is scaled ×683 (→ W = 4π·cd) to match three's
candela-based lights. Runtime `lightMapIntensity` = π / encodeScale.

Outputs (source artefacts, committed):
  blender/rooms/<zone>/<zone>_baked.blend   joined lightmapped geometry + UV1 (what gets exported)
  blender/textures_src/<zone>/T_<Zone>_Lightmap.png   8-bit sRGB-encoded, scaled by encodeScale
  blender/textures_src/<zone>/T_<Zone>_Lightmap.json  { "intensity": π / encodeScale, … }
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    sys.exit("usage: … --python bake_lightmap.py -- <zone> <Zone> [size=2048] [samples=256]")
zone_id, ZONE = argv[0], argv[1]
SIZE = int(argv[2]) if len(argv) > 2 else 2048
SAMPLES = int(argv[3]) if len(argv) > 3 else 256

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_BLEND = os.path.join(ROOT, "blender", "rooms", zone_id, f"{zone_id}_baked.blend")
OUT_DIR = os.path.join(ROOT, "blender", "textures_src", zone_id)
os.makedirs(OUT_DIR, exist_ok=True)
t_start = time.time()
scene = bpy.context.scene
vl = bpy.context.view_layer


def log(msg):
    print(f"[bake {time.time() - t_start:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------- 1) apply modifiers, join per material
flagged = [o for o in scene.objects if o.type == "MESH" and o.get("lightmap")]
log(f"{len(flagged)} lightmapped objects")
dg = bpy.context.evaluated_depsgraph_get()
for o in flagged:
    if o.modifiers:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear()
        o.data = me
groups = {}
for o in flagged:
    key = o.active_material.name if o.active_material else "_none"
    groups.setdefault(key, []).append(o)

bpy.ops.object.select_all(action="DESELECT")
joined = []
for i, (mat, objs) in enumerate(sorted(groups.items())):
    for o in objs:
        o.select_set(True)
    vl.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = vl.objects.active
    ob.name = ob.data.name = f"ROOM_{ZONE}_Lightmapped_{i + 1:02d}"
    ob["lightmap"] = True
    joined.append(ob)
    bpy.ops.object.select_all(action="DESELECT")
log(f"joined into {len(joined)} objects by material")

# ---------------------------------------------------------------- 2) UV1 atlas
for ob in joined:
    uv0 = ob.data.uv_layers[0]
    uv0.active_render = True           # material textures keep using UV0
    lm = ob.data.uv_layers.new(name="Lightmap")
    ob.data.uv_layers.active = lm      # unwrap + bake target
for ob in joined:
    ob.select_set(True)
vl.objects.active = joined[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.select_all(action="SELECT")
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(rotate=True, margin=2.5 / SIZE * 4)
bpy.ops.object.mode_set(mode="OBJECT")
log("UV1 unwrapped and packed")

# ---------------------------------------------------------------- 3) Cycles setup
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:  # pragma: no cover - CPU fallback
    log(f"GPU unavailable ({e}); baking on CPU")
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 4
scene.cycles.glossy_bounces = 2
scene.cycles.sample_clamp_indirect = 8.0  # tame fireflies from tiny bright emitters
scene.world.color = (0, 0, 0)
scene.render.bake.margin = 6
scene.render.bake.margin_type = "EXTEND"

lights = [o for o in scene.objects if o.type == "LIGHT"]
energy = {o.name: o.data.energy for o in lights}
for o in lights:
    o.data.energy *= 683.0  # W = 4π·cd/683  →  4π·cd  (three.js point-light units)

img = bpy.data.images.new(f"T_{ZONE}_Lightmap_bake", SIZE, SIZE, float_buffer=True, alpha=False)
bake_nodes = []
for mat in {s.material for ob in joined for s in ob.material_slots if s.material}:
    nt = mat.node_tree
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = img
    n.interpolation = "Linear"
    nt.nodes.active = n
    bake_nodes.append((nt, n))

bpy.ops.object.select_all(action="DESELECT")
for ob in joined:
    ob.select_set(True)
vl.objects.active = joined[0]


def bake(pass_filter):
    bpy.ops.object.bake(type="DIFFUSE", pass_filter=pass_filter, margin=6, margin_type="EXTEND", use_clear=True, target="IMAGE_TEXTURES")
    return np.array(img.pixels[:], dtype=np.float32).reshape(SIZE, SIZE, 4)[..., :3].copy()


log(f"baking INDIRECT ({SIZE}², {SAMPLES} spp, all lights)")
indirect = bake({"INDIRECT"})
dynamic = [o for o in lights if not o.get("bakeOnly")]
for o in dynamic:
    o.hide_render = True
log(f"baking DIRECT (bake-only lights: {len(lights) - len(dynamic)}; dynamic hidden: {[o.name for o in dynamic]})")
direct = bake({"DIRECT"})
for o in dynamic:
    o.hide_render = False
for o in lights:
    o.data.energy = energy[o.name]
for nt, n in bake_nodes:
    nt.nodes.remove(n)

# ---------------------------------------------------------------- 4) encode: scale → sRGB 8-bit
lm = indirect + direct
lum = lm @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
covered = lum > 1e-6
p = float(np.percentile(lum[covered], 99.5)) if covered.any() else 1.0
encode_scale = 1.0 / max(p, 1e-6)
v = np.clip(lm * encode_scale, 0, 1)
srgb = np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)
out = bpy.data.images.new(f"T_{ZONE}_Lightmap", SIZE, SIZE, alpha=False)  # byte image: values stored as-is
out.pixels.foreach_set(np.concatenate([srgb, np.ones((SIZE, SIZE, 1), np.float32)], -1).ravel())
png = os.path.join(OUT_DIR, f"T_{ZONE}_Lightmap.png")
out.filepath_raw = png
out.file_format = "PNG"
out.save()
meta = {
    "zone": zone_id, "size": SIZE, "samples": SAMPLES,
    "encodeScale": encode_scale, "intensity": math.pi / encode_scale,
    "p99_5": p, "max": float(lum.max()), "coverage": float(covered.mean()),
    "objects": [o.name for o in joined],
    "bakeOnlyLights": [o.name for o in lights if o.get("bakeOnly")],
    "seconds": round(time.time() - t_start, 1),
}
with open(os.path.join(OUT_DIR, f"T_{ZONE}_Lightmap.json"), "w") as f:
    json.dump(meta, f, indent=2)
log(f"lightmap → {png} (encodeScale {encode_scale:.4f}, runtime intensity {meta['intensity']:.3f})")

# ---------------------------------------------------------------- 5) save the baked working file
for ob in joined:
    del ob["lightmap"]           # authoring-only flag; must not become glTF extras
bpy.data.images.remove(img)
bpy.data.images.remove(out)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
log(f"saved {OUT_BLEND}")
