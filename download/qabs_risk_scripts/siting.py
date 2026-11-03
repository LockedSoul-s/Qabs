#!/usr/bin/env python3
"""QABS risk assessment - pilot siting: 30 mesh-connected sensor nodes, 3 gateways,
3 siren hamlets in the Nefza-Cap Negro pilot zone, ranked by
priority = risk x (1 + remoteness) x (1 + hamlet proximity)  [QABS siting rules].
"""
import json
import numpy as np
from scipy import ndimage

OUT = "/home/z/my-project/geo/out"
PILOT = dict(lonmin=8.95, lonmax=9.30, latmin=36.98, latmax=37.20)
N_NODES, N_GATE, N_SIREN = 30, 3, 3
LINK_MAX, LINK_EXT, MIN_SPACING = 600.0, 900.0, 250.0

def log(s): print(s, flush=True)

m = np.load(f"{OUT}/grid_meta.npz")
X0, Y0, NX, NY, CELL = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"]), float(m["cell"])
import pyproj
tr = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)

def cell_lonlat(rows, cols):
    x = X0 + (np.asarray(cols) + 0.5) * CELL
    y = Y0 + (NY - np.asarray(rows) - 0.5) * CELL
    return tr.transform(x, y)

if __name__ == "__main__":
    t = np.load(f"{OUT}/terrain.npz")
    elev, sea = t["elev"], t["sea"]
    r = np.load(f"{OUT}/risk.npz")
    risk, burn26 = r["risk"], r["burn2026"]
    o = np.load(f"{OUT}/osm_layers.npz", allow_pickle=True)
    d_access, d_settle, ign = o["d_access"], o["d_settle"], o["ign"]
    settlements = list(o["settlements"])
    wc = np.load(f"{OUT}/worldcover.npz")["lc"]
    land = (~sea) & (wc != 0)

    yy, xx = np.mgrid[0:NY, 0:NX]
    lon_g, lat_g = tr.transform(X0 + (xx + 0.5) * CELL, Y0 + (NY - yy - 0.5) * CELL)
    pilot = ((lon_g >= PILOT["lonmin"]) & (lon_g <= PILOT["lonmax"]) &
             (lat_g >= PILOT["latmin"]) & (lat_g <= PILOT["latmax"]) & land &
             np.isin(wc, [10, 20, 30, 40]))

    # ---------------- candidate sites
    d_scar = ndimage.distance_transform_edt(~burn26, sampling=(CELL, CELL))
    prio = (risk / 100.0) * (1 + 0.4 * np.clip(d_access / 2000.0, 0, 1)) * \
           (1 + 0.4 * np.exp(-d_settle / 3000.0)) * \
           (1 + 0.8 * np.exp(-d_scar / 1500.0))  # reburn-corridor proximity
    cands = {}
    hi = pilot & (risk >= np.nanpercentile(risk[pilot], 85))
    cands["risk-cell"] = np.argwhere(hi)
    trail = o["d_trail"] < 150.0
    cands["trail"] = np.argwhere(pilot & trail & (np.isin(wc, [10, 20, 30])))
    # reburn corridor: unburned wildland within 300-800 m of a 2026 scar
    from scipy import ndimage as ndi
    scar_zone = ndi.binary_dilation(burn26, iterations=8) & ~burn26
    scar_edge = pilot & scar_zone & np.isin(wc, [10, 20, 30])
    cands["scar-edge"] = np.argwhere(scar_edge)
    poi_rows, poi_cols = [], []
    for p in o["poi"]:
        cl = int((p["lon"] - X0) // CELL); rw = int((Y0 + NY * CELL - p["lat"]) // CELL)
        if 0 <= cl < NX and 0 <= rw < NY and pilot[rw, cl]:
            poi_rows.append(rw); poi_cols.append(cl)
    cands["picnic-camp"] = np.column_stack([poi_rows, poi_cols]) if poi_rows else np.zeros((0, 2), int)
    n_total = sum(len(v) for v in cands.values())
    log(f"candidates: { {k: len(v) for k, v in cands.items()} } total {n_total}")

    allc = np.vstack([np.column_stack([v, np.full(len(v), i)]) for i, (k, v) in enumerate(cands.items())])
    KINDS = list(cands)
    pr = np.array([prio[r_, c_] for r_, c_, _ in allc])
    order = np.argsort(-pr)

    def d2(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 * CELL

    # ---------------- greedy mesh selection: 3 clusters of 10, seeds on scar-edge sites
    CLUSTERS = 3
    sel, sel_meta, ext_links = [], [], 0
    seeds = []
    scar_idx = [i for i in order if KINDS[int(allc[i, 2])] == "scar-edge"]
    for idx in scar_idx:
        rc = allc[idx, :2]
        if all(d2(rc, s) >= 6000.0 for s in seeds):
            seeds.append(rc)
            sel.append(rc)
            sel_meta.append(dict(kind=str(allc[idx, 2]), row=int(rc[0]), col=int(rc[1]),
                                 prio=float(pr[idx]), risk=float(risk[rc[0], rc[1]]),
                                 link=0.0, ext=False, cluster=len(seeds) - 1))
        if len(seeds) >= CLUSTERS:
            break
    log("cluster seeds: " + "; ".join(f"({s[0]},{s[1]})" for s in seeds))
    for idx in order:
        if len(sel) >= N_NODES:
            break
        rc = allc[idx, :2]
        if any(d2(rc, s) < MIN_SPACING for s in sel):
            continue
        ok = False; ext = False; near = 0.0; target = None
        best_ci, best_d = None, 1e18
        for ci in range(CLUSTERS):
            cm = [s for j, s in enumerate(sel) if sel_meta[j]["cluster"] == ci]
            if not cm or sum(1 for x in sel_meta if x["cluster"] == ci) >= N_NODES // CLUSTERS:
                continue
            dmin = min(d2(rc, s) for s in cm)
            if dmin < best_d:
                best_d, best_ci = dmin, ci
        if best_ci is None:
            continue
        if best_d <= LINK_MAX:
            ok = True; near = best_d; target = best_ci
        elif best_d <= LINK_EXT and ext_links < CLUSTERS * 2:
            ok = True; ext = True; near = best_d; target = best_ci; ext_links += 1
        if not ok:
            continue
        cm = [s for j, s in enumerate(sel) if sel_meta[j]["cluster"] == target]
        parent = int(np.argmin([d2(rc, s) for s in cm]))
        cm_ids = [j for j, x in enumerate(sel_meta) if x["cluster"] == target]
        sel.append(rc)
        sel_meta.append(dict(kind=str(allc[idx, 2]), row=int(rc[0]), col=int(rc[1]),
                             prio=float(pr[idx]), risk=float(risk[rc[0], rc[1]]),
                             link=float(near), ext=ext, cluster=target,
                             parent=cm_ids[parent]))
    for j, sm in enumerate(sel_meta[:CLUSTERS]):
        sm.setdefault("cluster", j)
    log(f"selected {len(sel)} nodes in {CLUSTERS} clusters, extended links: {ext_links}, "
        f"cluster sizes: {[sum(1 for x in sel_meta if x.get('cluster') == ci) for ci in range(CLUSTERS)]}")

    # ---------------- gateways: one per cluster - highest peak within 5 km of cluster centroid
    sel_rc = [s for s in sel]
    def d_mesh(rc):
        return min(d2(rc, s) for s in sel_rc)
    elev_m = np.where(land, elev, -999.0)
    mx = ndimage.maximum_filter(elev_m, size=int(2000 / CELL))
    peaks = np.argwhere((elev_m == mx) & (elev_m > 0))
    gates = []
    for ci in range(CLUSTERS):
        cm = [s for j, s in enumerate(sel_rc) if sel_meta[j]["cluster"] == ci]
        cy = float(np.mean([s[0] for s in cm])); cx = float(np.mean([s[1] for s in cm]))
        for radius_km in (3.0, 5.0, 8.0):
            near_peaks = [p for p in peaks if abs(p[0] - cy) * CELL <= radius_km * 1000
                          and abs(p[1] - cx) * CELL <= radius_km * 1000 and elev_m[p[0], p[1]] > 0]
            if near_peaks:
                best = max(near_peaks, key=lambda p: elev_m[p[0], p[1]])
                if all(d2(best, g) >= 2000.0 for g in gates):
                    gates.append(best)
                    break
            elif radius_km == 8.0:
                log(f"WARN no gateway peak within 8 km of cluster {ci}")
    node_g = []
    for s in sel_rc:
        gd = [d2(s, g) for g in gates]
        i = int(np.argmin(gd))
        node_g.append(dict(gw=i, dist=float(gd[i])))
    gd_nodes = [min(d2(g, s) for s in sel_rc) for g in gates]
    log("gateways: " + "; ".join(f"G{i+1} {elev_m[g[0],g[1]]:.0f} m, nearest node {d/1000:.1f} km"
                                 for i, (g, d) in enumerate(zip(gates, gd_nodes))))

    # ---------------- sirens: 3 largest settlements near the mesh (<= 10 km)
    GAZ = {"سجنان": "Sejnane", "نفزة": "Nefza", "وشتاتة": "Wachtata", "بازينة": "Bazina",
           "تمرة": "Tamra", "الفيرمة": "El Ferma", "الحشاشنة": "El Hchachna",
           "شعبة الحوت": "Chaabet El Hout"}
    # location override: the OSM node named 'Sejnane' sits at Nefza town's coordinates
    for s in settlements:
        if abs(s["lon"] - 9.2333) < 0.03 and abs(s["lat"] - 37.0667) < 0.03:
            s["name"] = "Nefza"
        elif s["name"] in GAZ:
            s["name"] = GAZ[s["name"]]
        elif s["name"] in (None, "", "None", "nan", "hamlet"):
            s["name"] = ""
    out_names = []
    for s in settlements:
        out_names.append(s["name"] or "unnamed hamlet")
    mesh_lon = float(np.mean([X0 + (s[1] + 0.5) * CELL for s in sel_rc]))
    mesh_lat = float(np.mean([Y0 + (NY - s[0] - 0.5) * CELL for s in sel_rc]))
    trw = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)
    ml_lon, ml_lat = trw.transform(mesh_lon, mesh_lat)
    from math import radians, sin, cos, asin, sqrt
    def haver(a, b, c, d):
        R = 6371000.0
        dLat, dLon = radians(c - a), radians(d - b)
        h = sin(dLat / 2) ** 2 + cos(radians(a)) * cos(radians(c)) * sin(dLon / 2) ** 2
        return 2 * R * asin(sqrt(h))
    ps = [dict(s, d_mesh=haver(ml_lat, ml_lon, s["lat"], s["lon"]))
          for s in settlements
          if PILOT["lonmin"] - 0.05 <= s["lon"] <= PILOT["lonmax"] + 0.05
          and PILOT["latmin"] - 0.05 <= s["lat"] <= PILOT["latmax"] + 0.05]
    # one siren per cluster: highest-population settlement within 8 km of the cluster centre
    sirens = []
    for ci in range(CLUSTERS):
        cm = [sel_rc[j] for j in range(len(sel_rc)) if sel_meta[j]["cluster"] == ci]
        clon = float(np.mean([X0 + (s[1] + 0.5) * CELL for s in cm]))
        clat = float(np.mean([Y0 + (NY - s[0] - 0.5) * CELL for s in cm]))
        clon_w, clat_w = trw.transform(clon, clat)
        cand = [dict(s, d_cl=haver(clat_w, clon_w, s["lat"], s["lon"])) for s in ps]
        cand = [c for c in cand if c["d_cl"] <= 8000.0]
        cand.sort(key=lambda c: -(c["pop2km"] * (0.5 + 0.5 * np.exp(-c["d_cl"] / 4000.0))))
        if cand:
            sirens.append(cand[0])
    sirens = sirens[:N_SIREN]
    log("mesh centre ~%.4f,%.4f" % (ml_lat, ml_lon))
    log("sirens: " + "; ".join(f"{s['name'] or 'unnamed hamlet'} (pop~{s['pop2km']})" for s in sirens))

    # ---------------- coverage stats (pilot corridor footprint = 1.5 km around the mesh)
    net_mask = np.zeros((NY, NX), bool)
    for s in sel_rc:
        net_mask[s[0], s[1]] = True
    near_node = ndimage.distance_transform_edt(~net_mask, sampling=(CELL, CELL))
    footprint = ndimage.binary_dilation(net_mask, iterations=15) & land  # 1.5 km
    wild_pilot = pilot & np.isin(wc, [10, 20, 30])
    wild_fp = footprint & np.isin(wc, [10, 20, 30])
    b26_fp = (burn26 & footprint).sum()
    cov = dict(
        footprint_ha=float(footprint.sum()),
        footprint_wild_ha=float(wild_fp.sum()),
        burn26_in_footprint_ha=float(b26_fp),
        pct_burn26_within_1km=float((burn26 & footprint & (near_node <= 1000)).sum() /
                                    max(1.0, float(b26_fp)) * 100),
        pct_wild_within_1km_of_mesh=float((wild_pilot & (near_node <= 1000)).sum() /
                                          max(1.0, float(wild_pilot.sum())) * 100),
        mean_risk_at_nodes=float(np.mean([sm["risk"] for sm in sel_meta])),
        mean_risk_pilot_wild=float(np.nanmean(risk[wild_pilot])),
        mean_node_trail=float(np.mean([o["d_trail"][s[0], s[1]] for s in sel_rc])),
        mean_access_dist=float(np.mean([d_access[s[0], s[1]] for s in sel_rc])),
        mesh_total_km=float(sum(s["link"] for s in sel_meta) / 1000.0),
        max_gateway_dist=float(max(n["dist"] for n in node_g)),
        min_gateway_dist=float(min(n["dist"] for n in node_g)),
        max_node_spacing=float(max([sm["link"] for sm in sel_meta])))
    log("coverage: " + json.dumps({k: round(v, 1) for k, v in cov.items()}))

    # ---------------- build output tables
    tr_wgs = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)
    nodes = []
    for i, (s, sm, ng) in enumerate(zip(sel_rc, sel_meta, node_g)):
        lon, lat = tr_wgs.transform(X0 + (s[1] + 0.5) * CELL, Y0 + (NY - s[0] - 0.5) * CELL)
        if sirens:
            d_h = [haver(lat, lon, x["lat"], x["lon"]) for x in sirens]
            near_s = sirens[int(np.argmin(d_h))]["name"]
        else:
            near_s = ""
        nodes.append(dict(id=f"N{i+1:02d}", kind=sm["kind"], lat=round(lat, 5), lon=round(lon, 5),
                          elev_m=round(float(elev[s[0], s[1]])), risk=round(sm["risk"], 1),
                          cluster=int(sm["cluster"]) + 1,
                          parent=(f"N{sm['parent']+1:02d}" if sm.get("parent") is not None and sm["parent"] < i else ""),
                          link_m=int(sm["link"]), extended_link=sm["ext"],
                          gateway=f"G{ng['gw']+1}", gw_dist_m=int(ng["dist"]),
                          access_dist_m=int(d_access[s[0], s[1]]),
                          settle_dist_m=int(d_settle[s[0], s[1]]),
                          nearest_siren=near_s))
    gws = []
    for i, g in enumerate(gates):
        lon, lat = tr_wgs.transform(X0 + (g[1] + 0.5) * CELL, Y0 + (NY - g[0] - 0.5) * CELL)
        gws.append(dict(id=f"G{i+1}", lat=round(lat, 5), lon=round(lon, 5),
                        elev_m=round(float(elev_m[g[0], g[1]])), nearest_node_m=int(gd_nodes[i])))
    json.dump(dict(nodes=nodes, gateways=gws,
                   sirens=[dict(name=(s["name"] or f"unnamed {s['fclass']}"), lat=s["lat"], lon=s["lon"],
                                pop2km=s["pop2km"]) for s in sirens],
                   coverage=cov, extended_links=ext_links),
              open(f"{OUT}/siting.json", "w"), indent=1)
    log("saved siting.json")
