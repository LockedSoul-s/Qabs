QABS WILDFIRE RISK ATLAS - REPRODUCIBILITY SCRIPTS
Run order (Python 3.12; needs numpy, rasterio, geopandas, pyogrio, scipy, matplotlib,
pyproj, arabic-reshaper, python-bidi, reportlab, pypdf):
  1. fetch_data.py        - Sentinel-2 NBR stack 2020-2026, DEM, WorldCover, WorldPop, OSM
  2. fetch_weather.py     - Open-Meteo ERA5 daily series 2025-2026 + Chandler Burning Index
  3. process_layers.py    - terrain / fuel / OSM ignition-proximity layers on the 100 m grid
  4. burn_analysis.py     - annual dNBR burn scars, frequency, time-since-burn
  5. risk_model.py        - weighted MCA composite, zone ranking, sensitivity
  6. siting.py            - 30-node / 3-gateway / 3-siren pilot plan (Nefza-Cap Negro)
  7. make_maps.py         - the ten report figures
  8. export_mappack.py    - GeoTIFF / GeoJSON / KML / CSV GIS pack
  9. report/cover.html    - cover (render with html2poster.js --width 794px)
 10. report/make_report.py- ReportLab body; merge cover with pypdf
All data sources are public and open-licensed (see the report, Section 10).
