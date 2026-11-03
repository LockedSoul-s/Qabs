#!/usr/bin/env python3
"""QABS risk assessment - export the GIS map pack to download/map_pack/.
GeoTIFF rasters (UTM32N), GeoJSON + KML vectors, CSV node table, README."""
import json
import os
import numpy as np
import pyproj
from rasterio.transform import from_origin as tf_from_origin

OUT = "/home/z/my-project/geo/out"
PACK = "/home/z/my-project/download/map_pack"
os.makedirs(PACK, exist_ok=True)

m = np.load(f"{OUT}/grid_meta.npz")
X0, Y0, NX, NY, CELL = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"]), float(m["cell"])
GT = tf_from_origin(X0, Y0 + NY * CELL, CELL, CELL)
CRS = "EPSG:32632"
tr = pyproj.Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)

def write_tif(name, arr, dtype="float32", nodata=None, compress=True):
    import rasterio
    p = f"{PACK}/{name}.tif"
    profile = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                   dtype=dtype, crs=CRS, transform=GT, compress="deflate" if compress else None)
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(p, "w", **profile) as dst:
        dst.write(arr.astype(dtype), 1)
    print("tif:", name)

def wkt_point(lon, lat):
    return f"{lon:.6f},{lat:.6f}"

def write_geojson(name, feats):
    import json as js
    doc = dict(type="FeatureCollection",
               name=name,
               crs=dict(type="name", properties=dict(name="urn:ogc:def:crs:OGC:1.3:CRS84")),
               features=feats)
    with open(f"{PACK}/{name}.geojson", "w") as f:
        js.dump(doc, f, indent=1)
    print("geojson:", name)

def write_kml(name, placemarks):
    items = []
    for pm in placemarks:
        items.append(f"""    <Placemark>
      <name>{pm['name']}</name>
      <description>{pm.get('desc','')}</description>
      <styleUrl>#{pm.get('style','node')}</styleUrl>
      <Point><coordinates>{pm['lon']:.6f},{pm['lat']:.6f},0</coordinates></Point>
    </Placemark>""")
    styles = """  <Style id="node"><IconStyle><color>ff1482e0</color><scale>0.9</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>
  <Style id="gateway"><IconStyle><color>ffe07b1c</color><scale>1.3</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon></IconStyle></Style>
  <Style id="siren"><IconStyle><color>ff9a3d6a</color><scale>1.1</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/open-diamond.png</href></Icon></IconStyle></Style>"""
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
  <name>{name}</name>
{styles}
{chr(10).join(items)}
</Document></kml>"""
    with open(f"{PACK}/{name}.kml", "w") as f:
        f.write(kml)
    print("kml:", name)

def main():
    t = np.load(f"{OUT}/terrain.npz")
    risk = np.load(f"{OUT}/risk.npz")
    b = np.load(f"{OUT}/burns.npz")
    o = np.load(f"{OUT}/osm_layers.npz", allow_pickle=True)
    fuel = np.load(f"{OUT}/fuel.npz")["fuel"]

    sea = t["sea"]
    nod = -9999.0
    write_tif("qabs_composite_fire_risk", np.where(sea, nod, risk["risk"]).astype(np.float32), nodata=nod)
    write_tif("qabs_fuel_hazard", np.where(sea, nod, fuel), nodata=nod)
    write_tif("qabs_ignition_proximity", np.where(sea, nod, o["ign"]), nodata=nod)
    write_tif("qabs_burn_frequency_2021_2025", np.where(sea, nod, b["freq"]), "int8", nodata=-128)
    write_tif("qabs_burned_2026", np.where(sea, nod, b["burn_2026"].astype(np.int8)), "int8", nodata=-128)
    write_tif("qabs_time_since_burn", np.where(sea, nod, b["tslb"]), nodata=nod)
    write_tif("qabs_elevation", np.where(sea, nod, t["elev"]), nodata=nod)
    write_tif("qabs_slope_degrees", np.where(sea, nod, t["slope"]), nodata=nod)

    S = json.load(open(f"{OUT}/siting.json"))
    feats = []
    kml_nodes = []
    for n in S["nodes"]:
        feats.append(dict(type="Feature",
                          geometry=dict(type="Point", coordinates=[n["lon"], n["lat"]]),
                          properties=dict(id=n["id"], type="sensor_node", siting=n["kind"],
                                          risk_score=n["risk"], elevation_m=n["elev_m"],
                                          mesh_link_m=n["link_m"], extended_link=n["extended_link"],
                                          gateway=n["gateway"], gateway_dist_m=n["gw_dist_m"],
                                          road_access_m=n["access_dist_m"],
                                          settlement_m=n["settle_dist_m"])))
        kml_nodes.append(dict(name=f"{n['id']} sensor node", lat=n["lat"], lon=n["lon"],
                              desc=f"siting: {n['kind']}; risk {n['risk']}; link {n['link_m']} m; "
                                   f"gateway {n['gateway']} at {n['gw_dist_m']} m"))
    write_geojson("qabs_pilot_nodes", feats)
    gw_feats = [dict(type="Feature", geometry=dict(type="Point", coordinates=[g["lon"], g["lat"]]),
                     properties=dict(id=g["id"], type="lora_gateway", elevation_m=g["elev_m"],
                                     nearest_node_m=g["nearest_node_m"])) for g in S["gateways"]]
    write_geojson("qabs_pilot_gateways", gw_feats)
    kml_gw = [dict(name=f"{g['id']} LoRa gateway", lat=g["lat"], lon=g["lon"], style="gateway",
                   desc=f"elevation {g['elev_m']} m; nearest node {g['nearest_node_m']} m")
              for g in S["gateways"]]
    kml_siren = []
    sr_feats = []
    for s in S["sirens"]:
        sr_feats.append(dict(type="Feature", geometry=dict(type="Point", coordinates=[s["lon"], s["lat"]]),
                             properties=dict(name=f"{s['name']} siren", type="siren_hamlet",
                                             pop_2km=s["pop2km"])))
        kml_siren.append(dict(name=f"{s['name']} siren", lat=s["lat"], lon=s["lon"], style="siren",
                              desc=f"population ~{s['pop2km']} within 2 km; 110 dB unit, ~70 dB at 100 m"))
    write_geojson("qabs_pilot_sirens", sr_feats)
    write_kml("qabs_pilot_sites", kml_nodes + kml_gw + kml_siren)

    # node CSV
    import csv as csvmod
    with open(f"{PACK}/qabs_pilot_node_table.csv", "w", newline="") as f:
        w = csvmod.writer(f)
        w.writerow(["node_id", "siting_class", "lat", "lon", "elev_m", "risk_score",
                    "mesh_link_m", "extended_link", "gateway", "gateway_dist_m",
                    "road_access_m", "settlement_m"])
        for n in S["nodes"]:
            w.writerow([n["id"], n["kind"], n["lat"], n["lon"], n["elev_m"], n["risk"],
                        n["link_m"], "yes" if n["extended_link"] else "no", n["gateway"],
                        n["gw_dist_m"], n["access_dist_m"], n["settle_dist_m"]])
    print("csv: qabs_pilot_node_table.csv")

    readme = """QABS WILDFIRE RISK MAP PACK
Ignition-stage wildfire detection and last-mile alerting - Kroumirie-Mogods, NW Tunisia
Companion data for the satellite risk-assessment report. All layers 100 m grid, UTM zone 32N (EPSG:32632).
Generated {date} from public open data; no proprietary sources.

FILES
  qabs_composite_fire_risk.tif      Composite risk 0-100: 0.35*fuel + 0.25*ignition + 0.20*terrain + 0.20*burn activity
  qabs_fuel_hazard.tif              Fuel hazard score from ESA WorldCover 2021 classes (0-1)
  qabs_ignition_proximity.tif       Proximity to OSM trails/forest tracks/minor roads/picnic sites/hamlets (0-1)
  qabs_burn_frequency_2021_2025.tif Burn count 2021-2025 from Sentinel-2 dNBR (0-3+)
  qabs_burned_2026.tif              2026 fire-season scars, dNBR > 0.25 (1=burned)
  qabs_time_since_burn.tif          Years since last detected burn (capped 6)
  qabs_elevation.tif                Elevation (m), AWS/Mapzen Terrain tiles
  qabs_slope_degrees.tif            Slope (degrees)
  qabs_pilot_nodes.geojson          30 proposed sensor-node sites (Nefza-Cap Negro pilot)
  qabs_pilot_gateways.geojson       3 proposed LoRa gateway sites (ridge / high ground)
  qabs_pilot_sirens.geojson         3 siren hamlets (largest settlements in pilot)
  qabs_pilot_sites.kml              All pilot sites for Google Earth
  qabs_pilot_node_table.csv         Node table: coordinates, risk, mesh link, gateway, access distances

LICENSES / ATTRIBUTION
  Sentinel-2: Contains modified Copernicus Sentinel data [2020-2026] (free, open)
  ESA WorldCover: (c) ESA 2021, CC-BY 4.0
  Terrain: Mapzen/AWS Terrain Tiles (SRTM, GMTED, ETOPO1), open
  OpenStreetMap: (c) OpenStreetMap contributors, ODbL
  WorldPop: (c) WorldPop, University of Southampton, CC-BY 4.0
  Fire weather: Open-Meteo ERA5 archive (CC-BY 4.0)

NOTE: planning-grade model for siting support; validate on the ground (Phase 2 walk test)
before any installation. Node coordinates are candidates subject to landowner/ONL agreements,
panel shading checks and ANF radio rules.
"""
    with open(f"{PACK}/README.txt", "w") as f:
        f.write(readme.replace("{date}", "2026-11-02"))
    print("README written")

if __name__ == "__main__":
    main()
