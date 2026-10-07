"""Marble floor kit shared by the mansion's halls (Layer 1). Lifted from the casino-era Grand Lobby.

    import floors
    floors.flat(K, name, polys, mat, z)                        # flat faces, UV0 in metres
    floors.checker(K, M, field, centre, hole_r)                # 45° Calacatta / Bardiglio checker + Nero cabochons
    floors.key_band(K, M, outer, inner)                        # Greek-key band in Nero with a Calacatta meander
    floors.medallion(K, M, centre, R)                          # compass-rose medallion with gilt rings

Layers sit 0.8 mm apart above the slab (z = 0); all faces are lightmapped.
"""
import math

import bmesh
import numpy as np
from mathutils import Vector

Z_GROUT, Z_TILE, Z_CAB, Z_BAND, Z_KEY = 0.0008, 0.0016, 0.0024, 0.0016, 0.0024


def flat(K, name, polys, mat, z, lightmap=True, uv_jitter=None):
    """Flat faces at height z; UV0 in metres (optionally offset/rotated per face for vein variety)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    for k, poly in enumerate(polys):
        if len(poly) < 3:
            continue
        f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in poly])
        if f.normal.z < 0:
            f.normal_flip()
        ox, oy, rot = uv_jitter[k] if uv_jitter else (0, 0, 0)
        c, s_ = math.cos(rot), math.sin(rot)
        for loop in f.loops:
            x, y = loop.vert.co.x, loop.vert.co.y
            loop[uv].uv = (x * c - y * s_ + ox, x * s_ + y * c + oy)
    return K.obj(name, bm, mat, uv=None, lightmap=lightmap)


def clip(poly, rect):
    """Sutherland–Hodgman against an axis-aligned rectangle (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = rect
    for inside, cut in ((lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
                        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
                        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
                        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1))):
        out = []
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            if inside(b):
                if not inside(a):
                    out.append(cut(a, b))
                out.append(b)
            elif inside(a):
                out.append(cut(a, b))
        poly = out
        if not poly:
            break
    return poly


def rect_poly(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def checker(K, M, field, centre, hole_r=0.0, S=0.72, skip=None, seed=7):
    """45° checker of Calacatta and Bardiglio tiles over a grout bed, symmetric about `centre`, with Nero
    cabochons at the corners. Tiles inside `hole_r` of the centre (under a medallion) or where `skip(x, y)`
    is true (under a staircase) are left out."""
    JOINT, r2 = 0.001, math.sqrt(0.5)
    cx, cy = centre
    flat(K, K.name("ROOM", "FloorGrout"), [rect_poly(*field)], K.mat["grout"], Z_GROUT)
    n = int(math.hypot(field[2] - field[0], field[3] - field[1]) / S) + 2
    tiles, jit = {"marble": [], "bardiglio": []}, {"marble": [], "bardiglio": []}
    rng = np.random.default_rng(seed)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            u0, u1, v0, v1 = i * S + JOINT, (i + 1) * S - JOINT, j * S + JOINT, (j + 1) * S - JOINT
            corners = [(cx + (u - v) * r2, cy + (u + v) * r2) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
            mx, my = sum(p[0] for p in corners) / 4, sum(p[1] for p in corners) / 4
            if hole_r and math.hypot(mx - cx, my - cy) < hole_r - 0.6:
                continue
            if skip and skip(mx, my):
                continue
            poly = clip(corners, field)
            if len(poly) < 3:
                continue
            key = "marble" if (i + j) % 2 == 0 else "bardiglio"
            tiles[key].append(poly)
            jit[key].append((rng.random() * 4, rng.random() * 4, rng.integers(4) * math.pi / 2))
    for key in tiles:
        flat(K, K.name("ROOM", f"FloorTile{key.capitalize()}"), tiles[key], M[key], Z_TILE, uv_jitter=jit[key])
    cab = K.prototype(K.box(K.name("PROP", "Cabochon"), (0.12, 0.12, 0.003), (0, 0, -30), M["nero"]))
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            u, v = i * S, j * S
            x, y = cx + (u - v) * r2, cy + (u + v) * r2
            if not (field[0] + 0.1 < x < field[2] - 0.1 and field[1] + 0.1 < y < field[3] - 0.1):
                continue
            if (hole_r and math.hypot(x - cx, y - cy) < hole_r + 0.1) or (skip and skip(x, y)):
                continue
            K.linked(K.name("PROP", "Cabochon"), cab, (x, y, Z_CAB))


def key_band(K, M, outer, inner, LW=0.03, PAD=0.055):
    """Greek-key band between two rectangles (x0, y0, x1, y1): Nero ground, Calacatta meander and fillets,
    corner blocks."""
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    band = iy0 - oy0
    flat(K, K.name("ROOM", "FloorBand"), [rect_poly(ox0, oy0, ox1, iy0), rect_poly(ox0, iy1, ox1, oy1),
                                          rect_poly(ox0, iy0, ix0, iy1), rect_poly(ix1, iy0, ox1, iy1)], M["nero"], Z_BAND)
    Hk = band - 2 * PAD
    Pk = Hk * 1.25

    def run(a0, a1):
        rects = [(a0, -LW / 2, a1, LW / 2), (a0, Hk - LW / 2, a1, Hk + LW / 2)]
        n = int((a1 - a0) // Pk)
        start = a0 + ((a1 - a0) - n * Pk) / 2
        for k in range(n):
            a = start + k * Pk
            pts = [(a, 0), (a, Hk * 0.8), (a + Pk * 0.72, Hk * 0.8), (a + Pk * 0.72, Hk * 0.3), (a + Pk * 0.36, Hk * 0.3), (a + Pk * 0.36, Hk * 0.55)]
            for (p0, q0), (p1, q1) in zip(pts, pts[1:]):
                rects.append((min(p0, p1) - LW / 2, min(q0, q1) - LW / 2, max(p0, p1) + LW / 2, max(q0, q1) + LW / 2))
        return rects

    polys = []
    for side in ("front", "back", "left", "right"):
        if side in ("front", "back"):
            base = oy0 + PAD if side == "front" else oy1 - PAD
            for (pa0, pb0, pa1, pb1) in run(ix0, ix1):
                polys.append(rect_poly(pa0, base + pb0, pa1, base + pb1) if side == "front" else rect_poly(pa0, base - pb1, pa1, base - pb0))
        else:
            base = ox0 + PAD if side == "left" else ox1 - PAD
            for (pa0, pb0, pa1, pb1) in run(iy0, iy1):
                polys.append(rect_poly(base + pb0, pa0, base + pb1, pa1) if side == "left" else rect_poly(base - pb1, pa0, base - pb0, pa1))
    for cx_, cy_ in ((ox0 + band / 2, oy0 + band / 2), (ox1 - band / 2, oy0 + band / 2), (ox0 + band / 2, oy1 - band / 2), (ox1 - band / 2, oy1 - band / 2)):
        h_ = band / 2 - PAD / 2
        polys.append(rect_poly(cx_ - h_, cy_ - h_, cx_ + h_, cy_ + h_))
    flat(K, K.name("ROOM", "FloorKey"), polys, M["marble"], Z_KEY)


def medallion(K, M, centre, R=3.4):
    """Compass-rose medallion: Nero disc, Rosso band with a Calacatta sawtooth, faceted rays, gilt rings."""
    cx, cy = centre
    k_ = R / 3.4

    def disc(name, r, z, mat, seg=160):
        return flat(K, name, [[(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]], mat, z)

    def ring(name, r0, r1, z, mat, seg=160):
        polys = []
        for k in range(seg):
            a, b = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            polys.append([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                          (cx + r1 * math.cos(b), cy + r1 * math.sin(b)), (cx + r0 * math.cos(b), cy + r0 * math.sin(b))])
        return flat(K, name, polys, mat, z)

    def rays(n, r_tip, r_base, half_w, rot, z, mat_a, mat_b, tag):
        left, right = [], []
        for k in range(n):
            a = rot + 2 * math.pi * k / n
            d = Vector((math.cos(a), math.sin(a), 0))
            t = Vector((-d.y, d.x, 0))
            tip, base = d * r_tip, d * r_base
            P = lambda v: (v.x + cx, v.y + cy)  # noqa: E731
            left.append([(cx, cy), P(tip), P(base + t * half_w)])
            right.append([(cx, cy), P(base - t * half_w), P(tip)])
        flat(K, K.name("ROOM", f"Medallion{tag}A"), left, mat_a, z)
        flat(K, K.name("ROOM", f"Medallion{tag}B"), right, mat_b, z)

    zc = 0.003
    disc(K.name("ROOM", "Medallion"), R, zc, M["nero"])
    ring(K.name("ROOM", "Medallion"), 2.93 * k_, 3.28 * k_, zc + 0.0008, M["rosso"])
    teeth, NT = [], 48
    for k in range(NT):
        a0, a1, am = 2 * math.pi * k / NT, 2 * math.pi * (k + 1) / NT, 2 * math.pi * (k + 0.5) / NT
        r0, r1 = 2.96 * k_, 3.25 * k_
        teeth.append([(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1)), (cx + r1 * math.cos(am), cy + r1 * math.sin(am))])
    flat(K, K.name("ROOM", "MedallionTeeth"), teeth, M["marble"], zc + 0.0016)
    disc(K.name("ROOM", "Medallion"), 2.9 * k_, zc + 0.0016, M["marble"])
    ring(K.name("ROOM", "MedallionLine"), 2.06 * k_, 2.12 * k_, zc + 0.0024, M["nero"])
    rays(8, 2.1 * k_, 0.62 * k_, 0.3 * k_, math.pi / 8, zc + 0.0032, M["rosso"], M["nero"], "RayMinor")
    rays(8, 2.82 * k_, 0.75 * k_, 0.38 * k_, 0.0, zc + 0.004, M["nero"], M["bardiglio"], "RayMajor")
    ring(K.name("ROOM", "MedallionCore"), 0.62 * k_, 0.9 * k_, zc + 0.0048, M["rosso"])
    disc(K.name("ROOM", "MedallionCore"), 0.62 * k_, zc + 0.0048, M["marble"])
    rays(8, 0.56 * k_, 0.16 * k_, 0.12 * k_, math.pi / 8, zc + 0.0056, M["nero"], M["bardiglio"], "RayCore")
    for Rr, r, z in ((3.29, 0.018, zc + 0.002), (2.92, 0.015, zc + 0.0024), (0.905, 0.014, zc + 0.0056), (0.62, 0.012, zc + 0.0064)):
        K.torus(K.name("ROOM", "MedallionRing"), Rr * k_, r, (cx, cy, z - r * 0.7), M["gilt"], major=160, minor=6)
