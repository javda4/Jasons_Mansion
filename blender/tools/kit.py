"""Shared Blender authoring kit for Riviera zones (Layer 1).

Geometry helpers that produce export-ready objects following CLAUDE.md §6: metre-scale UVs on UV0,
named objects in ZONE_<Zone> › VISUAL/COLLISION/LOGIC/LIGHTS/PROBES collections, linked duplicates
for repeated props (→ GPU instancing), lights in physical units, custom properties → glTF extras.

    import kit
    K = kit.Zone("Lobby")
    K.box("ROOM_Lobby_Floor", (16, 24, 0.2), (0, 8, -0.1), K.mat["marble"], lightmap=True)
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB_TEX = os.path.join(ROOT, "blender", "textures_src", "polyhaven")
FONT = os.path.join(ROOT, "blender", "fonts", "Cinzel.ttf")
UP = Vector((0, 0, 1))


def watts(candela: float) -> float:
    """Blender light power for a runtime intensity (exporter SPEC mode: cd = W / 4π × 683)."""
    return candela * 4 * math.pi / 683


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0
    world = bpy.data.worlds.new("World")
    world.color = (0, 0, 0)
    s.world = world


# ----------------------------------------------------------------------------- UV helpers

def box_uv(bm, offset=Vector()):
    """Box-map UV0 in metres (world-aligned when offset = object location)."""
    uv = bm.loops.layers.uv.verify()
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            c = loop.vert.co + offset
            loop[uv].uv = (c.y, c.z) if ax == 0 else (c.x, c.z) if ax == 1 else (c.x, c.y)


def cube_bm(sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    return bm


# ----------------------------------------------------------------------------- zone context

class Zone:
    def __init__(self, zone: str):
        self.zone = zone
        root = bpy.data.collections.new(f"ZONE_{zone}")
        bpy.context.scene.collection.children.link(root)
        self.coll = {}
        for sub in ("VISUAL", "COLLISION", "LOGIC", "LIGHTS", "PROBES"):
            c = bpy.data.collections.new(f"{sub}_{zone}")
            root.children.link(c)
            self.coll[sub] = c
        self.wip = bpy.data.collections.new(f"_WIP_{zone}")
        root.children.link(self.wip)
        self.mat = {}
        self._n = {}

    # ---- naming
    def idx(self, key: str) -> str:
        self._n[key] = self._n.get(key, 0) + 1
        n = self._n[key]
        return f"{n:02d}" if n < 100 else f"{n // 100:02d}_{n % 100:02d}"

    def name(self, prefix: str, what: str) -> str:
        return f"{prefix}_{self.zone}_{what}_{self.idx(prefix + what)}"

    # ---- materials
    def material(self, key, name, base=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, coat=0.0, coat_rough=0.03, sheen=0.0,
                 lib=None, base_tex=None, emis_tex=None, emis_color=None, emis_strength=0.0, alpha=1.0,
                 normal_tex=None, orm_tex=None, normal_strength=1.0, extension="REPEAT", sheen_tint=None):
        m = bpy.data.materials.new(name)
        if bpy.app.version < (5, 0, 0):
            m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*base, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_rough
        b.inputs["Sheen Weight"].default_value = sheen
        # Blender's default sheen tint is white → a white film over dyed fibres once exported (KHR_materials_sheen)
        b.inputs["Sheen Tint"].default_value = (*(sheen_tint or base), 1)
        if lib:  # viewport preview for library materials; stripped by the asset build
            stem = os.path.join(LIB_TEX, f"T_{lib}")
            if os.path.exists(stem + "_BaseColor.jpg"):
                t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-500, 300)
                t.image = bpy.data.images.load(stem + "_BaseColor.jpg", check_existing=True)
                nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
            if os.path.exists(stem + "_Normal.jpg"):
                t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-700, -300)
                t.image = bpy.data.images.load(stem + "_Normal.jpg", check_existing=True)
                t.image.colorspace_settings.name = "Non-Color"
                nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-300, -300)
                nt.links.new(t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        if base_tex:
            t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-500, 300)
            t.image = bpy.data.images.load(base_tex, check_existing=True)
            t.extension = extension
            nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if normal_tex:  # exported as the glTF normalTexture
            t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-700, -350)
            t.image = bpy.data.images.load(normal_tex, check_existing=True)
            t.image.colorspace_settings.name = "Non-Color"
            t.extension = extension
            nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-300, -350)
            nm.inputs["Strength"].default_value = normal_strength
            nt.links.new(t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        if orm_tex:  # G → roughness, B → metallic: exported as one glTF metallicRoughnessTexture
            t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-800, 0)
            t.image = bpy.data.images.load(orm_tex, check_existing=True)
            t.image.colorspace_settings.name = "Non-Color"
            t.extension = extension
            sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-450, 0)
            nt.links.new(t.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], b.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
        if emis_tex:
            t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-500, -100)
            t.image = bpy.data.images.load(emis_tex, check_existing=True)
            nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        if emis_color:
            b.inputs["Emission Color"].default_value = (*emis_color, 1)
        if emis_tex or emis_color:
            b.inputs["Emission Strength"].default_value = emis_strength
        if alpha < 1.0:  # exported as alphaMode BLEND (glass, veils)
            b.inputs["Alpha"].default_value = alpha
            m.surface_render_method = "BLENDED"
        self.mat[key] = m
        return m

    # ---- object creation
    def obj(self, name, bm_or_mesh, mat, coll="VISUAL", loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, segments=2,
            subsurf=0, smooth_angle=None, uv="box", lightmap=False):
        if isinstance(bm_or_mesh, bmesh.types.BMesh):
            if uv == "box":
                box_uv(bm_or_mesh, Vector(loc))
            me = bpy.data.meshes.new(name)
            bm_or_mesh.to_mesh(me)
            bm_or_mesh.free()
        else:
            me = bm_or_mesh
            me.name = name
        ob = bpy.data.objects.new(name, me)
        ob.location, ob.rotation_euler = loc, rot
        if mat:
            me.materials.clear()
            me.materials.append(mat)
        self.coll[coll].objects.link(ob)
        if smooth_angle is not None or bevel or subsurf:
            for p in me.polygons:
                p.use_smooth = True
            if smooth_angle is not None and hasattr(me, "set_sharp_from_angle"):
                me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        if bevel:
            m = ob.modifiers.new("Bevel", "BEVEL")
            m.width, m.segments, m.limit_method = bevel, segments, "ANGLE"
            m.harden_normals = not subsurf
        if subsurf:
            m = ob.modifiers.new("Subdivision", "SUBSURF")
            m.levels = m.render_levels = subsurf
        if lightmap:
            ob["lightmap"] = True  # consumed by bake_lightmap.py (not exported: stripped before export)
        return ob

    def box(self, name, size, loc, mat, **kw):
        return self.obj(name, cube_bm(*size), mat, loc=loc, **kw)

    def cyl(self, name, r1, r2, h, loc, mat, segments=24, rot=(0, 0, 0), **kw):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r1, radius2=r2, depth=h)
        kw.setdefault("smooth_angle", 40)
        return self.obj(name, bm, mat, loc=loc, rot=rot, **kw)

    def lathe(self, name, profile, loc, mat, segments=32, rot=(0, 0, 0), scale=1.0, **kw):
        """Revolve [(radius, z), ...] around local Z."""
        bm = bmesh.new()
        verts = [bm.verts.new((r * scale, 0, z * scale)) for r, z in profile]
        edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
        bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=segments, use_merge=True)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        kw.setdefault("smooth_angle", 50)
        return self.obj(name, bm, mat, loc=loc, rot=rot, **kw)

    def torus(self, name, R, r, loc, mat, major=48, minor=10, rot=(0, 0, 0), arc=2 * math.pi, **kw):
        bm = bmesh.new()
        closed = abs(arc - 2 * math.pi) < 1e-6
        n_major = major if closed else major + 1
        rings = []
        for i in range(n_major):
            a = arc * i / major
            rings.append([bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
                          for b in (2 * math.pi * j / minor for j in range(minor))])
        for i in range(major):
            i2 = (i + 1) % n_major
            for j in range(minor):
                bm.faces.new((rings[i][j], rings[i2][j], rings[i2][(j + 1) % minor], rings[i][(j + 1) % minor]))
        return self.obj(name, bm, mat, loc=loc, rot=rot, smooth_angle=60, **kw)

    def linked(self, name, src, loc, rot=(0, 0, 0), scale=(1, 1, 1), coll="VISUAL"):
        """Linked duplicate: shares mesh data → one GPU-instanced draw after the asset build."""
        ob = bpy.data.objects.new(name, src.data)
        ob.location, ob.rotation_euler, ob.scale = loc, rot, scale
        for m in src.modifiers:
            n = ob.modifiers.new(m.name, m.type)
            for attr in ("width", "segments", "limit_method", "harden_normals", "levels", "render_levels"):
                if hasattr(m, attr):
                    setattr(n, attr, getattr(m, attr))
        self.coll[coll].objects.link(ob)
        return ob

    def join_into(self, target, parts):
        """Bake modifiers and merge child parts into `target` (one node, multi-material mesh).
        Needed for anything that moves as a unit (door leaves): the pipeline flattens hierarchies."""
        dg = bpy.context.evaluated_depsgraph_get()
        for o in [target, *parts]:
            if o.modifiers:
                me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
                o.modifiers.clear()
                o.data = me
        bpy.ops.object.select_all(action="DESELECT")
        for o in [target, *parts]:
            o.select_set(True)
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.join()
        # baked-modifier meshes come back as "<name>.001" while the orphaned original still holds the name;
        # instance nodes take the mesh name, so free it and rename
        stale = bpy.data.meshes.get(target.name)
        if stale is not None and stale is not target.data and stale.users == 0:
            bpy.data.meshes.remove(stale)
        target.data.name = target.name
        return target

    def import_prop(self, pid, key, pick=None, scale=1.0, origin="base", tint=None, face="+Y", decimate=None):
        """Import a Poly Haven model (scripts/fetch-models.mjs) as ONE instanceable prototype.

        - `pick`: keep only mesh objects whose name contains one of these substrings
        - rotated so its front faces local +Y (our furniture convention), origin at the base centre
          ("base") or the back centre ("back", for wall-hung pieces), scale applied to the mesh
        - materials renamed MAT_<Key>_<Part> (the key names the surface); glass loses transmission (an extra render pass
          at runtime) and becomes alpha-blended; `tint={substring: (r, g, b)}` multiplies a base colour
          (exported as baseColorFactor); `decimate` = collapse ratio for dense scans
        Place copies with K.linked(K.name("PROP", key), proto, loc, rot) → GPU instances after the build.
        """
        path = os.path.join(ROOT, "blender", "props", "polyhaven", pid, f"{pid}.gltf")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH" and (not pick or any(p in o.name for p in pick))]
        for o in new:
            if o not in meshes:
                bpy.data.objects.remove(o, do_unlink=True)
        for o in meshes:  # bake transforms into the data, drop parents
            o.data = o.data.copy() if o.data.users > 1 else o.data
            o.data.transform(o.matrix_world)
            o.parent = None
            o.matrix_world = Matrix.Identity(4)
        target = meshes[0]
        if len(meshes) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for o in meshes:
                o.select_set(True)
            bpy.context.view_layer.objects.active = target
            bpy.ops.object.join()
        if decimate:  # scans can be dense for a real-time budget: collapse-decimate once, on the prototype
            mod = target.modifiers.new("Decimate", "DECIMATE")
            mod.ratio = decimate
            dg = bpy.context.evaluated_depsgraph_get()
            dense = target.data
            target.data = bpy.data.meshes.new_from_object(target.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            target.modifiers.clear()
            if dense.users == 0:
                bpy.data.meshes.remove(dense)
        me = target.data
        rot = {"+Y": Matrix.Rotation(math.pi, 4, "Z"), "-Y": Matrix.Identity(4)}[face]
        me.transform(rot @ Matrix.Scale(scale, 4))
        xs = [v.co for v in me.vertices]
        lo = Vector((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)))
        hi = Vector((max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))
        if origin == "base":
            me.transform(Matrix.Translation(Vector(((lo.x + hi.x) / -2, (lo.y + hi.y) / -2, -lo.z))))
        else:  # back: wall-hung, the back plane at y = 0, centred in x and z
            me.transform(Matrix.Translation(Vector(((lo.x + hi.x) / -2, -lo.y, (lo.z + hi.z) / -2))))
        name = self.name("PROP", key)
        target.name = name
        me.name = name
        for slot in target.material_slots:
            m = slot.material
            if m is None or m.name.startswith("MAT_"):
                continue
            part = m.name.replace(pid, "").strip("_- ")
            part = "".join(w.capitalize() for w in part.replace("-", "_").split("_") if w)
            b = m.node_tree.nodes.get("Principled BSDF")
            if b is not None and b.inputs["Transmission Weight"].default_value > 0:
                b.inputs["Transmission Weight"].default_value = 0
                b.inputs["Alpha"].default_value = 0.22
                b.inputs["Roughness"].default_value = 0.04
                m.surface_render_method = "BLENDED"
            for sub, rgb in (tint or {}).items():
                if sub in m.name and b is not None and b.inputs["Base Color"].is_linked:
                    src = b.inputs["Base Color"].links[0].from_socket
                    mix = m.node_tree.nodes.new("ShaderNodeMix")
                    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
                    mix.inputs["Factor"].default_value = 1.0
                    m.node_tree.links.new(src, mix.inputs[6])
                    mix.inputs[7].default_value = (*rgb, 1)
                    m.node_tree.links.new(mix.outputs[2], b.inputs["Base Color"])
            if part and part[0].isdigit():
                part = "Main" + part
            m.name = f"MAT_{key}_{part or 'Main'}"          # MAT_<Surface>_<Variant> (§6)
        for c in list(target.users_collection):
            c.objects.unlink(target)
        self.wip.objects.link(target)
        target["dims"] = [hi.x - lo.x, hi.y - lo.y, hi.z - lo.z]
        return target

    def import_pack(self, path, key, pick=None, scale=1.0, rz=0.0):
        """Import a licensed pack model (blender/props/kraffing/<Name>.glb) as ONE instanceable prototype.

        Unlike import_prop the pack's own origin is kept (floor centre of the piece), so separately imported
        parts of one model (a roulette table and its wheel) stay registered to each other. `rz` turns the
        model so its player side matches our convention and `scale` brings it to real-world size; both are
        baked into the mesh. `pick` keeps only mesh objects whose name starts with one of the prefixes (the
        pack's bar stools, loose coins and cards are dropped — the runtime deals real cards and chips).
        Materials become MAT_Kraffing_<Name> (§6), shared between parts imported into one zone.
        """
        before = set(bpy.data.objects)
        mats_before = set(bpy.data.materials)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH" and (not pick or any(o.name.startswith(p) for p in pick))]
        for o in new:
            if o not in meshes:
                bpy.data.objects.remove(o, do_unlink=True)
        for o in meshes:
            o.data = o.data.copy() if o.data.users > 1 else o.data
            o.data.transform(o.matrix_world)
            o.parent = None
            o.matrix_world = Matrix.Identity(4)
        target = meshes[0]
        if len(meshes) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for o in meshes:
                o.select_set(True)
            bpy.context.view_layer.objects.active = target
            bpy.ops.object.join()
        target.data.transform(Matrix.Rotation(rz, 4, "Z") @ Matrix.Scale(scale, 4))
        name = self.name("PROP", key)
        target.name = target.data.name = name
        for slot in target.material_slots:
            m = slot.material
            if m is None or m.name.startswith("MAT_"):
                continue
            stem = m.name.split(".")[0].removeprefix("TX_")
            want = "MAT_Kraffing_" + "".join(w[:1].upper() + w[1:] for w in stem.replace("-", "_").split("_") if w)
            have = bpy.data.materials.get(want)
            if have is not None and have is not m:
                slot.material = have           # the same pack material, already imported with another part
            else:
                m.name = want
        for m in [m for m in bpy.data.materials if m not in mats_before and m.users == 0]:
            bpy.data.materials.remove(m)
        for c in list(target.users_collection):
            c.objects.unlink(target)
        self.wip.objects.link(target)
        return target

    def prototype(self, ob):
        """Move a linked-duplicate source into _WIP so only its copies export."""
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        self.wip.objects.link(ob)
        return ob

    # ---- swept mouldings
    def sweep(self, name, path, plane_normal, profile, mat, closed=False, flip=False, n1_hint=None, **kw):
        """Sweep a 2D profile [(a, b), ...] along a planar polyline.

        a = offset in the path plane perpendicular to the path (N1), b = offset along plane_normal (N2).
        Corners are mitred. UV0: u = distance along the path, v = distance along the profile (metres).
        """
        pts = [Vector(p) for p in path]
        n2 = Vector(plane_normal).normalized()
        count = len(pts)
        seg_t = []
        for i in range(count - (0 if closed else 1)):
            seg_t.append((pts[(i + 1) % count] - pts[i]).normalized())

        if n1_hint is not None:  # orient profile 'a' along the hint (e.g. up, or away from an opening)
            flip = n2.cross(seg_t[0]).normalized().dot(Vector(n1_hint)) < 0

        def n1_of(t):
            v = n2.cross(t).normalized()
            return -v if flip else v

        frames = []
        for i in range(count):
            if closed:
                t_in, t_out = seg_t[i - 1], seg_t[i % len(seg_t)]
            else:
                t_in = seg_t[max(0, i - 1)]
                t_out = seg_t[min(i, len(seg_t) - 1)]
            a_in, a_out = n1_of(t_in), n1_of(t_out)
            n1 = (a_in + a_out).normalized()
            scale = 1.0 / max(0.2, n1.dot(a_out))
            frames.append((pts[i], n1 * scale))

        bm = bmesh.new()
        uv = bm.loops.layers.uv.verify()
        rings = [[bm.verts.new(p + n1 * a + n2 * b) for (a, b) in profile] for p, n1 in frames]
        prof_len = [0.0]
        for k in range(1, len(profile)):
            prof_len.append(prof_len[-1] + math.dist(profile[k], profile[k - 1]))
        path_len = [0.0]
        for i in range(1, count):
            path_len.append(path_len[-1] + (pts[i] - pts[i - 1]).length)
        if closed:
            path_len.append(path_len[-1] + (pts[0] - pts[-1]).length)
        n_seg = count if closed else count - 1
        for i in range(n_seg):
            r0, r1 = rings[i], rings[(i + 1) % count]
            u0, u1 = path_len[i], path_len[i + 1]
            for k in range(len(profile) - 1):
                f = bm.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
                for loop, (u, v) in zip(f.loops, ((u0, prof_len[k]), (u1, prof_len[k]), (u1, prof_len[k + 1]), (u0, prof_len[k + 1]))):
                    loop[uv].uv = (u, v)
        if not closed:
            for ring in (rings[0], rings[-1]):
                try:
                    f = bm.faces.new(ring)
                    for loop in f.loops:
                        loop[uv].uv = (0, 0)
                except ValueError:
                    pass
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        kw.setdefault("smooth_angle", 35)
        return self.obj(name, bm, mat, uv=None, **kw)

    def frame(self, name, center, width, height, wall_normal, profile, mat, **kw):
        """Rectangular moulded frame on a wall (profile a = inward, b = out of the wall)."""
        n = Vector(wall_normal).normalized()
        right = UP.cross(n).normalized()
        c = Vector(center)
        hw, hh = width / 2, height / 2
        path = [c - right * hw - UP * hh, c + right * hw - UP * hh, c + right * hw + UP * hh, c - right * hw + UP * hh]
        return self.sweep(name, path, n, profile, mat, closed=True, **kw)

    # ---- curves & text → mesh
    def tube(self, name, points, radius, mat, bezier=True, resolution=12, bevel_res=4, **kw):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = radius
        cu.bevel_resolution = bevel_res
        cu.resolution_u = resolution
        cu.use_fill_caps = True
        sp = cu.splines.new("BEZIER" if bezier else "POLY")
        if bezier:
            sp.bezier_points.add(len(points) - 1)
            for bp, p in zip(sp.bezier_points, points):
                bp.co = p
                bp.handle_left_type = bp.handle_right_type = "AUTO"
        else:
            sp.points.add(len(points) - 1)
            for sp_p, p in zip(sp.points, points):
                sp_p.co = (*p, 1)
        return self._curve_to_mesh(name, cu, mat, **kw)

    def text(self, name, body, size, mat, extrude=0.004, align="CENTER", resolution=6, **kw):
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = body
        if os.path.exists(FONT):
            cu.font = bpy.data.fonts.load(FONT, check_existing=True)
        cu.size = size
        cu.extrude = extrude
        cu.align_x = align
        cu.align_y = "CENTER"
        cu.resolution_u = resolution
        return self._curve_to_mesh(name, cu, mat, **kw)

    def _curve_to_mesh(self, name, cu, mat, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
        tmp = bpy.data.objects.new(name + "_tmp", cu)
        bpy.context.scene.collection.objects.link(tmp)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        bpy.data.objects.remove(tmp)
        bpy.data.curves.remove(cu)
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        kw.setdefault("smooth_angle", 40)
        return self.obj(name, bm, mat, loc=loc, rot=rot, **kw)

    # ---- fluted column shaft
    def fluted_shaft(self, name, radius, height, loc, mat, flutes=20, depth=0.018, entasis=0.06, rings=12, **kw):
        bm = bmesh.new()
        seg = flutes * 6
        layers = []
        for r in range(rings + 1):
            t = r / rings
            scale = 1 - entasis * t ** 1.5
            z = height * t
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                flute = max(0.0, math.cos(flutes * a)) ** 2
                rr = (radius - depth * flute) * scale
                ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
            layers.append(ring)
        for r in range(rings):
            for k in range(seg):
                bm.faces.new((layers[r][k], layers[r][(k + 1) % seg], layers[r + 1][(k + 1) % seg], layers[r + 1][k]))
        bm.faces.new(list(reversed(layers[0])))
        bm.faces.new(layers[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self.obj(name, bm, mat, loc=loc, smooth_angle=50, **kw)

    # ---- logic & lights
    def collider(self, what, lo, hi):
        size = [hi[i] - lo[i] for i in range(3)]
        loc = [(hi[i] + lo[i]) / 2 for i in range(3)]
        ob = self.obj(f"COLLIDER_{self.zone}_{what}", cube_bm(*size), None, coll="COLLISION", loc=loc, uv=None)
        ob.display_type = "WIRE"
        ob.hide_render = True
        return ob

    def empty(self, name, loc, coll="LOGIC", rot=(0, 0, 0), kind="PLAIN_AXES", size=0.3):
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_type, ob.empty_display_size = kind, size
        ob.location, ob.rotation_euler = loc, rot
        self.coll[coll].objects.link(ob)
        return ob

    def light(self, name, kind, loc, candela, color=(1.0, 0.69, 0.44), rng=6.0, bake_only=False, shadow=False,
              flicker=False, angle=None, blend=0.8, rot=(0, 0, 0)):
        lt = bpy.data.lights.new(name, kind)
        lt.energy = watts(candela)
        lt.color = color
        lt.shadow_soft_size = 0.06
        lt.use_custom_distance = True
        lt.cutoff_distance = rng
        if kind == "SPOT":
            lt.spot_size = angle or math.radians(90)
            lt.spot_blend = blend
        ob = bpy.data.objects.new(name, lt)
        ob.location, ob.rotation_euler = loc, rot
        if bake_only:
            ob["bakeOnly"] = True
        if shadow:
            ob["castShadow"] = True
        if flicker:
            ob["flicker"] = True
        self.coll["LIGHTS"].objects.link(ob)
        return ob


# ----------------------------------------------------------------------------- procedural images

def save_image(path, rgba: np.ndarray):
    h, w, _ = rgba.shape
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    img.pixels.foreach_set(np.clip(rgba, 0, 1).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def blur(a, r):
    for axis in (0, 1):
        acc = np.zeros_like(a)
        for k in range(-r, r + 1):
            acc += np.roll(a, k, axis=axis)
        a = acc / (2 * r + 1)
    return a
