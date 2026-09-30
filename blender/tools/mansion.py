"""The mansion's shared architectural kit for Blender authoring (Layer 1).

Every zone — lobby, galleries, game rooms — is built from the same vocabulary so the house reads as
one building: panelled walls with swept mouldings, fluted pilasters, damask fields in gilt frames,
coffered ceilings, crystal chandeliers, two-arm sconces, panelled double doors (DOOR_ contract),
3D-lettered plaques, arched sea-view windows with velvet drapes, and real public-domain paintings.

    import kit, mansion
    K = kit.Zone("Poker")
    A = mansion.Mansion(K, height=5.2)
    A.wall("Back", "x", surface=12, normal=-1, lo=-7, hi=7, pilasters=[...], sconces=[...])

Heights derive from the ceiling: field top = H − 1.3 m, frieze top = H − 0.78 m (lobby: 5.9 / 6.42).
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import kit

UPV = (0, 0, 1)
RUG_SHEEN = (0.42, 0.12, 0.08)   # wool pile catches light in the dye's colour, not white
ART_DIR = os.path.join(kit.ROOT, "blender", "textures_src", "art")
P_FRAME = [(0, 0), (0, 0.022), (0.012, 0.03), (0.03, 0.03), (0.045, 0.018), (0.05, 0)]
P_PANEL = [(0, 0), (0, 0.012), (0.025, 0.02), (0.05, 0.02), (0.06, 0)]


def library_materials(K):
    """The shared library (src/render/materialNames.ts) — preview textures only; stripped at build."""
    K.material("marble", "MAT_Marble_Calacatta", (0.85, 0.8, 0.72), 0.2, coat=1, lib="Marble_Calacatta")
    K.material("nero", "MAT_Marble_Nero", (0.05, 0.045, 0.04), 0.2, coat=1, lib="Marble_Calacatta")
    K.material("rosso", "MAT_Marble_Rosso", (0.35, 0.1, 0.08), 0.2, coat=1, lib="Marble_Calacatta")
    K.material("bardiglio", "MAT_Marble_Bardiglio", (0.45, 0.46, 0.47), 0.2, coat=1, lib="Marble_Calacatta")
    K.material("walnut", "MAT_Wood_WalnutPolished", (0.3, 0.19, 0.12), 0.55, coat=0.22, coat_rough=0.38, lib="Wood_WalnutPolished")
    K.material("walnut_dark", "MAT_Wood_WalnutDark", (0.12, 0.07, 0.05), 0.6, coat=0.12, coat_rough=0.45, lib="Wood_WalnutPolished")
    K.material("damask", "MAT_Fabric_DamaskOxblood", (0.3, 0.05, 0.05), 0.9, sheen=0.4, lib="Fabric_Damask")
    K.material("damask_green", "MAT_Fabric_DamaskForest", (0.1, 0.2, 0.13), 0.9, sheen=0.4, lib="Fabric_Damask")
    K.material("damask_gold", "MAT_Fabric_DamaskGold", (0.4, 0.29, 0.13), 0.9, sheen=0.5, lib="Fabric_Damask")
    K.material("carpet", "MAT_Fabric_CarpetCrimson", (0.3, 0.06, 0.04), 1.0, sheen=0.4, lib="Carpet_Gul")
    K.material("carpet_green", "MAT_Fabric_CarpetForest", (0.16, 0.12, 0.08), 1.0, sheen=0.4, lib="Carpet_Gul")
    K.material("velvet", "MAT_Fabric_VelvetRed", (0.22, 0.02, 0.02), 0.85, sheen=1.0, lib="Fabric_Velvet")
    K.material("felt", "MAT_Fabric_FeltGreen", (0.1, 0.35, 0.18), 1.0, sheen=0.5, lib="Fabric_Felt")
    K.material("leather", "MAT_Leather_Oxblood", (0.25, 0.06, 0.05), 0.7, coat=0.12, coat_rough=0.5, lib="Leather_Oxblood")
    K.material("brass", "MAT_Brass_Aged", (0.6, 0.45, 0.24), 0.52, metal=1)
    K.material("gilt", "MAT_Gold_Gilt", (0.72, 0.56, 0.29), 0.46, metal=1)
    K.material("crystal", "MAT_Crystal_Clear", (1, 1, 1), 0.02)
    K.material("candle", "MAT_Emissive_Candle", (0, 0, 0), 0.5, emis_color=(1, 0.76, 0.48), emis_strength=40)
    K.material("shade", "MAT_Fabric_LampShade", (0.9, 0.83, 0.66), 0.9, emis_color=(1, 0.72, 0.44), emis_strength=1.6)
    K.material("ceiling", "MAT_Plaster_Ceiling", (0.12, 0.08, 0.05), 0.55, lib="Plaster_Ceiling")
    K.material("lacquer", f"MAT_{K.zone}_Lacquer", (0.012, 0.01, 0.009), 0.15, coat=1, coat_rough=0.02)
    return K.mat


def sea_texture(path, seed=1924, moon_x=0.3):
    """Night over the Riviera for window views (emissive), generated once per zone."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = np.random.default_rng(seed)
    w = h = 1024
    y = np.linspace(0, 1, h)[:, None]
    horizon = 0.36
    sky = np.stack([0.02 + 0.09 * (1 - y), 0.03 + 0.1 * (1 - y), 0.1 + 0.2 * (1 - y)], -1) * np.ones((1, w, 1))
    sea = np.stack([0.01 + 0.02 * y, 0.015 + 0.03 * y, 0.04 + 0.07 * y], -1) * np.ones((1, w, 1))
    img = np.where((y > horizon)[..., None], sky, sea)
    n = 600
    img[rng.integers(int(h * 0.42), h, n), rng.integers(0, w, n)] += rng.uniform(0.2, 0.9, (n, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    mx, my = int(w * moon_x), int(h * 0.82)
    d = np.hypot(xx - mx, yy - my)
    img += (np.exp(-(d / 110) ** 2) * 0.22)[..., None] * np.array([1, 0.95, 0.85])
    img[d < 24] = [1.0, 0.97, 0.88]
    glint = (np.abs(xx - mx) < (10 + (horizon * h - yy) * 0.4)) & (yy < horizon * h) & (rng.random((h, w)) < 0.35)
    img[glint] += np.array([0.5, 0.45, 0.35]) * ((yy[glint] / (horizon * h)) ** 1.5)[:, None]
    ridge = horizon * h + 110 * np.sin(np.linspace(0, math.pi, w)) * (np.linspace(0, 1, w) > 0.45) + 5
    land = (yy < ridge[None, :]) & (yy > horizon * h - 2) & (xx > w * 0.45)
    img[land] = [0.01, 0.01, 0.015]
    for px in rng.integers(int(w * 0.46), w, 140):
        py = int(horizon * h + rng.random() * (ridge[px] - horizon * h))
        img[py:py + 2, px:px + 2] = [1.0, 0.72, 0.36]
    img = kit.blur(img, 1)
    return kit.save_image(path, np.concatenate([np.clip(img, 0, 1), np.ones((h, w, 1))], -1))


def artworks():
    """Public-domain paintings fetched by scripts/fetch-art.mjs (1024² POT copies + true aspect)."""
    with open(os.path.join(ART_DIR, "art.json")) as f:
        works = json.load(f)["works"]
    for w in works:
        w["path"] = os.path.join(kit.ROOT, w["src"])
    return works


class Mansion:
    def __init__(self, K, height, thickness=0.3, sea=None):
        self.K = K
        self.M = K.mat if K.mat else library_materials(K)
        self.H = height
        self.T = thickness
        self.field_top = height - 1.3
        self.frieze_top = height - 0.78
        self.art = artworks()
        self._art_mats = {}
        self._sconce = {}
        self._chair = {}
        self._dining = {}
        self._props = {}
        if sea:
            K.material("sea", f"MAT_{K.zone}_SeaView", (0, 0, 0), 0.1, emis_tex=sea, emis_strength=1.1)

    # ------------------------------------------------------------------ walls
    def wall(self, tag, axis, surface, normal, lo, hi, base=0.0, openings=(), windows=(), paintings=(),
             pilasters=(), sconces=(), field=None, jambs=True, mass=True):
        """A dressed wall: mass with openings, skirting, wainscot with raised panels, chair rail, fabric
        field in gilt frames, fluted pilasters, frieze with dentils and a swept crown cornice.
        axis 'x': runs along X at y=surface; 'y': along Y at x=surface. `normal` (±1) points into the room.
        openings: (centre, width, height); paintings: (centre, art index)."""
        K, M, T, H = self.K, self.M, self.T, self.H
        FT, FZ = self.field_top, self.frieze_top
        field = field or M["damask"]
        n = Vector((0, normal, 0)) if axis == "x" else Vector((normal, 0, 0))
        t_dir = Vector((1, 0, 0)) if axis == "x" else Vector((0, 1, 0))

        def P(c, off, z):
            p = Vector((c, surface + off * normal, z)) if axis == "x" else Vector((surface + off * normal, c, z))
            return p

        def boxw(name, c, length, off, depth, z0, z1, mat, **kw):
            size = (length, depth, z1 - z0) if axis == "x" else (depth, length, z1 - z0)
            return K.box(name, size, tuple(P(c, off + depth / 2, (z0 + z1) / 2)), mat, **kw)

        def col(a, b, z0, z1):
            lo_c, hi_c = P(a, -T, z0), P(b, 0, z1)
            K.collider(f"{tag}_{K.idx(tag + 'col')}", [min(lo_c[i], hi_c[i]) for i in range(3)], [max(lo_c[i], hi_c[i]) for i in range(3)])

        gaps = sorted((c - w / 2, c + w / 2, h) for c, w, h in openings)
        spans, start = [], lo
        for g0, g1, _ in gaps:
            if g0 > start:
                spans.append((start, g0))
            start = g1
        if start < hi:
            spans.append((start, hi))

        for a, b in spans:
            if mass:
                boxw(K.name("ROOM", f"{tag}Wall"), (a + b) / 2, b - a, -T, T + 0.02, base, H, M["walnut_dark"], lightmap=True)
                col(a, b, base, H)
            else:
                boxw(K.name("ROOM", f"{tag}Wall"), (a + b) / 2, b - a, -0.02, 0.04, base, H, M["walnut_dark"], lightmap=True)
        for c, w, h in openings:
            boxw(K.name("ROOM", f"{tag}Lintel"), c, w, -T if mass else -0.02, (T + 0.02) if mass else 0.04, base + h, H, M["walnut_dark"], lightmap=True)
            if mass:
                col(c - w / 2, c + w / 2, base + h, H)
            if jambs and mass:
                for s in (-1, 1):
                    boxw(K.name("ROOM", f"{tag}Jamb"), c + s * (w / 2 - 0.03), 0.06, -T, T, base, base + h, M["walnut"], lightmap=True)
                boxw(K.name("ROOM", f"{tag}Jamb"), c, w, -T, T, base + h - 0.06, base + h, M["walnut"], lightmap=True)
                boxw(K.name("ROOM", f"{tag}Threshold"), c, w, -T, T, base, base + 0.02, M["nero"], lightmap=True)
            path = [P(c - w / 2 - 0.02, 0.0, base), P(c - w / 2 - 0.02, 0.0, base + h + 0.02), P(c + w / 2 + 0.02, 0.0, base + h + 0.02), P(c + w / 2 + 0.02, 0.0, base)]
            K.sweep(K.name("ROOM", f"{tag}Architrave"), path, n, [(0, 0), (0, 0.05), (0.06, 0.07), (0.14, 0.07), (0.2, 0.05), (0.22, 0)], M["walnut"], n1_hint=-t_dir, lightmap=True)
            K.sweep(K.name("ROOM", f"{tag}ArchitraveGilt"), path, n, [(0.02, 0.07), (0.03, 0.085), (0.05, 0.085), (0.06, 0.07)], M["gilt"], n1_hint=-t_dir)
            top = min(base + h + 0.52, FT - 0.02)
            boxw(K.name("ROOM", f"{tag}Overdoor"), c, w + 0.7, 0, 0.14, base + h + 0.2, top, M["walnut"], bevel=0.01, lightmap=True)
            boxw(K.name("ROOM", f"{tag}Overdoor"), c, w + 0.9, 0, 0.22, top, top + 0.08, M["gilt"], bevel=0.012)

        for a, b in spans:
            z = base
            K.sweep(K.name("ROOM", f"{tag}Skirting"), [P(a, 0, z), P(b, 0, z)], n,
                    [(h_, d_) for (d_, h_) in [(0, 0), (0.035, 0), (0.035, 0.14), (0.025, 0.155), (0.02, 0.17), (0.012, 0.19), (0, 0.2)]],
                    M["walnut"], n1_hint=UPV, lightmap=True)
            boxw(K.name("ROOM", f"{tag}Wainscot"), (a + b) / 2, b - a, 0, 0.03, z, z + 1.05, M["walnut"], lightmap=True)
            K.sweep(K.name("ROOM", f"{tag}Rail"), [P(a, 0, z + 1.07), P(b, 0, z + 1.07)], n,
                    [(h_, d_) for (d_, h_) in [(0, -0.03), (0.02, -0.03), (0.045, -0.015), (0.055, 0), (0.05, 0.018), (0.03, 0.03), (0.012, 0.04), (0, 0.045)]],
                    M["gilt"], n1_hint=UPV)
            boxw(K.name("ROOM", f"{tag}Field"), (a + b) / 2, b - a, 0, 0.018, z + 1.12, FT, field, lightmap=True)
            k = max(1, round((b - a) / 1.4))
            pw = (b - a) / k
            for i in range(k):
                c = a + pw * (i + 0.5)
                if pw < 0.6:
                    continue
                boxw(K.name("ROOM", f"{tag}Panel"), c, pw - 0.36, 0.03, 0.02, z + 0.3, z + 0.9, M["walnut_dark"], bevel=0.012, segments=3, lightmap=True)
                K.frame(K.name("ROOM", f"{tag}PanelFrame"), tuple(P(c, 0.03, z + 0.6)), pw - 0.3, 0.66, n, P_PANEL, M["walnut"])

        boxw(K.name("ROOM", f"{tag}Frieze"), (lo + hi) / 2, hi - lo, 0, 0.06, FT, FZ, M["walnut"], lightmap=True)
        dentil = K.prototype(K.box(K.name("PROP", f"{tag}Dentil"), (0.06, 0.06, 0.08), (0, 0, -5), M["gilt"]))
        x = lo + 0.08
        while x < hi - 0.05:
            K.linked(K.name("PROP", "Dentil"), dentil, tuple(P(x, 0.09, FZ - 0.06)))
            x += 0.15
        crown_h = H - FZ
        K.sweep(K.name("ROOM", f"{tag}Crown"), [P(lo, 0.0, FZ), P(hi, 0.0, FZ)], n,
                [(h_, d_) for (d_, h_) in [(0, 0), (0.05, 0), (0.06, 0.08), (0.1, 0.1), (0.2, 0.16), (0.26, 0.22), (0.28, 0.26), (0.3, 0.3), (0.3, 0.34), (0.3, crown_h), (0, crown_h)]],
                M["walnut"], n1_hint=UPV, lightmap=True)
        K.sweep(K.name("ROOM", f"{tag}CrownGilt"), [P(lo, 0.0, FZ + 0.34), P(hi, 0.0, FZ + 0.34)], n,
                [(h_, d_) for (d_, h_) in [(0.3, 0), (0.33, 0.01), (0.34, 0.03), (0.33, 0.05), (0.3, 0.06)]], M["gilt"], n1_hint=UPV)

        for i in range(len(pilasters) - 1):
            a, b = pilasters[i], pilasters[i + 1]
            c = (a + b) / 2
            if any(abs(c - oc) < 0.6 for oc, _, _ in openings) or any(abs(c - wc) < 0.6 for wc in windows):
                continue
            fw, fh = (b - a) - 0.9, FT - (base + 1.12) - 0.5
            if fh > 0.6 and fw > 0.5:
                K.frame(K.name("ROOM", f"{tag}FieldFrame"), tuple(P(c, 0.018, (base + 1.12 + FT) / 2)), fw, fh, n, P_FRAME, M["gilt"])
        for pc in pilasters:
            z0 = base
            boxw(K.name("ROOM", f"{tag}Pilaster"), pc, 0.46, 0, 0.12, z0, FT - 0.3, M["walnut"], bevel=0.01, lightmap=True)
            for f in (-0.12, -0.04, 0.04, 0.12):
                boxw(K.name("ROOM", f"{tag}Flute"), pc + f, 0.035, 0.12, 0.012, z0 + 1.3, FT - 0.55, M["walnut_dark"])
            boxw(K.name("ROOM", f"{tag}PilasterBase"), pc, 0.56, 0, 0.16, z0, z0 + 0.32, M["walnut"], bevel=0.012, lightmap=True)
            boxw(K.name("ROOM", f"{tag}Capital"), pc, 0.56, 0, 0.17, FT - 0.3, FT - 0.12, M["gilt"], bevel=0.015, segments=3)
            boxw(K.name("ROOM", f"{tag}Capital"), pc, 0.64, 0, 0.2, FT - 0.12, FT, M["walnut"], bevel=0.01)
            for s in (-1, 1):
                vol = P(pc + s * 0.24, 0.17, FT - 0.2)
                K.torus(K.name("PROP", f"{tag}Volute"), 0.05, 0.014, tuple(vol), M["gilt"], major=20, minor=6,
                        rot=(math.pi / 2, 0, 0) if axis == "x" else (math.pi / 2, 0, math.pi / 2))

        for c in windows:
            self.window(tag, P, n, t_dir, c, base)
        for c, idx in paintings:
            self.painting(tag, P, n, c, base, idx)
        for c in sconces:
            self.sconce(P, n, c, base)

    def window(self, tag, P, n, t_dir, c, base, w=1.9):
        K, M = self.K, self.M
        bottom, top = base + 1.35, min(base + 5.25, self.field_top - 0.55)
        hh = top - bottom
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.verify()
        pts = [(-w / 2, 0), (w / 2, 0), (w / 2, hh - w / 2)]
        for k in range(1, 16):
            a = math.pi * k / 16
            pts.append((w / 2 * math.cos(a), hh - w / 2 + w / 2 * math.sin(a)))
        pts.append((-w / 2, hh - w / 2))
        right = Vector((0, 0, 1)).cross(n).normalized()
        f = bm.faces.new([bm.verts.new(P(c, -0.02, bottom) + right * u + Vector((0, 0, v))) for u, v in pts])
        for loop, (u, v) in zip(f.loops, pts):
            loop[uvl].uv = (u / w + 0.5, v / hh)
        if f.normal.dot(n) < 0:
            f.normal_flip()
        K.obj(K.name("PROP", f"{tag}WindowView"), bm, M["sea"], uv=None)
        for zz in (bottom + hh * 0.26, bottom + hh * 0.52, bottom + hh * 0.75):
            K.box(K.name("PROP", f"{tag}Glazing"), (w, 0.04, 0.035) if abs(n.y) > 0.5 else (0.04, w, 0.035), tuple(P(c, 0.0, zz)), M["walnut"])
        K.box(K.name("PROP", f"{tag}Glazing"), (0.05, 0.04, hh) if abs(n.y) > 0.5 else (0.04, 0.05, hh), tuple(P(c, 0.0, bottom + hh / 2)), M["walnut"])
        arch = [P(c - w / 2, 0.0, bottom)] + [P(c + (w / 2) * math.cos(math.pi - math.pi * k / 16), 0.0, bottom + hh - w / 2 + (w / 2) * math.sin(math.pi * k / 16)) for k in range(17)] + [P(c + w / 2, 0.0, bottom)]
        K.sweep(K.name("ROOM", f"{tag}WindowSurround"), arch, n, [(0, 0), (0, 0.04), (0.05, 0.06), (0.12, 0.05), (0.14, 0)], M["gilt"], n1_hint=-t_dir)
        K.box(K.name("ROOM", f"{tag}WindowSill"), (w + 0.5, 0.3, 0.08) if abs(n.y) > 0.5 else (0.3, w + 0.5, 0.08), tuple(P(c, 0.15, bottom - 0.04)), M["nero"], bevel=0.01, lightmap=True)
        key = f"drape{round(self.field_top - base, 2)}"
        if key not in self._sconce:
            self._sconce[key] = K.prototype(K.cyl(K.name("PROP", "Drape"), 0.085, 0.085, self.field_top - base - 0.1, (0, 0, -20), M["velvet"], segments=12, subsurf=1))
        for s in (-1, 1):
            for k in range(5):
                p = P(c + s * (w / 2 + 0.12 + k * 0.1), 0.2 + (k % 2) * 0.03, base + (self.field_top - base) / 2)
                K.linked(K.name("PROP", "Drape"), self._sconce[key], tuple(p))
        K.box(K.name("PROP", f"{tag}Pelmet"), (w + 1.4, 0.16, 0.42) if abs(n.y) > 0.5 else (0.16, w + 1.4, 0.42), tuple(P(c, 0.22, self.field_top - 0.25)), M["velvet"], bevel=0.03, segments=3)
        K.box(K.name("PROP", f"{tag}PelmetGilt"), (w + 1.45, 0.18, 0.05) if abs(n.y) > 0.5 else (0.18, w + 1.45, 0.05), tuple(P(c, 0.23, self.field_top - 0.47)), M["gilt"], bevel=0.01)

    def art_material(self, idx):
        work = self.art[idx % len(self.art)]
        if work["id"] not in self._art_mats:
            n = len(self._art_mats) + 1
            self._art_mats[work["id"]] = self.K.material(f"art{n}", f"MAT_{self.K.zone}_Art{n:02d}", rough=0.42, base_tex=work["path"])
        return self._art_mats[work["id"]], work["aspect"]

    def painting(self, tag, P, n, c, base, idx, max_w=1.7, max_h=None):
        """A public-domain painting at its true proportions in a deep gilt frame."""
        K, M = self.K, self.M
        mat, aspect = self.art_material(idx)
        max_h = max_h or min(2.4, self.field_top - base - 1.9)
        w = min(max_w, max_h * aspect)
        h = w / aspect
        zc = base + 1.12 + (self.field_top - base - 1.12) / 2 + 0.05
        right = Vector((0, 0, 1)).cross(n).normalized()
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.verify()
        center = P(c, 0.05, zc)
        corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
        f = bm.faces.new([bm.verts.new(center + right * u + Vector((0, 0, v))) for u, v in corners])
        for loop, (u, v) in zip(f.loops, corners):
            loop[uvl].uv = (u / w + 0.5, v / h + 0.5)
        if f.normal.dot(n) < 0:
            f.normal_flip()
            for loop in f.loops:
                loop[uvl].uv = (1 - loop[uvl].uv[0], loop[uvl].uv[1])
        K.obj(K.name("PROP", f"{tag}Painting"), bm, mat, uv=None)
        K.frame(K.name("PROP", f"{tag}PaintingFrame"), tuple(P(c, 0.03, zc)), w + 0.02, h + 0.02, n,
                [(-0.02, 0), (-0.02, 0.03), (0.02, 0.07), (0.07, 0.08), (0.12, 0.06), (0.16, 0.03), (0.18, 0)], M["gilt"], flip=True)

    def sconce(self, P, n, c, base, candela=6):
        """Two-arm sconce: gilt backplate, curved arms, silk shades, bake-only light (in the lightmap)."""
        K, M, S = self.K, self.M, self._sconce
        if "plate" not in S:
            S["plate"] = K.prototype(K.lathe(K.name("PROP", "SconcePlate"), [(0, 0), (0.07, 0), (0.09, 0.08), (0.06, 0.22), (0.08, 0.32), (0.02, 0.42), (0, 0.42)], (0, 0, -30), M["gilt"], segments=20))
            S["shade"] = K.prototype(K.lathe(K.name("PROP", "SconceShade"), [(0.09, 0), (0.05, 0.13)], (0, 0, -30), M["shade"], segments=24))
            S["candle"] = K.prototype(K.cyl(K.name("PROP", "SconceCandle"), 0.013, 0.013, 0.1, (0, 0, -30), M["shade"], segments=10))
        right = Vector((0, 0, 1)).cross(n).normalized()
        z = base + min(2.75, self.field_top - base - 0.8)
        root = P(c, 0.13, z)
        rz = math.atan2(n.y, n.x) - math.pi / 2
        K.linked(K.name("PROP", "SconcePlate"), S["plate"], tuple(root + Vector((0, 0, -0.2))), rot=(0, 0, rz), scale=(1, 0.35, 1))
        for s in (-1, 1):
            tip = root + right * (s * 0.27) + n * 0.14 + Vector((0, 0, 0.04))
            K.tube(K.name("PROP", "SconceArm"), [root + Vector((0, 0, -0.08)), root + right * (s * 0.14) + n * 0.12 + Vector((0, 0, -0.14)), tip - Vector((0, 0, 0.04))], 0.011, M["gilt"])
            K.linked(K.name("PROP", "SconceCandle"), S["candle"], tuple(tip + Vector((0, 0, 0.02))))
            K.linked(K.name("PROP", "SconceShade"), S["shade"], tuple(tip + Vector((0, 0, 0.08))))
        K.light(K.name("LIGHT", "Sconce"), "POINT", tuple(root + n * 0.3 + Vector((0, 0, 0.12))), candela, rng=7, bake_only=True)

    # ------------------------------------------------------------------ doors & plaques
    def double_door(self, did, center, wall_normal, w, h, base, prompt, target=None, locked=False, depth=None):
        """DOOR_<Zone>_<Id> empty (local +Z → owning room) with door extras + `collider`, and two leaf
        meshes with origins on the hinges (§6). Leaves are unique, single meshes (the pipeline
        flattens hierarchies and would otherwise leave panels behind when the leaf swings)."""
        K, M = self.K, self.M
        T = self.T if depth is None else depth
        n = Vector(wall_normal)
        right = Vector((0, 0, 1)).cross(n).normalized()
        c = Vector(center)
        door = K.empty(f"DOOR_{K.zone}_{did}", tuple(c + Vector((0, 0, base))), kind="SINGLE_ARROW", size=0.6,
                       rot=Vector((0, 0, 1)).rotation_difference(n).to_euler())
        door["interactable"] = True
        door["interactionType"] = "door"
        door["interactionPrompt"] = prompt
        if target:
            door["target"] = target
        if locked:
            door["locked"] = True
        door["collider"] = f"COLLIDER_{K.zone}_Door{did}"
        lw = w / 2 - 0.01
        for side, sgn in (("L", -1), ("R", 1)):
            hinge = c + right * (sgn * (w / 2 - 0.005)) - n * (T / 2) + Vector((0, 0, base + 0.01))
            bm = kit.cube_bm(lw, 0.07, h - 0.02)
            bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((-sgn * lw / 2, 0, (h - 0.02) / 2)))
            rz = math.atan2(right.y, right.x)
            leaf = K.obj(f"DOOR_{K.zone}_{did}_{side}", bm, M["walnut_dark"], loc=tuple(hinge), rot=(0, 0, rz), bevel=0.008)
            parts = []
            for face in (-1, 1):
                for z0, ph in ((0.35, 0.85), (1.35, max(0.6, h - 2.1)), (h - 0.62, 0.36)):
                    if z0 + ph > h - 0.12:
                        continue
                    p = K.box(K.name("DOOR", f"{did}{side}Panel"), (lw - 0.26, 0.02, ph), (-sgn * lw / 2, face * 0.045, z0 + ph / 2), M["walnut"], bevel=0.008)
                    p.parent = leaf
                    parts.append(p)
                    fr = K.frame(K.name("DOOR", f"{did}{side}PanelFrame"), (-sgn * lw / 2, face * 0.056, z0 + ph / 2), lw - 0.2, ph + 0.05,
                                 (0, face, 0), [(0, 0), (0, 0.01), (0.015, 0.016), (0.03, 0)], M["gilt"])
                    fr.parent = leaf
                    parts.append(fr)
                hd = K.lathe(K.name("DOOR", f"{did}{side}Handle"), [(0, 0), (0.016, 0), (0.028, 0.05), (0.014, 0.14), (0.028, 0.2), (0, 0.22)],
                             (-sgn * (lw - 0.1), face * 0.075, 0.95), M["gilt"], segments=12)
                hd.parent = leaf
                parts.append(hd)
            bpy.context.view_layer.update()
            K.join_into(leaf, parts)
        lo = c - right * (w / 2) - n * T
        hi = c + right * (w / 2)
        K.collider(f"Door{did}", [min(lo[i], hi[i]) for i in range(2)] + [base], [max(lo[i], hi[i]) for i in range(2)] + [base + h])
        return door

    def plaque(self, lines, center, wall_normal, width=1.9, height=0.5):
        """Black lacquer plaque with a moulded gilt frame and 3D Cinzel lettering."""
        K, M = self.K, self.M
        n = Vector(wall_normal)
        c = Vector(center)
        rz = math.atan2(n.y, n.x) + math.pi / 2
        K.box(K.name("PROP", "Plaque"), (width, 0.04, height) if abs(n.y) > 0.5 else (0.04, width, height), tuple(c + n * 0.02), M["lacquer"], bevel=0.006)
        K.frame(K.name("PROP", "PlaqueFrame"), tuple(c + n * 0.03), width + 0.02, height + 0.02, n,
                [(-0.03, 0), (-0.03, 0.02), (0.0, 0.04), (0.03, 0.025), (0.035, 0)], M["gilt"], flip=True)
        for i, line in enumerate(lines):
            size = height * (0.3 if i == 0 else 0.15)
            z = c.z + (height * 0.14 if len(lines) > 1 and i == 0 else -height * 0.24 if i else 0)
            if "letters" not in M:   # gold leaf that catches the light: the aged trim gilt reads too dark here
                K.material("letters", f"MAT_{K.zone}_PlaqueLetters", (0.9, 0.7, 0.36), 0.28, metal=1, emis_color=(1.0, 0.8, 0.5), emis_strength=0.9)
            txt = K.text(K.name("PROP", "PlaqueText"), line.upper(), size, M["letters"], extrude=0.004,
                         loc=tuple(Vector((c.x, c.y, z)) + n * 0.045), rot=(math.pi / 2, 0, rz))
            if txt.dimensions.x > width - 0.2:
                s = (width - 0.2) / txt.dimensions.x
                txt.scale = (s, s, s)

    # ------------------------------------------------------------------ floors & ceilings
    def bordered_floor(self, x0, x1, y0, y1, field, band, margin=None, m=0.6, bw=0.3):
        K = self.K
        W, D, cx, cy = x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2
        margin = margin or field
        slabs = [
            ((W, m), (cx, y0 + m / 2), margin), ((W, m), (cx, y1 - m / 2), margin),
            ((m, D - 2 * m), (x0 + m / 2, cy), margin), ((m, D - 2 * m), (x1 - m / 2, cy), margin),
            ((W - 2 * m, bw), (cx, y0 + m + bw / 2), band), ((W - 2 * m, bw), (cx, y1 - m - bw / 2), band),
            ((bw, D - 2 * m - 2 * bw), (x0 + m + bw / 2, cy), band), ((bw, D - 2 * m - 2 * bw), (x1 - m - bw / 2, cy), band),
            ((W - 2 * m - 2 * bw, D - 2 * m - 2 * bw), (cx, cy), field),
        ]
        for (sx, sy), (px, py), mat in slabs:
            K.box(K.name("ROOM", "Floor"), (sx, sy, 0.2), (px, py, -0.1), mat, lightmap=True)
        K.collider("Floor", (x0 - 0.5, y0 - 0.5, -0.5), (x1 + 0.5, y1 + 0.5, 0))

    def coffered_ceiling(self, x0, x1, y0, y1, spacing=2.0, beam_d=0.34):
        K, M, H = self.K, self.M, self.H
        W, D, cx, cy = x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2
        K.box(K.name("ROOM", "Ceiling"), (W, D, 0.3), (cx, cy, H + 0.15), M["ceiling"], lightmap=True)
        nx, ny = max(1, round(W / spacing)), max(1, round(D / spacing))
        xs = [x0 + i * W / nx for i in range(1, nx)]
        ys = [y0 + i * D / ny for i in range(1, ny)]
        for x in xs:
            K.box(K.name("ROOM", "Beam"), (0.26, D, beam_d), (x, cy, H - beam_d / 2), M["walnut"], lightmap=True)
            for s in (-1, 1):
                K.sweep(K.name("ROOM", "BeamMoulding"), [(x + s * 0.13, y0, H - beam_d), (x + s * 0.13, y1, H - beam_d)], (s, 0, 0),
                        [(0, 0), (0, 0.02), (0.03, 0.04), (0.06, 0.045), (0.06, 0)], M["gilt"], n1_hint=UPV)
        for y in ys:
            K.box(K.name("ROOM", "Beam"), (W, 0.26, beam_d), (cx, y, H - beam_d / 2 - 0.001), M["walnut"], lightmap=True)
        rosette = self._sconce.get("rosette")
        if rosette is None:
            rosette = self._sconce["rosette"] = K.prototype(K.lathe(K.name("PROP", "Rosette"), [(0, -0.07), (0.05, -0.065), (0.09, -0.04), (0.12, -0.02), (0.13, 0), (0, 0)], (0, 0, -30), M["gilt"], segments=16))
        for x in xs:
            for y in ys:
                K.linked(K.name("PROP", "Rosette"), rosette, (x, y, H - beam_d - 0.001))

    # ------------------------------------------------------------------ chandelier
    def chandelier(self, x, y, scale=1.0, drop=None, point_cd=90, key_cd=None, key=True, tiers=3):
        """Tiered crystal chandelier with S-curved arms and swags; point light + optional shadow key
        placed below the crystal cascade (so it never shadows the floor with itself)."""
        K, M, H, s = self.K, self.M, self.H, scale
        drop = drop if drop is not None else 1.6 * s
        cz = H - drop - 0.6 * s
        K.cyl(K.name("PROP", "ChandelierStem"), 0.03 * s, 0.03 * s, drop, (x, y, H - drop / 2), M["brass"], segments=12)
        K.lathe(K.name("PROP", "ChandelierBody"), [(0, -1.15), (0.12, -1.1), (0.2, -0.9), (0.1, -0.7), (0.18, -0.45), (0.26, -0.15), (0.14, 0.05), (0.06, 0.14), (0.09, 0.3), (0, 0.4)],
                (x, y, cz), M["gilt"], segments=32, scale=s)
        P = self._sconce
        if "crystal" not in P:
            P["crystal"] = K.prototype(K.lathe(K.name("PROP", "Crystal"), [(0, 0), (0.022, 0.03), (0, 0.08)], (0, 0, -30), M["crystal"], segments=6, smooth_angle=None))
            P["pendant"] = K.prototype(K.lathe(K.name("PROP", "CrystalPendant"), [(0, 0), (0.035, 0.05), (0.02, 0.12), (0, 0.16)], (0, 0, -30), M["crystal"], segments=8, smooth_angle=None))
            P["cup"] = K.prototype(K.lathe(K.name("PROP", "CandleCup"), [(0, 0), (0.05, 0.0), (0.06, 0.035), (0.035, 0.06), (0, 0.06)], (0, 0, -30), M["gilt"], segments=14))
            P["candle"] = K.prototype(K.cyl(K.name("PROP", "Candle"), 0.015, 0.015, 0.15, (0, 0, -30), M["shade"], segments=10))
            P["flame"] = K.prototype(K.lathe(K.name("PROP", "Flame"), [(0, 0), (0.014, 0.012), (0.01, 0.035), (0, 0.055)], (0, 0, -30), M["candle"], segments=8))

        def link(key, loc, rot=(0, 0, 0), sc=(1, 1, 1)):
            K.linked(K.name("PROP", P[key].name.split("_")[2]), P[key], tuple(loc), rot=rot, scale=sc)

        spec = ((1.35, -0.55, 16), (0.9, 0.0, 12), (0.5, 0.4, 8))[:tiers]
        for tier, (R, dz, n) in enumerate(spec):
            R, z = R * s, cz + dz * s
            K.torus(K.name("PROP", "ChandelierRing"), R * 0.62, 0.024 * s, (x, y, z - 0.1 * s), M["gilt"], major=64, minor=8)
            for i in range(n):
                a = 2 * math.pi * (i + 0.5 * tier) / n
                ca, sa = math.cos(a), math.sin(a)
                tip = Vector((x + R * ca, y + R * sa, z))
                K.tube(K.name("PROP", "ChandelierArm"), [Vector((x + 0.15 * s * ca, y + 0.15 * s * sa, z - 0.18 * s)),
                                                          Vector((x + R * 0.45 * ca, y + R * 0.45 * sa, z - 0.32 * s)),
                                                          Vector((x + R * 0.85 * ca, y + R * 0.85 * sa, z - 0.2 * s)), tip], 0.014 * s, M["gilt"])
                link("cup", tip)
                link("candle", tip + Vector((0, 0, 0.12)))
                link("flame", tip + Vector((0, 0, 0.195)))
                for k in range(4):
                    link("crystal", tip + Vector((0, 0, -0.1 - k * 0.075)), rot=(math.pi, 0, 0))
                link("pendant", tip + Vector((0, 0, -0.42)), rot=(math.pi, 0, 0))
                a2 = 2 * math.pi * (i + 1 + 0.5 * tier) / n
                for k in range(1, 7):
                    u = k / 7
                    aa = a + (a2 - a) * u
                    sag = math.sin(u * math.pi) * 0.2 * s
                    link("crystal", (x + R * 0.98 * math.cos(aa), y + R * 0.98 * math.sin(aa), z - 0.05 * s - sag), rot=(math.pi, 0, 0))
        for ring in range(8):
            rr = (0.6 - ring * 0.07) * s
            cnt = max(6, round((28 - ring * 3) * s))
            for i in range(cnt):
                a = 2 * math.pi * i / cnt + ring * 0.3
                link("crystal", (x + rr * math.cos(a), y + rr * math.sin(a), cz - (0.95 + ring * 0.1) * s), rot=(math.pi, 0, 0))
        link("pendant", (x, y, cz - 1.85 * s), rot=(math.pi, 0, 0), sc=(1.8, 1.8, 2.2))
        K.light(K.name("LIGHT", "Chandelier"), "POINT", (x, y, cz - 0.5 * s), point_cd, rng=22 * max(s, 0.6))  # electric: steady
        if key:
            K.light(K.name("LIGHT", "ChandelierKey"), "SPOT", (x, y, cz - 2.0 * s), key_cd or point_cd * 1.7, rng=16, shadow=True, angle=2.1, blend=0.9)

    # ------------------------------------------------------------------ furniture
    # red velvet over the bergère's grey upholstery (multiplied → glTF baseColorFactor); the frame darkens to mahogany
    VELVET_TINT = (0.5, 0.07, 0.065)

    def prop(self, pid, key, **kw):
        """A Poly Haven prototype, imported once per zone (kit.import_prop)."""
        if key not in self._props:
            self._props[key] = self.K.import_prop(pid, key, **kw)
        return self._props[key]

    def place(self, key, loc, rz=0.0, scale=1.0, collide=None):
        """Instance a prototype; `collide` = (half-x, half-y, height) for an axis-aligned collider."""
        K = self.K
        p = self._props[key]
        K.linked(K.name("PROP", key), p, loc, rot=(0, 0, rz), scale=(scale,) * 3)
        if collide:
            hx, hy, hz = collide
            if abs(math.sin(rz)) > 0.7:
                hx, hy = hy, hx
            K.collider(f"{key}_{K.idx('c' + key)}", (loc[0] - hx, loc[1] - hy, loc[2]), (loc[0] + hx, loc[1] + hy, loc[2] + hz))

    def club_chair(self, loc, rz):
        """Louis XVI bergère (Poly Haven ArmChair_01, photoscanned) in red velvet; faces local +Y after rz."""
        self.prop("ArmChair_01", "Bergere", tint={"Armchair": self.VELVET_TINT})
        self.place("Bergere", (loc[0], loc[1], 0), rz, collide=(0.42, 0.4, 1.0))

    def dining_chair(self, loc, rz, collide=True):
        """Table seat: the red velvet tub chair (casino.png, poker room). Kept as an alias for call sites."""
        self.tub_chair(loc, rz, collide)

    def _tub_back(self, name):
        """Barrel back of a tub chair: a velvet shell wrapping ~230° with a rolled top and channel tufting."""
        K, M = self.K, self.M
        a, b, cy = 0.3, 0.29, -0.01             # plan ellipse (x, y semi-axes; centre y)
        t0, t1 = math.radians(152), math.radians(388)
        N, T, R = 54, 0.1, 0.045                # arc samples (6 per channel), shell thickness, top-roll radius
        CH = 9                                   # tufted channels
        bm = bmesh.new()
        rings = []
        for i in range(N + 1):
            t = t0 + (t1 - t0) * i / N
            u = (t - math.radians(270)) / math.radians(118)
            h = 0.86 - 0.2 * u * u               # arms low, back high
            P = Vector((a * math.cos(t), cy + b * math.sin(t), 0))
            n = Vector((math.cos(t) / a, math.sin(t) / b, 0)).normalized()
            s_ = i / N
            ripple = 0.018 * (0.5 - 0.5 * math.cos(2 * math.pi * CH * s_))   # channel ridges
            prof = [(0.0, 0.4), (0.0, h - R)]
            for k in range(1, 8):
                ph = math.pi * k / 8
                prof.append((R - R * math.cos(ph), h - R + R * math.sin(ph)))
            prof += [(T - ripple, h - R), (T - ripple * 0.6, 0.62), (T + 0.03, 0.43)]  # tucks in behind the cushion
            rings.append([bm.verts.new(P - n * d + Vector((0, 0, z))) for d, z in prof])
        for i in range(N):
            for j in range(len(rings[0]) - 1):
                bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j + 1], rings[i][j + 1]))
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return K.obj(name, bm, M["velvet"], smooth_angle=80)

    @staticmethod
    def _loft(K, name, mat, a, b, cy, levels, cap_top=True, seg=48, **kw):
        """Closed elliptical loft: levels = [(z, scale), ...] bottom → top."""
        bm = bmesh.new()
        rings = []
        for z, sc in levels:
            rings.append([bm.verts.new((a * sc * math.cos(2 * math.pi * k / seg), cy + b * sc * math.sin(2 * math.pi * k / seg), z)) for k in range(seg)])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(seg):
                bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]))
        bm.faces.new(list(reversed(rings[0])))
        if cap_top:
            bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return K.obj(name, bm, mat, **kw)

    def tub_chair(self, loc, rz, collide=True):
        """Red velvet tub chair: barrel back with channel tufting, domed cushion, walnut plinth, turned legs.
        Faces local +Y after rz; seat height 0.49 m."""
        K, M, C = self.K, self.M, self._dining
        if not C:
            C["back"] = K.prototype(self._tub_back(K.name("CHAIR", "TubBack")))
            C["body"] = K.prototype(self._loft(K, K.name("CHAIR", "TubBody"), M["velvet"], 0.3, 0.29, -0.01,
                                               [(0.15, 0.93), (0.17, 1.0), (0.37, 1.0), (0.395, 0.97), (0.4, 0.93)], seg=40, smooth_angle=80))
            C["plinth"] = K.prototype(self._loft(K, K.name("CHAIR", "TubPlinth"), M["walnut_dark"], 0.305, 0.295, -0.01,
                                                 [(0.12, 1.0), (0.155, 1.02), (0.165, 0.99)], seg=40, smooth_angle=60))
            C["cushion"] = K.prototype(self._loft(K, K.name("CHAIR", "TubCushion"), M["velvet"], 0.24, 0.245, 0.025,
                                                  [(0.4, 1.0), (0.44, 1.02), (0.465, 1.02), (0.482, 0.97), (0.492, 0.84), (0.497, 0.45)], seg=40, smooth_angle=80))
            C["leg"] = K.prototype(K.lathe(K.name("CHAIR", "TubLeg"), [(0, 0), (0.016, 0), (0.02, 0.02), (0.026, 0.06), (0.03, 0.1), (0.034, 0.125), (0, 0.125)],
                                           (0, 0, -30), M["walnut_dark"], segments=12))
            C["cap"] = K.prototype(K.cyl(K.name("CHAIR", "TubLegCap"), 0.017, 0.017, 0.012, (0, 0, -30), M["brass"], segments=10))
        c, s = math.cos(rz), math.sin(rz)

        def at(dx, dy, dz):
            return (loc[0] + dx * c - dy * s, loc[1] + dx * s + dy * c, dz)
        for key in ("back", "body", "plinth", "cushion"):
            K.linked(K.name("CHAIR", C[key].name.split("_")[2]), C[key], at(0, 0, 0), rot=(0, 0, rz))
        for dx, dy in ((-0.21, -0.2), (0.21, -0.2), (-0.21, 0.18), (0.21, 0.18)):
            K.linked(K.name("CHAIR", "TubLeg"), C["leg"], at(dx, dy, 0))
            K.linked(K.name("CHAIR", "TubLegCap"), C["cap"], at(dx, dy, 0.006))
        if collide:
            K.collider(f"Chair_{K.idx('chair')}", (loc[0] - 0.3, loc[1] - 0.3, 0), (loc[0] + 0.3, loc[1] + 0.3, 0.9))

    def rug(self, tag, cx, cy, length, width, rz, stem, fringe=True):
        """A real carpet (scripts/make-carpets.mjs → textures_src/carpets/T_<stem>_*): 1 cm pile slab with
        the photographed design on top (u across, v along) and knotted-wool fringes at both ends."""
        K, M = self.K, self.M
        key = f"rug_{stem}"
        if key not in M:
            base = os.path.join(kit.ROOT, "blender", "textures_src", "carpets", f"T_{stem}")
            K.material(key, f"MAT_{K.zone}_{stem.replace('_', '')}", (1, 1, 1), 1.0, sheen=0.3, sheen_tint=RUG_SHEEN,
                       base_tex=base + "_BaseColor.png", normal_tex=base + "_Normal.png", orm_tex=base + "_ORM.png", extension="EXTEND")
        if "fringe" not in M:
            K.material("fringe", f"MAT_{K.zone}_RugFringe", (0.5, 0.44, 0.33), 0.95, sheen=0.2)
        c, s = math.cos(rz), math.sin(rz)
        W, L, H = width / 2, length / 2, 0.011
        bm = bmesh.new()
        uv = bm.loops.layers.uv.verify()

        def P(x, y, z):
            return Vector((cx + x * c - y * s, cy + x * s + y * c, z))
        top = [bm.verts.new(P(x, y, H)) for x, y in ((-W, -L), (W, -L), (W, L), (-W, L))]
        bot = [bm.verts.new(P(x * 1.002, y * 1.002, 0.0005)) for x, y in ((-W, -L), (W, -L), (W, L), (-W, L))]
        f = bm.faces.new(top)
        for loop, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = (u, v)
        for k in range(4):  # sides take the edge texels (the dyed selvedge)
            f = bm.faces.new((bot[k], bot[(k + 1) % 4], top[(k + 1) % 4], top[k]))
            e = ((0, 0), (1, 0), (1, 1), (0, 1))
            for loop, idx in zip(f.loops, (k, (k + 1) % 4, (k + 1) % 4, k)):
                loop[uv].uv = e[idx]
        ob = K.obj(K.name("PROP", tag), bm, M[key], uv=None, lightmap=True)
        if fringe:
            fb = bmesh.new()
            n = int(width / 0.008)
            rnd = np.random.default_rng(sum(map(ord, tag)))  # deterministic (hash() is salted per run)
            for end in (-1, 1):
                for k in range(n):
                    x = -W + (k + 0.5) * width / n
                    ln = 0.055 + rnd.random() * 0.02
                    dx = (rnd.random() - 0.5) * 0.012
                    y0, y1 = end * L, end * (L + ln)
                    q = [fb.verts.new(P(x + ox, y, z)) for (ox, y, z) in
                         ((-0.0016, y0, H * 0.6), (0.0016, y0, H * 0.6), (0.0016 + dx, y1, 0.0015), (-0.0016 + dx, y1, 0.0015))]
                    fb.faces.new(q if end > 0 else list(reversed(q)))
            K.obj(K.name("PROP", f"{tag}Fringe"), fb, M["fringe"])   # box UV0 in metres (§6: every mesh has UV0)
        return ob

    def lamp_table(self, x, y, candela=7):
        """Mahogany pedestal stand with an antique oil lamp (both photoscanned); warm bake-only light."""
        self.prop("side_table_tall_01", "Pedestal")
        self.prop("vintage_oil_lamp", "OilLamp", scale=0.72)
        self.place("Pedestal", (x, y, 0), collide=(0.2, 0.2, 0.8))
        self.place("OilLamp", (x, y, 0.762))
        self.K.light(self.K.name("LIGHT", "Lamp"), "POINT", (x, y, 0.762 + 0.3), candela, rng=6, bake_only=True)

    def table_lamp(self, x, y, z, candela=7):
        K, M = self.K, self.M
        K.lathe(K.name("PROP", "LampBase"), [(0, 0), (0.09, 0), (0.1, 0.03), (0.05, 0.08), (0.07, 0.2), (0.03, 0.3), (0.015, 0.44), (0, 0.44)], (x, y, z), M["brass"], segments=20)
        K.lathe(K.name("PROP", "LampShade"), [(0.22, 0), (0.12, 0.26)], (x, y, z + 0.335), M["shade"], segments=32)
        K.light(K.name("LIGHT", "Lamp"), "POINT", (x, y, z + 0.49), candela, rng=6, bake_only=True)

    def console(self, x, y, rz, lamp=True):
        """Marble-topped console table against a wall (long axis along local X)."""
        K, M = self.K, self.M
        c, s = math.cos(rz), math.sin(rz)
        size = (1.5, 0.44) if abs(s) < 0.5 else (0.44, 1.5)
        K.box(K.name("TABLE", "Console"), (size[0] + 0.1, size[1] + 0.06, 0.06), (x, y, 0.86), M["nero"], bevel=0.01)
        K.box(K.name("TABLE", "Console"), (size[0], size[1], 0.16), (x, y, 0.76), M["walnut"], bevel=0.01)
        for d in (-0.62, 0.62):
            K.lathe(K.name("TABLE", "ConsoleLeg"), [(0, 0), (0.04, 0), (0.03, 0.2), (0.045, 0.5), (0.03, 0.68), (0, 0.68)], (x + d * c, y + d * s, 0), M["gilt"], segments=12)
        K.collider(f"Console_{K.idx('console')}", (x - size[0] / 2 - 0.05, y - size[1] / 2 - 0.05, 0), (x + size[0] / 2 + 0.05, y + size[1] / 2 + 0.05, 0.9))
        if lamp:
            self.table_lamp(x + 0.4 * c, y + 0.4 * s, 0.89)

    def audio(self, what, loc, sound, gain=0.5, mode="random", interval=(6, 14)):
        """AUDIO_ emitter (→ runtime SoundEmitterDef)."""
        e = self.K.empty(self.K.name("AUDIO", what), loc, kind="SPHERE", size=0.15)
        e["sound"] = sound
        e["gain"] = gain
        e["mode"] = mode
        if mode == "random":
            e["intervalMin"], e["intervalMax"] = interval
        return e

    def logic(self, spawn=None, probe=(0, 0, 1.7), bounds=None):
        K = self.K
        if spawn is not None:
            K.empty(f"SPAWN_{K.zone}_Main", spawn[0], kind="SINGLE_ARROW", rot=spawn[1])
        K.empty(f"PROBE_{K.zone}_Main", probe, coll="PROBES", kind="SPHERE")
        (x0, y0, z0), (x1, y1, z1) = bounds
        trig = K.obj(f"TRIGGER_{K.zone}_Bounds", kit.cube_bm(x1 - x0, y1 - y0, z1 - z0), None, coll="LOGIC",
                     loc=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), uv=None)
        trig.display_type = "WIRE"
        trig.hide_render = True


def save(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()
    print(f"[author] wrote {path}: {len(bpy.data.objects)} objects, {len(bpy.data.materials)} materials, "
          f"{sum(1 for o in bpy.data.objects if o.get('lightmap'))} lightmapped")
