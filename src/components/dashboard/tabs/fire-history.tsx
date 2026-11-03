"use client";
import { AnalysisData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useLang } from "../lang";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export default function FireHistory() {
  const { t, fmt } = useLang();
  const data = useJson<AnalysisData>("/data/analysis.json");
  if (!data) return <Skeleton className="h-[480px] w-full rounded-xl" />;

  const years = Object.keys(data.burn.per_year).sort();
  const rows = years.map((y) => ({
    year: y,
    wildland: data.burn.per_year[y].wildland_ha,
    cropland: data.burn.per_year[y].cropland_ha,
  }));
  const meanWild = rows.reduce((a, r) => a + r.wildland, 0) / rows.length;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t("hist.title")}</h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("hist.sub")}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{t("hist.card.peak")}</div>
            <div className="mt-1 text-xl font-bold text-red-700">{t("hist.card.peak.v")}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{t("hist.card.2026")}</div>
            <div className="mt-1 text-xl font-bold text-orange-600">{t("hist.card.2026.v")}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{t("hist.card.avg")}</div>
            <div className="mt-1 text-xl font-bold">{fmt(Math.round(meanWild))} ha</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="h-[380px] w-full" dir="ltr">
            <ResponsiveContainer>
              <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e5e5" />
                <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => fmt(Number(v))} />
                <Tooltip
                  formatter={(v: number, name) => [`${fmt(Number(v))} ${t("hist.ha")}`, name === "wildland" ? t("hist.wildland") : t("hist.cropland")]}
                  labelFormatter={(l) => `${l}`}
                />
                <Legend formatter={(v) => (v === "wildland" ? t("hist.wildland") : t("hist.cropland"))} />
                <Bar dataKey="wildland" stackId="a" fill="#dc2626" radius={[0, 0, 0, 0]} />
                <Bar dataKey="cropland" stackId="a" fill="#fdba74" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <p className="max-w-3xl text-sm text-muted-foreground">{t("hist.note")}</p>
    </div>
  );
}
