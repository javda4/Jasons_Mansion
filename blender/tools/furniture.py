"""Authored period furniture for the mansion's rooms (Layer 1): pieces Poly Haven has no CC0 scan of.

    import furniture as F
    F.fireplace(A, (x, y), rz, width=2.1)   # Louis XV marble mantel, trumeau mirror, garniture, a lit log fire (FX_)
    F.grand_piano(A, (x, y), rz)            # concert grand, lid raised, keyboard and lyre; bench
    F.bureau_plat(A, (x, y), rz)            # writing table with a leather top, inkstand, lamp and a bergère
    F.vitrine(A, (x, y), rz)                # glazed display cabinet filled with porcelain
    F.gueridon(A, (x, y), z0=0.0)           # round pedestal table; returns its top height

Placement: (x, y) is the piece's centre (or, for wall pieces, the wall-surface point it stands against) and rz
turns local +Y (the front: towards the room or the player) into the world. Colliders are the rotated footprint's
axis-aligned box. The fire's materials end in _LogBark / _LogEnd / _Ashes, which src/fx/fire.ts recognises.
"""
import math
import os
import shutil
import urllib.request

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import kit

PH = "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/{id}/{id}_{map}_1k.jpg"
TEX = os.path.join(kit.ROOT, "blender", "textures_src", "hearth")


def frame(x, y, rz):
    """Local → world for a piece at (x, y) turned by rz: T(lx, ly, z)."""
    c, s = math.cos(rz), math.sin(rz)
    return lambda lx, ly, z=0.0: Vector((x + lx * c - ly * s, y + lx * s + ly * c, z))


def collide(K, tag, T, lo, hi, z0, z1):
    pts = [T(a, b) for a in (lo[0], hi[0]) for b in (lo[1], hi[1])]
    K.collider(f"{tag}_{K.idx('f' + tag)}", (min(p.x for p in pts), min(p.y for p in pts), z0), (max(p.x for p in pts), max(p.y for p in pts), z1))


def mats(A):
    K, M = A.K, A.M
    if "mirror" not in M:
        K.material("mirror", f"MAT_{K.zone}_Mirror", (0.82, 0.83, 0.8), 0.04, metal=1.0)
        K.material("piano", f"MAT_{K.zone}_PianoLacquer", (0.012, 0.011, 0.01), 0.3, coat=0.2, coat_rough=0.12)
        K.material("ivory", f"MAT_{K.zone}_KeyIvory", (0.86, 0.81, 0.7), 0.35)
        K.material("ebony", f"MAT_{K.zone}_KeyEbony", (0.02, 0.018, 0.016), 0.4)
        K.material("glass", f"MAT_{K.zone}_Glass", (0.9, 0.92, 0.9), 0.03, alpha=0.12)
        K.material("deskleather", f"MAT_{K.zone}_DeskLeather", (0.07, 0.14, 0.08), 0.6)
        K.material("soot", f"MAT_{K.zone}_Firebrick", (0.018, 0.015, 0.013), 0.97)
        K.material("iron", f"MAT_{K.zone}_CastIron", (0.02, 0.019, 0.018), 0.8, metal=0.2)
    return M


# ============================================================================ hearth

def _fire_textures():
    """Bark and ash sets (Poly Haven, CC0) for the log fire; reuses the Salon Privé's downloads when present."""
    os.makedirs(TEX, exist_ok=True)
    out = {}
    for pid, name, legacy in (("bark_brown_02", "LogBark", "Vip_LogBark"), ("burned_ground_01", "Ashes", "Vip_Ashes")):
        maps = {}
        for ph, ours in (("diff", "BaseColor"), ("nor_gl", "Normal"), ("arm", "ORM")):
            path = os.path.join(TEX, f"T_Hearth{name}_{ours}.jpg")
            old = os.path.join(kit.ROOT, "blender", "textures_src", "vip", f"T_{legacy}_{ours}.jpg")
            if not os.path.exists(path):
                if os.path.exists(old):
                    shutil.copyfile(old, path)
                else:
                    urllib.request.urlretrieve(PH.format(id=pid, map=ph), path)
            maps[ours] = path
        out[name] = maps
    return out


def _log(K, M, name, length, radius, loc, rz, ry, seed):
    """A split log along local X: irregular tapered bark cylinder, charred end caps (two materials)."""
    rng = np.random.default_rng(seed)
    seg, rings = 18, 7
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    lobes = rng.normal(0, 0.07, seg)
    lobes = (lobes + np.roll(lobes, 1) + np.roll(lobes, -1)) / 3
    grid = []
    for i in range(rings + 1):
        t = i / rings
        row = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            r = radius * (1.0 - 0.12 * t) * (1 + lobes[j] + rng.normal(0, 0.025))
            row.append(bm.verts.new(((t - 0.5) * length, r * math.cos(a), r * math.sin(a) + 0.012 * math.sin(t * math.pi))))
        grid.append(row)
    circ = 2 * math.pi * radius
    for i in range(rings):
        for j in range(seg):
            jn = (j + 1) % seg
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][jn], grid[i][jn]))
            f.smooth = True
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (jj / seg * circ / 0.5, (ii / rings) * length / 0.5)
    for row, flip in ((grid[0], True), (grid[-1], False)):
        f = bm.faces.new(list(reversed(row)) if flip else row)
        f.material_index = 1
        c = sum((v.co for v in row), Vector()) / len(row)
        for loop in f.loops:
            loop[uv].uv = ((loop.vert.co.y - c.y) / 0.3 + 0.5, (loop.vert.co.z - c.z) / 0.3 + 0.5)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M["bark"])
    me.materials.append(M["logend"])
    ob = bpy.data.objects.new(name, me)
    ob.location, ob.rotation_euler = loc, (0, ry, rz)
    K.coll["VISUAL"].objects.link(ob)
    return ob


def fireplace(A, at, rz, width=2.1, marble=None, lit=True, mirror=True, garniture=True, candela=14):
    """A Louis XV mantelpiece against the wall point `at` (rz: 0 = facing +Y): moulded jambs and serpentine frieze
    with a gilt cartouche, a soot-lined firebox, hearth slab and brass fender; a lit fire (logs on a basket grate
    over embers, FX_ flame, flickering light, crackle); a trumeau mirror in a gilt frame; clock and candelabra.
    Needs the props "MantelClock", "Candelabra" and "Vase" imported on A when `garniture`."""
    K = A.K
    M = mats(A)
    stone = marble or M["marble"]
    T = frame(at[0], at[1], rz)
    W, D, H = width, 0.36, 1.18                       # mantel
    OW, OH = width - 0.74, 0.86                       # firebox opening
    rot = (0, 0, rz)
    # hearth slab and the moulded mantel
    K.box(K.name("ROOM", "Hearth"), (W + 0.5, 0.62, 0.05), tuple(T(0, 0.31, 0.025)), M["nero"], rot=rot, bevel=0.01, lightmap=True)
    for s in (-1, 1):
        K.box(K.name("ROOM", "MantelJamb"), (0.34, D, H - 0.3), tuple(T(s * (W / 2 - 0.17), D / 2, (H - 0.3) / 2)), stone, rot=rot, bevel=0.02, segments=3, lightmap=True)
        K.box(K.name("ROOM", "MantelJambFoot"), (0.42, D + 0.06, 0.14), tuple(T(s * (W / 2 - 0.17), (D + 0.06) / 2, 0.07)), stone, rot=rot, bevel=0.015, lightmap=True)
        K.lathe(K.name("PROP", "MantelScroll"), [(0, 0), (0.06, 0.0), (0.075, 0.05), (0.05, 0.12), (0.07, 0.2), (0.03, 0.26), (0, 0.27)],
                tuple(T(s * (W / 2 - 0.17), D + 0.02, H - 0.62)), M["gilt"], segments=16, rot=(math.pi / 2, 0, rz))
    K.box(K.name("ROOM", "MantelFrieze"), (W, D, 0.3), tuple(T(0, D / 2, H - 0.15)), stone, rot=rot, bevel=0.02, segments=3, lightmap=True)
    # serpentine apron under the frieze: a shallow swept arch in marble
    apron = [T(-OW / 2 + (OW * k / 16), D - 0.01, H - 0.3 - 0.07 * math.sin(math.pi * k / 16)) for k in range(17)]
    K.sweep(K.name("ROOM", "MantelApron"), apron, tuple(Vector((-math.sin(rz), math.cos(rz), 0))), [(0, 0), (0, 0.04), (0.03, 0.06), (0.05, 0.03), (0.05, 0)], stone, n1_hint=(0, 0, 1))
    K.lathe(K.name("PROP", "MantelCartouche"), [(0, 0), (0.09, 0.0), (0.12, 0.02), (0.1, 0.04), (0.04, 0.06), (0, 0.06)],
            tuple(T(0, D + 0.005, H - 0.16)), M["gilt"], segments=24, rot=(-math.pi / 2, 0, rz))
    K.box(K.name("ROOM", "MantelShelf"), (W + 0.2, D + 0.12, 0.07), tuple(T(0, (D + 0.12) / 2, H + 0.035)), stone, rot=rot, bevel=0.02, segments=3, lightmap=True)
    K.box(K.name("ROOM", "MantelShelfLip"), (W + 0.12, D + 0.08, 0.04), tuple(T(0, (D + 0.08) / 2, H - 0.02)), stone, rot=rot, bevel=0.012, lightmap=True)
    # soot-lined firebox and the fire bed
    K.box(K.name("PROP", "Firebox"), (OW, 0.04, OH), tuple(T(0, 0.02, OH / 2)), M["soot"], rot=rot)
    for s in (-1, 1):
        K.box(K.name("PROP", "Firebox"), (0.04, D, OH), tuple(T(s * OW / 2, D / 2, OH / 2)), M["soot"], rot=rot)
    K.box(K.name("PROP", "Firebox"), (OW, D, 0.04), tuple(T(0, D / 2, OH)), M["soot"], rot=rot)
    K.tube(K.name("PROP", "Fender"), [T(-OW / 2 - 0.18, 0.55, 0.09), T(-OW / 2 - 0.1, 0.62, 0.09), T(OW / 2 + 0.1, 0.62, 0.09), T(OW / 2 + 0.18, 0.55, 0.09)], 0.022, M["brass"], bezier=False)
    collide(K, "Fireplace", T, (-W / 2 - 0.25, 0), (W / 2 + 0.25, 0.66), 0, H + 0.1)
    if lit:
        tex = _fire_textures()
        if "bark" not in M:
            K.material("bark", f"MAT_{K.zone}_LogBark", rough=0.9, base_tex=tex["LogBark"]["BaseColor"], normal_tex=tex["LogBark"]["Normal"], orm_tex=tex["LogBark"]["ORM"])
            K.material("logend", f"MAT_{K.zone}_LogEnd", (0.035, 0.03, 0.028), 0.95)
            K.material("ashes", f"MAT_{K.zone}_Ashes", rough=0.95, base_tex=tex["Ashes"]["BaseColor"], normal_tex=tex["Ashes"]["Normal"], orm_tex=tex["Ashes"]["ORM"])
        floor, grate = 0.05, 0.15
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=20, y_segments=6, size=0.5)
        uvl = bm.loops.layers.uv.verify()
        rng = np.random.default_rng(abs(int(at[0] * 100 + at[1] * 10)))
        for v in bm.verts:
            x, y = v.co.x * (OW - 0.12), v.co.y * 0.28
            v.co = Vector((x, y, max(0.0, 0.032 * math.exp(-((x / 0.38) ** 2) - ((y / 0.11) ** 2)) + rng.normal(0, 0.003))))
        for f in bm.faces:
            f.smooth = True
            for loop in f.loops:
                loop[uvl].uv = (loop.vert.co.x / 0.6, loop.vert.co.y / 0.6)
        K.obj(K.name("PROP", "Ashes"), bm, M["ashes"], loc=tuple(T(0, 0.18, floor + 0.002)), rot=rot, uv=None)
        for i, ly in enumerate(np.linspace(0.08, 0.3, 5)):
            K.cyl(K.name("PROP", "FireGrate"), 0.011, 0.011, OW - 0.5, tuple(T(0, ly, grate)), M["iron"], segments=10, rot=(0, math.pi / 2, rz))
        for s in (-1, 1):
            K.lathe(K.name("PROP", "Andiron"), [(0, 0), (0.05, 0), (0.05, 0.02), (0.02, 0.04), (0.016, 0.3), (0, 0.3)], tuple(T(s * (OW / 2 - 0.2), 0.38, floor)), M["iron"], segments=16)
            K.lathe(K.name("PROP", "AndironFinial"), [(0, 0), (0.02, 0), (0.03, 0.02), (0.038, 0.05), (0.03, 0.08), (0.012, 0.1), (0.018, 0.115), (0, 0.13)],
                    tuple(T(s * (OW / 2 - 0.2), 0.38, floor + 0.3)), M["brass"], segments=20)
        for k, (ln, r, lx, ly, lz, a, ry) in enumerate(((0.72, 0.07, 0.0, 0.12, 0.08, 0.04, 0.0), (0.64, 0.06, 0.03, 0.26, 0.07, -0.07, 0.0), (0.56, 0.052, -0.04, 0.2, 0.2, 0.42, -0.12))):
            _log(K, M, K.name("PROP", "FireLog"), ln, r, tuple(T(lx, ly, grate + lz)), rz + a, ry, seed=k + 1)
        fx = bpy.data.objects.new(K.name("FX", "Fire"), None)
        fx.empty_display_type, fx.empty_display_size = "CONE", 0.2
        fx.location = tuple(T(0, 0.19, grate + 0.05))
        fx["effect"], fx["width"], fx["depth"], fx["height"] = "fire", min(0.62, OW - 0.5), 0.2, 0.5
        K.coll["LOGIC"].objects.link(fx)
        K.light(K.name("LIGHT", "Fire"), "POINT", tuple(T(0, 1.2, 0.55)), candela, color=(1.0, 0.5, 0.2), rng=7, flicker=True)
        A.audio("Fire", tuple(T(0, 0.4, 0.5)), "fireCrackle", gain=0.5, mode="loop")
    if mirror:   # trumeau: a mirror over the mantel, in a gilt frame with a crest
        mh = min(2.0, A.field_top - H - 0.25)
        K.box(K.name("PROP", "TrumeauGlass"), (W - 0.2, 0.02, mh), tuple(T(0, 0.03, H + 0.14 + mh / 2)), M["mirror"], rot=rot)
        n = Vector((-math.sin(rz), math.cos(rz), 0))
        K.frame(K.name("PROP", "TrumeauFrame"), tuple(T(0, 0.04, H + 0.14 + mh / 2)), W - 0.16, mh + 0.04, tuple(n),
                [(-0.02, 0), (-0.02, 0.03), (0.02, 0.07), (0.07, 0.08), (0.12, 0.06), (0.16, 0.03), (0.18, 0)], M["gilt"], flip=True)
        K.lathe(K.name("PROP", "TrumeauCrest"), [(0, 0), (0.22, 0), (0.2, 0.06), (0.12, 0.14), (0.05, 0.2), (0, 0.22)], tuple(T(0, 0.05, H + 0.14 + mh + 0.06)), M["gilt"],
                segments=24, rot=(-math.pi / 2, 0, rz))
    if garniture:
        top = H + 0.07
        A.place("MantelClock", tuple(T(0, 0.2, top)), rz)
        for s in (-1, 1):
            A.place("Candelabra", tuple(T(s * (W / 2 - 0.25), 0.2, top)), rz)
            A.place("Vase", tuple(T(s * (W / 2 - 0.62), 0.18, top)), rz, scale=0.7)
            K.light(K.name("LIGHT", "Candelabra"), "POINT", tuple(T(s * (W / 2 - 0.25), 0.25, top + 0.9)), 3, rng=5, bake_only=True)


# ============================================================================ grand piano

def _outline():
    """Plan outline of a concert grand (x across the keyboard, y towards the tail), counter-clockwise."""
    pts = [(0.0, 0.0), (1.52, 0.0), (1.52, 0.52)]
    bent = [(1.52, 0.52), (1.38, 0.95), (1.08, 1.4), (0.8, 1.85), (0.55, 2.12), (0.3, 2.22), (0.1, 2.18), (0.0, 2.06)]
    for (x0, y0), (x1, y1) in zip(bent, bent[1:]):        # a smooth bentside: subdivide and relax
        for k in range(1, 4):
            t = k / 4
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        pts.append((x1, y1))
    return pts


def _prism(K, name, poly, z0, z1, mat, loc, rz, **kw):
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for k in range(len(poly)):
        bm.faces.new((bot[k], bot[(k + 1) % len(poly)], top[(k + 1) % len(poly)], top[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return K.obj(name, bm, mat, loc=loc, rot=(0, 0, rz), **kw)


def grand_piano(A, at, rz, lid=38):
    """A black-lacquered grand: case, raised lid on its stick, keyboard (52 ivory, 36 ebony keys), music desk, three
    turned legs on brass castors, lyre with pedals; a tufted bench. `at` is the keyboard's centre front;
    local +Y runs to the tail (the pianist faces +Y)."""
    K = A.K
    M = mats(A)
    T = frame(at[0], at[1], rz)
    poly = [(x - 0.76, y) for x, y in _outline()]
    origin = tuple(T(0, 0, 0))
    _prism(K, K.name("PROP", "PianoCase"), poly, 0.64, 0.98, M["piano"], origin, rz, smooth_angle=30)
    _prism(K, K.name("PROP", "PianoSoundboard"), [(x * 0.97, y * 0.98 + 0.02) for x, y in poly], 0.9, 0.975, M["walnut"], origin, rz)
    # the lid, hinged along the spine (local x = -0.76) and raised
    lid_ob = _prism(K, K.name("PROP", "PianoLid"), [(x + 0.76, y) for x, y in poly], 0.0, 0.025, M["piano"], tuple(T(-0.76, 0, 0.985)), rz)
    lid_ob.rotation_euler = (0, -math.radians(lid), rz)          # XYZ: hinge about the spine, then turn with the room
    K.cyl(K.name("PROP", "PianoLidStick"), 0.011, 0.011, 0.72, tuple(T(0.55, 1.05, 1.32)), M["piano"], segments=8, rot=(0, math.radians(-18), rz))
    # keyboard: keybed, keys, cheeks, fallboard, music desk
    K.box(K.name("PROP", "PianoKeybed"), (1.52, 0.32, 0.1), tuple(T(0, -0.14, 0.66)), M["piano"], rot=(0, 0, rz), bevel=0.008)
    for s in (-1, 1):
        K.box(K.name("PROP", "PianoCheek"), (0.06, 0.32, 0.14), tuple(T(s * 0.73, -0.14, 0.75)), M["piano"], rot=(0, 0, rz), bevel=0.01)
    key = A._props.get("_pianoWhite")
    if key is None:
        key = A._props["_pianoWhite"] = K.prototype(K.box(K.name("PROP", "PianoKeyWhite"), (0.0225, 0.15, 0.022), (0, 0, -30), M["ivory"], bevel=0.002))
        A._props["_pianoBlack"] = K.prototype(K.box(K.name("PROP", "PianoKeyBlack"), (0.012, 0.095, 0.03), (0, 0, -30), M["ebony"], bevel=0.002))
    x0 = -52 * 0.0235 / 2
    for k in range(52):
        K.linked(K.name("PROP", "PianoKeyWhite"), key, tuple(T(x0 + (k + 0.5) * 0.0235, -0.2, 0.722)), rot=(0, 0, rz))
        if k % 7 not in (2, 6) and k < 51:      # no black key after E and B
            K.linked(K.name("PROP", "PianoKeyBlack"), A._props["_pianoBlack"], tuple(T(x0 + (k + 1) * 0.0235, -0.17, 0.745)), rot=(0, 0, rz))
    K.box(K.name("PROP", "PianoFallboard"), (1.4, 0.08, 0.06), tuple(T(0, -0.04, 0.79)), M["piano"], rot=(0, 0, rz), bevel=0.01)
    desk = K.box(K.name("PROP", "PianoDesk"), (0.9, 0.015, 0.3), tuple(T(0, 0.12, 1.12)), M["piano"], bevel=0.004)
    desk.rotation_euler = (math.radians(-14), 0, rz)
    # legs, castors, lyre and pedals
    leg = [(0, 0), (0.06, 0), (0.07, 0.06), (0.05, 0.12), (0.06, 0.3), (0.075, 0.46), (0.06, 0.55), (0.08, 0.6), (0.085, 0.64), (0, 0.64)]
    for lx, ly in ((-0.66, 0.08), (0.66, 0.08), (-0.25, 1.95)):
        K.lathe(K.name("PROP", "PianoLeg"), leg, tuple(T(lx, ly, 0.0)), M["piano"], segments=16)
        K.cyl(K.name("PROP", "PianoCastor"), 0.035, 0.035, 0.03, tuple(T(lx, ly, 0.015)), M["brass"], segments=12, rot=(0, math.pi / 2, rz))
    for s in (-1, 1):
        K.box(K.name("PROP", "PianoLyre"), (0.03, 0.05, 0.5), tuple(T(s * 0.09, 0.12, 0.38)), M["piano"], rot=(0, 0, rz), bevel=0.008)
    K.box(K.name("PROP", "PianoLyre"), (0.3, 0.12, 0.05), tuple(T(0, 0.12, 0.1)), M["piano"], rot=(0, 0, rz), bevel=0.01)
    for s in (-1, 1):
        K.box(K.name("PROP", "PianoPedal"), (0.03, 0.12, 0.012), tuple(T(s * 0.04, 0.04, 0.09)), M["brass"], rot=(0, 0, rz), bevel=0.004)
    collide(K, "Piano", T, (-0.78, -0.32), (0.78, 2.24), 0, 1.0)
    # bench: a tufted velvet seat on cabriole-ish legs
    K.box(K.name("PROP", "PianoBench"), (0.8, 0.36, 0.09), tuple(T(0, -0.72, 0.48)), M["velvet"], rot=(0, 0, rz), bevel=0.03, segments=3)
    K.box(K.name("PROP", "PianoBenchApron"), (0.82, 0.38, 0.06), tuple(T(0, -0.72, 0.41)), M["piano"], rot=(0, 0, rz), bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.lathe(K.name("PROP", "PianoBenchLeg"), [(0, 0), (0.018, 0), (0.024, 0.08), (0.02, 0.3), (0.028, 0.38), (0, 0.38)], tuple(T(sx * 0.36, -0.72 + sy * 0.15, 0)), M["piano"], segments=10)
    collide(K, "PianoBench", T, (-0.42, -0.92), (0.42, -0.52), 0, 0.55)


# ============================================================================ writing table, vitrine, guéridon

def bureau_plat(A, at, rz, chair=True, lamp=True):
    """Louis XV bureau plat: walnut with gilt mounts and a green leather top; an inkstand, books and a lamp;
    a velvet bergère drawn up behind it (the chair faces local +Y, the writer's side is local -Y)."""
    K = A.K
    M = mats(A)
    T = frame(at[0], at[1], rz)
    rot = (0, 0, rz)
    K.box(K.name("TABLE", "BureauTop"), (1.6, 0.8, 0.04), tuple(T(0, 0, 0.76)), M["walnut"], rot=rot, bevel=0.012)
    K.box(K.name("TABLE", "BureauLeather"), (1.42, 0.62, 0.004), tuple(T(0, 0, 0.782)), M["deskleather"], rot=rot)
    K.box(K.name("TABLE", "BureauApron"), (1.5, 0.7, 0.12), tuple(T(0, 0, 0.68)), M["walnut"], rot=rot, bevel=0.01)
    for s in (-1, 1):
        K.box(K.name("TABLE", "BureauDrawerFront"), (0.42, 0.01, 0.08), tuple(T(s * 0.42, -0.355, 0.68)), M["walnut_dark"], rot=rot, bevel=0.004)
        K.lathe(K.name("PROP", "BureauHandle"), [(0, 0), (0.012, 0), (0.016, 0.01), (0, 0.02)], tuple(T(s * 0.42, -0.365, 0.68)), M["gilt"], segments=10, rot=(math.pi / 2, 0, rz))
    leg = [(0, 0), (0.022, 0), (0.03, 0.04), (0.024, 0.2), (0.034, 0.44), (0.05, 0.6), (0.045, 0.62), (0, 0.62)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.lathe(K.name("TABLE", "BureauLeg"), leg, tuple(T(sx * 0.72, sy * 0.33, 0)), M["walnut"], segments=12)
            K.lathe(K.name("PROP", "BureauSabot"), [(0, 0), (0.026, 0), (0.026, 0.04), (0, 0.04)], tuple(T(sx * 0.72, sy * 0.33, 0)), M["gilt"], segments=10)
    # inkstand, a stack of bound volumes, a quill
    K.box(K.name("PROP", "Inkstand"), (0.3, 0.16, 0.025), tuple(T(0.25, 0.18, 0.795)), M["gilt"], rot=rot, bevel=0.005)
    for s in (-1, 1):
        K.lathe(K.name("PROP", "InkWell"), [(0, 0), (0.03, 0), (0.035, 0.03), (0.02, 0.05), (0.024, 0.055), (0, 0.06)], tuple(T(0.25 + s * 0.08, 0.18, 0.808)), M["crystal"], segments=12)
    for k, (w, h, th) in enumerate(((0.24, 0.035, 0.05), (0.22, 0.03, 0.12), (0.26, 0.04, -0.06))):
        K.box(K.name("PROP", "Book"), (w, 0.17, h), tuple(T(-0.45, 0.12, 0.784 + h / 2 + k * 0.038)), M["leather"] if k != 1 else M["damask"], rot=(0, 0, rz + th), bevel=0.003)
    K.cyl(K.name("PROP", "Quill"), 0.003, 0.001, 0.26, tuple(T(0.18, -0.05, 0.79)), M["shade"], segments=6, rot=(math.radians(82), 0, rz + 0.5))
    if lamp:
        A.table_lamp(*tuple(T(0.62, 0.22))[:2], 0.78, candela=5)
    collide(K, "Bureau", T, (-0.82, -0.42), (0.82, 0.42), 0, 0.85)
    if chair:
        p = T(0, -0.72)
        A.club_chair((p.x, p.y), rz)


def vitrine(A, at, rz, width=1.2, height=1.9, depth=0.42, fill=("Vase", "TeaSet")):
    """Glazed Louis XV vitrine against the wall point `at`: gilt-bronze frame, glass sides and door, three
    shelves dressed with porcelain (the given prototypes, which must be imported on A)."""
    K = A.K
    M = mats(A)
    T = frame(at[0], at[1], rz)
    rot = (0, 0, rz)
    z0 = 0.18
    K.box(K.name("PROP", "VitrineBase"), (width, depth, z0), tuple(T(0, depth / 2, z0 / 2)), M["walnut"], rot=rot, bevel=0.01, lightmap=True)
    K.box(K.name("PROP", "VitrineCrown"), (width + 0.06, depth + 0.04, 0.1), tuple(T(0, depth / 2, z0 + height + 0.05)), M["walnut"], rot=rot, bevel=0.012, lightmap=True)
    K.box(K.name("PROP", "VitrineBack"), (width, 0.02, height), tuple(T(0, 0.01, z0 + height / 2)), M["damask_gold"], rot=rot)
    for sx in (-1, 1):
        for sy in (0.02, depth - 0.02):
            K.box(K.name("PROP", "VitrinePost"), (0.035, 0.035, height), tuple(T(sx * (width / 2 - 0.018), sy, z0 + height / 2)), M["gilt"], rot=rot)
        K.box(K.name("PROP", "VitrineGlass"), (0.006, depth - 0.04, height - 0.04), tuple(T(sx * (width / 2 - 0.01), depth / 2, z0 + height / 2)), M["glass"], rot=rot)
    K.box(K.name("PROP", "VitrineGlass"), (width - 0.04, 0.006, height - 0.04), tuple(T(0, depth - 0.01, z0 + height / 2)), M["glass"], rot=rot)
    K.box(K.name("PROP", "VitrineMullion"), (0.02, 0.012, height), tuple(T(0, depth - 0.006, z0 + height / 2)), M["gilt"], rot=rot)
    shelves = [z0 + height * f for f in (0.03, 0.36, 0.68)]
    for z in shelves:
        K.box(K.name("PROP", "VitrineShelf"), (width - 0.06, depth - 0.06, 0.012), tuple(T(0, depth / 2, z)), M["glass"], rot=rot)
    for k, z in enumerate(shelves):
        what = fill[k % len(fill)]
        if what == "TeaSet":
            A.place(what, tuple(T(0, depth / 2, z + 0.008)), rz, scale=0.85)
        else:
            for s in (-1, 0, 1):
                A.place(what, tuple(T(s * (width / 3.2), depth / 2, z + 0.008)), rz + s * 0.4, scale=0.55)
    collide(K, "Vitrine", T, (-width / 2, 0), (width / 2, depth + 0.02), 0, z0 + height + 0.1)


def gueridon(A, at, z0=0.0, r=0.3, h=0.72, top=None):
    """Round walnut pedestal table with a marble top; returns the top height."""
    K = A.K
    M = A.M
    K.lathe(K.name("TABLE", "Gueridon"), [(0, 0), (0.22, 0), (0.2, 0.03), (0.05, 0.08), (0.035, 0.4), (0.05, h - 0.1), (0.03, h - 0.04), (0, h - 0.04)],
            (at[0], at[1], z0), M["walnut"], segments=28)
    K.cyl(K.name("TABLE", "GueridonTop"), r, r, 0.04, (at[0], at[1], z0 + h - 0.02), top or M["marble"], segments=40, bevel=0.008)
    K.torus(K.name("PROP", "GueridonRim"), r, 0.008, (at[0], at[1], z0 + h - 0.01), M["gilt"], major=40, minor=6)
    K.collider(f"Gueridon_{K.idx('fgue')}", (at[0] - r, at[1] - r, z0), (at[0] + r, at[1] + r, z0 + h + 0.1))
    return z0 + h
