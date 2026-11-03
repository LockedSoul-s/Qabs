"use client";
import { useLang } from "../lang";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download } from "lucide-react";

export default function ReportTab() {
  const { t } = useLang();
  const pdfUrl = "/report/QABS_Wildfire_Risk_Atlas.pdf";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("rep.title")}</h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("rep.sub")}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <a href={pdfUrl} target="_blank" rel="noreferrer">
              <FileText className="me-2 h-4 w-4" /> {t("rep.open")}
            </a>
          </Button>
          <Button variant="outline" asChild>
            <a href={pdfUrl} download="QABS_Wildfire_Risk_Atlas.pdf">
              <Download className="me-2 h-4 w-4" /> PDF
            </a>
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="mb-3 text-sm font-semibold">{t("rep.findings")}</div>
          <ol className="ms-4 list-decimal space-y-2 text-sm leading-relaxed">
            {["rep.f1", "rep.f2", "rep.f3", "rep.f4", "rep.f5", "rep.f6"].map((k) => (
              <li key={k}>{t(k)}</li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <Card className="overflow-hidden p-0">
        <CardContent className="p-0">
          <iframe
            src={pdfUrl}
            title={t("rep.title")}
            className="h-[70vh] min-h-[480px] w-full border-0"
          />
        </CardContent>
      </Card>
    </div>
  );
}
