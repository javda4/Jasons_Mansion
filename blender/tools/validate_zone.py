"""Validate a zone .blend against the naming / authoring contract before export.

Usage (headless):
    blender -b blender/rooms/<zone>/<zone>.blend --python blender/tools/validate_zone.py -- <Zone>
Exits non-zero when there are errors. Also imported by export_zone.py.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import conventions as C  # noqa: E402


def _collections_of(obj):
    names = [c.name for c in obj.users_collection]
    # include ancestors so a _WIP parent excludes its children
    for coll in bpy.data.collections:
        for child in coll.children_recursive:
            if child.name in names:
                names.append(coll.name)
    return names


def exported_objects():
    return [o for o in bpy.data.objects if o.users_scene and not C.is_excluded(_collections_of(o))]


def validate(zone: str):
    errors, warnings = [], []
    objs = exported_objects()
    if not objs:
        errors.append("nothing to export")

    seen_logic = {"TRIGGER": 0, "SPAWN": 0, "PROBE": 0, "COLLIDER": 0}
    tri_count = 0
    for o in objs:
        info = C.parse_name(o.name)
        if not info:
            errors.append(f"{o.name}: name does not match PREFIX_Zone_Name[_NN] (§6)")
            continue
        prefix = info["prefix"]
        if info["zone"] != zone:
            errors.append(f"{o.name}: zone segment '{info['zone']}' != '{zone}'")
        if prefix in seen_logic:
            seen_logic[prefix] += 1

        if o.type == "MESH" and prefix not in C.MESH_PREFIXES:
            errors.append(f"{o.name}: a mesh cannot use prefix {prefix}_")
        if o.type == "EMPTY" and prefix not in C.EMPTY_PREFIXES:
            errors.append(f"{o.name}: an empty cannot use prefix {prefix}_")
        if o.type == "LIGHT" and prefix not in C.LIGHT_PREFIXES:
            errors.append(f"{o.name}: lights must be named LIGHT_…")
        if o.type == "LIGHT" and o.data.type not in {"POINT", "SPOT"}:
            errors.append(f"{o.name}: only POINT and SPOT lights are supported at runtime")

        if o.type == "MESH":
            if any(abs(s - 1.0) > 1e-4 for s in o.scale) and prefix in {"COLLIDER", "TRIGGER", "ROOM"}:
                errors.append(f"{o.name}: apply scale (Ctrl+A) — {prefix}_ objects must have scale 1")
            if prefix in {"COLLIDER", "TRIGGER", "INTERACT"}:
                if o.material_slots and any(s.material for s in o.material_slots):
                    warnings.append(f"{o.name}: {prefix}_ meshes should have no materials (never rendered)")
                rot = o.rotation_euler
                if prefix == "INTERACT":
                    continue
                if abs(rot.x) > 1e-4 or abs(rot.y) > 1e-4 or abs((rot.z / 1.5707963) - round(rot.z / 1.5707963)) > 1e-4:
                    errors.append(f"{o.name}: collision/trigger boxes must be axis-aligned (Z rotations in 90° steps only)")
            else:
                if not o.data.uv_layers:
                    errors.append(f"{o.name}: missing UV map (UV0)")
                for slot in o.material_slots:
                    m = slot.material
                    if m is None:
                        errors.append(f"{o.name}: empty material slot")
                    elif not C.MATERIAL_RE.match(m.name):
                        errors.append(f"{o.name}: material '{m.name}' must be named MAT_<Surface>_<Variant> (no .001 copies)")
                mesh = o.data
                mesh.calc_loop_triangles()
                tri_count += len(mesh.loop_triangles)

    for key, n in seen_logic.items():
        if n == 0:
            # only zones the player can arrive in directly need a spawn point
            (warnings if key == "SPAWN" else errors).append(f"zone has no {key}_ object")

    for img in bpy.data.images:
        if img.users == 0 or img.source != "FILE":
            continue
        w, h = img.size
        if w and (w & (w - 1) or h & (h - 1)):
            errors.append(f"image {img.name}: {w}×{h} is not power-of-two")
        if max(w, h) > C.MAX_TEXTURE_SIZE:
            errors.append(f"image {img.name}: {w}×{h} exceeds {C.MAX_TEXTURE_SIZE}")
        if not C.TEXTURE_RE.match(os.path.basename(img.filepath or img.name)):
            warnings.append(f"image {img.name}: expected T_<Material>_<Map>.<ext>")

    if tri_count > C.MAX_ZONE_TRIANGLES:
        errors.append(f"zone has {tri_count:,} triangles (budget {C.MAX_ZONE_TRIANGLES:,})")
    return errors, warnings, {"objects": len(objs), "triangles_pre_modifiers": tri_count}


def report(zone):
    errors, warnings, stats = validate(zone)
    for w in warnings:
        print(f"  warning: {w}")
    for e in errors:
        print(f"  ERROR:   {e}")
    print(f"[validate] {zone}: {stats['objects']} objects, {len(errors)} errors, {len(warnings)} warnings")
    return not errors


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        sys.exit("usage: ... --python validate_zone.py -- <Zone>")
    sys.exit(0 if report(argv[0]) else 1)
