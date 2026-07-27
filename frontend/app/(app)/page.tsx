"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Bell,
  CalendarClock,
  MessageCircle,
  MoreVertical,
  Plus,
  Users,
  FileText,
} from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type ProjectResponse,
  type RunFeedItem,
  type RunResponse,
  type ScheduledFeedItem,
  type ScheduledRunSkipReason,
} from "@/lib/api";
import { RUN_STATUS_DOT, RUN_STATUS_PILL } from "@/lib/format";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { Badge } from "@/components/ui";
import { ContextMenu } from "@/components/ui/context-menu";
import { RunDialog } from "@/components/run-dialog";
import { RunTypePickerSheet } from "@/components/run-type-picker-sheet";
import { ScheduledRunDialog } from "@/components/scheduled-run-dialog";

type View = "feed" | "schedule";
type RunTypeFilter = "all" | "stat_collection" | "deep_analysis";
type RunType = "stat_collection" | "deep_analysis";

const IN_PROGRESS_STATUSES = new Set(["pending", "scraping", "summarizing"]);
const POLL_MS = 5000;

const SKIP_REASON_KEYS: Record<ScheduledRunSkipReason, string> = {
  no_accounts: "skipReasonNoAccounts",
  no_tokens: "skipReasonNoTokens",
  quota_exceeded: "skipReasonQuotaExceeded",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function RunFeedPage() {
  const t = useTranslations("RunFeed");
  const tSched = useTranslations("ScheduledRuns");
  const router = useRouter();
  const { addToast } = useToast();

  const [view, setView] = useState<View>("feed");
  const [filter, setFilter] = useState<RunTypeFilter>("all");
  const [runs, setRuns] = useState<RunFeedItem[] | null>(null);
  const [scheduled, setScheduled] = useState<ScheduledFeedItem[] | null>(null);
  const [lastRuns, setLastRuns] = useState<Record<string, RunResponse>>({});

  // Default project + accounts — needed to open RunDialog
  const [defaultProject, setDefaultProject] = useState<ProjectResponse | null>(null);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [dialogRunType, setDialogRunType] = useState<RunType | null>(null);

  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ScheduledFeedItem | null>(null);
  const [editingAccounts, setEditingAccounts] = useState<AccountResponse[]>([]);
  const [scheduleMenuId, setScheduleMenuId] = useState<string | null>(null);
  const [scheduleMenuAnchorEl, setScheduleMenuAnchorEl] = useState<HTMLElement | null>(null);

  const loadFeed = useCallback(async () => {
    try {
      const [runsData, scheduledData] = await Promise.all([
        api.getRunFeed(),
        api.getScheduledRunFeed(),
      ]);
      setRuns(runsData);
      setScheduled(scheduledData);

      const lastRunIds = [
        ...new Set(
          scheduledData.map((s) => s.last_run_id).filter((id): id is string => id != null),
        ),
      ];
      const lastRunResults = await Promise.all(
        lastRunIds.map((id) => api.getRun(id).catch(() => null)),
      );
      const map: Record<string, RunResponse> = {};
      lastRunResults.forEach((run) => {
        if (run) map[run.id] = run;
      });
      setLastRuns(map);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [t, addToast]);

  async function onOpenSchedule(sr: ScheduledFeedItem) {
    try {
      const accts = await api.listAccounts(sr.project_id);
      setEditingAccounts(accts);
      setEditingSchedule(sr);
      setScheduleDialogOpen(true);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : tSched("genericError"));
    }
  }

  async function onToggleScheduleActive(sr: ScheduledFeedItem) {
    try {
      await api.updateScheduledRun(sr.project_id, sr.id, {
        duration_days: sr.duration_days ?? undefined,
        item_limit: sr.item_limit ?? undefined,
        account_ids: sr.account_ids ?? undefined,
        mode: sr.mode,
        days_of_week: sr.days_of_week,
        time_of_day: sr.time_of_day,
        timezone: sr.timezone,
        active: !sr.active,
        notify_enabled: sr.notify_enabled,
      });
      await loadFeed();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : tSched("genericError"));
    }
  }

  async function onDeleteSchedule(sr: ScheduledFeedItem) {
    setScheduleMenuId(null);
    try {
      await api.deleteScheduledRun(sr.project_id, sr.id);
      await loadFeed();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : tSched("genericError"));
    }
  }

  // Load default project + accounts on mount
  useEffect(() => {
    api
      .listProjects()
      .then((projects) => {
        const active = projects.filter((p) => p.archived_at === null);
        const proj = active[0] ?? projects[0] ?? null;
        setDefaultProject(proj);
        if (proj) {
          return api.listAccounts(proj.id).then(setAccounts);
        }
      })
      .catch(() => {});
  }, []);

  // Load feed on mount
  useEffect(() => {
    void loadFeed();
  }, [loadFeed]);

  // Poll while any run is in progress
  useEffect(() => {
    if (!runs) return;
    const hasInProgress = runs.some((r) => IN_PROGRESS_STATUSES.has(r.status));
    if (!hasInProgress) return;
    const handle = setInterval(() => void loadFeed(), POLL_MS);
    return () => clearInterval(handle);
  }, [runs, loadFeed]);

  function onPickRunType(runType: RunType) {
    setPickerOpen(false);
    setDialogRunType(runType);
  }

  const filteredRuns =
    filter === "all" ? (runs ?? []) : (runs ?? []).filter((r) => r.run_type === filter);

  const hasStatRuns = (runs ?? []).some((r) => r.run_type === "stat_collection");
  const hasDeepRuns = (runs ?? []).some((r) => r.run_type === "deep_analysis");

  const statusLabel: Record<RunFeedItem["status"], string> = {
    pending: t("statusPending"),
    scraping: t("statusScraping"),
    summarizing: t("statusSummarizing"),
    done: t("statusDone"),
    failed: t("statusFailed"),
  };

  return (
    <main
      className="relative mx-auto flex w-full max-w-2xl flex-col gap-4 p-4"
      style={{ paddingBottom: "max(5.5rem, calc(env(safe-area-inset-bottom) + 5.5rem))" }}
    >
      {view === "feed" && (
        <>
          {/* Filter chips + schedule icon */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setFilter("all")}
                className={`rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
                  filter === "all"
                    ? "bg-ink text-white"
                    : "border border-border text-secondary hover:text-ink"
                }`}
              >
                {t("filterAll")}
              </button>
              {hasStatRuns && (
                <button
                  onClick={() => setFilter("stat_collection")}
                  className={`rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
                    filter === "stat_collection"
                      ? "bg-ink text-white"
                      : "border border-border text-secondary hover:text-ink"
                  }`}
                >
                  {t("filterStat")}
                </button>
              )}
              {hasDeepRuns && (
                <button
                  onClick={() => setFilter("deep_analysis")}
                  className={`rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
                    filter === "deep_analysis"
                      ? "bg-ink text-white"
                      : "border border-border text-secondary hover:text-ink"
                  }`}
                >
                  {t("filterDeep")}
                </button>
              )}
            </div>
            <button
              onClick={() => setView("schedule")}
              aria-label={t("scheduleIconLabel")}
              className="inline-flex shrink-0 items-center justify-center rounded-control border border-border p-2.5 text-secondary transition-colors active:scale-[0.98] hover:bg-bg"
            >
              <CalendarClock className="h-4 w-4" />
            </button>
          </div>

          {/* Runs list */}
          {runs === null && <SkeletonList count={4} />}
          {runs !== null && filteredRuns.length === 0 && (
            <p className="py-8 text-center text-sm text-secondary">{t("emptyRuns")}</p>
          )}
          {filteredRuns.length > 0 && (
            <div className="flex flex-col gap-2">
              {filteredRuns.map((run) => (
                <div
                  key={run.id}
                  className="flex overflow-hidden rounded-card border border-border bg-card"
                >
                  <div
                    className={`flex w-[5%] min-w-[22px] shrink-0 items-center justify-center ${
                      run.run_type === "deep_analysis" ? "bg-ink text-lime" : "bg-lime text-ink"
                    }`}
                  >
                    <span className="[writing-mode:vertical-rl] text-[10px] font-semibold tracking-wide">
                      {run.run_type === "deep_analysis" ? t("runTypeDeep") : t("runTypeStat")}
                    </span>
                  </div>
                  <button
                    onClick={() => router.push(`/projects/${run.project_id}/runs/${run.id}`)}
                    className="flex flex-1 flex-col gap-2 px-4 py-3.5 text-left transition-all active:scale-[0.99] hover:bg-bg"
                  >
                    <div className="flex items-center justify-end gap-2">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${
                          RUN_STATUS_PILL[run.status]
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${RUN_STATUS_DOT[run.status]}`} />
                        {statusLabel[run.status]}
                      </span>
                    </div>
                    <p className="font-mono text-sm font-medium text-ink">{formatDate(run.created_at)}</p>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                      <span className="inline-flex items-center gap-1.5 text-xs text-secondary">
                        <Users className="h-3.5 w-3.5" />
                        {t("kpiCompetitors")}{" "}
                        <span className="font-mono font-semibold text-ink">{run.progress_accounts}</span>
                      </span>
                      <span className="inline-flex items-center gap-1.5 text-xs text-secondary">
                        <FileText className="h-3.5 w-3.5" />
                        {t("kpiPublications")}{" "}
                        <span className="font-mono font-semibold text-ink">{run.progress_items}</span>
                      </span>
                      {run.run_type === "deep_analysis" && run.comments_count !== null && (
                        <span className="inline-flex items-center gap-1.5 text-xs text-secondary">
                          <MessageCircle className="h-3.5 w-3.5" />
                          {t("kpiComments")}{" "}
                          <span className="font-mono font-semibold text-ink">{run.comments_count}</span>
                        </span>
                      )}
                    </div>
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {view === "schedule" && (
        <>
          <button
            onClick={() => setView("feed")}
            className="flex w-fit items-center gap-1 text-sm text-secondary transition-colors hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("back")}
          </button>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("tabScheduled")}</h1>

          {scheduled === null && <SkeletonList count={3} />}
          {scheduled !== null && scheduled.length === 0 && (
            <p className="py-8 text-center text-sm text-secondary">{t("emptyScheduled")}</p>
          )}
          {scheduled !== null && scheduled.length > 0 && (
            <div className="flex flex-col gap-2">
              {scheduled.map((sr) => {
                const lastRun = sr.last_run_id ? lastRuns[sr.last_run_id] : undefined;
                const accountsText =
                  sr.account_ids == null
                    ? tSched("allAccounts")
                    : tSched("accountsCount", { count: sr.account_ids.length });
                const daysText = [...sr.days_of_week]
                  .sort((a, b) => a - b)
                  .map((d) => tSched(`weekday${d}`))
                  .join(", ");
                const modeText =
                  sr.mode === "once" ? tSched("repeatModeOnce") : tSched("repeatModeRecurring");

                return (
                  <div
                    key={sr.id}
                    className="flex overflow-hidden rounded-card border border-border bg-card"
                  >
                    <div
                      className={`flex w-[5%] min-w-[22px] shrink-0 items-center justify-center ${
                        sr.run_type === "deep_analysis" ? "bg-ink text-lime" : "bg-lime text-ink"
                      }`}
                    >
                      <span className="[writing-mode:vertical-rl] text-[10px] font-semibold tracking-wide">
                        {sr.run_type === "deep_analysis" ? t("runTypeDeep") : t("runTypeStat")}
                      </span>
                    </div>
                    <div className="flex flex-1 items-start justify-between gap-2 p-4">
                      <button
                        onClick={() => void onOpenSchedule(sr)}
                        className="flex flex-1 flex-col items-start gap-1 text-left"
                      >
                        <span className="text-sm font-semibold text-ink">
                          {daysText} · {sr.time_of_day.slice(0, 5)} · {modeText}
                        </span>
                        <span className="text-xs text-secondary">{accountsText}</span>
                        <span className="text-xs text-secondary">
                          {tSched("lastRunLabel")}:{" "}
                          {lastRun
                            ? formatDate(lastRun.finished_at ?? lastRun.created_at)
                            : tSched("never")}
                        </span>
                        {sr.last_skip_reason && (
                          <span className="text-xs font-medium text-danger">
                            {tSched(SKIP_REASON_KEYS[sr.last_skip_reason])}
                          </span>
                        )}
                        <div className="mt-1 flex items-center gap-2">
                          <Badge variant={sr.active ? "success" : "default"}>
                            {sr.active ? tSched("activeLabel") : tSched("inactiveLabel")}
                          </Badge>
                          {sr.notify_enabled && (
                            <Bell
                              className="h-3.5 w-3.5 text-secondary"
                              aria-label={tSched("notifyBadge")}
                            />
                          )}
                        </div>
                      </button>
                      <button
                        onClick={(e) => {
                          setScheduleMenuId(sr.id);
                          setScheduleMenuAnchorEl(e.currentTarget);
                        }}
                        className="shrink-0 rounded-control p-1.5 text-secondary hover:bg-border transition-colors"
                        aria-label="Действия"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* FAB — available on both the feed and schedule views */}
      <button
        onClick={() => setPickerOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex h-16 w-16 items-center justify-center rounded-full bg-lime shadow-[0_8px_24px_rgba(140,170,20,0.40)] transition-all active:scale-[0.96] hover:opacity-90"
        style={{ bottom: "max(1.5rem, calc(env(safe-area-inset-bottom) + 1.5rem))" }}
        aria-label="Новый запуск"
      >
        <Plus className="h-7 w-7 text-ink" />
      </button>

      {/* Run type picker */}
      {pickerOpen && (
        <RunTypePickerSheet
          onPick={onPickRunType}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {/* Run dialog */}
      {dialogRunType !== null && defaultProject && (
        <RunDialog
          projectId={defaultProject.id}
          projectName={defaultProject.name}
          accounts={accounts}
          runType={dialogRunType}
          onClose={() => {
            setDialogRunType(null);
            void loadFeed();
          }}
        />
      )}

      {/* Scheduled run 3-dot menu */}
      <ContextMenu
        open={scheduleMenuId !== null}
        onClose={() => setScheduleMenuId(null)}
        anchorEl={scheduleMenuAnchorEl}
      >
        <div className="flex flex-col py-1">
          <button
            onClick={() => {
              const sr = scheduled?.find((s) => s.id === scheduleMenuId);
              setScheduleMenuId(null);
              if (sr) void onToggleScheduleActive(sr);
            }}
            className="px-4 py-2.5 text-left text-sm text-ink hover:bg-bg transition-colors"
          >
            {scheduled?.find((s) => s.id === scheduleMenuId)?.active
              ? tSched("deactivateAction")
              : tSched("activateAction")}
          </button>
          <button
            onClick={() => {
              const sr = scheduled?.find((s) => s.id === scheduleMenuId);
              if (sr) void onDeleteSchedule(sr);
            }}
            className="px-4 py-2.5 text-left text-sm text-danger hover:bg-bg transition-colors"
          >
            {tSched("deleteAction")}
          </button>
        </div>
      </ContextMenu>

      {/* Scheduled run edit dialog */}
      {scheduleDialogOpen && editingSchedule && (
        <ScheduledRunDialog
          projectId={editingSchedule.project_id}
          accounts={editingAccounts}
          existing={editingSchedule}
          onClose={() => setScheduleDialogOpen(false)}
          onSaved={() => {
            setScheduleDialogOpen(false);
            void loadFeed();
          }}
        />
      )}
    </main>
  );
}
