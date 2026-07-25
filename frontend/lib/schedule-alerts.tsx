"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, type SkippedScheduleResponse } from "./api";

const STORAGE_KEY = "content-scout-seen-schedule-skips";
// Skips are rare and server-side (a cron tick, not a user action) — a slower poll than
// run-tracker's 3s is plenty and keeps this from hammering the API while logged in.
const POLL_INTERVAL_MS = 30_000;

interface ScheduleAlertsContextValue {
  alerts: SkippedScheduleResponse[];
  unseenCount: number;
  markAllSeen: () => void;
}

const ScheduleAlertsContext = createContext<ScheduleAlertsContextValue | null>(null);

// Keyed by schedule id + skip timestamp, not just id — a schedule that gets fixed, skips
// again later, and gets seen again should re-surface as unseen rather than staying muted.
function seenKey(a: SkippedScheduleResponse): string {
  return `${a.id}:${a.skipped_at}`;
}

function loadSeen(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw) as string[]) : new Set();
  } catch {
    return new Set();
  }
}

export function ScheduleAlertsProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<SkippedScheduleResponse[]>([]);
  const [seen, setSeen] = useState<Set<string>>(() => loadSeen());

  const load = useCallback(() => {
    if (!getToken()) return;
    api
      .listSkippedSchedules()
      .then(setAlerts)
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  const markAllSeen = useCallback(() => {
    setSeen((prev) => {
      const next = new Set(prev);
      for (const a of alerts) next.add(seenKey(a));
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(next)));
      return next;
    });
  }, [alerts]);

  const unseenCount = alerts.filter((a) => !seen.has(seenKey(a))).length;

  return (
    <ScheduleAlertsContext.Provider value={{ alerts, unseenCount, markAllSeen }}>
      {children}
    </ScheduleAlertsContext.Provider>
  );
}

export function useScheduleAlerts(): ScheduleAlertsContextValue {
  const ctx = useContext(ScheduleAlertsContext);
  if (!ctx) throw new Error("useScheduleAlerts must be used within ScheduleAlertsProvider");
  return ctx;
}
