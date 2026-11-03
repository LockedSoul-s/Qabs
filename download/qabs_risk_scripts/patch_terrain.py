#!/usr/bin/env python3
"""Fill edge NaNs in terrain.npz (grid corners outside the DEM lat/lon rectangle)."""
import numpy as np
from scipy import ndimage

p = "/home/z/my-project/geo/out/terrain.npz"
t = dict(np.load(p))
sea = t["sea"]
for key in ("elev", "slope", "aspect"):
    a = t[key]
    bad = np.isnan(a) & ~sea
    if bad.any():
        idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
        a[bad] = a[tuple(i[bad] for i in idx)]
        t[key] = a
        print(key, "filled", int(bad.sum()))
# recompute aspect factor + hillshade for consistency
gy, gx = np.gradient(t["elev"], 100.0, 100.0)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
slope[t["sea"]] = np.nan
asp = np.degrees(np.arctan2(gy, gx))
aspect = (450.0 - asp) % 360.0
aspect[slope < 0.5] = -1.0
af = np.full_like(slope, 0.5)
ok = aspect >= 0
af[ok] = 0.2 + 0.8 * (0.5 * (1 - np.cos(np.radians(aspect[ok] - 180.0))))
az, alt = np.radians(315.0), np.radians(45.0)
shaded = (np.sin(alt) * np.cos(np.nan_to_num(slope)) +
          np.cos(alt) * np.sin(np.nan_to_num(slope)) * np.cos(az - np.radians(450.0 - np.nan_to_num(asp))))
hs = np.clip(shaded, 0, 1) * 255
hs[t["sea"]] = 0
t["slope"], t["aspect"], t["hillshade"] = slope, aspect, hs.astype(np.uint8)
np.savez_compressed(p, **t)
print("terrain patched")
