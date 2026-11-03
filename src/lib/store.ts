"use client";
import { create } from "zustand";
import { FlyTarget } from "@/lib/types";

interface DashState {
  tab: string;
  setTab: (t: string) => void;
  flyTarget: FlyTarget | null;
  flyTo: (lat: number, lon: number, zoom?: number) => void;
  highlightNode: string | null;
  highlight: (id: string | null) => void;
}

export const useDash = create<DashState>((set) => ({
  tab: "map",
  setTab: (t) => set({ tab: t }),
  flyTarget: null,
  flyTo: (lat, lon, zoom = 13) => set({ flyTarget: { lat, lon, zoom, ts: Date.now() } }),
  highlightNode: null,
  highlight: (id) => set({ highlightNode: id }),
}));
