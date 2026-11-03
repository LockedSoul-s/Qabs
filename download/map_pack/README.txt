QABS WILDFIRE RISK MAP PACK
Ignition-stage wildfire detection and last-mile alerting - Kroumirie-Mogods, NW Tunisia
Companion data for the satellite risk-assessment report. All layers 100 m grid, UTM zone 32N (EPSG:32632).
Generated 2026-11-02 from public open data; no proprietary sources.

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
