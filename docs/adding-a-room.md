# Adding a room

Rooms are **zones**: Blender-authored GLBs, each in its own local frame. The master layout
`blender/zones.json` places them in the world; the zone manager streams them in and out and wires their doors.
The floor plan and the room list are in `docs/mansion-plan.md`.

1. **Pick the anchor.** The local origin is the centre of the room's main doorway at floor level, and the room
   extends along Blender +Y (glTF −Z). The Stair Hall is the exception: its frame *is* the world frame.
2. **Author it** with a script in `blender/tools/` (start from `author_stair_hall.py`), building on the shared kit:
   - `mansion.Mansion`: walls, doors, windows, paintings, sconces, chandeliers;
   - `floors.py`: marble checker, Greek-key band, medallion;
   - `flora.py`: floral arrangements;
   - `kit.import_prop`: Poly Haven scans; `K.import_pack`: the Kraffing tables and slots.

   Dress the room fully as its real type (docs/mansion-plan.md "Dressing rule"). For comfort seating use
   `A.club_chair` (velvet bergère) and the `LouisSofa`, never the box-built leather armchairs.
3. **Lights are data.** Use `K.light`, `A.chandelier`, `A.sconce`. Most lights are `bake_only`. Never add
   three.js lights at runtime: the LightPool owns all real lights.
4. **Colliders** are axis-aligned boxes: `K.collider(name, lo, hi)`. Curves are sliced into several boxes.
5. **Doors**: `A.double_door(id, centre, normal, w, h, base, prompt, target='<zone>')`. Leave out `target` and
   pass `locked=True` while the far room isn't built. The wall needs a matching opening.
6. **Games**: place a Kraffing table with `casino_props.kr_*_table(A, x, y, tableId)`. A `tableId` is always
   `<gameType>_<NN>`; presenters are picked per table, so any room can hold any game.
7. **Register** the zone in `blender/zones.json`:
   - `title`, `source`/`blend`, a PascalCase `zone` segment, `neighbors`, `lightmap`;
   - `transform { x, z, rotY }`: world placement of the local origin in glTF axes, with `rotY` a multiple of π/2.

   Line the doorway up with the neighbour's door, then unlock that door (give it a `target`).
8. **Build**:

   ```
   blender -b --factory-startup --python blender/tools/author_<room>.py
   npm run bake -- <zone>
   npm run build:assets -- <zone>
   npm run typecheck && npm test && npm run build
   ```

9. **Verify**: open `npm run dev` with `?debug`, walk through the door, sit at each table, and check the console.
