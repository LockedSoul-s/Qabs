"use client";
import { useMemo, useState } from "react";
import { SitesData } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import { useDash } from "@/lib/store";
import { useLang } from "../lang";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CLUSTER_COLORS } from "../map-constants";
import { Search, MapPin, ArrowUpDown } from "lucide-react";

type SortKey = "id" | "cluster" | "elev_m" | "risk" | "link_m" | "gw_dist_m" | "access_dist_m" | "settle_dist_m";

export default function Siting() {
  const { t, fmt } = useLang();
  const sites = useJson<SitesData>("/data/sites.json");
  const [q, setQ] = useState("");
  const [cluster, setCluster] = useState<number | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [asc, setAsc] = useState(true);

  const cov = sites?.coverage;

  const cards = useMemo(() => {
    if (!cov) return [];
    return [
      { label: t("site.card.nodes"), value: "30", sub: t("site.sub.cap") },
      { label: t("site.card.mesh"), value: `${fmt(cov.mesh_total_km, 1)} km` },
      { label: t("site.card.spacing"), value: `${fmt(Math.round(cov.max_node_spacing))} m`, sub: t("site.sub.ext") },
      { label: t("site.card.gw"), value: `${fmt(Math.round(cov.min_gateway_dist))}–${fmt(Math.round(cov.max_gateway_dist))} m` },
      { label: t("site.card.cover"), value: `${fmt(cov.pct_burn26_within_1km, 0)}%`, sub: `${fmt(Math.round(cov.burn26_in_footprint_ha))} ha` },
      {
        label: t("site.card.risk"),
        value: `${fmt(cov.mean_risk_at_nodes, 1)} / ${fmt(cov.mean_risk_pilot_wild, 1)}`,
        sub: t("site.sub.ratio"),
      },
    ];
  }, [cov, t, fmt]);

  const rows = useMemo(() => {
    if (!sites) return [];
    let r = sites.nodes;
    if (cluster !== "all") r = r.filter((n) => n.cluster === cluster);
    if (q.trim()) {
      const s = q.trim().toLowerCase();
      r = r.filter(
        (n) =>
          n.id.toLowerCase().includes(s) ||
          n.gateway.toLowerCase().includes(s) ||
          n.nearest_siren.toLowerCase().includes(s) ||
          String(n.cluster) === s
      );
    }
    const dir = asc ? 1 : -1;
    return r.slice().sort((a, b) => {
      const va = a[sortKey] as string | number;
      const vb = b[sortKey] as string | number;
      if (typeof va === "string" && typeof vb === "string") return dir * va.localeCompare(vb);
      return dir * (Number(va) - Number(vb));
    });
  }, [sites, q, cluster, sortKey, asc]);

  const locate = (lat: number, lon: number, id: string) => {
    useDash.getState().flyTo(lat, lon, 14);
    useDash.getState().highlight(id);
    useDash.getState().setTab("map");
  };

  const th = (label: string, key?: SortKey) => (
    <TableHead className={`text-xs ${key ? "cursor-pointer select-none hover:text-foreground" : ""} ${key && key !== "id" && key !== "cluster" ? "text-end" : ""}`}
      onClick={
        key
          ? () => {
              if (sortKey === key) setAsc(!asc);
              else {
                setSortKey(key);
                setAsc(true);
              }
            }
          : undefined
      }
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {key && <ArrowUpDown className="h-3 w-3 opacity-40" />}
      </span>
    </TableHead>
  );

  if (!sites || !cov) return <Skeleton className="h-[480px] w-full rounded-xl" />;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t("site.title")}</h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("site.sub")}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardContent className="p-3">
              <div className="text-[11px] font-medium leading-tight text-muted-foreground">{c.label}</div>
              <div dir="ltr" className="mt-1 text-lg font-bold leading-tight">{c.value}</div>
              {c.sub && <div dir="ltr" className="text-[10px] text-muted-foreground">{c.sub}</div>}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="relative min-w-56 flex-1">
              <Search className="absolute start-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("site.search")} className="ps-8" />
            </div>
            <div className="flex gap-1 rounded-lg bg-muted p-1">
              <button
                onClick={() => setCluster("all")}
                className={`rounded-md px-3 py-1.5 text-xs font-medium ${cluster === "all" ? "bg-background shadow-sm" : "text-muted-foreground"}`}
              >
                {t("site.all")}
              </button>
              {[1, 2, 3].map((c) => (
                <button
                  key={c}
                  onClick={() => setCluster(c)}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${cluster === c ? "bg-background shadow-sm" : "text-muted-foreground"}`}
                >
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: CLUSTER_COLORS[c] }} />
                  {t(`site.c${c}`)}
                </button>
              ))}
            </div>
            <span className="text-xs text-muted-foreground">{rows.length} / {sites.nodes.length}</span>
          </div>

          <div className="max-h-[52vh] overflow-auto rounded-lg border" dir="ltr">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-background">
                <TableRow>
                  {th("Node", "id")}
                  {th(t("node.cluster"), "cluster")}
                  {th(t("node.kind"))}
                  {th(t("node.elev"), "elev_m")}
                  {th(t("node.risk"), "risk")}
                  {th(t("node.link"), "link_m")}
                  {th(t("node.gateway"), "gw_dist_m")}
                  {th(t("node.road"), "access_dist_m")}
                  {th(t("node.settle"), "settle_dist_m")}
                  {th(t("node.siren"))}
                  <TableHead className="text-xs" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((n) => (
                  <TableRow
                    key={n.id}
                    className="cursor-pointer"
                    onClick={() => locate(n.lat, n.lon, n.id)}
                  >
                    <TableCell className="text-xs font-bold">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: CLUSTER_COLORS[n.cluster] }} />
                        {n.id}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs">{n.cluster}</TableCell>
                    <TableCell className="whitespace-nowrap text-xs">{n.kind === "2" ? t("node.seed") : t("node.mesh")}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(n.elev_m)}</TableCell>
                    <TableCell className="text-end text-xs font-semibold">{fmt(n.risk, 1)}</TableCell>
                    <TableCell className="text-end text-xs">
                      {n.parent ? `${fmt(n.link_m)}${n.extended_link ? " *" : ""}` : "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-end text-xs">
                      {n.gateway} · {fmt(n.gw_dist_m)}
                    </TableCell>
                    <TableCell className="text-end text-xs">{fmt(n.access_dist_m)}</TableCell>
                    <TableCell className="text-end text-xs">{fmt(n.settle_dist_m)}</TableCell>
                    <TableCell className="whitespace-nowrap text-xs">{n.nearest_siren || "—"}</TableCell>
                    <TableCell className="text-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2"
                        onClick={(e) => {
                          e.stopPropagation();
                          locate(n.lat, n.lon, n.id);
                        }}
                      >
                        <MapPin className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">* {t("map.extended")} — max {fmt(Math.round(cov.max_node_spacing))} m</p>
        </CardContent>
      </Card>
    </div>
  );
}
