"use client";
import { useEffect, useState } from "react";

const cache: Record<string, unknown> = {};

export function useJson<T>(url: string): T | null {
  const [data, setData] = useState<T | null>(() => (cache[url] as T) ?? null);
  useEffect(() => {
    if (cache[url]) return;
    let ok = true;
    fetch(url)
      .then((r) => r.json())
      .then((j) => {
        cache[url] = j;
        if (ok) setData(j);
      })
      .catch(() => {});
    return () => {
      ok = false;
    };
  }, [url]);
  return data;
}
