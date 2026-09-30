"""Cut flowers for the mansion's arrangements (Layer 1): modelled roses, rose leaves and greenery sprays.

A rose head is ~18 individually shaped petals — cupped across, curled back at the lip, opening from a
tight spiral bud to wide outer petals — textured with a generated petal map (deep base → lighter
edge, fine veins, bruised rim). Leaves are serrated, folded along the midrib and veined. Everything is
built once as a prototype and placed as linked copies, so an arrangement of hundreds of stems exports
as a handful of GPU-instanced meshes.
"""
import math
import os

import bmesh
import numpy as np
from mathutils import Matrix, Vector

import kit

TEX = os.path.join(kit.ROOT, "blender", "textures_src", "flora")


# ----------------------------------------------------------------------------- textures
def _petal_texture(path, base, edge, seed):
    """RGBA petal map: v = 0 at the petal's heel, 1 at its lip."""
    rng = np.random.default_rng(seed)
    n = 256
    v, u = np.mgrid[0:n, 0:n] / (n - 1)
    grad = np.clip(v ** 0.8, 0, 1)[..., None]
    col = np.array(base)[None, None] * (1 - grad) + np.array(edge)[None, None] * grad
    veins = 0.5 + 0.5 * np.sin((u - 0.5) * 70 + np.sin(v * 9) * 1.5)
    veins = kit.blur(veins ** 6, 2)
    noise = kit.blur(rng.random((n, n)), 3)
    col *= (0.9 + 0.12 * noise)[..., None]
    col *= (1 - 0.1 * veins * (1 - v))[..., None]
    lip = np.clip((v - 0.9) / 0.1, 0, 1) * (0.35 + 0.65 * kit.blur(rng.random((n, n)), 1))
    col *= (1 - 0.35 * lip)[..., None]                            # slightly bruised, darker rim
    heel = np.clip(1 - v / 0.12, 0, 1)
    col = col * (1 - 0.5 * heel[..., None]) + np.array([0.35, 0.4, 0.12])[None, None] * 0.5 * heel[..., None]
    rgba = np.concatenate([np.clip(col, 0, 1), np.ones((n, n, 1))], -1)
    kit.save_image(path, rgba)


def _leaf_texture(path, seed):
    rng = np.random.default_rng(seed)
    n = 256
    v, u = np.mgrid[0:n, 0:n] / (n - 1)
    base = np.array([0.1, 0.19, 0.07])
    col = base[None, None] * (0.85 + 0.3 * kit.blur(rng.random((n, n)), 6))[..., None]
    mid = np.exp(-((u - 0.5) / 0.012) ** 2)
    side = np.abs(u - 0.5)
    sec = np.exp(-((((v - side * 1.2) * 11) % 1 - 0.5) / 0.07) ** 2) * (side > 0.02) * (side < 0.46)
    col += np.array([0.1, 0.14, 0.05])[None, None] * (0.8 * mid + 0.35 * sec)[..., None]
    col *= (1 - 0.25 * np.clip(side * 2 - 0.7, 0, 1))[..., None]
    rgba = np.concatenate([np.clip(col, 0, 1), np.ones((n, n, 1))], -1)
    kit.save_image(path, rgba)


def materials(K):
    """MAT_<Zone>_RoseRed / RoseIvory / RoseLeaf (textured, double-sided)."""
    os.makedirs(TEX, exist_ok=True)
    specs = {
        "rose_red": ("RoseRed", (0.24, 0.006, 0.022), (0.46, 0.022, 0.045), 11),   # sRGB; deep, velvety crimson
        "rose_ivory": ("RoseIvory", (0.62, 0.58, 0.44), (0.82, 0.77, 0.66), 12),
    }
    for key, (name, base, edge, seed) in specs.items():
        p = os.path.join(TEX, f"T_{name}_BaseColor.png")
        _petal_texture(p, base, edge, seed)
        m = K.material(key, f"MAT_{K.zone}_{name}", (1, 1, 1), 0.78, sheen=0.2, sheen_tint=edge, base_tex=p)
        m.use_backface_culling = False
    p = os.path.join(TEX, "T_RoseLeaf_BaseColor.png")
    if not os.path.exists(p):
        _leaf_texture(p, 13)
    m = K.material("rose_leaf", f"MAT_{K.zone}_RoseLeaf", (1, 1, 1), 0.38, coat=0.3, coat_rough=0.25, base_tex=p)
    m.use_backface_culling = False
    return K.mat


# ----------------------------------------------------------------------------- geometry
def _petal(bm, uv, xf, w, l, cup, curl, open_, NU=4, NV=4):
    """One petal: obovate outline (narrow heel, broad rounded lip), cupped across, opened back from
    vertical by `open_` and its lip rolled outward by `curl`. Local +Z = up the stem, +Y = outward."""
    rows = []
    r = z = 0.0
    for j in range(NV + 1):
        v = j / NV
        width = w * math.sqrt(max(0.0, 1 - ((v - 0.62) / 0.66) ** 2))
        ang = open_ * v + curl * max(0.0, v - 0.7) / 0.3
        if j:
            r += l / NV * math.sin(ang)
            z += l / NV * math.cos(ang)
        row = []
        for i in range(NU + 1):
            s = i / NU - 0.5
            dr = -cup * (1 - (2 * s) ** 2) * width * 0.45 * (1 - 0.5 * v)   # edges wrap forward (cup)
            row.append(bm.verts.new(xf @ Vector((s * width, r + dr * math.cos(ang), z - dr * math.sin(ang)))))
        rows.append(row)
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / NU, b / NV)


def rose_head(K, name, mat, size=0.09, petals=20, seed=0):
    """A rose bloom ~size across, stem axis +Z, origin at the base of the head: a tight spiral bud
    inside, broad cupped petals opening outward, a few outer guard petals rolled back."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    golden = math.radians(137.5)
    for k in range(petals):
        t = k / (petals - 1)                      # 0 = innermost
        w = size * (0.32 + 0.5 * t) * (0.93 + 0.14 * rng.random())
        l = size * (0.36 + 0.3 * t)
        radius = size * (0.03 + 0.2 * t ** 1.5)
        open_ = 0.08 + 0.95 * t ** 2.2            # inner petals upright, outer ones open
        curl = 0.15 + 0.55 * t ** 3               # guard petals' lips roll back
        cup = 1.0 - 0.35 * t
        a = k * golden + rng.normal(0, 0.12)
        xf = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0, radius, size * 0.12 * (1 - t)))
        _petal(bm, uv, xf, w, l, cup, curl, open_)
    return K.obj(name, bm, mat, uv=None, smooth_angle=80)


def rose_leaf(K, name, mat, length=0.075, seed=0):
    """Serrated, midrib-folded rose leaf with a short petiole; points +Y from the origin."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    NU, NV = 4, 9
    rows = []
    for j in range(NV + 1):
        v = j / NV
        half = length * 0.3 * math.sin(math.pi * min(1, v * 1.05)) ** 0.8
        serr = 1 + 0.07 * (1 if j % 2 else -1) * (0.3 < v < 0.95)
        row = []
        for i in range(NU + 1):
            s = (i / NU - 0.5) * 2
            x = s * half * serr
            z = abs(s) * half * 0.35 + 0.18 * length * v * v   # V-fold along the midrib, arching
            row.append(bm.verts.new((x, v * length, z)))
        rows.append(row)
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / NU, b / NV)
    return K.obj(name, bm, mat, uv=None, smooth_angle=60)


def spray(K, name, mat, length=0.45, leaves=11, seed=0):
    """Greenery spray (a stem with paired leaves) for the arrangement's silhouette; grows along +Z."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    pts = [Vector((0.02 * math.sin(3 * t), 0, length * t)) for t in np.linspace(0, 1, 8)]
    for a, b in zip(pts, pts[1:]):   # thin stem ribbon (two crossed quads)
        for d in (Vector((0.002, 0, 0)), Vector((0, 0.002, 0))):
            f = bm.faces.new([bm.verts.new(p) for p in (a - d, a + d, b + d, b - d)])
            for loop, c in zip(f.loops, ((0.5, 0.0), (0.5, 0.02), (0.5, 0.04), (0.5, 0.06))):
                loop[uv].uv = c
    for k in range(leaves):
        t = 0.15 + 0.85 * k / leaves
        side = 1 if k % 2 else -1
        base = Vector((0.02 * math.sin(3 * t), 0, length * t))
        L = 0.05 + 0.03 * (1 - t) + rng.random() * 0.01
        xf = (Matrix.Translation(base) @ Matrix.Rotation(k * 2.4, 4, "Z") @ Matrix.Rotation(side * (0.9 - 0.4 * t), 4, "X"))
        NU, NV = 2, 5
        rows = []
        for j in range(NV + 1):
            v = j / NV
            half = L * 0.28 * math.sin(math.pi * v) ** 0.8
            rows.append([bm.verts.new(xf @ Vector(((i / NU - 0.5) * 2 * half, 0.004, v * L))) for i in range(NU + 1)])
        for j in range(NV):
            for i in range(NU):
                f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
                for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uv].uv = (a / NU, b / NV)
    return K.obj(name, bm, mat, uv=None, smooth_angle=60)


def arrangement(K, centre, top_z, radius=0.46, height=0.5, reds=80, ivories=60, leaves=170, sprays=18, seed=1924):
    """A grand dome of red and ivory roses over a skirt of leaves, broken by trailing greenery sprays.
    `top_z` is the vessel's rim; the dome's base sits just above it."""
    M = materials(K)
    rng = np.random.default_rng(seed)
    protos = {
        "red": [K.prototype(rose_head(K, K.name("PROP", "RoseRed"), M["rose_red"], seed=s)) for s in (1, 2, 3)],
        "ivory": [K.prototype(rose_head(K, K.name("PROP", "RoseIvory"), M["rose_ivory"], seed=s)) for s in (4, 5)],
        "leaf": [K.prototype(rose_leaf(K, K.name("PROP", "RoseLeaf"), M["rose_leaf"], seed=s)) for s in (6, 7)],
        "spray": [K.prototype(spray(K, K.name("PROP", "Greenery"), M["rose_leaf"], length=0.32, leaves=9, seed=s)) for s in (8, 9)],
    }
    cx, cy = centre
    z0 = top_z + 0.05

    def dome(u, v, rr=radius, hh=height):
        th, ph = 2 * math.pi * u, math.acos(1 - v)          # v ∈ [0, 1] → upper hemisphere
        n = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
        return Vector((cx + rr * n.x, cy + rr * n.y, z0 + hh * n.z)), n

    def place(kind, p, n, spin, scale):
        axis = n.to_track_quat("Z", "Y").to_euler()
        ob = K.linked(K.name("PROP", protos[kind][0].name.split("_")[2]), protos[kind][rng.integers(len(protos[kind]))], tuple(p),
                      rot=(axis.x, axis.y, axis.z + spin), scale=(scale,) * 3)
        return ob

    # roses: jittered Fibonacci points over the dome so blooms don't clump
    total = reds + ivories
    kinds = ["red"] * reds + ["ivory"] * ivories
    rng.shuffle(kinds)
    for k in range(total):
        u = (k * 0.618034) % 1 + rng.normal(0, 0.01)
        v = min(0.98, (k + 0.5) / total * 1.02)
        p, n = dome(u, v)
        n = (n + Vector((rng.normal(0, 0.12), rng.normal(0, 0.12), 0.15))).normalized()
        place(kinds[k], p - n * 0.05, n, rng.random() * 6.28, 0.95 + rng.random() * 0.3)
    # leaves: a skirt around the rim and tucked between blooms
    for k in range(leaves):
        u = rng.random()
        v = 0.65 + 0.4 * rng.random() if k < leaves * 0.7 else rng.random() * 0.8
        p, n = dome(u, v, radius * 0.98, height * 0.95)
        tang = Vector((-n.y, n.x, 0)).normalized() if abs(n.z) < 0.99 else Vector((1, 0, 0))
        d = (n * 0.8 + tang * rng.normal(0, 0.5) + Vector((0, 0, -0.3 * (v > 0.6)))).normalized()
        place("leaf", p - n * 0.03, d, rng.random() * 6.28, 0.8 + 0.5 * rng.random())
    # greenery sprays radiating out and down past the rim
    for k in range(sprays):
        th = 2 * math.pi * k / sprays + rng.normal(0, 0.08)
        p = Vector((cx + radius * 0.75 * math.cos(th), cy + radius * 0.75 * math.sin(th), z0 + 0.04))
        d = Vector((math.cos(th), math.sin(th), -0.25 + 0.45 * rng.random())).normalized()   # arching over the rim
        place("spray", p, d, rng.random() * 6.28, 0.9 + 0.5 * rng.random())
