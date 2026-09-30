"""Layer 1 → Layer 2 naming contract (CLAUDE.md §6), shared by validate_zone.py and export_zone.py.

Keep in sync with: src/loading/glbZone.ts (runtime parser), scripts/validate-assets.mjs,
src/interaction/schema.ts (extras) and src/render/materialNames.ts (library materials).
"""
import re

PREFIXES = (
    "ROOM", "COLLIDER", "TRIGGER", "PORTAL", "DOOR", "SPAWN", "INTERACT",
    "TABLE", "CHAIR", "SLOT", "PROP", "LIGHT", "PROBE", "NAV", "AUDIO",
)

# PREFIX_Zone_Name[_Index][_Subindex][_LODn] — PascalCase segments, 2-digit indices
NAME_RE = re.compile(
    r"^(?P<prefix>" + "|".join(PREFIXES) + r")_(?P<zone>[A-Z][A-Za-z0-9]*)"
    r"(?:_(?:[A-Z][A-Za-z0-9]*|\d{2}))*(?:_LOD\d)?$"
)
MATERIAL_RE = re.compile(r"^MAT_[A-Z][A-Za-z0-9]*_[A-Z][A-Za-z0-9]*$")
TEXTURE_RE = re.compile(r"^T_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*_(BaseColor|Normal|ORM|Emissive|Lightmap)\.(png|jpg|jpeg|exr|tif|tiff)$")

# Collections whose contents are never exported
EXCLUDED_COLLECTION_PREFIXES = ("_WIP", "_REF")

# Object types allowed per prefix
MESH_PREFIXES = {"ROOM", "COLLIDER", "TRIGGER", "PORTAL", "DOOR", "INTERACT", "TABLE", "CHAIR", "SLOT", "PROP", "NAV"}
EMPTY_PREFIXES = {"SPAWN", "PROBE", "AUDIO", "DOOR", "INTERACT", "PROP"}
LIGHT_PREFIXES = {"LIGHT"}

# Budgets checked at authoring time (the Node validator re-checks the optimised GLB)
MAX_TEXTURE_SIZE = 2048
MAX_ZONE_TRIANGLES = 1_500_000


def parse_name(name: str):
    m = NAME_RE.match(name)
    return m.groupdict() if m else None


def is_excluded(collection_names) -> bool:
    return any(c.startswith(EXCLUDED_COLLECTION_PREFIXES) for c in collection_names)
