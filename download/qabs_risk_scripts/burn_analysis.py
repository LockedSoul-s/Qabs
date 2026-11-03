#!/usr/bin/env python3
"""QABS risk assessment - burn history from Sentinel-2 NBR stack (2020-2026).
Annual dNBR = NBR(y-1) - NBR(y); scars where dNBR > threshold on wildland fuels,
small patches removed. Outputs burn masks, frequency, time-since-burn, 2026 stats.
"""
import json
import numpy as np
from scipy import ndimage

OUT = "/home/z/my-project/geo/out"
YEARS = list(range(2020, 2027))
DTHRESH_WILD = 0.25   # dNBR scar threshold on forest/shrub/grass
DTHRESH_CROP = 0.40   # cropland: harvest causes big drops, stricter threshold
MIN_PATCH_HA = 2.0    # keep patches >= 2 cells (2 ha) at 100 m

def log(s): print(s, flush=True)

def main():
    nbr = {}
    for y in YEARS:
        p = f"{OUT}/nbr_{y}.npz"
        try:
            nbr[y] = np.load(p)["nbr"]
        except Exception:
            log(f"NBR {y} missing - skipped")
    sea = np.load(f"{OUT}/terrain.npz")["sea"]
    wc = np.load(f"{OUT}/worldcover.npz")["lc"]
    wild = np.isin(wc, [10, 20, 30])          # forest / shrub / grassland
    crop = wc == 40

    masks, stats = {}, {}
    years_avail = sorted(nbr)
    for y in years_avail[1:]:
        a, b = nbr[y - 1], nbr[y]
        dnbr = a - b
        ok = ~np.isnan(dnbr) & ~sea
        m = ok & (((wild | crop & ~wild) & (dnbr > DTHRESH_WILD)) |
                  (crop & (dnbr > DTHRESH_CROP)))
        m = m & (wc > 0) & (wc != 80)
        # remove tiny patches
        lab, n = ndimage.label(m)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool); keep[1:] = sizes >= MIN_PATCH_HA
        m = keep[lab]
        masks[y] = m
        ha = m.sum() * 1.0
        wild_ha = (m & wild).sum() * 1.0
        stats[y] = dict(total_ha=float(ha), wildland_ha=float(wild_ha),
                        cropland_ha=float(ha - wild_ha))
        log(f"burn {y}: total {ha:,.0f} ha (wildland {wild_ha:,.0f} ha) - {int(m.sum())} cells")

    # burn frequency 2021-2025 (fuel-model window, excludes the 2026 season itself)
    hist_years = [y for y in masks if 2021 <= y <= 2025]
    freq = np.zeros(masks[hist_years[0]].shape, np.float32)
    for y in hist_years:
        freq += masks[y].astype(np.float32)
    # time since last burn (years), from 2026 backwards over available masks, cap 6+
    tslb = np.full(freq.shape, 6.0, np.float32)  # >=6 (outside observation window)
    for y in sorted(hist_years, reverse=True):
        tslb[masks[y] & (tslb >= 6)] = 2026 - y
    # 2026 scars (the season under study) kept separate
    m2026 = masks.get(2026)
    dnbr26 = (nbr[2025] - nbr[2026]) if 2026 in nbr and 2025 in nbr else None

    np.savez_compressed(f"{OUT}/burns.npz", freq=freq, tslb=tslb,
                        **{f"burn_{y}": masks[y].astype(bool) for y in masks},
                        dnbr_2026=dnbr26.astype(np.float32) if dnbr26 is not None else np.zeros(freq.shape, np.float32))
    json.dump({"per_year": {str(k): v for k, v in stats.items()}},
              open(f"{OUT}/burn_stats.json", "w"), indent=1)
    log(f"saved burns.npz ({len(masks)} years) + burn_stats.json")

if __name__ == "__main__":
    main()
