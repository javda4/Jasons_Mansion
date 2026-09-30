# Audio

`src/audio/` — Layer 4, independent of the renderer except for reading the camera transform.

- **Start-up:** the `AudioContext` is created on the "Enter the Mansion" click (browser autoplay rules).
- **Zone beds:** each zone has a mix of looping beds (`BEDS` in `audioEngine.ts`: room tone, distant
  murmur, slot-hall chimes). On `zone:entered` the bed gains crossfade over ~1.6 s.
- **Emitters (`AUDIO_` role):** positional sources declared per zone — `b.sound({...})` in code rooms,
  or `AUDIO_<Zone>_<Name>` empties in Blender with custom properties
  `sound` (a `SoundId`), `gain`, `mode` (`loop` | `random`), `intervalMin`, `intervalMax`.
  Only emitters of visible zones play; they use HRTF panning with inverse distance roll-off.
- **Event sounds:** doors (`door:moved`), and game events at the table (cards, chips, roulette ball,
  slot chimes/wins) via `GameView.onEvents`.
- **Sounds are synthesised** (`synth.ts`) because the project has no recorded audio yet. Each `SoundId`
  can be replaced by a streamed CC0 recording under `public/assets/audio/` without changing callers.
- **Controls:** volume slider in the pause menu; **M** toggles mute.
