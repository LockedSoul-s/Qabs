// Leaflet-free shared constants & types for the map UI.
// Kept separate from map-canvas.tsx so client modules (panels, tables)
// never pull the leaflet module graph into SSR evaluation.
export type BasemapId = "sat" | "topo" | "street";

export const BASEMAPS: Record<BasemapId, { url: string; attr: string; maxZoom: number }> = {
  sat: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr: "Imagery &copy; Esri, Maxar, Earthstar Geographics",
    maxZoom: 18,
  },
  topo: {
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr: "&copy; OpenTopoMap (CC-BY-SA)",
    maxZoom: 17,
  },
  street: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  },
};

export const CLUSTER_COLORS: Record<number, string> = { 1: "#f59e0b", 2: "#14b8a6", 3: "#a855f7" };

export interface LayerVis {
  on: boolean;
  opacity: number;
}
