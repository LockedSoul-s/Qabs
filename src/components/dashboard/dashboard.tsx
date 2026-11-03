"use client";
import { AnalysisData, FWData, SitesData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useDash } from "@/lib/store";
import { useLang, LOCALE_OPTIONS } from "./lang";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import Overview from "./tabs/overview";
import MapTab from "./map-tab";
import FireHistory from "./tabs/fire-history";
import FireWeather from "./tabs/fire-weather";
import ZoneRanking from "./tabs/zone-ranking";
import Siting from "./tabs/siting";
import ReportTab from "./tabs/report-tab";
import { Flame, Activity, MapPinned, Radar, Radio, Users, Network } from "lucide-react";

function Kpi({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-700">{icon}</div>
      <div className="min-w-0">
        <div className="truncate text-[11px] font-medium leading-tight text-muted-foreground">{label}</div>
        <div dir="ltr" className="truncate text-base font-bold leading-tight">{value}</div>
        {sub && <div dir="ltr" className="truncate text-[10px] text-muted-foreground">{sub}</div>}
      </div>
    </div>
  );
}

function KpiStrip() {
  const { t, fmt } = useLang();
  const analysis = useJson<AnalysisData>("/data/analysis.json");
  const sites = useJson<SitesData>("/data/sites.json");
  const fw = useJson<FWData>("/data/fireweather.json");

  if (!analysis || !sites || !fw) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    );
  }
  const burn26 = analysis.burn.per_year["2026"]?.wildland_ha ?? 0;
  const top = analysis.risk.zones[0];
  const extMax = Math.max(...fw.stations.map((s) => fw.stats[s]["2026"].extreme_days));

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <Kpi icon={<Flame className="h-4 w-4" />} label={t("kpi.burned2026")} value={`${fmt(burn26)} ha`} sub={t("kpi.sub.ratio")} />
      <Kpi icon={<Activity className="h-4 w-4" />} label={t("kpi.extremeDays")} value={`${fmt(extMax)}`} sub={t("kpi.sub.prev")} />
      <Kpi icon={<MapPinned className="h-4 w-4" />} label={t("kpi.topZone")} value={top.zone.replace("-", "–")} sub={`${fmt(top.mean_risk, 1)} / 100`} />
      <Kpi icon={<Radar className="h-4 w-4" />} label={t("kpi.coverage")} value={`${fmt(sites.coverage.pct_burn26_within_1km, 0)}%`} sub={`${fmt(Math.round(sites.coverage.burn26_in_footprint_ha))} ha`} />
      <Kpi icon={<Radio className="h-4 w-4" />} label={t("kpi.nodes")} value="30" sub={t("kpi.sub.clusters")} />
      <Kpi icon={<Network className="h-4 w-4" />} label={t("kpi.mesh")} value={`${fmt(sites.coverage.mesh_total_km, 1)} km`} sub={t("kpi.sub.gw")} />
    </div>
  );
}

const TAB_ITEMS = [
  { id: "overview", icon: Users },
  { id: "map", icon: MapPinned },
  { id: "history", icon: Flame },
  { id: "weather", icon: Activity },
  { id: "ranking", icon: MapPinned },
  { id: "siting", icon: Radar },
  { id: "report", icon: null },
];

export default function Dashboard() {
  const { t, locale, setLocale } = useLang();
  const tab = useDash((s) => s.tab);
  const setTab = useDash((s) => s.setTab);

  return (
    <div className="flex min-h-screen flex-col bg-stone-100">
      <header className="sticky top-0 z-40 border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold sm:text-lg">
              <span className="me-1.5 inline-flex h-6 w-6 items-center justify-center rounded-md bg-red-600 align-[-4px] text-white">
                <Flame className="h-4 w-4" />
              </span>
              {t("app.title")}
            </h1>
            <p className="truncate text-xs text-muted-foreground">{t("app.subtitle")}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-[10px] leading-tight text-muted-foreground md:block">{t("app.basemapNote")}</span>
            <div className="flex rounded-lg border bg-muted p-0.5" role="group" aria-label="Language">
              {LOCALE_OPTIONS.map((o) => (
                <button
                  key={o.code}
                  onClick={() => setLocale(o.code)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
                    locale === o.code ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                  aria-pressed={locale === o.code}
                >
                  {o.short}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-4 sm:px-6">
        <KpiStrip />

        <Tabs value={tab} onValueChange={setTab} className="mt-4">
          <div className="overflow-x-auto pb-1">
            <TabsList className="h-auto w-max min-w-full justify-start gap-1 p-1">
              {TAB_ITEMS.map(({ id }) => (
                <TabsTrigger key={id} value={id} className="whitespace-nowrap px-3 py-1.5 text-xs sm:text-sm">
                  {t(`tab.${id}`)}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <TabsContent value="overview" className="mt-4">
            <Overview />
          </TabsContent>
          <TabsContent value="map" className="mt-4">
            <MapTab />
          </TabsContent>
          <TabsContent value="history" className="mt-4">
            <FireHistory />
          </TabsContent>
          <TabsContent value="weather" className="mt-4">
            <FireWeather />
          </TabsContent>
          <TabsContent value="ranking" className="mt-4">
            <ZoneRanking />
          </TabsContent>
          <TabsContent value="siting" className="mt-4">
            <Siting />
          </TabsContent>
          <TabsContent value="report" className="mt-4">
            <ReportTab />
          </TabsContent>
        </Tabs>
      </main>

      <footer className="mt-auto border-t bg-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-2 px-4 py-3 text-[11px] text-muted-foreground sm:px-6">
          <span>{t("foot.credit")} — Sentinel-2 · ESA WorldCover · Mapzen/AWS Terrain · OpenStreetMap · WorldPop · Open-Meteo ERA5</span>
          <span className="flex items-center gap-3">
            <a href="/report/QABS_Wildfire_Risk_Atlas.pdf" target="_blank" rel="noreferrer" className="font-medium text-red-700 hover:underline">
              {t("foot.report")}
            </a>
            <span className="text-stone-400">IEEE TSYP14 · QABS</span>
          </span>
        </div>
        <div className="border-t bg-stone-50 px-4 py-1.5 text-center text-[10px] text-muted-foreground sm:px-6">
          {t("foot.disclaimer")}
        </div>
      </footer>
    </div>
  );
}
