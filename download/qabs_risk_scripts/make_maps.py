#!/usr/bin/env python3
"""QABS risk assessment - report figures: 7 maps + 3 charts (matplotlib, PNG 200 dpi).
Style per charts skill: no top/right spines, dashed grid 20%, legend outside/no frame,
first/last/max/min labels only on dense lines."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import matplotlib.patheffects as pe
from rasterio.transform import rowcol  # noqa

OUT = "/home/z/my-project/geo/out"
FIG = "/home/z/my-project/download/figures"
import os
os.makedirs(FIG, exist_ok=True)

m = np.load(f"{OUT}/grid_meta.npz")
X0, Y0, NX, NY, CELL = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"]), float(m["cell"])
import pyproj
tr = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)
lon_l, lat_b = tr.transform(X0, Y0)
lon_r, lat_t = tr.transform(X0 + NX * CELL, Y0 + NY * CELL)
EXT = (lon_l, lon_r, lat_b, lat_t)

MASSIFS = {"Tabarka": (8.758, 36.954), "Ain Draham": (8.467, 36.785),
           "Fernana": (8.983, 36.648), "Nefza": (9.234, 37.057),
           "Sejnane": (9.367, 37.185)}
PILOT = dict(lonmin=8.95, lonmax=9.30, latmin=36.98, latmax=37.20)
ATTR = ("Data: Copernicus Sentinel-2 (2020-2026), ESA WorldCover 2021 (c) ESA, "
        "(c) OpenStreetMap contributors, AWS/Mapzen Terrain, WorldPop, Open-Meteo ERA5")

plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#888888",
                     "axes.linewidth": 0.6, "figure.dpi": 200})

def load_all():
    L = dict()
    L["t"] = np.load(f"{OUT}/terrain.npz")
    L["risk"] = np.load(f"{OUT}/risk.npz")
    L["burns"] = np.load(f"{OUT}/burns.npz")
    L["osm"] = np.load(f"{OUT}/osm_layers.npz", allow_pickle=True)
    L["fuel"] = np.load(f"{OUT}/fuel.npz")["fuel"]
    L["wc"] = np.load(f"{OUT}/worldcover.npz")["lc"]
    L["stats"] = json.load(open(f"{OUT}/risk_stats.json"))
    L["siting"] = json.load(open(f"{OUT}/siting.json"))
    L["fw"] = np.load(f"{OUT}/fireweather.npz", allow_pickle=True)
    return L

def base_map(ax, t, extent=EXT, sea_color="#d7e6f2"):
    hs = t["hillshade"]
    sea = t["sea"]
    ax.imshow(hs, extent=extent, origin="upper", cmap="gray", vmin=0, vmax=255, zorder=0)
    w = np.where(sea, 1.0, np.nan)
    ax.imshow(w, extent=extent, origin="upper", cmap=matplotlib.colors.ListedColormap([sea_color]),
              vmin=0, vmax=1, zorder=1, alpha=0.9)

def draw_scale_north(ax, x0, y0, length_km=10):
    ax.plot([x0, x0 + length_km / 111.32 / np.cos(np.radians(37))], [y0, y0],
            color="black", lw=2, zorder=10, solid_capstyle="butt")
    ax.text(x0 + length_km / 111.32 / np.cos(np.radians(37)) / 2, y0 + 0.012,
            f"{length_km} km", ha="center", va="bottom", fontsize=7, zorder=10)
    ax.annotate("N", xy=(0.94, 0.93), xytext=(0.94, 0.80), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2),
                ha="center", va="center", fontsize=9, zorder=10)

def add_labels(ax, o, min_pop=150):
    placed = []
    for s in o["settlements"]:
        if s["pop2km"] >= min_pop and s["name"]:
            x, y = s["lon"], s["lat"]
            if EXT[0] < x < EXT[1] and EXT[2] < y < EXT[3]:
                txt = ax.text(x, y, s["name"], fontsize=6.5, color="#1a1a1a", zorder=9,
                              ha="center", path_effects=[pe.withStroke(linewidth=2, foreground="white")])
                placed.append(txt)

def finish(fig, ax, name, attr=True):
    ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3])
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if attr:
        fig.text(0.01, 0.005, ATTR, fontsize=4.2, color="#666666")
    fig.savefig(f"{FIG}/{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name, flush=True)

# ---------------------------------------------------------------- maps
def map_study(L):
    t = L["t"]
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    base_map(ax, t)
    # forest context: tree+shrub translucent green
    wc, sea = L["wc"], t["sea"]
    wild = np.where(np.isin(wc, [10, 20]) & ~sea, 1.0, np.nan)
    ax.imshow(wild, extent=EXT, origin="upper",
              cmap=matplotlib.colors.ListedColormap(["#7fae7a"]), vmin=0, vmax=1, alpha=0.55, zorder=2)
    for name, (mx, my) in MASSIFS.items():
        ax.plot(mx, my, marker="o", ms=4, color="#8a2b1d", zorder=8)
        ax.text(mx, my + 0.015, name, fontsize=8, ha="center", color="#8a2b1d", weight="bold", zorder=9)
    add_labels(ax, L["osm"])
    # pilot rectangle
    ax.add_patch(plt.Rectangle((PILOT["lonmin"], PILOT["latmin"]),
                               PILOT["lonmax"] - PILOT["lonmin"], PILOT["latmax"] - PILOT["latmin"],
                               fill=False, ec="#b3261e", lw=1.6, zorder=9))
    ax.text((PILOT["lonmin"] + PILOT["lonmax"]) / 2, PILOT["latmax"] + 0.008, "Pilot zone (Fig. 8)",
            fontsize=7.5, color="#b3261e", ha="center", zorder=9)
    draw_scale_north(ax, 8.42, 36.60)
    finish(fig, ax, "map01_study_area")

def map_fuel(L):
    t = L["t"]
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    base_map(ax, t)
    fuel = np.where(L["t"]["sea"], np.nan, L["fuel"])
    im = ax.imshow(fuel, extent=EXT, origin="upper", cmap="YlGn", vmin=0, vmax=1, alpha=0.85, zorder=2)
    cb = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.015)
    cb.set_label("Fuel hazard score (WorldCover class + fire-return context)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    for name, (mx, my) in MASSIFS.items():
        ax.text(mx, my + 0.015, name, fontsize=7, ha="center", color="#1a1a1a", zorder=9,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    draw_scale_north(ax, 8.42, 36.60)
    finish(fig, ax, "map02_fuel")

def map_ignition(L):
    t = L["t"]
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    base_map(ax, t)
    ign = np.where(t["sea"], np.nan, L["osm"]["ign"])
    im = ax.imshow(ign, extent=EXT, origin="upper", cmap="viridis", vmin=0, vmax=1, alpha=0.85, zorder=2)
    cb = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.015)
    cb.set_label("Ignition proximity (trails, tracks, picnic sites, hamlets)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    draw_scale_north(ax, 8.42, 36.60)
    finish(fig, ax, "map03_ignition")

def map_burns(L):
    t = L["t"]
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    base_map(ax, t)
    b = L["burns"]
    freq = np.where(t["sea"], np.nan, b["freq"])
    im = ax.imshow(freq, extent=EXT, origin="upper", cmap="Oranges", vmin=0, vmax=3, alpha=0.9, zorder=2)
    b26 = np.where(b["burn_2026"], 1.0, np.nan)
    ax.imshow(b26, extent=EXT, origin="upper",
              cmap=matplotlib.colors.ListedColormap(["#a41d1d"]), vmin=0, vmax=1, alpha=0.95, zorder=3)
    cb = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.015)
    cb.set_label("Burns 2021-2025 (count)", fontsize=7.5)
    cb.set_ticks([0, 1, 2, 3]); cb.ax.tick_params(labelsize=7)
    ax.plot([], [], "s", color="#a41d1d", ms=6, label="2026 season scars (dNBR)")
    ax.legend(loc="lower left", frameon=False, fontsize=8)
    for name, (mx, my) in MASSIFS.items():
        ax.text(mx, my + 0.015, name, fontsize=7, ha="center", color="#1a1a1a", zorder=9,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    draw_scale_north(ax, 8.42, 36.60)
    finish(fig, ax, "map04_burn_history")

def map_2026(L):
    t = L["t"]
    # zoom to pilot + Fernana area of interest
    ext = (8.85, 9.45, 36.90, 37.25)
    fig, ax = plt.subplots(figsize=(8.6, 6.4))
    hs = t["hillshade"]
    ax.imshow(hs, extent=EXT, origin="upper", cmap="gray", vmin=0, vmax=255, zorder=0)
    sea = t["sea"]
    w = np.where(sea, 1.0, np.nan)
    ax.imshow(w, extent=ext, origin="upper", cmap=matplotlib.colors.ListedColormap(["#d7e6f2"]),
              vmin=0, vmax=1, zorder=1, alpha=0.9)
    b = L["burns"]
    d = b["dnbr_2026"]
    scar = np.where(np.nan_to_num(d, nan=0) > 0.25, np.clip(d, 0.25, 0.66), np.nan)
    im = ax.imshow(scar, extent=EXT, origin="upper", cmap="YlOrRd", vmin=0.25, vmax=0.66, zorder=3)
    cb = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.015)
    cb.set_label("2026 burn severity (dNBR, Sentinel-2)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    for name, (mx, my) in (("Nefza", (9.234, 37.057)), ("Cap Negro", (9.207, 37.102)),
                           ("Tabarka", (8.758, 36.954))):
        ax.text(mx, my, name, fontsize=8, color="#1a1a1a", ha="center", zorder=9,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
    ax.add_patch(plt.Rectangle((PILOT["lonmin"], PILOT["latmin"]),
                               PILOT["lonmax"] - PILOT["lonmin"], PILOT["latmax"] - PILOT["latmin"],
                               fill=False, ec="#1c447e", lw=1.4, ls="--", zorder=9))
    ax.text(PILOT["lonmin"] + 0.01, PILOT["latmin"] - 0.008, "Pilot zone", fontsize=7.5,
            color="#1c447e", zorder=9)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    draw_scale_north(ax, 8.90, 36.925, length_km=5)
    fig.text(0.01, 0.005, ATTR, fontsize=4.2, color="#666666")
    fig.savefig(f"{FIG}/map05_2026_scars.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("saved map05_2026_scars", flush=True)

def map_risk(L):
    t = L["t"]
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    base_map(ax, t)
    risk = np.where(t["sea"], np.nan, L["risk"]["risk"])
    risk = np.where(risk < 1, np.nan, risk)  # hide zero-risk water/sea
    im = ax.imshow(risk, extent=EXT, origin="upper", cmap="YlOrRd", vmin=0, vmax=100,
                   alpha=0.9, zorder=2)
    cb = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.015)
    cb.set_label("Composite fire risk (0-100)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    for name, (mx, my) in MASSIFS.items():
        ax.text(mx, my + 0.015, name, fontsize=7, ha="center", color="#1a1a1a", zorder=9,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    ax.add_patch(plt.Rectangle((PILOT["lonmin"], PILOT["latmin"]),
                               PILOT["lonmax"] - PILOT["lonmin"], PILOT["latmax"] - PILOT["latmin"],
                               fill=False, ec="#1c447e", lw=1.5, ls="--", zorder=9))
    ax.text((PILOT["lonmin"] + PILOT["lonmax"]) / 2, PILOT["latmax"] + 0.008, "Pilot zone",
            fontsize=7.5, color="#1c447e", ha="center", zorder=9)
    draw_scale_north(ax, 8.42, 36.60)
    finish(fig, ax, "map06_risk")

def map_siting(L):
    t = L["t"]
    ext = (8.95, 9.34, 36.97, 37.22)
    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    hs = t["hillshade"]
    ax.imshow(hs, extent=EXT, origin="upper", cmap="gray", vmin=0, vmax=255, zorder=0)
    w = np.where(t["sea"], 1.0, np.nan)
    ax.imshow(w, extent=ext, origin="upper", cmap=matplotlib.colors.ListedColormap(["#d7e6f2"]),
              vmin=0, vmax=1, zorder=1, alpha=0.9)
    risk = np.where(t["sea"], np.nan, L["risk"]["risk"])
    risk = np.where(risk < 1, np.nan, risk)
    ax.imshow(risk, extent=EXT, origin="upper", cmap="YlOrRd", vmin=0, vmax=100, alpha=0.75, zorder=2)
    S = L["siting"]
    # mesh links: each node to its declared parent within the same cluster
    byid = {n["id"]: n for n in S["nodes"]}
    for n in S["nodes"]:
        if n.get("parent") and n["parent"] in byid:
            pn = byid[n["parent"]]
            ax.plot([n["lon"], pn["lon"]], [n["lat"], pn["lat"]], "-", lw=0.9,
                    color="#4a4a4a", zorder=5, alpha=0.75)
    # gateway links (dotted)
    for n in S["nodes"]:
        gw = S["gateways"][int(n["gateway"][1]) - 1]
        ax.plot([n["lon"], gw["lon"]], [n["lat"], gw["lat"]], ls=":", lw=0.7,
                color="#1c447e", zorder=4, alpha=0.65)
    # siren coverage circles
    for s in S["sirens"]:
        ax.add_patch(plt.Circle((s["lon"], s["lat"]), 0.0063, fill=False, ec="#6a3d9a",
                                lw=1.1, ls="--", zorder=5))
        ax.plot(s["lon"], s["lat"], marker="^", ms=9, mfc="#6a3d9a", mec="white", mew=0.6, zorder=7)
        ax.text(s["lon"], s["lat"] - 0.009, f"{s['name']} siren", fontsize=6.5, ha="center",
                color="#6a3d9a", zorder=9, path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    # nodes
    ax.plot([n["lon"] for n in S["nodes"]], [n["lat"] for n in S["nodes"]], "o",
            ms=3.4, mfc="#e08214", mec="black", mew=0.4, zorder=6)
    for g in S["gateways"]:
        ax.plot(g["lon"], g["lat"], marker="*", ms=15, mfc="#1c447e", mec="white", mew=0.6, zorder=7)
        ax.text(g["lon"], g["lat"] + 0.006, f"{g['id']} gateway ({g['elev_m']} m)", fontsize=6.5,
                ha="center", color="#1c447e", zorder=9, weight="bold",
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    ax.plot([], [], "^", color="#6a3d9a", ms=7, label="Siren hamlet (500 m)")
    ax.plot([], [], "*", color="#1c447e", ms=11, label="LoRa gateway (tower)")
    ax.plot([], [], "o", ms=3.4, mfc="#e08214", mec="black", mew=0.4, label="Sensor node (30)")
    ax.plot([], [], ":", color="#1c447e", lw=0.9, label="Gateway link")
    ax.legend(loc="lower left", frameon=False, fontsize=7.5)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    draw_scale_north(ax, 8.98, 36.99, length_km=5)
    fig.text(0.01, 0.005, ATTR, fontsize=4.2, color="#666666")
    fig.savefig(f"{FIG}/map07_siting.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("saved map07_siting", flush=True)

# ---------------------------------------------------------------- charts
def chart_cbi(L):
    fw = L["fw"]
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    import datetime as dt
    series = {}
    for st in ("Ain Draham", "Tabarka", "Fernana", "Nefza"):
        dates = [dt.date.fromisoformat(d) for d in fw[f"{st}_2026_dates"]]
        cbi = np.asarray(fw[f"{st}_2026_cbi"], dtype=float)
        series[st] = (dates, cbi)
    dates = series["Fernana"][0]
    for st, (dd, cbi) in series.items():
        ax.plot(dd, cbi, lw=1.6, label=st)
    ax.axhline(75, color="#888888", ls="--", lw=0.8); ax.axhline(90, color="#b3261e", ls="--", lw=0.8)
    ax.text(dates[2], 91.5, "extreme (CBI 90)", fontsize=7, color="#b3261e")
    ax.text(dates[2], 76.5, "very high (CBI 75)", fontsize=7, color="#666666")
    for a, b, lab in ((dt.date(2026, 7, 14), dt.date(2026, 7, 16), "blackout 14-15 Jul"),
                      (dt.date(2026, 7, 20), dt.date(2026, 7, 23), "900+ fires 20-22 Jul")):
        ax.axvspan(a, b, color="#f2c096", alpha=0.45, zorder=0)
        ax.text(a + dt.timedelta(hours=18), 128, lab, fontsize=6.8, color="#7a4a10", rotation=0)
    # first/last/max labels on Fernana only (dense rule)
    dd, cbi = series["Fernana"]
    imax = int(np.argmax(cbi))
    ax.annotate(f"peak {cbi[imax]:.0f}", xy=(dd[imax], cbi[imax]), xytext=(6, 6),
                textcoords="offset points", fontsize=7.5)
    ax.set_ylim(0, 135)
    ax.set_ylabel("Chandler Burning Index (daily)", fontsize=8.5)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(True, ls="--", lw=0.5, alpha=0.2)
    ax.legend(loc="upper left", frameon=False, fontsize=7.5, ncol=4)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    fig.tight_layout()
    fig.savefig(f"{FIG}/chart01_cbi_2026.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("saved chart01_cbi_2026", flush=True)

def chart_zones(L):
    zs = [z for z in L["stats"]["zones"] if z["zone"] != "Other corridor"]
    zs.sort(key=lambda z: z["mean_risk"])
    names = [z["zone"] for z in zs]
    means = [z["mean_risk"] for z in zs]
    hi = [z["high_risk_ha"] / 100.0 for z in zs]  # km2
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    bars = ax.barh(names, means, color="#c8642a", alpha=0.85, height=0.62, zorder=3)
    for b, z, h in zip(bars, zs, hi):
        ax.text(b.get_width() + 0.6, b.get_y() + b.get_height() / 2,
                f"{z['mean_risk']:.1f}   ({z['high_risk_ha']:,.0f} ha above 70)",
                va="center", fontsize=7.6, color="#333333")
    ax.set_xlim(0, max(means) * 1.75)
    ax.set_xlabel("Mean composite fire risk (0-100), wildland cells", fontsize=8.5)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(True, axis="x", ls="--", lw=0.5, alpha=0.2)
    fig.tight_layout()
    fig.savefig(f"{FIG}/chart02_zone_ranking.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("saved chart02_zone_ranking", flush=True)

def chart_burn_years(L):
    b = L["burns"]; stats = json.load(open(f"{OUT}/burn_stats.json"))["per_year"]
    years = sorted(int(y) for y in stats)
    wild = [stats[str(y)]["wildland_ha"] for y in years]
    crop = [stats[str(y)]["cropland_ha"] for y in years]
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    ax.bar(years, wild, color="#a43a2a", width=0.62, label="Wildland (forest/shrub/grass)", zorder=3)
    ax.bar(years, crop, bottom=wild, color="#d8b25a", width=0.62, label="Cropland", zorder=3)
    for x, w, c in zip(years, wild, crop):
        ax.text(x, w + c + 40, f"{w + c:,.0f} ha", ha="center", fontsize=7.6, color="#333333")
    ax.set_xticks(years)
    ax.set_ylabel("Area burned (ha, Sentinel-2 dNBR)", fontsize=8.5)
    ax.set_ylim(0, max(np.array(wild) + np.array(crop)) * 1.22)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", ls="--", lw=0.5, alpha=0.2)
    ax.legend(loc="upper left", frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(f"{FIG}/chart03_burn_by_year.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("saved chart03_burn_by_year", flush=True)

if __name__ == "__main__":
    L = load_all()
    map_study(L); map_fuel(L); map_ignition(L); map_burns(L)
    map_2026(L); map_risk(L); map_siting(L)
    chart_cbi(L); chart_zones(L); chart_burn_years(L)
    print("ALL FIGURES DONE")
