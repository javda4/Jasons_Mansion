"""Salon Privé hearth: a real wood fire bed in place of the painted flame cards.

    blender -b blender/rooms/vip/vip.blend --python blender/tools/vip_fire.py

Builds (idempotent — re-running replaces its own objects):
- three split-oak logs with photographed bark (Poly Haven bark_brown_02, CC0) and charred end grain,
  irregular and tapered, stacked on a cast-iron basket grate with brass-finialled andirons
- a bed of ash and embers (Poly Haven burned_ground_01, CC0), gently heaped
- FX_Vip_Fire_01: the flames themselves are simulated at runtime (src/fx/fire.ts) — animated flame,
  glowing ember cracks on the logs' undersides and the ash, rising sparks. glTF can't carry animated
  fire; a painted texture on a card is what read as fake.

Materials the runtime recognises by name (src/fx/fire.ts): MAT_Vip_LogBark, MAT_Vip_LogEnd, MAT_Vip_Ashes.
"""
import math
import os
import sys
import urllib.request

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "blender", "textures_src", "vip")
PH = "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/{id}/{id}_{map}_1k.jpg"
RNG = np.random.default_rng(1927)


def fetch(pid, name):
    """Poly Haven 1k set → T_<Name>_{BaseColor,Normal,ORM}.jpg (CC0 source textures, Layer 1)."""
    out = {}
    for ph, ours in (("diff", "BaseColor"), ("nor_gl", "Normal"), ("arm", "ORM")):
        path = os.path.join(TEX, f"T_{name}_{ours}.jpg")
        if not os.path.exists(path):
            urllib.request.urlretrieve(PH.format(id=pid, map=ph), path)
            if ours != "BaseColor":   # data maps at 512, like the scanned props: small on screen, UASTC is heavy
                img = bpy.data.images.load(path)
                img.scale(512, 512)
                img.filepath_raw, img.file_format = path, "JPEG"
                img.save()
                bpy.data.images.remove(img)
        out[ours] = path
    return out


# ---------------------------------------------------------------- clear the old hearth contents
OLD = ("PROP_Vip_Fire_", "PROP_Vip_Log_", "PROP_Vip_FireLog_", "PROP_Vip_FireGrate_", "PROP_Vip_Andiron_", "PROP_Vip_Ashes_", "FX_Vip_Fire_")
for o in [o for o in bpy.data.objects if o.name.startswith(OLD)]:
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for d in [d for d in coll if d.users == 0]:
        coll.remove(d)

K = kit.Zone.__new__(kit.Zone)
K.zone, K.mat, K._n = "Vip", {}, {}
K.coll = {c: bpy.data.collections[f"{c}_Vip"] for c in ("VISUAL", "COLLISION", "LOGIC", "LIGHTS", "PROBES")}
K.wip = bpy.data.collections.get("_WIP_Vip_Notes")

bark = fetch("bark_brown_02", "Vip_LogBark")
ash = fetch("burned_ground_01", "Vip_Ashes")
M = {
    "bark": K.material("bark", "MAT_Vip_LogBark", rough=0.9, base_tex=bark["BaseColor"], normal_tex=bark["Normal"], orm_tex=bark["ORM"]),
    # end grain after an hour in the fire: charred black with a grey ash skin
    "end": K.material("end", "MAT_Vip_LogEnd", base=(0.035, 0.03, 0.028), rough=0.95),
    "ash": K.material("ash", "MAT_Vip_Ashes", rough=0.95, base_tex=ash["BaseColor"], normal_tex=ash["Normal"], orm_tex=ash["ORM"]),
    "iron": K.material("iron", "MAT_Vip_CastIron", base=(0.02, 0.019, 0.018), rough=0.8, metal=0.2),   # stove-blacked iron
    "brass": bpy.data.materials.get("MAT_Brass_Aged") or K.material("brass", "MAT_Brass_Aged", (0.6, 0.45, 0.25), 0.4, 1.0, lib="Brass_Aged"),
}

FY = 10.0                     # firebox back wall (author_vip: fy = D)
FLOOR = 0.06                  # hearth slab top inside the firebox
GRATE_Z = FLOOR + 0.1         # basket bars


def log(name, length, radius, loc, rz=0.0, ry=0.0, seed=0):
    """A split log: an irregular, slightly tapered bark cylinder along local X with charred end caps.
    UV0 in metres (bark tiles at ~0.5 m); the ends are separate faces with MAT_Vip_LogEnd."""
    rng = np.random.default_rng(seed)
    seg, rings = 18, 7
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    # radial bumps (knots, ridges) that persist along the log + a gentle taper and bow
    lobes = rng.normal(0, 0.07, seg)
    lobes = (lobes + np.roll(lobes, 1) + np.roll(lobes, -1)) / 3
    grid = []
    for i in range(rings + 1):
        t = i / rings
        x = (t - 0.5) * length
        taper = 1.0 - 0.12 * t
        bow = 0.012 * math.sin(t * math.pi)
        row = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            r = radius * taper * (1 + lobes[j] + rng.normal(0, 0.025))
            row.append(bm.verts.new((x, r * math.cos(a), r * math.sin(a) + bow)))
        grid.append(row)
    circ = 2 * math.pi * radius
    for i in range(rings):
        for j in range(seg):
            jn = (j + 1) % seg
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][jn], grid[i][jn]))
            f.smooth = True
            f.material_index = 0
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (jj / seg * circ / 0.5, (ii / rings) * length / 0.5)
    for row, flip in ((grid[0], True), (grid[-1], False)):
        vs = list(reversed(row)) if flip else row
        f = bm.faces.new(vs)
        f.material_index = 1
        c = sum((v.co for v in row), Vector()) / len(row)
        for loop in f.loops:
            loop[uv].uv = ((loop.vert.co.y - c.y) / 0.3 + 0.5, (loop.vert.co.z - c.z) / 0.3 + 0.5)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M["bark"])
    me.materials.append(M["end"])
    ob = bpy.data.objects.new(name, me)
    ob.location, ob.rotation_euler = loc, (0, ry, rz)
    K.coll["VISUAL"].objects.link(ob)
    return ob


# ---------------------------------------------------------------- ash & ember bed
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=24, y_segments=8, size=0.5)
uv = bm.loops.layers.uv.verify()
for v in bm.verts:
    x, y = v.co.x * 1.42, v.co.y * 0.3               # 1.42 × 0.3 m
    heap = 0.035 * math.exp(-((x / 0.42) ** 2) - ((y / 0.12) ** 2)) + RNG.normal(0, 0.003)
    v.co = Vector((x, y, max(0.0, heap)))
for f in bm.faces:
    f.smooth = True
    for loop in f.loops:
        loop[uv].uv = (loop.vert.co.x / 0.6, loop.vert.co.y / 0.6)
me = bpy.data.meshes.new("PROP_Vip_Ashes_01")
bm.to_mesh(me)
bm.free()
me.materials.append(M["ash"])
ashes = bpy.data.objects.new("PROP_Vip_Ashes_01", me)
ashes.location = (0, FY - 0.19, FLOOR + 0.002)
K.coll["VISUAL"].objects.link(ashes)

# ---------------------------------------------------------------- cast-iron basket grate + andirons
gy0, gy1 = FY - 0.3, FY - 0.08
for i, y in enumerate(np.linspace(gy0, gy1, 5)):
    K.cyl(f"PROP_Vip_FireGrate_{i + 1:02d}", 0.011, 0.011, 0.86, (0, y, GRATE_Z), M["iron"], segments=10, rot=(0, math.pi / 2, 0))
for i, x in enumerate((-0.4, 0.4)):
    K.box(f"PROP_Vip_FireGrate_{i + 6:02d}", (0.022, gy1 - gy0 + 0.05, 0.022), (x, (gy0 + gy1) / 2, GRATE_Z - 0.012), M["iron"])
    for j, y in enumerate((gy0, gy1)):                                                   # legs
        K.cyl(f"PROP_Vip_FireGrate_{8 + i * 2 + j:02d}", 0.012, 0.016, GRATE_Z - FLOOR, (x, y, (FLOOR + GRATE_Z) / 2), M["iron"], segments=10)
    # andiron: a front upright with a turned brass finial, the usual Belle Époque hearth dress
    K.lathe(f"PROP_Vip_Andiron_{i * 2 + 1:02d}", [(0, 0), (0.05, 0), (0.05, 0.02), (0.02, 0.04), (0.016, 0.3), (0, 0.3)],
            (x * 1.12, gy0 - 0.05, FLOOR), M["iron"], segments=16)
    K.lathe(f"PROP_Vip_Andiron_{i * 2 + 2:02d}", [(0, 0), (0.02, 0), (0.03, 0.02), (0.038, 0.05), (0.03, 0.08), (0.012, 0.1), (0.018, 0.115), (0, 0.13)],
            (x * 1.12, gy0 - 0.05, FLOOR + 0.3), M["brass"], segments=20)

# ---------------------------------------------------------------- logs: two on the grate, one across them
log("PROP_Vip_FireLog_01", 0.74, 0.07, (0.0, FY - 0.13, GRATE_Z + 0.08), rz=0.04, seed=1)          # back log
log("PROP_Vip_FireLog_02", 0.66, 0.06, (0.03, FY - 0.26, GRATE_Z + 0.07), rz=-0.07, seed=2)        # front log
log("PROP_Vip_FireLog_03", 0.58, 0.052, (-0.04, FY - 0.2, GRATE_Z + 0.2), rz=0.42, ry=-0.12, seed=3)  # across, leaning

# ---------------------------------------------------------------- soot & firelight
# a working firebox is lined with soot (albedo ≈ 0.02), not warm brick
soot = bpy.data.materials.get("MAT_Vip_Firebrick")
if soot:
    b = soot.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.018, 0.015, 0.013, 1)
    b.inputs["Roughness"].default_value = 0.97
# the firelight sits out in front of the opening, at hearth height: inside the firebox (0.3 m from the
# logs) it blew the whole hearth out to cream. 12 cd (SPEC: W = cd·4π/683) — the flames are the bright part
fl = bpy.data.objects.get("LIGHT_Vip_Fire_01")
if fl:
    fl.location = (0, FY - 1.25, 0.55)
    fl.data.energy = kit.watts(12)

# ---------------------------------------------------------------- the runtime flame
fx = bpy.data.objects.new("FX_Vip_Fire_01", None)
fx.empty_display_type = "CONE"
fx.empty_display_size = 0.2
fx.location = (0, FY - 0.19, GRATE_Z + 0.05)
fx["effect"] = "fire"
fx["width"] = 0.62      # flame bed extent (m) along X
fx["depth"] = 0.2       # … along Y
fx["height"] = 0.5      # tallest tongues
K.coll["LOGIC"].objects.link(fx)

bpy.ops.wm.save_mainfile()
print("[vip_fire] hearth rebuilt:", len([o for o in bpy.data.objects if o.name.startswith(OLD)]), "objects")
