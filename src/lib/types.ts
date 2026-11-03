// Shared data types for the QABS dashboard
export type LatLng4 = [number, number, number, number]; // south, west, north, east

export interface LegendStop { v: number; color: string }
export interface LayerMeta {
  id: string;
  png: string;
  bounds: LatLng4;
  vmin: number;
  vmax: number;
  unit: string;
  opacity: number;
  on: boolean;
  legend: { kind: "gradient" | "binary"; stops: LegendStop[] };
}
export interface LayersData {
  corridor: LatLng4;
  layers: LayerMeta[];
}

export interface SiteNode {
  id: string;
  kind: string; // "2" = seed, "0" = mesh
  lat: number;
  lon: number;
  elev_m: number;
  risk: number;
  cluster: number;
  parent: string;
  link_m: number;
  extended_link: boolean;
  gateway: string;
  gw_dist_m: number;
  access_dist_m: number;
  settle_dist_m: number;
  nearest_siren: string;
}
export interface Gateway { id: string; lat: number; lon: number; elev_m: number; nearest_node_m: number }
export interface Siren { id: string; name: string; lat: number; lon: number; pop2km: number }
export interface Coverage {
  footprint_ha: number;
  footprint_wild_ha: number;
  burn26_in_footprint_ha: number;
  pct_burn26_within_1km: number;
  pct_wild_within_1km_of_mesh: number;
  mean_risk_at_nodes: number;
  mean_risk_pilot_wild: number;
  mean_node_trail: number;
  mean_access_dist: number;
  mesh_total_km: number;
  max_gateway_dist: number;
  min_gateway_dist: number;
  max_node_spacing: number;
}
export interface SitesData {
  nodes: SiteNode[];
  gateways: Gateway[];
  sirens: Siren[];
  coverage: Coverage;
}

export interface DayRow { date: string; tmax: number; rh: number; wind: number; precip: number; cbi: number }
export interface YearStats { extreme_days: number; high_days: number; peak_cbi: number; peak_tmax: number; n: number }
export interface FWData {
  stations: string[];
  series: Record<string, Record<string, DayRow[]>>;
  stats: Record<string, Record<string, YearStats>>;
}

export interface BurnYear { total_ha: number; wildland_ha: number; cropland_ha: number }
export interface ZoneRow {
  zone: string;
  area_ha: number;
  wildland_ha: number;
  mean_risk: number;
  p90_risk: number;
  high_risk_ha: number;
  burn21_25_ha: number;
  burn2026_ha: number;
  mean_tslb: number;
}
export interface SensRow { name: string; spearman: number; zone_order: string[] }
export interface AnalysisData {
  burn: { per_year: Record<string, BurnYear> };
  risk: {
    weights: number[];
    zones: ZoneRow[];
    pilot: { area_ha: number; mean_risk: number; high_risk_ha: number; burn2026_ha: number; wildland_ha: number };
    sensitivity: SensRow[];
    rank_stable: boolean;
  };
}

export interface FlyTarget { lat: number; lon: number; zoom?: number; ts: number }
