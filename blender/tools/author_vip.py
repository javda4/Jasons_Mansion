"""Bootstrap authoring of the Salon Privé (VIP room) — the Phase 2 Blender → web demo zone.

Builds blender/rooms/vip/vip.blend from scratch (and its unique source textures). After this
one-time bootstrap the .blend is the source of truth: open it in Blender and edit by hand.

    blender -b --factory-startup --python blender/tools/author_vip.py

Conventions (CLAUDE.md §6): metres, Z-up (the exporter converts to Y-up), room origin = entrance
threshold centre at floor level, room extends along +Y (→ glTF -Z). Names PREFIX_Vip_Name_NN.
Library materials (src/render/materialNames.ts) are matched by name; MAT_Vip_* are zone-unique.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB_TEX = os.path.join(ROOT, "blender", "textures_src", "polyhaven")
VIP_TEX = os.path.join(ROOT, "blender", "textures_src", "vip")
OUT = os.path.join(ROOT, "blender", "rooms", "vip", "vip.blend")

W, D, H, T = 10.0, 10.0, 5.0, 0.3
DOOR_W, DOOR_H = 2.2, 3.1
RNG = np.random.default_rng(1924)


def watts(candela: float) -> float:
    """Blender light power for a target intensity (exporter SPEC mode: cd = W / 4π × 683)."""
    return candela * 4 * math.pi / 683


# ------------------------------------------------------------------ scene & collections
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

zone_coll = bpy.data.collections.new("ZONE_Vip")
scene.collection.children.link(zone_coll)
COLL = {}
for sub in ("VISUAL", "COLLISION", "LOGIC", "LIGHTS", "PROBES"):
    c = bpy.data.collections.new(f"{sub}_Vip")
    zone_coll.children.link(c)
    COLL[sub] = c
wip = bpy.data.collections.new("_WIP_Vip_Notes")  # never exported (§6)
zone_coll.children.link(wip)

# ------------------------------------------------------------------ textures (zone-unique)
os.makedirs(VIP_TEX, exist_ok=True)


def save_image(name: str, rgba: np.ndarray) -> str:
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(np.clip(rgba, 0, 1).astype(np.float32).ravel())
    path = os.path.join(VIP_TEX, f"{name}.png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def blur(a: np.ndarray, r: int) -> np.ndarray:
    for axis in (0, 1):
        acc = np.zeros_like(a)
        for k in range(-r, r + 1):
            acc += np.roll(a, k, axis=axis)
        a = acc / (2 * r + 1)
    return a


def fire_texture() -> str:
    w, h = 512, 512
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]  # row 0 = bottom in Blender images
    v = np.zeros((h, w))
    for c, peak, width in [(-0.55, 0.55, 0.16), (-0.25, 0.8, 0.2), (0.05, 0.95, 0.22), (0.35, 0.75, 0.18), (0.6, 0.5, 0.14)]:
        sway = 0.06 * np.sin(y * 9 + c * 5)
        shape = np.exp(-(((x - c - sway) / (width * (1 - y / peak) + 0.02)) ** 2)) * (y < peak) * np.clip(1 - y / peak, 0, 1) ** 0.5
        v += shape
    v += 0.6 * np.exp(-((y - 0.04) / 0.06) ** 2) * (np.abs(x) < 0.8)  # embers
    v = blur(np.clip(v, 0, 1.4), 3)
    rgb = np.stack([np.clip(v * 1.4, 0, 1), np.clip(v ** 1.6 * 0.9, 0, 1), np.clip(v ** 4 * 0.5, 0, 1)], axis=-1)
    return save_image("T_Vip_Fire_Emissive", np.concatenate([rgb, np.ones((h, w, 1))], axis=-1))


def sea_texture() -> str:
    w, h = 1024, 1024
    y = np.linspace(0, 1, h)[:, None]
    horizon = 0.38
    sky = np.stack([0.02 + 0.10 * (1 - y), 0.03 + 0.10 * (1 - y), 0.10 + 0.20 * (1 - y)], -1) * np.ones((1, w, 1))
    sea = np.stack([0.01 + 0.02 * y, 0.015 + 0.03 * y, 0.04 + 0.06 * y], -1) * np.ones((1, w, 1))
    img = np.where((y > horizon)[..., None], sky, sea)
    # stars
    n = 500
    sx, sy = RNG.integers(0, w, n), RNG.integers(int(h * 0.45), h, n)
    img[sy, sx] += RNG.uniform(0.2, 0.9, (n, 1))
    # moon + glow + moon path
    mx, my = int(w * 0.68), int(h * 0.8)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - mx, yy - my)
    img += (np.exp(-(d / 90) ** 2) * 0.25)[..., None] * np.array([1, 0.95, 0.85])
    img[d < 22] = [1.0, 0.97, 0.88]
    path = (np.abs(xx - mx) < (8 + (horizon * h - yy) * 0.35)) & (yy < horizon * h) & (RNG.random((h, w)) < 0.35)
    img[path] += np.array([0.5, 0.45, 0.35]) * ((yy[path] / (horizon * h)) ** 1.5)[:, None]
    # headland with villa lights
    ridge = horizon * h + 90 * np.sin(np.linspace(0, math.pi, w)) * (np.linspace(0, 1, w) < 0.55) + 6
    land = (yy < ridge[None, :]) & (yy > horizon * h - 2) & (xx < w * 0.55)
    img[land] = [0.01, 0.01, 0.015]
    lx = RNG.integers(0, int(w * 0.55), 110)
    ly = (horizon * h + RNG.random(110) * (ridge[lx] - horizon * h)).astype(int)
    for px, py in zip(lx, ly):
        img[py:py + 2, px:px + 2] = [1.0, 0.7, 0.35]
    img = blur(img, 1)
    return save_image("T_Vip_SeaView_Emissive", np.concatenate([np.clip(img, 0, 1), np.ones((h, w, 1))], axis=-1))


def painting_texture(name: str, seed: int) -> str:
    w, h = 512, 1024
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, h)[:, None, None]
    base = (1 - y) * np.array([0.08, 0.05, 0.03]) + y * np.array([0.35, 0.25, 0.12] if seed % 2 else [0.22, 0.26, 0.22])
    img = base * np.ones((1, w, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(40):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h * 0.6)
        rx, ry = rng.uniform(30, 160), rng.uniform(20, 90)
        m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1
        img[m] = img[m] * 0.5 + np.array(rng.choice([[0.2, 0.12, 0.05], [0.35, 0.22, 0.1], [0.1, 0.07, 0.04]])) * 0.5
    img = blur(img, 6)
    v = np.hypot((xx - w / 2) / w, (yy - h / 2) / h)
    img *= np.clip(1.25 - v * 1.6, 0.25, 1)[..., None]
    return save_image(name, np.concatenate([img, np.ones((h, w, 1))], axis=-1))


TEX_FIRE, TEX_SEA = fire_texture(), sea_texture()
TEX_PAINT_A, TEX_PAINT_B = painting_texture("T_Vip_PaintingA_BaseColor", 7), painting_texture("T_Vip_PaintingB_BaseColor", 12)

# ------------------------------------------------------------------ materials


def _image(path: str, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def material(name, base=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, coat=0.0, coat_rough=0.03, sheen=0.0,
             lib=None, base_tex=None, emis_tex=None, emis_strength=0.0):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True  # node materials are always on from Blender 5
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = coat_rough
    bsdf.inputs["Sheen Weight"].default_value = sheen
    y = 300
    if lib:  # authoring preview for library materials (textures are stripped at build time)
        stem = os.path.join(LIB_TEX, f"T_{lib}")
        if os.path.exists(stem + "_BaseColor.jpg"):
            t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-500, y); t.image = _image(stem + "_BaseColor.jpg")
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if os.path.exists(stem + "_Normal.jpg"):
            t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-700, -300); t.image = _image(stem + "_Normal.jpg", True)
            nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-300, -300)
            nt.links.new(t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if base_tex:
        t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-500, y); t.image = _image(base_tex)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if emis_tex:
        t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-500, -100); t.image = _image(emis_tex)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emis_strength
    return m


M = {
    # library (name-matched at runtime; preview only here)
    "marble": material("MAT_Marble_Calacatta", (0.85, 0.8, 0.72), 0.2, coat=1, lib="Marble_Calacatta"),
    "nero": material("MAT_Marble_Nero", (0.05, 0.045, 0.04), 0.2, coat=1, lib="Marble_Calacatta"),
    "walnut": material("MAT_Wood_WalnutPolished", (0.3, 0.19, 0.12), 0.45, coat=1, lib="Wood_WalnutPolished"),
    "walnut_dark": material("MAT_Wood_WalnutDark", (0.12, 0.07, 0.05), 0.5, coat=1, lib="Wood_WalnutPolished"),
    "damask": material("MAT_Fabric_DamaskOxblood", (0.3, 0.05, 0.05), 0.9, sheen=0.4, lib="Fabric_Damask"),
    "damask_green": material("MAT_Fabric_DamaskForest", (0.1, 0.2, 0.13), 0.9, sheen=0.4, lib="Fabric_Damask"),
    "carpet": material("MAT_Fabric_CarpetCrimson", (0.35, 0.05, 0.05), 1.0, sheen=0.6, lib="Fabric_Damask"),
    "velvet": material("MAT_Fabric_VelvetRed", (0.22, 0.02, 0.02), 0.85, sheen=1.0),
    "leather": material("MAT_Leather_Oxblood", (0.25, 0.06, 0.05), 0.6, coat=0.4, coat_rough=0.3),
    "brass": material("MAT_Brass_Aged", (0.72, 0.54, 0.29), 0.32, metal=1),
    "gilt": material("MAT_Gold_Gilt", (0.85, 0.68, 0.36), 0.22, metal=1),
    "crystal": material("MAT_Crystal_Clear", (1, 1, 1), 0.02),
    "candle": material("MAT_Emissive_Candle", (0, 0, 0), 0.5),
    "shade": material("MAT_Fabric_LampShade", (0.9, 0.83, 0.66), 0.9),
    "ceiling": material("MAT_Plaster_Ceiling", (0.12, 0.08, 0.05), 0.55),
    # zone-unique (ship in the GLB as KTX2)
    "fire": material("MAT_Vip_Fire", (0, 0, 0), 1.0, emis_tex=TEX_FIRE, emis_strength=6.0),
    "sea": material("MAT_Vip_SeaView", (0, 0, 0), 0.1, emis_tex=TEX_SEA, emis_strength=1.1),
    "paint_a": material("MAT_Vip_PaintingA", rough=0.45, base_tex=TEX_PAINT_A),
    "paint_b": material("MAT_Vip_PaintingB", rough=0.45, base_tex=TEX_PAINT_B),
    "mirror": material("MAT_Vip_Mirror", (0.9, 0.86, 0.78), 0.04, metal=1),
    "soot": material("MAT_Vip_Firebrick", (0.018, 0.015, 0.013), 0.97),
}
M["candle"].node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 0.76, 0.48, 1)
M["candle"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 40

# ------------------------------------------------------------------ geometry helpers


def box_uv(bm, offset=Vector()):
    """Box-map UV0 in metres so tiling library materials keep constant texel density."""
    uv = bm.loops.layers.uv.verify()
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            c = loop.vert.co + offset
            loop[uv].uv = (c.y, c.z) if ax == 0 else (c.x, c.z) if ax == 1 else (c.x, c.y)


def new_object(name, bm, mat, coll, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, segments=2, subsurf=0, smooth=False, offset_uv=True):
    if offset_uv:
        box_uv(bm, Vector(loc))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth or bevel or subsurf:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    if mat:
        me.materials.append(mat)
    coll.objects.link(ob)
    if bevel:
        mod = ob.modifiers.new("Bevel", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, segments, "ANGLE"
        mod.harden_normals = not subsurf
    if subsurf:
        mod = ob.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = mod.render_levels = subsurf
    return ob


def linked(name, src, coll, loc, rot=(0, 0, 0), scale=(1, 1, 1)):
    """Linked duplicate: shares mesh data → exported as a shared mesh → GPU instancing."""
    ob = bpy.data.objects.new(name, src.data)
    ob.location, ob.rotation_euler, ob.scale = loc, rot, scale
    for m in src.modifiers:
        n = ob.modifiers.new(m.name, m.type)
        for attr in ("width", "segments", "limit_method", "harden_normals", "levels", "render_levels"):
            if hasattr(m, attr):
                setattr(n, attr, getattr(m, attr))
    coll.objects.link(ob)
    return ob


def cube_bm(sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    return bm


def box(name, size, loc, mat, coll=None, **kw):
    return new_object(name, cube_bm(*size), mat, coll or COLL["VISUAL"], loc, **kw)


def cyl(name, r1, r2, h, loc, mat, segments=24, coll=None, rot=(0, 0, 0), **kw):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r1, radius2=r2, depth=h)
    return new_object(name, bm, mat, coll or COLL["VISUAL"], loc, rot=rot, smooth=True, **kw)


def torus(name, R, r, loc, mat, major=48, minor=8, coll=None):
    bm = bmesh.new()
    rings = []
    for i in range(major):
        a = 2 * math.pi * i / major
        ring = []
        for j in range(minor):
            b = 2 * math.pi * j / minor
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        rings.append(ring)
    for i in range(major):
        for j in range(minor):
            bm.faces.new((rings[i][j], rings[(i + 1) % major][j], rings[(i + 1) % major][(j + 1) % minor], rings[i][(j + 1) % minor]))
    return new_object(name, bm, mat, coll or COLL["VISUAL"], loc, smooth=True)


def collider(name, lo, hi):
    size = [hi[i] - lo[i] for i in range(3)]
    loc = [(hi[i] + lo[i]) / 2 for i in range(3)]
    ob = new_object(f"COLLIDER_Vip_{name}", cube_bm(*size), None, COLL["COLLISION"], loc, offset_uv=False)
    ob.display_type = "WIRE"
    ob.hide_render = True
    return ob


def point_light(name, loc, candela, color=(1.0, 0.69, 0.44), rng=6.0, flicker=False):
    lt = bpy.data.lights.new(name, "POINT")
    lt.energy = watts(candela)
    lt.color = color
    lt.shadow_soft_size = 0.05
    lt.use_custom_distance = True
    lt.cutoff_distance = rng
    ob = bpy.data.objects.new(name, lt)
    ob.location = loc
    if flicker:
        ob["flicker"] = True
    COLL["LIGHTS"].objects.link(ob)
    return ob


def spot_light(name, loc, candela, angle, blend=0.8, color=(1.0, 0.69, 0.44), rng=12.0, shadow=False):
    lt = bpy.data.lights.new(name, "SPOT")
    lt.energy = watts(candela)
    lt.color = color
    lt.spot_size = angle
    lt.spot_blend = blend
    lt.use_custom_distance = True
    lt.cutoff_distance = rng
    ob = bpy.data.objects.new(name, lt)
    ob.location = loc  # default orientation points down -Z
    if shadow:
        ob["castShadow"] = True
    COLL["LIGHTS"].objects.link(ob)
    return ob


def empty(name, loc, coll, rot=(0, 0, 0), kind="PLAIN_AXES"):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = kind
    ob.location, ob.rotation_euler = loc, rot
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ room shell
V = COLL["VISUAL"]
box("ROOM_Vip_Floor", (W, D, 0.2), (0, D / 2, -0.1), M["walnut"])
box("ROOM_Vip_Ceiling", (W, D, 0.3), (0, D / 2, H + 0.15), M["ceiling"])
for i, x in enumerate((-2.5, 0, 2.5)):
    box(f"ROOM_Vip_BeamX_{i + 1:02d}", (0.26, D, 0.3), (x, D / 2, H - 0.15), M["walnut"], bevel=0.01)
for i, y in enumerate((2.5, 5, 7.5)):
    box(f"ROOM_Vip_BeamY_{i + 1:02d}", (W, 0.26, 0.3), (0, y, H - 0.151), M["walnut"], bevel=0.01)

box("ROOM_Vip_WallBack", (W + 2 * T, T, H), (0, D + T / 2, H / 2), M["walnut_dark"])
box("ROOM_Vip_WallLeft", (T, D, H), (-W / 2 - T / 2, D / 2, H / 2), M["walnut_dark"])
box("ROOM_Vip_WallRight", (T, D, H), (W / 2 + T / 2, D / 2, H / 2), M["walnut_dark"])
side = (W / 2 - DOOR_W / 2)
box("ROOM_Vip_WallFrontL", (side, T, H), (-(DOOR_W / 2 + side / 2), -T / 2, H / 2), M["walnut_dark"])
box("ROOM_Vip_WallFrontR", (side, T, H), (DOOR_W / 2 + side / 2, -T / 2, H / 2), M["walnut_dark"])
box("ROOM_Vip_WallFrontTop", (DOOR_W, T, H - DOOR_H), (0, -T / 2, (H + DOOR_H) / 2), M["walnut_dark"])

collider("Floor", (-W / 2 - 0.5, -0.5, -0.5), (W / 2 + 0.5, D + 0.5, 0))
collider("WallBack", (-W / 2 - T, D, 0), (W / 2 + T, D + T, H))
collider("WallLeft", (-W / 2 - T, 0, 0), (-W / 2, D, H))
collider("WallRight", (W / 2, 0, 0), (W / 2 + T, D, H))
collider("WallFrontL", (-W / 2 - T, -T, 0), (-DOOR_W / 2, 0, H))
collider("WallFrontR", (DOOR_W / 2, -T, 0), (W / 2 + T, 0, H))
collider("WallFrontTop", (-DOOR_W / 2, -T, DOOR_H), (DOOR_W / 2, 0, H))


def dress_wall(tag, axis, surface, normal, lo, hi, gaps=(), field=M["damask"]):
    """Wainscot, chair rail, fabric field, frieze and stepped gilt cornice along one wall.
    axis 'x': wall runs along X at y=surface (normal ±Y); axis 'y': along Y at x=surface."""
    spans, start = [], lo
    for g0, g1 in sorted(gaps):
        if g0 > start:
            spans.append((start, g0))
        start = max(start, g1)
    if start < hi:
        spans.append((start, hi))
    layers = [  # (z0, z1, depth, material, bevel, full-height-only?)
        (0.0, 0.12, 0.09, M["walnut"], 0.01, False),  # skirting
        (0.0, 1.0, 0.05, M["walnut"], 0.006, False),  # wainscot
        (1.0, 1.07, 0.08, M["gilt"], 0.01, False),    # chair rail
        (1.07, 4.1, 0.02, field, 0.0, False),         # fabric field
        (4.1, 4.55, 0.08, M["walnut"], 0.006, True),  # frieze
        (4.55, 4.7, 0.14, M["gilt"], 0.01, True),     # cornice
        (4.7, 4.85, 0.2, M["walnut"], 0.01, True),
        (4.85, 5.0, 0.3, M["gilt"], 0.01, True),
    ]
    n = 0
    for (z0, z1, depth, mat, bev, full) in layers:
        for (a, b) in ([(lo, hi)] if full else spans):
            n += 1
            length, mid, zc = b - a, (a + b) / 2, (z0 + z1) / 2
            off = surface + normal * depth / 2
            if axis == "x":
                box(f"ROOM_Vip_{tag}_{n:02d}", (length, depth, z1 - z0), (mid, off, zc), mat, bevel=bev)
            else:
                box(f"ROOM_Vip_{tag}_{n:02d}", (depth, length, z1 - z0), (off, mid, zc), mat, bevel=bev)
    # raised wainscot panels
    for (a, b) in spans:
        k = max(1, round((b - a) / 1.3))
        pw = (b - a) / k
        for i in range(k):
            n += 1
            c = a + pw * (i + 0.5)
            off = surface + normal * 0.075
            size = (pw - 0.3, 0.02, 0.62) if axis == "x" else (0.02, pw - 0.3, 0.62)
            loc = (c, off, 0.52) if axis == "x" else (off, c, 0.52)
            box(f"ROOM_Vip_{tag}_{n:02d}", size, loc, M["walnut_dark"], bevel=0.008)


dress_wall("DressBack", "x", D, -1, -W / 2, W / 2, gaps=[(-1.45, 1.45)])
dress_wall("DressLeft", "y", -W / 2, 1, 0, D, gaps=[(3.3, 6.7)], field=M["damask_green"])
dress_wall("DressRight", "y", W / 2, -1, 0, D, gaps=[(3.6, 6.4)])
dress_wall("DressFront", "x", 0, 1, -W / 2, W / 2, gaps=[(-1.4, 1.4)])

# pilasters at corners and flanking features
for i, (x, y, sx, sy) in enumerate([
    (-4.8, D - 0.07, 0.4, 0.14), (4.8, D - 0.07, 0.4, 0.14), (-1.65, D - 0.07, 0.4, 0.14), (1.65, D - 0.07, 0.4, 0.14),
    (-4.8, 0.07, 0.4, 0.14), (4.8, 0.07, 0.4, 0.14), (-1.6, 0.07, 0.4, 0.14), (1.6, 0.07, 0.4, 0.14),
]):
    box(f"ROOM_Vip_Pilaster_{i + 1:02d}", (sx, sy, 4.1), (x, y, 2.05), M["walnut"], bevel=0.012)
    box(f"ROOM_Vip_PilasterCap_{i + 1:02d}", (sx + 0.06, sy + 0.04, 0.2), (x, y, 4.0), M["gilt"], bevel=0.01)

# door architrave on the room side
for i, x in enumerate((-1.2, 1.2)):
    box(f"ROOM_Vip_Architrave_{i + 1:02d}", (0.2, 0.08, DOOR_H + 0.2), (x, 0.04, (DOOR_H + 0.2) / 2), M["walnut"], bevel=0.01)
box("ROOM_Vip_Architrave_03", (DOOR_W + 0.6, 0.1, 0.22), (0, 0.05, DOOR_H + 0.11), M["walnut"], bevel=0.01)
box("ROOM_Vip_Architrave_04", (DOOR_W + 0.7, 0.14, 0.05), (0, 0.07, DOOR_H + 0.25), M["gilt"], bevel=0.01)

# ------------------------------------------------------------------ fireplace (back wall)
fy = D  # wall surface
for i, x in enumerate((-0.95, 0.95)):
    box(f"PROP_Vip_Fireplace_{i + 1:02d}", (0.36, 0.34, 1.2), (x, fy - 0.17, 0.6), M["marble"], bevel=0.02, segments=3)
box("PROP_Vip_Fireplace_03", (2.2, 0.3, 0.28), (0, fy - 0.15, 1.06), M["marble"], bevel=0.02, segments=3)
box("PROP_Vip_Fireplace_04", (2.7, 0.46, 0.09), (0, fy - 0.23, 1.25), M["marble"], bevel=0.02, segments=3)
box("PROP_Vip_Fireplace_05", (2.9, 0.85, 0.06), (0, fy - 0.42, 0.03), M["nero"], bevel=0.01)
box("PROP_Vip_Firebox_01", (1.56, 0.04, 0.92), (0, fy - 0.02, 0.46), M["soot"])
for i, x in enumerate((-0.76, 0.76)):
    box(f"PROP_Vip_Firebox_{i + 2:02d}", (0.04, 0.34, 0.92), (x, fy - 0.17, 0.46), M["soot"])
box("PROP_Vip_Firebox_04", (1.56, 0.34, 0.04), (0, fy - 0.17, 0.9), M["soot"])
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
for v in bm.verts:
    v.co = Vector((v.co.x * 2.3, 0, (v.co.y + 0.5) * 1.3))
bm.faces.ensure_lookup_table()
uv = bm.loops.layers.uv.verify()
for loop in bm.faces[0].loops:
    loop[uv].uv = (loop.vert.co.x / 1.15 + 0.5, loop.vert.co.z / 0.65)
fire = new_object("PROP_Vip_Fire_01", bm, M["fire"], V, (0, fy - 0.12, 0.08), offset_uv=False)
linked("PROP_Vip_Fire_02", fire, V, (0.05, fy - 0.2, 0.06), rot=(0, 0, math.radians(8)), scale=(0.8, 1, 0.85))
log = cyl("PROP_Vip_Log_01", 0.06, 0.06, 1.0, (0, fy - 0.22, 0.1), M["walnut_dark"], rot=(0, math.pi / 2, 0.1))
linked("PROP_Vip_Log_02", log, V, (0.05, fy - 0.15, 0.2), rot=(0, math.pi / 2, -0.2))
collider("Fireplace", (-1.45, fy - 0.85, 0), (1.45, fy, 1.3))
# mirror over the mantel
box("PROP_Vip_Mirror_01", (1.5, 0.02, 1.35), (0, fy - 0.03, 2.35), M["mirror"])
for i, (sx, sz, x, z) in enumerate([(1.75, 0.12, 0, 3.08), (1.75, 0.12, 0, 1.62), (0.12, 1.35, -0.81, 2.35), (0.12, 1.35, 0.81, 2.35)]):
    box(f"PROP_Vip_MirrorFrame_{i + 1:02d}", (sx, 0.08, sz), (x, fy - 0.05, z), M["gilt"], bevel=0.02, segments=3)
# candlesticks on the mantel
stick = cyl("PROP_Vip_Candlestick_01", 0.05, 0.02, 0.3, (-1.05, fy - 0.25, 1.45), M["brass"], bevel=0.005)
linked("PROP_Vip_Candlestick_02", stick, V, (1.05, fy - 0.25, 1.45))
flame = cyl("PROP_Vip_CandleFlame_01", 0.012, 0.004, 0.05, (-1.05, fy - 0.25, 1.64), M["candle"], segments=8)
linked("PROP_Vip_CandleFlame_02", flame, V, (1.05, fy - 0.25, 1.64))
# sconces flanking the mirror
plate = box("PROP_Vip_Sconce_01", (0.14, 0.04, 0.34), (-1.65, fy - 0.16, 2.5), M["gilt"], bevel=0.02, segments=3)
linked("PROP_Vip_Sconce_02", plate, V, (1.65, fy - 0.16, 2.5))
shade = cyl("PROP_Vip_SconceShade_01", 0.1, 0.05, 0.13, (-1.65, fy - 0.3, 2.72), M["shade"])
linked("PROP_Vip_SconceShade_02", shade, V, (1.65, fy - 0.3, 2.72))

# ------------------------------------------------------------------ window with sea view (right wall)
wx = W / 2
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
for v in bm.verts:
    v.co = Vector((0, v.co.x * 2.4, (v.co.y + 0.5) * 2.8))
bm.faces.ensure_lookup_table()
uv = bm.loops.layers.uv.verify()
for loop in bm.faces[0].loops:
    loop[uv].uv = (0.5 - loop.vert.co.y / 2.4, loop.vert.co.z / 2.8)
new_object("PROP_Vip_WindowView_01", bm, M["sea"], V, (wx - 0.02, D / 2, 1.15), offset_uv=False)
for i, (sy, sz, y, z) in enumerate([(2.6, 0.12, D / 2, 4.02), (2.6, 0.12, D / 2, 1.1), (0.12, 2.9, D / 2 - 1.26, 2.55), (0.12, 2.9, D / 2 + 1.26, 2.55)]):
    box(f"PROP_Vip_WindowFrame_{i + 1:02d}", (0.12, sy, sz), (wx - 0.06, y, z), M["gilt"], bevel=0.015)
for i, z in enumerate((1.85, 2.55, 3.25)):
    box(f"PROP_Vip_Glazing_{i + 1:02d}", (0.04, 2.4, 0.035), (wx - 0.05, D / 2, z), M["walnut"])
box("PROP_Vip_Glazing_04", (0.04, 0.05, 2.8), (wx - 0.05, D / 2, 2.55), M["walnut"])
box("PROP_Vip_WindowSill_01", (0.3, 2.9, 0.07), (wx - 0.15, D / 2, 1.07), M["nero"], bevel=0.01)
pleat = cyl("PROP_Vip_Drape_01", 0.08, 0.08, 4.2, (wx - 0.2, 3.35, 2.1), M["velvet"], segments=12, subsurf=1)
k = 1
for side_y in (3.35, 6.25):
    for j in range(5):
        if k > 1:
            linked(f"PROP_Vip_Drape_{k:02d}", pleat, V, (wx - 0.2 - (j % 2) * 0.03, side_y + j * 0.1, 2.1))
        k += 1
box("PROP_Vip_Pelmet_01", (0.16, 3.6, 0.38), (wx - 0.24, D / 2, 4.05), M["velvet"], bevel=0.03)

# ------------------------------------------------------------------ bookcase (left wall)
bx = -W / 2
carc = [("Side", (0.42, 0.05, 3.2), (bx + 0.21, 3.4, 1.6)), ("Side", (0.42, 0.05, 3.2), (bx + 0.21, 6.6, 1.6)),
        ("Top", (0.46, 3.3, 0.08), (bx + 0.23, 5.0, 3.24)), ("Base", (0.44, 3.25, 0.14), (bx + 0.22, 5.0, 0.07)),
        ("Back", (0.03, 3.2, 3.2), (bx + 0.015, 5.0, 1.6))]
for i, (_, size, loc) in enumerate(carc):
    box(f"PROP_Vip_Bookcase_{i + 1:02d}", size, loc, M["walnut"] if i < 4 else M["walnut_dark"], bevel=0.008)
book_meshes = [
    box("PROP_Vip_Book_01", (0.22, 0.045, 0.27), (bx + 0.2, 3.5, 0.3), M["leather"], bevel=0.004),
    box("PROP_Vip_Book_02", (0.22, 0.05, 0.3), (bx + 0.2, 3.55, 0.3), M["damask_green"], bevel=0.004),
    box("PROP_Vip_Book_03", (0.22, 0.04, 0.25), (bx + 0.2, 3.6, 0.3), M["walnut_dark"], bevel=0.004),
    box("PROP_Vip_Book_04", (0.22, 0.055, 0.29), (bx + 0.2, 3.65, 0.3), M["velvet"], bevel=0.004),
]
BOOK_WIDTHS = [0.045, 0.05, 0.04, 0.055]
for b in book_meshes:  # prototypes live in _WIP (never exported); linked copies fill the shelves
    V.objects.unlink(b)
    wip.objects.link(b)
n = 5
for s, z in enumerate((0.14, 0.78, 1.42, 2.06, 2.7)):
    if s:
        box(f"PROP_Vip_Shelf_{s:02d}", (0.4, 3.1, 0.03), (bx + 0.21, 5.0, z), M["walnut"], bevel=0.004)
    y = 3.48
    while y < 6.5:
        pick = int(RNG.integers(0, 4))
        src, width = book_meshes[pick], BOOK_WIDTHS[pick]
        lean = 0.0 if RNG.random() > 0.08 else 0.18
        linked(f"PROP_Vip_Book_{n:02d}" if n < 100 else f"PROP_Vip_Book_{n // 100:02d}_{n % 100:02d}", src, V,
               (bx + 0.2, y, z + 0.16), rot=(lean, 0, 0))
        n += 1
        y += width + 0.004 + (0.05 if RNG.random() < 0.04 else 0)

collider("Bookcase", (bx, 3.35, 0), (bx + 0.46, 6.65, 3.3))

# ------------------------------------------------------------------ seating around the hearth
rug = box("PROP_Vip_Rug_01", (4.6, 3.8, 0.014), (0, 6.2, 0.007), M["carpet"], bevel=0.004)


def sofa(idx, loc, rot_z):
    root = empty(f"PROP_Vip_Sofa_{idx:02d}", loc, V, rot=(0, 0, rot_z))
    parts = []
    if idx == 1:
        parts = [
            box("PROP_Vip_Sofa_01_01", (2.2, 0.9, 0.36), (0, 0, 0.24), M["leather"], bevel=0.05, segments=3),
            box("PROP_Vip_Sofa_01_02", (2.2, 0.26, 0.5), (0, -0.33, 0.65), M["leather"], bevel=0.08, subsurf=2),
            box("PROP_Vip_Sofa_01_03", (1.0, 0.66, 0.16), (-0.52, 0.08, 0.48), M["leather"], bevel=0.05, subsurf=2),
            box("PROP_Vip_Sofa_01_04", (1.0, 0.66, 0.16), (0.52, 0.08, 0.48), M["leather"], bevel=0.05, subsurf=2),
            cyl("PROP_Vip_Sofa_01_05", 0.14, 0.14, 0.9, (-1.08, 0, 0.62), M["leather"], rot=(math.pi / 2, 0, 0), subsurf=1),
            cyl("PROP_Vip_Sofa_01_06", 0.14, 0.14, 0.9, (1.08, 0, 0.62), M["leather"], rot=(math.pi / 2, 0, 0), subsurf=1),
        ]
        for i, (x, y) in enumerate([(-1, -0.38), (1, -0.38), (-1, 0.38), (1, 0.38)]):
            parts.append(cyl(f"PROP_Vip_Sofa_01_{7 + i:02d}", 0.035, 0.025, 0.08, (x, y, 0.04), M["walnut_dark"]))
        sofa.parts = parts
    else:
        for i, p in enumerate(sofa.parts):
            parts.append(linked(f"PROP_Vip_Sofa_{idx:02d}_{i + 1:02d}", p, V, p.location.copy(), rot=p.rotation_euler.copy()))
    for p in parts:
        p.parent = root
    return root


sofa(1, (-1.85, 6.2, 0), -math.pi / 2)
sofa(2, (1.85, 6.2, 0), math.pi / 2)
collider("Sofa_01", (-2.35, 5.05, 0), (-1.4, 7.35, 0.9))
collider("Sofa_02", (1.4, 5.05, 0), (2.35, 7.35, 0.9))


def armchair(idx, loc, rot_z):
    root = empty(f"PROP_Vip_Armchair_{idx:02d}", loc, V, rot=(0, 0, rot_z))
    if idx == 1:
        armchair.parts = [
            box("PROP_Vip_Armchair_01_01", (0.9, 0.85, 0.38), (0, 0, 0.25), M["leather"], bevel=0.05, segments=3),
            box("PROP_Vip_Armchair_01_02", (0.9, 0.24, 0.62), (0, -0.33, 0.7), M["leather"], bevel=0.08, subsurf=2),
            box("PROP_Vip_Armchair_01_03", (0.62, 0.62, 0.16), (0, 0.06, 0.5), M["leather"], bevel=0.05, subsurf=2),
            cyl("PROP_Vip_Armchair_01_04", 0.12, 0.12, 0.85, (-0.42, 0, 0.6), M["leather"], rot=(math.pi / 2, 0, 0), subsurf=1),
            cyl("PROP_Vip_Armchair_01_05", 0.12, 0.12, 0.85, (0.42, 0, 0.6), M["leather"], rot=(math.pi / 2, 0, 0), subsurf=1),
        ]
        parts = armchair.parts
    else:
        parts = [linked(f"PROP_Vip_Armchair_{idx:02d}_{i + 1:02d}", p, V, p.location.copy(), rot=p.rotation_euler.copy()) for i, p in enumerate(armchair.parts)]
    for p in parts:
        p.parent = root


armchair(1, (-0.75, 4.2, 0), 0)
armchair(2, (0.75, 4.2, 0), 0)
collider("Armchairs", (-1.25, 3.72, 0), (1.25, 4.65, 1.0))

# coffee table
box("TABLE_Vip_Coffee_01", (1.3, 0.72, 0.05), (0, 6.2, 0.44), M["nero"], bevel=0.012, segments=3)
box("TABLE_Vip_Coffee_02", (1.2, 0.62, 0.08), (0, 6.2, 0.38), M["walnut"], bevel=0.01)
leg = cyl("TABLE_Vip_CoffeeLeg_01", 0.03, 0.022, 0.34, (-0.52, 5.95, 0.17), M["walnut"])
for i, (x, y) in enumerate([(0.52, 5.95), (-0.52, 6.45), (0.52, 6.45)]):
    linked(f"TABLE_Vip_CoffeeLeg_{i + 2:02d}", leg, V, (x, y, 0.17))
collider("CoffeeTable", (-0.68, 5.82, 0), (0.68, 6.58, 0.48))

# side tables with lamps at the sofa ends
for i, (x, y) in enumerate([(-1.9, 7.75), (1.9, 7.75)]):
    top = cyl(f"TABLE_Vip_Side_{i + 1:02d}", 0.28, 0.28, 0.04, (x, y, 0.6), M["marble"], segments=32, bevel=0.01)
    cyl(f"TABLE_Vip_SidePedestal_{i + 1:02d}", 0.05, 0.16, 0.58, (x, y, 0.29), M["walnut"])
    cyl(f"PROP_Vip_LampBase_{i + 1:02d}", 0.08, 0.03, 0.4, (x, y, 0.82), M["brass"], bevel=0.005)
    cyl(f"PROP_Vip_LampShade_{i + 1:02d}", 0.22, 0.12, 0.26, (x, y, 1.12), M["shade"], segments=32)
    point_light(f"LIGHT_Vip_Lamp_{i + 1:02d}", (x, y, 1.05), 7, rng=6)
    collider(f"SideTable_{i + 1:02d}", (x - 0.3, y - 0.3, 0), (x + 0.3, y + 0.3, 0.65))

# ------------------------------------------------------------------ paintings flanking the door
for i, (x, mat) in enumerate(((-3.25, M["paint_a"]), (3.25, M["paint_b"]))):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co = Vector((v.co.x * 1.1, 0, v.co.y * 2.1))
    bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.verify()
    for loop in bm.faces[0].loops:
        loop[uvl].uv = (loop.vert.co.x / 1.1 + 0.5, loop.vert.co.z / 2.1 + 0.5)
    for f in bm.faces:
        f.normal_flip()  # face +Y into the room
    new_object(f"PROP_Vip_Painting_{i + 1:02d}", bm, mat, V, (x, 0.09, 2.55), offset_uv=False)
    for j, (sx, sz, dx, dz) in enumerate([(1.4, 0.15, 0, 1.12), (1.4, 0.15, 0, -1.12), (0.15, 2.1, 0.62, 0), (0.15, 2.1, -0.62, 0)]):
        box(f"PROP_Vip_PaintingFrame_{i + 1:02d}_{j + 1:02d}", (sx, 0.1, sz), (x + dx, 0.08, 2.55 + dz), M["gilt"], bevel=0.02, segments=3)

# ------------------------------------------------------------------ chandelier
cz = H - 1.35
cyl("PROP_Vip_ChandelierStem_01", 0.02, 0.02, 1.1, (0, 5.6, H - 0.55), M["brass"], segments=10)
torus("PROP_Vip_ChandelierRing_01", 0.62, 0.02, (0, 5.6, cz), M["gilt"])
torus("PROP_Vip_ChandelierRing_02", 0.36, 0.015, (0, 5.6, cz + 0.32), M["gilt"])
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=4, radius1=0.0, radius2=0.02, depth=0.03)
bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=4, radius1=0.02, radius2=0.0, depth=0.05,
                      matrix=Matrix.Translation((0, 0, -0.04)))
crystal = new_object("PROP_Vip_Crystal_01", bm, M["crystal"], V, (0, 5.6, cz - 0.9), offset_uv=True)
candle = cyl("PROP_Vip_ChandelierCandle_01", 0.013, 0.013, 0.12, (0.62, 5.6, cz + 0.06), M["shade"], segments=10)
cflame = cyl("PROP_Vip_ChandelierFlame_01", 0.014, 0.004, 0.05, (0.62, 5.6, cz + 0.15), M["candle"], segments=8)
k = 2
for i in range(12):
    a = 2 * math.pi * i / 12
    x, y = 0.62 * math.cos(a), 5.6 + 0.62 * math.sin(a)
    if i:
        linked(f"PROP_Vip_ChandelierCandle_{i + 1:02d}", candle, V, (x, y, cz + 0.06))
        linked(f"PROP_Vip_ChandelierFlame_{i + 1:02d}", cflame, V, (x, y, cz + 0.15))
    for j in range(4):
        linked(f"PROP_Vip_Crystal_{k // 100:02d}_{k % 100:02d}" if k >= 100 else f"PROP_Vip_Crystal_{k:02d}", crystal, V,
               (x * 0.98, 5.6 + (y - 5.6) * 0.98, cz - 0.06 - j * 0.06))
        k += 1
for ring in range(5):
    rr = 0.45 - ring * 0.08
    for i in range(max(6, 20 - ring * 3)):
        a = 2 * math.pi * i / max(6, 20 - ring * 3) + ring * 0.3
        linked(f"PROP_Vip_Crystal_{k // 100:02d}_{k % 100:02d}" if k >= 100 else f"PROP_Vip_Crystal_{k:02d}", crystal, V,
               (rr * math.cos(a), 5.6 + rr * math.sin(a), cz - 0.15 - ring * 0.1))
        k += 1

# ------------------------------------------------------------------ lights (physical: candela via watts())
point_light("LIGHT_Vip_Chandelier_01", (0, 5.6, cz - 0.2), 40, rng=16)
spot_light("LIGHT_Vip_Chandelier_02", (0, 5.6, cz - 0.4), 75, math.radians(115), 0.9, rng=14, shadow=True)
point_light("LIGHT_Vip_Fire_01", (0, D - 0.55, 0.45), 22, color=(1.0, 0.5, 0.2), rng=7, flicker=True)
point_light("LIGHT_Vip_Sconce_01", (-1.65, D - 0.4, 2.7), 4, rng=5)
point_light("LIGHT_Vip_Sconce_02", (1.65, D - 0.4, 2.7), 4, rng=5)
spot_light("LIGHT_Vip_Moon_01", (W / 2 + 2.5, D / 2, 4.5), 18, math.radians(70), 1.0, color=(0.55, 0.63, 0.85), rng=20)
bpy.data.objects["LIGHT_Vip_Moon_01"].rotation_euler = (0, math.radians(-60), 0)

# ------------------------------------------------------------------ logic: spawn, probe, bounds
empty("SPAWN_Vip_Main", (0, 1.6, 0), COLL["LOGIC"], kind="SINGLE_ARROW", rot=(-math.pi / 2, 0, 0))  # arrow points +Y = facing
empty("PROBE_Vip_Main", (0, 5.0, 1.7), COLL["PROBES"], kind="SPHERE")
fire_snd = empty("AUDIO_Vip_Fire_01", (0, D - 0.4, 0.5), COLL["LOGIC"], kind="SPHERE")
fire_snd["sound"] = "fireCrackle"   # → glTF extras → runtime SoundEmitterDef (src/audio)
fire_snd["gain"] = 0.9
fire_snd["mode"] = "loop"
trig = new_object("TRIGGER_Vip_Bounds", cube_bm(W, D - 0.05, H + 1), None, COLL["LOGIC"], (0, D / 2 + 0.025, H / 2 - 0.5), offset_uv=False)
trig.display_type = "WIRE"
trig.hide_render = True

# a note that must never ship
note = bpy.data.objects.new("NOTE_Scale_Reference", None)
wip.objects.link(note)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
bpy.ops.file.make_paths_relative()  # portable: textures resolve relative to the .blend
bpy.ops.wm.save_mainfile()
print(f"[author] wrote {OUT}: {len(bpy.data.objects)} objects, {len(bpy.data.materials)} materials")
