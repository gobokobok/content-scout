"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, type RunResponse } from "./api";
import { useAuth } from "./auth-context";

const STORAGE_KEY = "content-scout-tracked-runs";
const POLL_INTERVAL_MS = 3000;
const MAX_TRACKED = 20;

const TERMINAL = new Set(["done", "failed"]);

export interface TrackedRun {
  run: RunResponse;
  projectId: string;
  projectName: string;
  seen: boolean;
}

interface StoredRunRef {
  runId: string;
  projectId: string;
  projectName: string;
}

interface RunTrackerContextValue {
  trackedRuns: TrackedRun[];
  unseenCount: number;
  track: (run: RunResponse, projectId: string, projectName: string) => void;
  markAllSeen: () => void;
  dismiss: (runId: string) => void;
}

const RunTrackerContext = createContext<RunTrackerContextValue | null>(null);

function loadStoredRefs(): StoredRunRef[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredRunRef[]) : [];
  } catch {
    return [];
  }
}

export function RunTrackerProvider({ children }: { children: React.ReactNode }) {
  const { refreshUser } = useAuth();
  const [runs, setRuns] = useState<Map<string, TrackedRun>>(new Map());
  const runsRef = useRef(runs);
  runsRef.current = runs;
  const bootstrapped = useRef(false);

  // Reload tracked runs (e.g. after a page refresh) from the refs we persisted last time.
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    const refs = loadStoredRefs();
    if (refs.length === 0) return;
    void (async () => {
      const results = await Promise.all(
        refs.map(async (ref) => {
          try {
            return { ref, run: await api.getRun(ref.runId) };
          } catch {
            return null;
          }
        }),
      );
      setRuns((prev) => {
        const next = new Map(prev);
        for (const r of results) {
          if (!r) continue;
          next.set(r.run.id, {
            run: r.run,
            projectId: r.ref.projectId,
            projectName: r.ref.projectName,
            seen: TERMINAL.has(r.run.status),
          });
        }
        return next;
      });
    })();
  }, []);

  // Persist just enough to rebuild state after a reload — live status is always refetched.
  useEffect(() => {
    const refs: StoredRunRef[] = Array.from(runs.values()).map((t) => ({
      runId: t.run.id,
      projectId: t.projectId,
      projectName: t.projectName,
    }));
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(refs));
  }, [runs]);

  // Single poll loop for every in-progress tracked run, regardless of which page is open —
  // this is what lets a run keep reporting progress after its dialog has been closed.
  useEffect(() => {
    const interval = setInterval(() => {
      const inProgress = Array.from(runsRef.current.values()).filter((t) => !TERMINAL.has(t.run.status));
      if (inProgress.length === 0) return;
      void Promise.all(
        inProgress.map(async (t) => {
          try {
            return await api.getRun(t.run.id);
          } catch {
            return null;
          }
        }),
      ).then((updates) => {
        let anyJustFinished = false;
        setRuns((prev) => {
          const next = new Map(prev);
          for (const updated of updates) {
            if (!updated) continue;
            const existing = next.get(updated.id);
            if (!existing) continue;
            const justFinished = !TERMINAL.has(existing.run.status) && TERMINAL.has(updated.status);
            if (justFinished) anyJustFinished = true;
            next.set(updated.id, { ...existing, run: updated, seen: justFinished ? false : existing.seen });
          }
          return next;
        });
        // A run finishing may have spent tokens — keep the header's balance current
        // without waiting for the user to open the usage page.
        if (anyJustFinished) void refreshUser();
      });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refreshUser]);

  const track = useCallback((run: RunResponse, projectId: string, projectName: string) => {
    setRuns((prev) => {
      const next = new Map(prev);
      next.set(run.id, { run, projectId, projectName, seen: TERMINAL.has(run.status) });
      if (next.size > MAX_TRACKED) {
        const oldestTerminal = Array.from(next.values())
          .filter((t) => TERMINAL.has(t.run.status))
          .sort((a, b) => a.run.created_at.localeCompare(b.run.created_at))[0];
        if (oldestTerminal) next.delete(oldestTerminal.run.id);
      }
      return next;
    });
  }, []);

  const markAllSeen = useCallback(() => {
    setRuns((prev) => {
      const next = new Map(prev);
      for (const [id, t] of next) next.set(id, { ...t, seen: true });
      return next;
    });
  }, []);

  const dismiss = useCallback((runId: string) => {
    setRuns((prev) => {
      const next = new Map(prev);
      next.delete(runId);
      return next;
    });
  }, []);

  const trackedRuns = Array.from(runs.values()).sort((a, b) =>
    b.run.created_at.localeCompare(a.run.created_at),
  );
  const unseenCount = trackedRuns.filter((t) => !t.seen).length;

  return (
    <RunTrackerContext.Provider value={{ trackedRuns, unseenCount, track, markAllSeen, dismiss }}>
      {children}
    </RunTrackerContext.Provider>
  );
}

export function useRunTracker(): RunTrackerContextValue {
  const ctx = useContext(RunTrackerContext);
  if (!ctx) throw new Error("useRunTracker must be used within RunTrackerProvider");
  return ctx;
}
