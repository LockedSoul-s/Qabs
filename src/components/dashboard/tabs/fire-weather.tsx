"use client";
import { useState } from "react";
import { FWData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useLang } from "../lang";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs as UITabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";

export default function FireWeather() {
  const { t, fmt } = useLang();
  const data = useJson<FWData>("/data/fireweather.json");
  const [station, setStation] = useState<string>("Fernana");

  if (!data) return <Skeleton className="h-[480px] w-full rounded-xl" />;

  const series25 = data.series[station]?.["2025"] ?? [];
  const series26 = data.series[station]?.["2026"] ?? [];
  // merge on day-of-season index (May 1 = day 0) so the two years align on one axis
  const rows = series26.map((r26, i) => {
    const r25 = series25[i];
    return {
      day: r26.date.slice(5),
      cbi26: r26.cbi,
      cbi25: r25 ? r25.cbi : null,
      tmax26: r26.tmax,
    };
  });
  const s25 = data.stats[station]?.["2025"];
  const s26 = data.stats[station]?.["2026"];

  const statCards: { label: string; v25: string; v26: string }[] = [
    { label: t("wx.extreme"), v25: `${fmt(s25?.extreme_days ?? 0)}`, v26: `${fmt(s26?.extreme_days ?? 0)}` },
    { label: t("wx.high"), v25: `${fmt(s25?.high_days ?? 0)}`, v26: `${fmt(s26?.high_days ?? 0)}` },
    { label: t("wx.peakcbi"), v25: fmt(s25?.peak_cbi ?? 0, 1), v26: fmt(s26?.peak_cbi ?? 0, 1) },
    { label: t("wx.peaktmax"), v25: `${fmt(s25?.peak_tmax ?? 0, 1)} °C`, v26: `${fmt(s26?.peak_tmax ?? 0, 1)} °C` },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("wx.title")}</h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("wx.sub")}</p>
        </div>
        <UITabs value={station} onValueChange={setStation}>
          <TabsList>
            {data.stations.map((st) => (
              <TabsTrigger key={st} value={st} className="text-xs">
                {st.replace("_", " ")}
              </TabsTrigger>
            ))}
          </TabsList>
        </UITabs>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        {statCards.map((c) => (
          <Card key={c.label}>
            <CardContent className="p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{c.label}</div>
              <div dir="ltr" className="mt-1.5 flex items-baseline gap-2 text-xl font-bold">
                <span className="text-stone-500">{c.v25}</span>
                <span className="text-sm font-medium text-muted-foreground">→</span>
                <span className="text-red-700">{c.v26}</span>
              </div>
              <div className="mt-0.5 text-[10px] text-muted-foreground">{t("wx.2025")} → {t("wx.2026")}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="h-[380px] w-full" dir="ltr">
            <ResponsiveContainer>
              <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e5e5" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} interval={30} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(v: number, name) => [fmt(Number(v), 1), name === "cbi26" ? t("wx.2026") : t("wx.2025")]}
                  labelFormatter={(l) => `${station.replace("_", " ")} · ${l}`}
                />
                <Legend formatter={(v) => (v === "cbi26" ? t("wx.2026") : t("wx.2025"))} />
                <ReferenceLine y={90} stroke="#dc2626" strokeDasharray="6 4"
                  label={{ value: t("wx.threshold"), position: "insideTopRight", fontSize: 11, fill: "#dc2626" }} />
                <Line type="monotone" dataKey="cbi25" stroke="#a8a29e" strokeWidth={1.4} dot={false} />
                <Line type="monotone" dataKey="cbi26" stroke="#dc2626" strokeWidth={1.8} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <p className="max-w-3xl text-sm text-muted-foreground">{t("wx.note")}</p>
    </div>
  );
}
