"use client";
import { AnalysisData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useDash } from "@/lib/store";
import { useLang } from "../lang";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Map, ExternalLink } from "lucide-react";

const WEIGHT_COLORS = ["#dc2626", "#f97316", "#14b8a6", "#a855f7"];

export default function Overview() {
  const { t, fmt } = useLang();
  const analysis = useJson<AnalysisData>("/data/analysis.json");
  const setTab = useDash((s) => s.setTab);

  const weights = analysis?.risk.weights ?? [0.35, 0.25, 0.2, 0.2];
  const weightRows = [
    { name: t("layer.fuel"), v: weights[0] },
    { name: t("layer.ignition"), v: weights[1] },
    { name: t("layer.elev") + " · " + t("layer.slope"), v: weights[2] },
    { name: t("layer.burnfreq"), v: weights[3] },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t("ov.title")}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted-foreground">{t("ov.p1")}</p>
        <Button className="mt-3" onClick={() => setTab("map")}>
          <Map className="me-2 h-4 w-4" /> {t("ov.goMap")}
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardContent className="p-4">
            <div className="mb-3 text-sm font-semibold">{t("ov.sources")}</div>
            <ul className="space-y-2 text-sm">
              {["ov.src1", "ov.src2", "ov.src3", "ov.src4", "ov.src5", "ov.src6"].map((k) => (
                <li key={k} className="flex items-start gap-2">
                  <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span>{t(k)}</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 rounded-lg bg-muted p-3 text-xs leading-relaxed text-muted-foreground">{t("ov.all")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="mb-1 text-sm font-semibold">{t("ov.weights")}</div>
            {!analysis ? (
              <Skeleton className="mx-auto h-48 w-48 rounded-full" />
            ) : (
              <>
                <div className="h-[220px] w-full" dir="ltr">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={weightRows} dataKey="v" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                        {weightRows.map((_, i) => (
                          <Cell key={i} fill={WEIGHT_COLORS[i % WEIGHT_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => fmt(Number(v), 2)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="space-y-1.5 text-xs">
                  {weightRows.map((w, i) => (
                    <li key={w.name} className="flex items-center gap-2">
                      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: WEIGHT_COLORS[i] }} />
                      <span className="flex-1">{w.name}</span>
                      <span className="font-semibold">{fmt(w.v, 2)}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
