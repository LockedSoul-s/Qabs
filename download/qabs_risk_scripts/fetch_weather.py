#!/usr/bin/env python3
"""QABS risk assessment - Fire weather 2026 (Open-Meteo ERA5 archive, open, no key).
Fetches daily series for 4 corridor stations (2025 + 2026 season), computes the
Chandler Burning Index (CBI) and saves to geo/out/fireweather.npz + csv copies.
"""
import json, time, urllib.request
import numpy as np

OUT = "/home/z/my-project/geo/out"
STATIONS = {
    "Ain Draham": (36.785, 8.467),
    "Tabarka":    (36.954, 8.758),
    "Fernana":    (36.648, 8.983),
    "Nefza":      (37.057, 9.234),
}
WINDOWS = [("2025-05-01", "2025-10-31"), ("2026-05-01", "2026-10-31")]
DAILY = ["temperature_2m_max", "temperature_2m_min", "relative_humidity_2m_mean",
         "wind_speed_10m_max", "precipitation_sum"]

def chandler_burning_index(tmax_c, rh_mean):
    """CBI from daily max temperature (C) and mean RH (%). Standard coefficients."""
    t = np.asarray(tmax_c, dtype=float); h = np.asarray(rh_mean, dtype=float)
    cbi = (((110.0 - 1.373 * h) - 0.54 * (10.20 - t)) * (124.0 * 10.0 ** (-0.0142 * h))) / 60.0
    return np.clip(cbi, 0, None)

def fetch_series(lat, lon, start, end):
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
           "&daily=" + ",".join(DAILY) + "&timezone=Africa%2FTunis")
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "qabs-risk-mapping/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            print(f"  retry {i+1}: {e}", flush=True); time.sleep(5)
    raise RuntimeError("open-meteo fetch failed")

def main():
    data = {}
    for year_windows in WINDOWS:
        for name, (lat, lon) in STATIONS.items():
            d = fetch_series(lat, lon, *year_windows)
            dates = d["daily"]["time"]
            tmax = np.array(d["daily"]["temperature_2m_max"], dtype=float)
            rh   = np.array(d["daily"]["relative_humidity_2m_mean"], dtype=float)
            wind = np.array(d["daily"]["wind_speed_10m_max"], dtype=float)
            prcp = np.array(d["daily"]["precipitation_sum"], dtype=float)
            cbi  = chandler_burning_index(tmax, rh)
            yr = dates[0][:4]
            data[f"{name}_{yr}"] = dict(dates=dates, tmax=tmax, rh=rh, wind=wind,
                                        prcp=prcp, cbi=cbi)
            n_ext = int(np.sum(cbi >= 90)); n_vh = int(np.sum((cbi >= 75) & (cbi < 90)))
            print(f"{name} {yr}: {len(dates)} days, CBI>=90 (extreme): {n_ext}, 75-90 (very high): {n_vh}, "
                  f"peak T {np.nanmax(tmax):.1f} C", flush=True)
            time.sleep(1.2)
    np.savez(f"{OUT}/fireweather.npz",
             **{f"{k}_{f}": np.array(v[f], dtype=object if f == "dates" else float)
                for k, v in data.items() for f in ("dates", "tmax", "rh", "wind", "prcp", "cbi")})
    # CSV copies for the map pack
    import csv, os
    os.makedirs("/home/z/my-project/download", exist_ok=True)
    for key, v in data.items():
        fn = f"/home/z/my-project/download/fireweather_{key.replace(' ', '_')}.csv"
        with open(fn, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "tmax_c", "rh_mean_pct", "wind_max_kmh", "precip_mm", "cbi"])
            for i, dt in enumerate(v["dates"]):
                w.writerow([dt, f"{v['tmax'][i]:.1f}", f"{v['rh'][i]:.0f}",
                            f"{v['wind'][i]:.1f}", f"{v['prcp'][i]:.1f}", f"{v['cbi'][i]:.1f}"])
    print("saved fireweather.npz + csv")

if __name__ == "__main__":
    main()
