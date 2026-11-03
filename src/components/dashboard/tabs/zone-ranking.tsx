"use client";
import { AnalysisData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useLang } from "../lang";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
} from "recharts";
import { Badge } from "@/components/ui/badge";

export default function ZoneRanking() {
  const { t, fmt } = useLang();
  const data = useJson<AnalysisData>("/data/analysis.json");
  if (!data) return <Skeleton className="h-[480px] w-full rounded-xl" />;

  const zones = data.risk.zones.filter((z) => z.zone !== "Other corridor").slice().sort((a, b) => b.mean_risk - a.mean_risk);
  const chartRows = zones.map((z) => ({ name: z.zone.replace("-", "–"), mean: Number(z.mean_risk.toFixed(1)) }));
  const pilot = data.risk.pilot;
  const topZone = zones[0];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t("rank.title")}</h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("rank.sub")}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardContent className="p-4">
            <div className="h-[320px] w-full" dir="ltr">
              <ResponsiveContainer>
                <BarChart data={chartRows} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e5e5" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => fmt(Number(v), 1)} />
                  <Bar dataKey="mean" radius={[0, 4, 4, 0]} barSize={22}>
                    {chartRows.map((r, i) => (
                      <Cell key={r.name} fill={i === 0 ? "#dc2626" : i === 1 ? "#f97316" : "#fdba74"} />
                    ))}
                    <LabelList dataKey="mean" position="right" fontSize={11} formatter={(v: number) => fmt(Number(v), 1)} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="text-sm font-semibold">{t("rank.sens")}</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">{t("rank.sens.scenario")}</TableHead>
                  <TableHead className="text-xs">{t("rank.sens.rho")}</TableHead>
                  <TableHead className="text-xs">{t("rank.sens.top")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.risk.sensitivity.map((s) => (
                  <TableRow key={s.name}>
                    <TableCell className="text-xs font-medium">{s.name === "base" ? "base (0.35/0.25/0.20/0.20)" : s.name}</TableCell>
                    <TableCell className="text-xs">{fmt(s.spearman, 3)}</TableCell>
                    <TableCell className="text-xs">
                      {s.zone_order[0] === topZone.zone ? (
                        <Badge variant="outline" className="border-emerald-600 text-emerald-700">#1 {s.zone_order[0]}</Badge>
                      ) : (
                        s.zone_order[0]
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-xs leading-relaxed text-muted-foreground">{t("rank.sens.note")}</p>
            <div className="rounded-lg bg-muted p-3 text-xs">
              <span className="font-semibold">{t("rank.pilot")}:</span>{" "}
              {fmt(pilot.area_ha)} ha · {t("rank.mean")} {fmt(pilot.mean_risk, 1)} · {t("rank.burn2026")} {fmt(pilot.burn2026_ha)} ha
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">#</TableHead>
                <TableHead className="text-xs">{t("rank.zone")}</TableHead>
                <TableHead className="text-end text-xs">{t("rank.mean")}</TableHead>
                <TableHead className="text-end text-xs">{t("rank.p90")}</TableHead>
                <TableHead className="text-end text-xs">{t("rank.high")}</TableHead>
                <TableHead className="text-end text-xs">{t("rank.wild")}</TableHead>
                <TableHead className="text-end text-xs">{t("rank.burn2125")}</TableHead>
                <TableHead className="text-end text-xs">{t("rank.burn2026")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.risk.zones
                .slice()
                .sort((a, b) => b.mean_risk - a.mean_risk)
                .map((z, i) => (
                  <TableRow key={z.zone} className={i === 0 ? "bg-red-50/60" : undefined}>
                    <TableCell className="text-xs font-bold">{i + 1}</TableCell>
                    <TableCell className="text-xs font-semibold">{z.zone}</TableCell>
                    <TableCell className="text-end text-xs font-bold">{fmt(z.mean_risk, 1)}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(z.p90_risk, 1)}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(z.high_risk_ha)}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(z.wildland_ha)}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(z.burn21_25_ha)}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(z.burn2026_ha)}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
