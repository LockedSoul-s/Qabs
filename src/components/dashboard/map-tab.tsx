"use client";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { LayersData, SitesData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useDash } from "@/lib/store";
import { useLang } from "./lang";
import { CLUSTER_COLORS, BASEMAPS, type BasemapId, type LayerVis } from "./map-constants";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Globe, Layers, MapPin } from "lucide-react";

const MapCanvas = dynamic(() => import("./map-canvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-muted/40">
      <div className="flex flex-col items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <span className="text-sm text-muted-foreground">Loading map…</span>
      </div>
    </div>
  ),
});

const LAYER_ORDER = ["risk", "burn26", "fuel", "ignition", "burnfreq", "tslb", "elev", "slope"];

export default function MapTab() {
  const { t, fmt } = useLang();
  const layers = useJson<LayersData>("/data/layers.json");
  const sites = useJson<SitesData>("/data/sites.json");
  const [basemap, setBasemap] = useState<BasemapId>("sat");
  const [visOverride, setVisOverride] = useState<Record<string, LayerVis> | null>(null);
  const [show, setShow] = useState({ nodes: true, gateways: true, sirens: true, mesh: true, gwlinks: true });

  const effVis = useMemo(() => {
    if (visOverride) return visOverride;
    const v: Record<string, LayerVis> = {};
    if (layers) for (const l of layers.layers) v[l.id] = { on: l.on, opacity: l.opacity };
    return v;
  }, [visOverride, layers]);

  const setLayer = (id: string, patch: Partial<LayerVis>) =>
    setVisOverride({ ...effVis, [id]: { ...effVis[id], ...patch } });

  const clusterCenter = (cl: number) => {
    if (!sites) return null;
    const ns = sites.nodes.filter((n) => n.cluster === cl);
    if (!ns.length) return null;
    const lat = ns.reduce((a, n) => a + n.lat, 0) / ns.length;
    const lon = ns.reduce((a, n) => a + n.lon, 0) / ns.length;
    return { lat, lon, zoom: 12 };
  };

  if (!layers || !sites) {
    return (
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <Skeleton className="h-[62vh] min-h-[420px] w-full rounded-xl" />
        <Skeleton className="h-[62vh] min-h-[420px] w-full rounded-xl" />
      </div>
    );
  }

  const corridor = layers.corridor;
  const midLat = (corridor[0] + corridor[2]) / 2;
  const midLon = (corridor[1] + corridor[3]) / 2;
  const ordered = layers.layers
    .slice()
    .sort((a, b) => LAYER_ORDER.indexOf(a.id) - LAYER_ORDER.indexOf(b.id));

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <Card className="overflow-hidden p-0">
        <CardContent className="h-[62vh] min-h-[420px] p-0">
          <MapCanvas layers={layers} sites={sites} vis={effVis} basemap={basemap} show={show} />
        </CardContent>
      </Card>

      <div className="flex max-h-[72vh] flex-col gap-4 overflow-y-auto pe-1">
        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Globe className="h-4 w-4" /> {t("map.basemap")}
            </div>
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted p-1">
              {(Object.keys(BASEMAPS) as BasemapId[]).map((b) => (
                <button
                  key={b}
                  onClick={() => setBasemap(b)}
                  className={`rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                    basemap === b ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {t(b === "sat" ? "map.satellite" : b === "topo" ? "map.topo" : "map.street")}
                </button>
              ))}
            </div>
            <Separator />
            <div className="flex items-center gap-2 text-sm font-semibold">
              <MapPin className="h-4 w-4" /> {t("map.fly")}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => useDash.getState().flyTo(midLat, midLon, 9)}
                className="col-span-2"
              >
                {t("map.fly.corridor")}
              </Button>
              {[1, 2, 3].map((c) => {
                const cc = clusterCenter(c);
                return (
                  <Button
                    key={c}
                    variant="outline"
                    size="sm"
                    onClick={() => cc && useDash.getState().flyTo(cc.lat, cc.lon, cc.zoom)}
                    className="justify-start text-xs"
                  >
                    <span
                      className="me-1.5 inline-block h-2.5 w-2.5 rounded-full"
                      style={{ background: CLUSTER_COLORS[c] }}
                    />
                    {t(`map.fly.c${c}`)}
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2.5 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Layers className="h-4 w-4" /> {t("map.layers")}
            </div>
            {ordered.map((l) => (
              <div key={l.id} className="space-y-1.5 rounded-lg border p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <label className="flex items-center gap-2 text-xs font-medium leading-tight">
                    <Checkbox
                      checked={effVis[l.id]?.on ?? false}
                      onCheckedChange={(c) => setLayer(l.id, { on: c === true })}
                      aria-label={t(`layer.${l.id}`)}
                    />
                    {t(`layer.${l.id}`)}
                  </label>
                  <span className="shrink-0 text-[10px] text-muted-foreground">{l.unit}</span>
                </div>
                {effVis[l.id]?.on && (
                  <>
                    <div className="flex items-center gap-2 ps-6">
                      <span className="whitespace-nowrap text-[10px] text-muted-foreground">{t("map.opacity")}</span>
                      <Slider
                        value={[Math.round(effVis[l.id].opacity * 100)]}
                        min={10}
                        max={100}
                        step={5}
                        onValueChange={(v) => setLayer(l.id, { opacity: (v[0] ?? 50) / 100 })}
                        className="flex-1"
                        aria-label={`${t("map.opacity")} ${t(`layer.${l.id}`)}`}
                      />
                    </div>
                    {l.legend.kind === "gradient" && (
                      <div className="ps-6">
                        <div
                          className="h-2 w-full rounded-full"
                          style={{
                            background: `linear-gradient(to right, ${l.legend.stops.map((s) => s.color).join(",")})`,
                          }}
                        />
                        <div className="flex justify-between text-[10px] text-muted-foreground">
                          <span>{fmt(l.vmin, l.vmin % 1 ? 1 : 0)}</span>
                          <span>{fmt(l.vmax, l.vmax % 1 ? 1 : 0)}</span>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2.5 p-4">
            <div className="text-sm font-semibold">{t("map.sites")}</div>
            <SiteToggle
              label={t("map.nodes")}
              checked={show.nodes}
              onChange={(v) => setShow((s) => ({ ...s, nodes: v }))}
              icon={<span className="inline-block h-3 w-3 shrink-0 rounded-full border-2 border-white" style={{ background: "#f59e0b" }} />}
              extra={
                <span className="flex gap-1">
                  {[1, 2, 3].map((c) => (
                    <span key={c} className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: CLUSTER_COLORS[c] }} />
                  ))}
                </span>
              }
            />
            <SiteToggle
              label={t("map.mesh")}
              checked={show.mesh}
              onChange={(v) => setShow((s) => ({ ...s, mesh: v }))}
              icon={<span className="inline-block h-0.5 w-4 shrink-0 rounded" style={{ background: "#14b8a6" }} />}
            />
            <SiteToggle
              label={t("map.gateways")}
              checked={show.gateways}
              onChange={(v) => setShow((s) => ({ ...s, gateways: v }))}
              icon={<span className="inline-flex h-3 w-3 shrink-0 items-center justify-center rounded-full border-2 border-stone-900 bg-white" />}
            />
            <SiteToggle
              label={t("map.gwlinks")}
              checked={show.gwlinks}
              onChange={(v) => setShow((s) => ({ ...s, gwlinks: v }))}
              icon={
                <span
                  className="inline-block h-0.5 w-4 shrink-0"
                  style={{ background: "repeating-linear-gradient(to right,#57534e 0 3px,transparent 3px 6px)" }}
                />
              }
            />
            <SiteToggle
              label={t("map.sirens")}
              checked={show.sirens}
              onChange={(v) => setShow((s) => ({ ...s, sirens: v }))}
              icon={<span className="inline-flex h-3 w-3 shrink-0 items-center justify-center rounded-full border-2 border-amber-900 bg-amber-400" />}
            />
            <p className="pt-1 text-[11px] leading-snug text-muted-foreground">{sites.nodes.length} · {sites.gateways.length} · {sites.sirens.length}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SiteToggle({
  label,
  checked,
  onChange,
  icon,
  extra,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  icon?: React.ReactNode;
  extra?: React.ReactNode;
}) {
  return (
    <label className="flex items-center gap-2 text-xs font-medium">
      <Checkbox checked={checked} onCheckedChange={(c) => onChange(c === true)} aria-label={label} />
      {icon}
      <span className="flex-1">{label}</span>
      {extra}
    </label>
  );
}
