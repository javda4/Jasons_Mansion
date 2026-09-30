/** All movement feel constants in one place (§8 Player & camera). Units: metres, seconds. */
export const MOVEMENT = {
  walkSpeed: 2.1,        // an unhurried stroll through a grand house
  sprintSpeed: 4.0,
  groundAccel: 14,       // how quickly we reach target speed (per second, exponential)
  groundDecel: 11,
  airControl: 0.15,
  gravity: 22,
  jumpSpeed: 4.4,
  capsuleRadius: 0.28,
  capsuleHeight: 1.8,
  stepHeight: 0.36,
  snapDown: 0.4,          // stick to descending stairs instead of hopping off them
  eyeHeight: 1.68,
  mouseSensitivity: 0.0022, // radians per pixel at sensitivity 1
  pitchLimit: Math.PI / 2 - 0.05,
} as const;
