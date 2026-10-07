"""Night sky for the window views (Layer 1 → a runtime texture). Run by scripts/make-night-sky.mjs.

Reads Poly Haven's qwantani_moonrise_puresky (CC0, 4k HDR) and writes:
- textures_src/env/T_NightSky.png: the sky hemisphere only (4096 × 1024), rows from the horizon (bottom) to the
  zenith (top), columns by azimuth in the mansion's frame from south through north (the centre column) and round
  again: az = -π … π, az = 0 north (the sea), growing towards east. The wrap is due south, which no window faces. It is
  rotated so the moon rises over the sea, and tone-mapped to sRGB with a known exposure.
- textures_src/env/T_NightSky.json: { moon: { az, el }, exposure }, so the runtime can add the moon's glow and the
  glitter path on the sea in the right place.
"""
import json
import math
import os
import sys

import bpy
import numpy as np

src, out_dir = sys.argv[sys.argv.index("--") + 1:][:2]
img = bpy.data.images.load(src)
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]      # rows bottom → top
lum = px @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
my, mx = np.unravel_index(np.argmax(lum[h // 2:]), lum[h // 2:].shape)       # the moon: brightest sky pixel
my += h // 2
moon_el = (my + 0.5) / h * math.pi - math.pi / 2
MOON_AZ = math.radians(18.0)                                                   # over the sea, a little east of north
OW, OH = 4096, 1024
az = (np.arange(OW) + 0.5) / OW * 2 * math.pi - math.pi                       # output columns: south → north → south
el = math.radians(0.6) + (np.arange(OH) + 0.5) / OH * (math.pi / 2 - math.radians(0.6))   # horizon (just above the photo's black ground) → zenith
src_u = ((mx + 0.5) / w + (az - MOON_AZ) / (2 * math.pi)) % 1.0
src_v = 0.5 + el / math.pi
xs = np.clip((src_u * w).astype(int), 0, w - 1)
ys = np.clip((src_v * h).astype(int), 0, h - 1)
sky = px[ys[:, None], xs[None, :]]                                              # (OH, OW, 3)
median = float(np.median(sky @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)))
exposure = 0.05 / max(median, 1e-6)                                            # a dark blue night, stars readable
ldr = 1.0 - np.exp(-sky * exposure)
srgb = np.where(ldr <= 0.0031308, ldr * 12.92, 1.055 * np.power(np.clip(ldr, 0, 1), 1 / 2.4) - 0.055)
outimg = bpy.data.images.new("T_NightSky", OW, OH, alpha=False)
outimg.pixels = np.concatenate([np.clip(srgb, 0, 1), np.ones((OH, OW, 1), np.float32)], -1).ravel()
outimg.filepath_raw = os.path.join(out_dir, "T_NightSky.png")
outimg.file_format = "PNG"
outimg.save()
with open(os.path.join(out_dir, "T_NightSky.json"), "w") as f:
    json.dump({"source": "Poly Haven qwantani_moonrise_puresky (CC0)", "moon": {"az": MOON_AZ, "el": moon_el}, "exposure": exposure,
               "layout": "rows horizon→zenith (bottom→top), columns az -π→π (south, east, north at the centre, west)"}, f, indent=2)
print(f"[night-sky] moon el {math.degrees(moon_el):.1f}°, median {median:.4g}, exposure {exposure:.3g}")
