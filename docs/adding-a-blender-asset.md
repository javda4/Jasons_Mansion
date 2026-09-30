# Adding a Blender-authored zone or asset

1. **Start the file** in `blender/rooms/<zone>/<zone>.blend`. Metric, 1 unit = 1 m, Z-up. Put the
   room's entrance threshold (centre, floor level) at the origin; the room extends along **+Y**.
2. **Collections:** `ZONE_<Zone>` › `VISUAL`, `COLLISION`, `LOGIC`, `LIGHTS`, `PROBES`. Anything in a
   collection starting `_WIP` or `_REF` is ignored by the exporter.
3. **Name everything** `PREFIX_<Zone>_Name[_NN]` (CLAUDE.md §6). Required: at least one `COLLIDER_`,
   one `TRIGGER_<Zone>_Bounds`, one `SPAWN_`, one `PROBE_`.
4. **Materials:** reuse library names (`src/render/materialNames.ts`) wherever possible; unique
   materials are `MAT_<Zone>_<Thing>` with Principled BSDF + image textures only (bake anything
   procedural). Textures `T_<Material>_<Map>.png/jpg`, power-of-two, ≤ 2048.
5. **Repeated props:** linked duplicates (Alt+D), not copies.
6. **Lights:** Point/Spot named `LIGHT_…`, Custom Distance set; custom properties `castShadow`,
   `flicker` as needed. Keep ≤ ~8 per room; the runtime shows the most relevant ones.
7. **Register** the zone in `blender/zones.json`, then `npm run build:assets -- <zone>`. Fix every
   `ERROR` (names, UVs, POT textures, budgets); warnings name the offending object.
8. **Run** `npm run dev`, open `?debug`, walk to the connecting door; the overlay shows the zone's
   state and load time, and `?debug` draws its colliders.
