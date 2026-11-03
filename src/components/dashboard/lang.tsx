"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Locale, LOCALE_OPTIONS, messages } from "@/lib/i18n";

interface LangCtx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (k: string) => string;
  dir: "ltr" | "rtl";
  fmt: (n: number, digits?: number) => string;
}

const Ctx = createContext<LangCtx | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");
  const dir: "ltr" | "rtl" = locale === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
  }, [locale, dir]);

  const t = useCallback(
    (k: string) => messages[locale][k] ?? messages.en[k] ?? k,
    [locale]
  );
  const fmt = useCallback(
    (n: number, digits = 0) =>
      n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }),
    []
  );

  const value = useMemo(() => ({ locale, setLocale, t, dir, fmt }), [locale, t, fmt, dir]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useLang(): LangCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useLang outside provider");
  return c;
}

export { LOCALE_OPTIONS };
