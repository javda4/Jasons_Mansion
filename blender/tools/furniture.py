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


def frame(x, y, rz, z0=0.0):
    """Local → world for a piece at (x, y) turned by rz, standing at height z0 (a dais): T(lx, ly, z)."""
    c, s = math.cos(rz), math.sin(rz)
    return lambda lx, ly, z=0.0: Vector((x + lx * c - ly * s, y + lx * s + ly * c, z0 + z))


def collide(K, tag, T, lo, hi, z0, z1):
    pts = [T(a, b) for a in (lo[0], hi[0]) for b in (lo[1], hi[1])]
    K.collider(f"{tag}_{K.idx('f' + tag)}", (min(p.x for p in pts), min(p.y for p in pts), z0), (max(p.x for p in pts), max(p.y for p in pts), z1))


def mats(A):
    K, M = A.K, A.M
    if "mirror" not in M:
        K.material("mirror", f"MAT_{K.zone}_Mirror", (0.82, 0.83, 0.8), 0.04, metal=1.0)
    if "piano" not in M:
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


def grand_piano(A, at, rz, lid=38, z0=0.0):
    """A black-lacquered grand: case, raised lid on its stick, keyboard (52 ivory, 36 ebony keys), music desk, three
    turned legs on brass castors, lyre with pedals; a tufted bench. `at` is the keyboard's centre front;
    local +Y runs to the tail (the pianist faces +Y)."""
    K = A.K
    M = mats(A)
    T = frame(at[0], at[1], rz, z0)
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
    collide(K, "Piano", T, (-0.78, -0.32), (0.78, 2.24), z0, z0 + 1.0)
    # bench: a tufted velvet seat on cabriole-ish legs
    K.box(K.name("PROP", "PianoBench"), (0.8, 0.36, 0.09), tuple(T(0, -0.72, 0.48)), M["velvet"], rot=(0, 0, rz), bevel=0.03, segments=3)
    K.box(K.name("PROP", "PianoBenchApron"), (0.82, 0.38, 0.06), tuple(T(0, -0.72, 0.41)), M["piano"], rot=(0, 0, rz), bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.lathe(K.name("PROP", "PianoBenchLeg"), [(0, 0), (0.018, 0), (0.024, 0.08), (0.02, 0.3), (0.028, 0.38), (0, 0.38)], tuple(T(sx * 0.36, -0.72 + sy * 0.15, 0)), M["piano"], segments=10)
    collide(K, "PianoBench", T, (-0.42, -0.92), (0.42, -0.52), z0, z0 + 0.55)


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
        # glass inset inside the posts (never coplanar with them: it flickered at a distance)
        K.box(K.name("PROP", "VitrineGlass"), (0.004, depth - 0.1, height - 0.06), tuple(T(sx * (width / 2 - 0.05), depth / 2, z0 + height / 2)), M["glass"], rot=rot)
    K.box(K.name("PROP", "VitrineGlass"), (width - 0.1, 0.004, height - 0.06), tuple(T(0, depth - 0.05, z0 + height / 2)), M["glass"], rot=rot)
    K.box(K.name("PROP", "VitrineMullion"), (0.02, 0.012, height), tuple(T(0, depth - 0.03, z0 + height / 2)), M["gilt"], rot=rot)
    shelves = [z0 + height * f for f in (0.03, 0.36, 0.68)]
    for z in shelves:
        K.box(K.name("PROP", "VitrineShelf"), (width - 0.14, depth - 0.14, 0.012), tuple(T(0, depth / 2, z)), M["glass"], rot=rot)
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


# ============================================================================ library

def book_atlas(path, seed=1905):
    """Spines of leather-bound volumes (32 designs side by side) over a strip of page edges: 1024² PNG.
    Each design: a dyed leather ground with grain, raised bands with gilt fillets, a title label in a gilt frame."""
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    w = h = 1024
    img = np.zeros((h, w, 3))
    leathers = [(0.32, 0.06, 0.05), (0.08, 0.2, 0.1), (0.07, 0.09, 0.2), (0.42, 0.26, 0.13), (0.05, 0.04, 0.035),
                (0.24, 0.05, 0.08), (0.3, 0.17, 0.08), (0.2, 0.22, 0.1), (0.45, 0.36, 0.22), (0.13, 0.06, 0.04)]
    gilt = np.array([0.78, 0.6, 0.3])
    spine_h = 896
    for k in range(32):
        x0, x1 = k * 32, (k + 1) * 32
        base = np.array(leathers[rng.integers(len(leathers))]) * rng.uniform(0.8, 1.15)
        grain = rng.normal(1.0, 0.06, (spine_h, 32, 1)) * (1 - 0.25 * np.abs(np.linspace(-1, 1, 32))[None, :, None] ** 2)
        img[h - spine_h:, x0:x1] = base * grain
        y = lambda f: h - spine_h + int(f * spine_h)  # noqa: E731
        for f in sorted(set([0.04, 0.96] + list(rng.choice([0.16, 0.3, 0.44, 0.58, 0.72, 0.86], rng.integers(2, 5), replace=False)))):
            img[y(f) - 6:y(f) + 6, x0:x1] *= 1.35                                  # raised band
            for d in (-7, 7):
                img[y(f) + d - 1:y(f) + d + 1, x0 + 2:x1 - 2] = gilt                # gilt fillets
        if rng.random() < 0.8:                                                      # title label
            lab = np.array([(0.35, 0.05, 0.04), (0.04, 0.035, 0.03), (0.08, 0.16, 0.09)][rng.integers(3)])
            ly0, ly1 = y(0.18), y(0.27)
            img[ly0:ly1, x0 + 4:x1 - 4] = lab
            img[ly0:ly0 + 2, x0 + 4:x1 - 4] = img[ly1 - 2:ly1, x0 + 4:x1 - 4] = gilt
            for r in range(ly0 + 8, ly1 - 6, 6):                                    # a suggestion of lettering
                img[r:r + 2, x0 + 9:x1 - 9 - rng.integers(0, 6)] = gilt * 0.9
    img[:h - spine_h] = np.array([0.78, 0.72, 0.58]) * rng.normal(1.0, 0.04, (h - spine_h, w, 1))   # page edges
    img = kit.blur(np.clip(img, 0, 1), 1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return kit.save_image(path, np.concatenate([img, np.ones((h, w, 1))], -1))


def _books(bm, uv, rng, p0, t, n, length, z, height, depth, mean_w=0.045):
    """Fill one shelf run (from p0 along t for `length`, front facing n) with books; returns the count."""
    up = Vector((0, 0, 1))
    s, count = 0.01, 0
    while s < length - 0.03:
        bw = float(np.clip(rng.normal(mean_w, 0.014), 0.02, 0.09))
        if s + bw > length - 0.01:
            break
        if rng.random() < 0.04:                       # a gap now and then
            s += rng.uniform(0.05, 0.14)
            continue
        bh = float(np.clip(height * rng.uniform(0.62, 0.95), 0.14, height - 0.02))
        bd = depth * rng.uniform(0.7, 0.95)
        c = p0 + t * (s + bw / 2) + n * (bd / 2 + 0.015)
        lean = rng.normal(0, 0.012) if rng.random() < 0.85 else 0.0
        col = int(rng.integers(32))
        u0, u1 = col / 32 + 0.002, (col + 1) / 32 - 0.002
        corners = {}
        for a in (-1, 1):
            for b in (-1, 1):
                for zz in (0, 1):
                    corners[(a, b, zz)] = bm.verts.new(c + t * (a * bw / 2 + lean * zz * bh) + n * (b * bd / 2) + up * (z + zz * bh))
        V = corners
        faces = (
            ((V[(-1, 1, 0)], V[(1, 1, 0)], V[(1, 1, 1)], V[(-1, 1, 1)]), [(u0, 0.125), (u1, 0.125), (u1, 1.0), (u0, 1.0)]),     # spine
            ((V[(-1, 1, 1)], V[(1, 1, 1)], V[(1, -1, 1)], V[(-1, -1, 1)]), [(u0, 0.0), (u1, 0.0), (u1, 0.12), (u0, 0.12)]),    # top: page edges
            ((V[(-1, -1, 0)], V[(-1, 1, 0)], V[(-1, 1, 1)], V[(-1, -1, 1)]), [(u0, 0.02), (u0 + 0.004, 0.02), (u0 + 0.004, 0.11), (u0, 0.11)]),
            ((V[(1, 1, 0)], V[(1, -1, 0)], V[(1, -1, 1)], V[(1, 1, 1)]), [(u1, 0.02), (u1 - 0.004, 0.02), (u1 - 0.004, 0.11), (u1, 0.11)]),
        )
        for vs, uvs in faces:
            f = bm.faces.new(vs)
            for loop, q in zip(f.loops, uvs):
                loop[uv].uv = q
        s += bw + rng.uniform(0.0, 0.004)
        count += 1
    return count


def bookcase(A, p0, p1, n, z0, z1, shelves, depth=0.38, bay=0.95, seed=0, books_mat=None, cornice=True):
    """A walnut bookcase run along a wall from p0 to p1 (plan points on the wall surface), front facing n: plinth,
    back panel, uprights every `bay`, `shelves` shelves between z0 and z1, a cornice; every shelf filled with books
    (books_mat: the atlas material). Returns the number of books."""
    K, M = A.K, A.M
    p0, p1, n = Vector((*p0, 0)), Vector((*p1, 0)), Vector((*n, 0)).normalized()
    t = (p1 - p0).normalized()
    L = (p1 - p0).length
    rz = math.atan2(t.y, t.x)
    mid = (p0 + p1) / 2
    box = lambda name, size, at, mat, **kw: K.box(K.name("ROOM", name), size, tuple(at), mat, rot=(0, 0, rz), **kw)  # noqa: E731
    box("CaseBack", (L, 0.02, z1 - z0), mid + n * 0.01 + Vector((0, 0, (z0 + z1) / 2)), M["walnut_dark"], lightmap=True)
    box("CasePlinth", (L, depth + 0.02, 0.12), mid + n * (depth / 2 + 0.01) + Vector((0, 0, z0 + 0.06)), M["walnut"], lightmap=True)
    if cornice:
        box("CaseCornice", (L, depth + 0.08, 0.1), mid + n * (depth / 2 + 0.04) + Vector((0, 0, z1 - 0.05)), M["walnut"], bevel=0.01, lightmap=True)
        K.sweep(K.name("ROOM", "CaseCorniceGilt"), [p0 + n * (depth + 0.08) + Vector((0, 0, z1 - 0.1)), p1 + n * (depth + 0.08) + Vector((0, 0, z1 - 0.1))],
                tuple(n), [(0, 0), (0.015, 0.0), (0.02, 0.02), (0, 0.025)], M["gilt"], n1_hint=(0, 0, -1))
    nb = max(1, round(L / bay))
    bw = L / nb
    for i in range(nb + 1):
        at = p0 + t * (i * bw) + n * (depth / 2 + 0.01) + Vector((0, 0, (z0 + z1) / 2))
        box("CaseUpright", (0.04, depth + 0.02, z1 - z0), at, M["walnut"], lightmap=True)
    pitch = (z1 - z0 - 0.12 - (0.1 if cornice else 0)) / shelves
    zs = [z0 + 0.12 + k * pitch for k in range(shelves + 1)]
    for z in zs[1:-1] + [zs[0]]:
        box("CaseShelf", (L, depth, 0.025), mid + n * (depth / 2 + 0.01) + Vector((0, 0, z)), M["walnut"], lightmap=True)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    rng = np.random.default_rng(seed)
    count = 0
    for i in range(nb):
        for k in range(shelves):
            count += _books(bm, uv, rng, p0 + t * (i * bw + 0.025), t, n, bw - 0.05, zs[k] + 0.013, pitch - 0.04, depth - 0.04)
    K.obj(K.name("PROP", "Books"), bm, books_mat, uv=None, lightmap=True)
    lo = [min(p0.x, p1.x, (p0 + n * depth).x, (p1 + n * depth).x), min(p0.y, p1.y, (p0 + n * depth).y, (p1 + n * depth).y)]
    hi = [max(p0.x, p1.x, (p0 + n * depth).x, (p1 + n * depth).x), max(p0.y, p1.y, (p0 + n * depth).y, (p1 + n * depth).y)]
    if z0 < 0.5:
        K.collider(f"Bookcase_{K.idx('fcase')}", (lo[0], lo[1], 0), (hi[0], hi[1], z1))
    return count


def gallery_walk(A, p0, p1, n, z, depth=0.8, posts=0.12):
    """A library gallery: a walnut walkway on brackets in front of the upper cases at height z, with a brass rail."""
    K, M = A.K, A.M
    p0, p1, n = Vector((*p0, 0)), Vector((*p1, 0)), Vector((*n, 0)).normalized()
    t = (p1 - p0).normalized()
    L = (p1 - p0).length
    rz = math.atan2(t.y, t.x)
    mid = (p0 + p1) / 2
    K.box(K.name("ROOM", "GalleryWalk"), (L, depth, 0.08), tuple(mid + n * (depth / 2) + Vector((0, 0, z - 0.04))), M["walnut"], rot=(0, 0, rz), lightmap=True)
    K.box(K.name("ROOM", "GalleryFascia"), (L, 0.04, 0.22), tuple(mid + n * (depth - 0.02) + Vector((0, 0, z - 0.11))), M["walnut"], rot=(0, 0, rz), bevel=0.006, lightmap=True)
    br = A._props.get("_bracket")
    if br is None:
        bm = bmesh.new()
        prof = [(0, 0), (0, -0.5), (0.06, -0.5), (0.12, -0.32), (0.3, -0.12), (depth - 0.06, -0.06), (depth - 0.06, 0)]
        f = bm.faces.new([bm.verts.new((-0.03, b, a)) for b, a in prof])
        bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, verts=[v for v in bm.verts if v not in f.verts], vec=(0.06, 0, 0))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        br = A._props["_bracket"] = K.prototype(K.obj(K.name("PROP", "GalleryBracket"), bm, M["walnut"], loc=(0, 0, -30)))
    nb = max(2, round(L / 1.2))
    for i in range(nb + 1):
        p = p0 + t * (L * i / nb) + Vector((0, 0, z - 0.08))
        K.linked(K.name("PROP", "GalleryBracket"), br, tuple(p), rot=(0, 0, math.atan2(n.y, n.x) - math.pi / 2))
    post = A._props.get("_railpost")
    if post is None:
        post = A._props["_railpost"] = K.prototype(K.cyl(K.name("PROP", "GalleryPost"), 0.009, 0.009, 0.9, (0, 0, -30), M["brass"], segments=8))
    k = max(2, int(L / posts))
    for i in range(k + 1):
        p = p0 + t * (L * i / k) + n * (depth - 0.05) + Vector((0, 0, z + 0.45))
        K.linked(K.name("PROP", "GalleryPost"), post, tuple(p))
    for hz in (0.92, 0.5):
        K.tube(K.name("PROP", "GalleryRail"), [p0 + n * (depth - 0.05) + Vector((0, 0, z + hz)), p1 + n * (depth - 0.05) + Vector((0, 0, z + hz))], 0.02 if hz > 0.9 else 0.01, M["brass"], bezier=False)


def spiral_stair(A, at, z_top, r=0.85, steps=18, turns=1.0, start=0.0):
    """A cast-iron and walnut spiral stair (decorative: the gallery is reached by the staff only); one collider."""
    K, M = A.K, mats(A)
    x, y = at
    K.cyl(K.name("PROP", "SpiralColumn"), 0.06, 0.06, z_top + 0.9, (x, y, (z_top + 0.9) / 2), M["iron"], segments=16)
    tread = A._props.get("_sptread")
    if tread is None:
        bm = bmesh.new()
        a = 2 * math.pi * turns / steps * 1.15
        pts = [(0.06 * math.cos(-a / 2), 0.06 * math.sin(-a / 2))] + [(r * math.cos(-a / 2 + a * k / 6), r * math.sin(-a / 2 + a * k / 6)) for k in range(7)] + [(0.06 * math.cos(a / 2), 0.06 * math.sin(a / 2))]
        f = bm.faces.new([bm.verts.new((px, py, 0)) for px, py in pts])
        bmesh.ops.extrude_face_region(bm, geom=[f])
        top = [v for v in bm.verts if v not in f.verts]
        bmesh.ops.translate(bm, verts=top, vec=(0, 0, 0.045))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        tread = A._props["_sptread"] = K.prototype(K.obj(K.name("PROP", "SpiralTread"), bm, M["walnut"], loc=(0, 0, -30)))
    pts = []
    for i in range(steps):
        a = start + 2 * math.pi * turns * i / steps
        z = z_top * (i + 1) / steps
        K.linked(K.name("PROP", "SpiralTread"), tread, (x, y, z - 0.045), rot=(0, 0, a))
        pts.append(Vector((x + (r - 0.04) * math.cos(a), y + (r - 0.04) * math.sin(a), z + 0.85)))
        K.cyl(K.name("PROP", "SpiralBaluster"), 0.008, 0.008, 0.85, (x + (r - 0.04) * math.cos(a), y + (r - 0.04) * math.sin(a), z + 0.425), M["iron"], segments=6)
    K.tube(K.name("PROP", "SpiralRail"), pts, 0.02, M["brass"])
    K.collider(f"SpiralStair_{K.idx('fsp')}", (x - r, y - r, 0), (x + r, y + r, z_top + 1.0))


def library_ladder(A, p0, p1, n, z_rail, at=0.4):
    """A brass rail along the cases and a walnut ladder hooked onto it, leaning out at the foot."""
    K, M = A.K, A.M
    p0, p1, n = Vector((*p0, 0)), Vector((*p1, 0)), Vector((*n, 0)).normalized()
    t = (p1 - p0).normalized()
    K.tube(K.name("PROP", "LadderRail"), [p0 + n * 0.42 + Vector((0, 0, z_rail)), p1 + n * 0.42 + Vector((0, 0, z_rail))], 0.016, M["brass"], bezier=False)
    base = p0 + t * ((p1 - p0).length * at)
    top, foot = base + n * 0.42 + Vector((0, 0, z_rail)), base + n * 1.25
    for s in (-0.24, 0.24):
        K.tube(K.name("PROP", "LadderStile"), [top + t * s, foot + t * s], 0.022, M["walnut"], bezier=False)
    for k in range(1, int(z_rail / 0.3)):
        f = k / int(z_rail / 0.3)
        p = foot.lerp(top, f)
        K.tube(K.name("PROP", "LadderRung"), [p - t * 0.24, p + t * 0.24], 0.013, M["walnut"], bezier=False)
    lo = Vector((min(foot.x, top.x), min(foot.y, top.y))) - Vector((0.3, 0.3))
    hi = Vector((max(foot.x, top.x), max(foot.y, top.y))) + Vector((0.3, 0.3))
    K.collider(f"Ladder_{K.idx('flad')}", (lo.x, lo.y, 0), (hi.x, hi.y, 1.6))


def globe(A, at, rz=0.0):
    """A library globe: a parchment sphere with gilt meridian and horizon rings on a turned walnut stand."""
    K = A.K
    M = mats(A)
    if "parchment" not in M:
        K.material("parchment", f"MAT_{K.zone}_GlobeParchment", (0.55, 0.45, 0.28), 0.55)
    x, y = at
    K.lathe(K.name("PROP", "GlobeStand"), [(0, 0), (0.3, 0), (0.28, 0.04), (0.06, 0.1), (0.04, 0.3), (0.07, 0.42), (0.04, 0.6), (0, 0.6)], (x, y, 0), M["walnut"], segments=24)
    for k in range(3):
        a = rz + k * 2 * math.pi / 3
        K.tube(K.name("PROP", "GlobeLeg"), [Vector((x, y, 0.55)), Vector((x + 0.28 * math.cos(a), y + 0.28 * math.sin(a), 0.62)), Vector((x + 0.34 * math.cos(a), y + 0.34 * math.sin(a), 0.82))], 0.02, M["walnut"])
    K.torus(K.name("PROP", "GlobeHorizon"), 0.36, 0.018, (x, y, 0.84), M["walnut"], major=48, minor=6)
    K.lathe(K.name("PROP", "GlobeSphere"), [(0, -0.3)] + [(0.3 * math.sin(math.pi * k / 16), -0.3 * math.cos(math.pi * k / 16)) for k in range(1, 16)] + [(0, 0.3)],
            (x, y, 1.0), M["parchment"], segments=32)
    K.torus(K.name("PROP", "GlobeMeridian"), 0.33, 0.01, (x, y, 1.0), M["brass"], major=48, minor=6, rot=(math.pi / 2, 0, rz + 0.4))
    K.collider(f"Globe_{K.idx('fglobe')}", (x - 0.38, y - 0.38, 0), (x + 0.38, y + 0.38, 1.4))


def library_table(A, at, rz=0.0, length=2.6, width=1.1):
    """A long walnut library table with turned legs, leather inset, books and two green banker's lamps."""
    K = A.K
    M = mats(A)
    T = frame(at[0], at[1], rz)
    rot = (0, 0, rz)
    K.box(K.name("TABLE", "LibraryTop"), (length, width, 0.05), tuple(T(0, 0, 0.765)), M["walnut"], rot=rot, bevel=0.012, lightmap=True)
    K.box(K.name("TABLE", "LibraryLeather"), (length - 0.24, width - 0.24, 0.004), tuple(T(0, 0, 0.792)), M["deskleather"], rot=rot)
    K.box(K.name("TABLE", "LibraryApron"), (length - 0.1, width - 0.1, 0.12), tuple(T(0, 0, 0.68)), M["walnut"], rot=rot, bevel=0.01, lightmap=True)
    leg = [(0, 0), (0.04, 0), (0.05, 0.06), (0.035, 0.12), (0.06, 0.3), (0.075, 0.42), (0.05, 0.55), (0.045, 0.62), (0, 0.62)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.lathe(K.name("TABLE", "LibraryLeg"), leg, tuple(T(sx * (length / 2 - 0.12), sy * (width / 2 - 0.12), 0)), M["walnut"], segments=14)
    for s in (-1, 1):
        bankers_lamp(A, tuple(T(s * length * 0.3, 0.12, 0.79))[:2], 0.79, rz)
    for k, (dx, w, h, th) in enumerate(((-0.1, 0.24, 0.04, 0.1), (-0.06, 0.2, 0.035, -0.2), (0.55, 0.26, 0.05, 0.4))):
        K.box(K.name("PROP", "Book"), (w, 0.17, h), tuple(T(dx, -0.2, 0.795 + h / 2 + (k if k < 2 else 0) * 0.04)), M["leather"] if k != 1 else M["damask_green"], rot=(0, 0, rz + th), bevel=0.003)
    collide(K, "LibraryTable", T, (-length / 2, -width / 2), (length / 2, width / 2), 0, 0.85)


def bankers_lamp(A, xy, z, rz=0.0, candela=4):
    """A brass banker's lamp with a green glass shade (lit; bake-only light)."""
    K = A.K
    M = mats(A)
    if "greenshade" not in M:
        K.material("greenshade", f"MAT_{K.zone}_GreenShade", (0.02, 0.12, 0.05), 0.12, emis_color=(0.3, 0.75, 0.4), emis_strength=0.12)   # cased green glass, faintly lit
    x, y = xy
    K.box(K.name("PROP", "BankerBase"), (0.22, 0.13, 0.025), (x, y, z + 0.0125), M["brass"], rot=(0, 0, rz), bevel=0.006)
    K.cyl(K.name("PROP", "BankerStem"), 0.009, 0.009, 0.3, (x, y, z + 0.17), M["brass"], segments=8)
    K.cyl(K.name("PROP", "BankerShade"), 0.07, 0.07, 0.27, (x, y, z + 0.33), M["greenshade"], segments=16, rot=(0, math.pi / 2, rz))
    K.light(K.name("LIGHT", "Banker"), "POINT", (x, y, z + 0.26), candela, color=(1.0, 0.82, 0.55), rng=4, bake_only=True)


def pendant_lamp(A, x, y, H, sx=1.6, candela=16, z_shade=1.72):
    """Brass billiard pendant over a card table with a live light under the shade."""
    K, M = A.K, A.M
    K.cyl(K.name("PROP", "PendantRod"), 0.008, 0.008, H - z_shade - 0.23, (x, y, (H + z_shade + 0.23) / 2), M["brass"], segments=8)
    shade = K.lathe(K.name("PROP", "PendantShade"), [(0.55, 0), (0.5, 0.05), (0.3, 0.2), (0.14, 0.3), (0.05, 0.32), (0, 0.33)], (x, y, z_shade), M["brass"], segments=48)
    shade.scale = (sx, 1, 1)
    glow = K.cyl(K.name("PROP", "PendantGlow"), 0.48, 0.48, 0.01, (x, y, z_shade + 0.01), M["shade"], segments=48)
    glow.scale = (sx, 1, 1)
    K.light(K.name("LIGHT", "Pendant"), "POINT", (x, y, z_shade - 0.12), candela, rng=4.5)


# ============================================================================ ballroom

def _gilt_chair_protos(A):
    """Prototype parts of a Louis XVI gilt side chair (chaise à la reine): fluted legs, a moulded seat rail,
    a velvet seat, an oval medallion back with a velvet pad. Seat height 0.47 m; faces local +Y."""
    K, M = A.K, A.M
    P = A._props.get("_giltchair")
    if P:
        return P
    P = A._props["_giltchair"] = {}
    P["leg"] = K.prototype(K.lathe(K.name("CHAIR", "GiltLeg"), [(0, 0), (0.014, 0), (0.018, 0.03), (0.016, 0.06), (0.024, 0.32), (0.03, 0.36), (0.03, 0.4), (0, 0.4)], (0, 0, -30), M["gilt"], segments=10))
    P["rail"] = K.prototype(K.box(K.name("CHAIR", "GiltRail"), (0.46, 0.44, 0.06), (0, 0, -30), M["gilt"], bevel=0.012))
    P["seat"] = K.prototype(K.box(K.name("CHAIR", "GiltSeat"), (0.42, 0.4, 0.06), (0, 0, -30), M["velvet"], bevel=0.025, segments=3))
    P["frame"] = K.prototype(K.torus(K.name("CHAIR", "GiltBackFrame"), 0.2, 0.016, (0, 0, -30), M["gilt"], major=32, minor=6, rot=(math.pi / 2, 0, 0)))
    P["pad"] = K.prototype(K.cyl(K.name("CHAIR", "GiltBackPad"), 0.19, 0.19, 0.03, (0, 0, -30), M["velvet"], segments=32, rot=(math.pi / 2, 0, 0)))
    P["post"] = K.prototype(K.cyl(K.name("CHAIR", "GiltBackPost"), 0.014, 0.014, 0.18, (0, 0, -30), M["gilt"], segments=8))
    return P


def gilt_chair(A, xy, rz, collide_=True, z0=0.0):
    """Place a gilt side chair at xy facing local +Y turned by rz (instanced parts)."""
    K = A.K
    P = _gilt_chair_protos(A)
    T = frame(xy[0], xy[1], rz, z0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.linked(K.name("CHAIR", "GiltLeg"), P["leg"], tuple(T(sx * 0.19, sy * 0.18, 0)))
    K.linked(K.name("CHAIR", "GiltRail"), P["rail"], tuple(T(0, 0, 0.42)), rot=(0, 0, rz))
    K.linked(K.name("CHAIR", "GiltSeat"), P["seat"], tuple(T(0, 0.01, 0.47)), rot=(0, 0, rz))
    for sx in (-1, 1):
        K.linked(K.name("CHAIR", "GiltBackPost"), P["post"], tuple(T(sx * 0.17, -0.2, 0.54)), rot=(0, 0, rz))
    back = T(0, -0.21, 0.82)
    for key in ("frame", "pad"):
        ob = K.linked(K.name("CHAIR", "GiltBack" + key.capitalize()), P[key], tuple(back), rot=(math.pi / 2 - 0.12, 0, rz))
        ob.scale = (0.9, 1.25, 1.0)
    if collide_:
        collide(K, "GiltChair", T, (-0.24, -0.26), (0.24, 0.24), z0, z0 + 1.0)


def banquette(A, xy, rz, length=1.8):
    """A long velvet banquette on gilt legs, set against a wall (faces local +Y)."""
    K, M = A.K, A.M
    T = frame(xy[0], xy[1], rz)
    rot = (0, 0, rz)
    K.box(K.name("PROP", "BanquetteSeat"), (length, 0.55, 0.16), tuple(T(0, 0, 0.36)), M["velvet"], rot=rot, bevel=0.05, segments=3)
    K.box(K.name("PROP", "BanquetteRail"), (length + 0.04, 0.58, 0.07), tuple(T(0, 0, 0.26)), M["gilt"], rot=rot, bevel=0.012)
    for k in range(4):
        for sy in (-1, 1):
            K.lathe(K.name("PROP", "BanquetteLeg"), [(0, 0), (0.016, 0), (0.022, 0.05), (0.02, 0.18), (0.028, 0.23), (0, 0.23)],
                    tuple(T((k / 3 - 0.5) * (length - 0.1), sy * 0.24, 0)), M["gilt"], segments=10)
    for s in (-1, 1):
        K.cyl(K.name("PROP", "BanquetteBolster"), 0.1, 0.1, 0.5, tuple(T(s * (length / 2 - 0.08), 0, 0.52)), M["velvet"], segments=16, rot=(math.pi / 2, 0, rz))
    collide(K, "Banquette", T, (-length / 2, -0.3), (length / 2, 0.3), 0, 0.6)


def harp(A, xy, rz, z0=0.0):
    """A gilded concert harp: pedestal base, fluted column, scrolled neck, tapering soundboard and strings."""
    K, M = A.K, A.M
    T = frame(xy[0], xy[1], rz, z0)
    K.box(K.name("PROP", "HarpBase"), (0.42, 0.3, 0.12), tuple(T(0, 0, 0.06)), M["gilt"], rot=(0, 0, rz), bevel=0.02)
    K.lathe(K.name("PROP", "HarpColumn"), [(0, 0), (0.05, 0), (0.04, 0.1), (0.035, 1.5), (0.06, 1.62), (0.05, 1.7), (0, 1.72)], tuple(T(-0.14, 0.05, 0.12)), M["gilt"], segments=16)
    neck = [T(-0.14, 0.05, 1.82), T(0.0, 0.05, 1.86), T(0.2, 0.05, 1.7), T(0.38, 0.05, 1.58), T(0.52, 0.05, 1.42)]
    K.tube(K.name("PROP", "HarpNeck"), neck, 0.035, M["gilt"])
    # soundboard: from the base up to the neck's end, widening downwards
    bm = bmesh.new()
    a0, a1 = T(0.1, 0.05, 0.12), T(0.52, 0.05, 1.42)
    ax = (a1 - a0).normalized()
    side = Vector((-math.sin(rz), math.cos(rz), 0))
    perp = ax.cross(side).normalized()
    ring = []
    for k in range(11):
        f = k / 10
        c = a0.lerp(a1, f)
        wdt = 0.17 * (1 - f) + 0.05 * f
        ring.append([bm.verts.new(c + side * sx * wdt + perp * sz * wdt * 0.6) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for r0, r1 in zip(ring, ring[1:]):
        for j in range(4):
            bm.faces.new((r0[j], r0[(j + 1) % 4], r1[(j + 1) % 4], r1[j]))
    bm.faces.new(list(reversed(ring[0])))
    bm.faces.new(ring[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    K.obj(K.name("PROP", "HarpSoundboard"), bm, M["gilt"], smooth_angle=40)
    strings = []
    for k in range(1, 34):
        f = k / 34
        top = neck[0].lerp(neck[-1], f) + Vector((0, 0, -0.05 - 0.12 * math.sin(math.pi * f)))
        bot = a0.lerp(a1, f * 0.98)
        strings.append((bot, top))
    sbm = bmesh.new()
    for bot, top in strings:
        d = (top - bot)
        if d.length < 0.05:
            continue
        w = side * 0.0015
        sbm.faces.new([sbm.verts.new(v) for v in (bot - w, bot + w, top + w, top - w)])
    K.obj(K.name("PROP", "HarpStrings"), sbm, M["shade"])
    collide(K, "Harp", T, (-0.3, -0.25), (0.6, 0.3), z0, z0 + 1.9)


def music_stand(A, xy, rz, z0=0.0):
    """A brass music stand: tripod foot, telescopic stem and a tilted desk with a part on it."""
    K, M = A.K, A.M
    T = frame(xy[0], xy[1], rz, z0)
    for k in range(3):
        a = rz + k * 2 * math.pi / 3
        K.tube(K.name("PROP", "StandFoot"), [T(0, 0, 0.3), Vector((xy[0] + 0.24 * math.cos(a), xy[1] + 0.24 * math.sin(a), z0 + 0.01))], 0.008, M["brass"], bezier=False)
    K.cyl(K.name("PROP", "StandStem"), 0.01, 0.01, 0.95, tuple(T(0, 0, 0.62)), M["brass"], segments=8)
    desk = K.box(K.name("PROP", "StandDesk"), (0.5, 0.012, 0.34), tuple(T(0, 0.04, 1.18)), M["brass"])
    desk.rotation_euler = (math.radians(-20), 0, rz)
    part = K.box(K.name("PROP", "StandPart"), (0.42, 0.004, 0.3), tuple(T(0, 0.055, 1.19)), M["shade"])
    part.rotation_euler = (math.radians(-20), 0, rz)


# ============================================================================ grand rooms: columns, torchères, theatre curtains

def column(A, xy, top, r=0.27, z0=0.0, collider=True):
    """A fluted Calacatta column on a Nero plinth with a gilt base, a gilt Ionic-ish capital and a walnut abacus,
    rising from z0 to `top`."""
    K, M = A.K, A.M
    x, y = xy
    K.box(K.name("ROOM", "ColumnPlinth"), (r * 2.6, r * 2.6, 0.36), (x, y, z0 + 0.18), M["nero"], bevel=0.02, segments=3, lightmap=True)
    K.lathe(K.name("ROOM", "ColumnBase"), [(0, 0), (r * 1.25, 0), (r * 1.25, 0.05), (r * 1.12, 0.1), (r * 1.05, 0.13), (r, 0.18), (0, 0.18)], (x, y, z0 + 0.36), M["gilt"], segments=40)
    shaft = top - z0 - 0.54 - 0.62
    K.fluted_shaft(K.name("ROOM", "ColumnShaft"), r, shaft, (x, y, z0 + 0.54), M["marble"], flutes=20, lightmap=True)
    K.lathe(K.name("ROOM", "ColumnCapital"), [(0, 0), (r * 0.96, 0), (r * 1.04, 0.06), (r * 1.2, 0.22), (r * 1.36, 0.38), (r * 1.5, 0.46), (0, 0.46)], (x, y, z0 + 0.54 + shaft), M["gilt"], segments=40)
    K.box(K.name("ROOM", "ColumnAbacus"), (r * 3.2, r * 3.2, 0.16), (x, y, top - 0.08), M["gilt"], bevel=0.02, segments=3)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        K.torus(K.name("PROP", "CapitalVolute"), r * 0.24, r * 0.07, (x + r * 1.3 * math.cos(a), y + r * 1.3 * math.sin(a), top - 0.25), M["gilt"],
                major=16, minor=6, rot=(math.pi / 2, 0, a + math.pi / 2))
    if collider:
        K.collider(f"Column_{K.idx('fcol')}", (x - r * 1.3, y - r * 1.3, z0), (x + r * 1.3, y + r * 1.3, top))


def torchere(A, xy, z0=0.0, height=2.3, arms=6, candela=4):
    """A gilt torchère: a tall turned standard carrying a crown of candle arms (lit, bake-only)."""
    K, M = A.K, A.M
    x, y = xy
    P = A._props.get("_torch")
    if P is None:
        P = A._props["_torch"] = {
            "cup": K.prototype(K.lathe(K.name("PROP", "TorchCup"), [(0, 0), (0.045, 0.0), (0.055, 0.03), (0.03, 0.05), (0, 0.05)], (0, 0, -30), M["gilt"], segments=12)),
            "candle": K.prototype(K.cyl(K.name("PROP", "TorchCandle"), 0.016, 0.016, 0.2, (0, 0, -30), M["shade"], segments=10)),
            "flame": K.prototype(K.lathe(K.name("PROP", "TorchFlame"), [(0, 0), (0.014, 0.012), (0.01, 0.035), (0, 0.055)], (0, 0, -30), M["candle"], segments=8)),
        }
    stand = [(0, 0), (0.3, 0), (0.28, 0.05), (0.12, 0.14), (0.08, 0.3), (0.05, 0.5), (0.07, 0.62), (0.04, 0.8), (0.035, height - 0.55),
             (0.07, height - 0.48), (0.05, height - 0.4), (0.09, height - 0.32), (0, height - 0.3)]
    K.lathe(K.name("PROP", "TorchStand"), stand, (x, y, z0), M["gilt"], segments=24)
    hub = Vector((x, y, z0 + height - 0.32))
    for k in range(arms):
        a = 2 * math.pi * k / arms
        tip = hub + Vector((0.32 * math.cos(a), 0.32 * math.sin(a), 0.16))
        K.tube(K.name("PROP", "TorchArm"), [hub, hub + Vector((0.16 * math.cos(a), 0.16 * math.sin(a), -0.06)), tip], 0.012, M["gilt"], resolution=5, bevel_res=2)
        for key, dz in (("cup", 0.0), ("candle", 0.14), ("flame", 0.24)):
            K.linked(K.name("PROP", "Torch" + key.capitalize()), P[key], tuple(tip + Vector((0, 0, dz))))
    for key, dz in (("cup", 0.02), ("candle", 0.16), ("flame", 0.26)):
        K.linked(K.name("PROP", "Torch" + key.capitalize()), P[key], tuple(hub + Vector((0, 0, 0.1 + dz))))
    K.light(K.name("LIGHT", "Torchere"), "POINT", tuple(hub + Vector((0, 0, 0.5))), candela, rng=6, bake_only=True)
    K.collider(f"Torchere_{K.idx('ftorch')}", (x - 0.3, y - 0.3, z0), (x + 0.3, y + 0.3, z0 + height))


def theatre_curtains(A, x0, x1, y, z_floor, z_top, tie_z=None, valance=1.0):
    """A proscenium's grand drape: two deep-pleated velvet curtains drawn and tied back to the sides (hourglass,
    hems pooling on the stage), a scalloped swag valance across the top with a gold bullion fringe. The curtains hang
    in the plane y (facing -Y, towards the house)."""
    K, M = A.K, A.M
    tie_z = tie_z if tie_z is not None else z_floor + 1.6
    span = x1 - x0
    H0 = z_top - valance - z_floor
    for sgn in (-1, 1):
        outer = (x0 if sgn < 0 else x1)
        bm = bmesh.new()
        nu, nv, folds = 80, 44, 16
        rows = []
        for j in range(nv + 1):
            fz = j / nv
            z = z_top - valance * 0.6 - fz * (H0 + valance * 0.4)
            if z >= tie_z:
                t = (z_top - z) / (z_top - tie_z)
                width = span * 0.5 * (1 - t ** 1.4) + 0.7 * t ** 1.4
            else:
                t = (tie_z - z) / max(0.01, tie_z - z_floor)
                width = 0.7 + 0.9 * math.sin(t * math.pi / 2)
            amp = 0.07 + 0.12 * max(0.0, 2.0 - width) / 2.0
            row = []
            for i in range(nu + 1):
                u = i / nu
                xx = outer - sgn * width * u
                d = amp * math.sin(2 * math.pi * folds * u) + amp
                zz = z
                if j == nv:
                    d += 0.12
                    zz = z_floor + 0.008
                row.append(bm.verts.new((xx, y - d, zz)))
            rows.append(row)
        for j in range(nv):
            for i in range(nu):
                f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
                f.smooth = True
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            if f.normal.y > 0:
                f.normal_flip()
        K.obj(K.name("PROP", "StageCurtain"), bm, M["velvet"])
        cx = outer - sgn * 0.35
        K.tube(K.name("PROP", "StageTieback"), [Vector((cx + 0.42 * math.cos(a), y - 0.15 - 0.25 * math.sin(a), tie_z)) for a in [2 * math.pi * k / 14 for k in range(15)]], 0.03, M["gilt"])
        K.lathe(K.name("PROP", "StageTassel"), [(0, 0), (0.07, 0.04), (0.09, 0.24), (0.04, 0.33), (0.06, 0.38), (0, 0.42)], (cx - sgn * 0.42, y - 0.15, tie_z - 0.5), M["gilt"], segments=14)
    # valance: a row of swags (catenaries) with jabots, pleated, across the top
    bm = bmesh.new()
    nu, swags = 160, 7
    top, bot = [], []
    for i in range(nu + 1):
        u = i / nu
        xx = x0 + span * u
        sag = valance * (0.45 + 0.55 * abs(math.sin(math.pi * swags * u)))
        d = 0.06 + 0.05 * math.sin(2 * math.pi * swags * 4 * u)
        top.append(bm.verts.new((xx, y - 0.3, z_top)))
        bot.append(bm.verts.new((xx, y - 0.3 - d, z_top - sag)))
    for i in range(nu):
        f = bm.faces.new((top[i], top[i + 1], bot[i + 1], bot[i]))
        f.smooth = True
        if f.normal.y > 0:
            f.normal_flip()
    K.obj(K.name("PROP", "StageValance"), bm, M["velvet"])
    fringe = A._props.get("_bullion")
    if fringe is None:
        fringe = A._props["_bullion"] = K.prototype(K.cyl(K.name("PROP", "BullionFringe"), 0.015, 0.008, 0.16, (0, 0, -30), M["gilt"], segments=6))
    for i in range(0, nu + 1, 1):
        u = i / nu
        sag = valance * (0.45 + 0.55 * abs(math.sin(math.pi * swags * u)))
        K.linked(K.name("PROP", "BullionFringe"), fringe, (x0 + span * u, y - 0.36, z_top - sag - 0.07))
