"use client";
import { useEffect } from "react";
import { MapContainer, TileLayer, ImageOverlay, CircleMarker, Polyline, Popup, Tooltip, useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import { LayersData, SitesData } from "@/lib/types";
import { useDash } from "@/lib/store";
import { useLang } from "./lang";
import { BASEMAPS, CLUSTER_COLORS, type BasemapId, type LayerVis } from "./map-constants";

export type { BasemapId, LayerVis };
export { BASEMAPS, CLUSTER_COLORS };
export interface MapProps {
  layers: LayersData;
  sites: SitesData;
  vis: Record<string, LayerVis>;
  basemap: BasemapId;
  show: { nodes: boolean; gateways: boolean; sirens: boolean; mesh: boolean; gwlinks: boolean };
}

function toBounds(b: [number, number, number, number]): LatLngBoundsExpression {
  return [
    [b[0], b[1]],
    [b[2], b[3]],
  ];
}

function FlyController() {
  const map = useMap();
  const flyTarget = useDash((s) => s.flyTarget);
  useEffect(() => {
    if (flyTarget) map.flyTo([flyTarget.lat, flyTarget.lon], flyTarget.zoom ?? 13, { duration: 1.1 });
  }, [flyTarget, map]);
  return null;
}

function NodePopup({ n }: { n: SitesData["nodes"][number] }) {
  const { t, fmt } = useLang();
  const rows: [string, string][] = [
    [t("node.cluster"), fmt(n.cluster)],
    [t("node.kind"), n.kind === "2" ? t("node.seed") : t("node.mesh")],
    [t("node.risk"), fmt(n.risk, 1)],
    [t("node.elev"), `${fmt(n.elev_m)} m`],
    [t("node.link"), n.parent ? `${fmt(n.link_m)} m${n.extended_link ? ` (${t("map.extended")})` : ""}` : "—"],
    [t("node.gateway"), `${n.gateway} · ${fmt(n.gw_dist_m)} m`],
    [t("node.road"), `${fmt(n.access_dist_m)} m`],
    [t("node.settle"), `${fmt(n.settle_dist_m)} m`],
    [t("node.siren"), n.nearest_siren || "—"],
  ];
  return (
    <div className="min-w-44 text-xs" dir="auto">
      <div className="mb-1 text-sm font-semibold">◉ {n.id}</div>
      <table className="w-full">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td className="pe-2 py-0.5 text-muted-foreground whitespace-nowrap">{k}</td>
              <td className="py-0.5 font-medium text-end">{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MapCanvas({ layers, sites, vis, basemap, show }: MapProps) {
  const { t, fmt } = useLang();
  const highlight = useDash((s) => s.highlightNode);
  const corridor = layers.corridor;
  const bm = BASEMAPS[basemap];
  const nodeById = new Map(sites.nodes.map((n) => [n.id, n]));
  const gwById = new Map(sites.gateways.map((g) => [g.id, g]));

  const meshLinks = sites.nodes
    .filter((n) => n.parent && nodeById.has(n.parent))
    .map((n) => {
      const p = nodeById.get(n.parent)!;
      return (
        <Polyline
          key={`lnk-${n.id}`}
          positions={[
            [n.lat, n.lon],
            [p.lat, p.lon],
          ]}
          pathOptions={{
            color: CLUSTER_COLORS[n.cluster] ?? "#888",
            weight: n.extended_link ? 2.2 : 1.6,
            opacity: 0.9,
            dashArray: n.extended_link ? "5 4" : undefined,
          }}
          eventHandlers={{ click: () => useDash.getState().highlight(n.id) }}
        />
      );
    });

  const gwLinks = sites.nodes
    .filter((n) => !n.parent && gwById.has(n.gateway))
    .map((n) => {
      const g = gwById.get(n.gateway)!;
      return (
        <Polyline
          key={`gw-${n.id}`}
          positions={[
            [n.lat, n.lon],
            [g.lat, g.lon],
          ]}
          pathOptions={{ color: "#57534e", weight: 1.4, opacity: 0.75, dashArray: "2 7" }}
        />
      );
    });

  return (
    <MapContainer
      bounds={toBounds(corridor)}
      boundsOptions={{ padding: [10, 10] }}
      className="h-full w-full"
      attributionControl
      scrollWheelZoom
    >
      <TileLayer key={basemap} url={bm.url} attribution={bm.attr} maxZoom={bm.maxZoom} />
      {layers.layers.map((layer) =>
        vis[layer.id]?.on ? (
          <ImageOverlay
            key={layer.id}
            url={layer.png}
            bounds={toBounds(layer.bounds)}
            opacity={vis[layer.id].opacity}
            interactive={false}
          />
        ) : null
      )}

      {show.gwlinks && gwLinks}
      {show.mesh && meshLinks}

      {show.sirens &&
        sites.sirens.map((s) => (
          <CircleMarker
            key={s.id}
            center={[s.lat, s.lon]}
            radius={9}
            pathOptions={{ color: "#7c2d12", weight: 2.5, fillColor: "#fbbf24", fillOpacity: 1 }}
          >
            <Tooltip permanent direction="top" offset={[0, -8]} className="qabs-siren-label">
              {s.name} · {fmt(s.pop2km)}
            </Tooltip>
            <Popup>
              <div className="text-xs">
                <div className="text-sm font-semibold">🔔 {s.name}</div>
                <div className="mt-1">
                  {t("map.sirens")} · pop 2 km: {fmt(s.pop2km)}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}

      {show.gateways &&
        sites.gateways.map((g) => (
          <CircleMarker
            key={g.id}
            center={[g.lat, g.lon]}
            radius={8}
            pathOptions={{ color: "#1c1917", weight: 2.5, fillColor: "#ffffff", fillOpacity: 1 }}
          >
            <Popup>
              <div className="text-xs" dir="auto">
                <div className="text-sm font-semibold">▲ {g.id}</div>
                <table className="mt-1 w-full">
                  <tbody>
                    <tr>
                      <td className="pe-2 text-muted-foreground">{t("node.elev")}</td>
                      <td className="text-end font-medium">{fmt(g.elev_m)} m</td>
                    </tr>
                    <tr>
                      <td className="pe-2 text-muted-foreground">{t("map.nodes")}</td>
                      <td className="text-end font-medium">{fmt(g.nearest_node_m)} m</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Popup>
          </CircleMarker>
        ))}

      {show.nodes &&
        sites.nodes.map((n) => {
          const hl = highlight === n.id;
          return (
            <CircleMarker
              key={n.id}
              center={[n.lat, n.lon]}
              radius={hl ? 11 : 7}
              pathOptions={{
                color: hl ? "#111827" : "#ffffff",
                weight: hl ? 3 : 1.6,
                fillColor: CLUSTER_COLORS[n.cluster] ?? "#f59e0b",
                fillOpacity: 0.95,
              }}
              eventHandlers={{ click: () => useDash.getState().highlight(n.id) }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                {n.id}
              </Tooltip>
              <Popup>
                <NodePopup n={n} />
              </Popup>
            </CircleMarker>
          );
        })}

      <FlyController />
    </MapContainer>
  );
}
