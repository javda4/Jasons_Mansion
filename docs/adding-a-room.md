# Adding a room

Rooms are **zones**: self-contained modules that build a `ZoneInstance` in their own local space.
The zone manager places them in the world, streams them in and out, and wires their doors.

1. **Pick the anchor.** Local origin = the centre of the entrance threshold at floor level; the room
   extends toward local **-Z**. (Same rule the Blender export will use, §6.)
2. **Create `src/rooms/<zone>/<zone>.ts`** exporting `build<Name>Room(materials): ZoneInstance`.
   Start from `roomShell()` (floor, coffered ceiling, four panelled walls, entrance opening), then
   add furniture from `rooms/shared/props.ts` and finish with `roomInstance(b, id, W, D, H)`.
3. **Lights are data.** Call `b.light({...})` (or use helpers such as `hangChandelier`, `tableLamp`,
   wall `sconceAfter`). Never add three.js `Light` objects to a zone — the LightPool owns all real
   lights so shader permutations never change while streaming.
4. **Colliders** are simple boxes: `b.box(..., { collide: true })`, `b.collider()` or
   `b.colliderBox(frame, min, max)`. Walls and doorways create their own.
5. **Doors** come from a wall opening with a `door` spec:
   `openings: [{ bay, width, height, plaque, door: { id, prompt, target: '<zoneId>' } }]`.
   Omit `target` and set `locked: true` for decorative doors. Door extras follow
   `src/interaction/schema.ts`.
6. **Register the zone** in `src/world/zoneGraph.ts`: id, title, `neighbors` (must match door
   targets — mismatches are warned at load), world `transform` (use `compose()` with `HALL_SLOTS`
   to hang a room off a gallery), and a dynamic `import()` so it becomes its own chunk.
7. **Verify**: `npm run dev`, open `?debug`, walk to the door. The overlay lists every zone's state
   and load time; the room must not overlap others (check its world bounds against neighbours).
