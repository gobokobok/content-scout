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
import {
  DEEP_ANALYSIS_STATUS_DOT,
  DEEP_ANALYSIS_STATUS_PILL,
  RUN_STATUS_DOT,
  RUN_STATUS_PILL,
} from "@/lib/format";
import { SkeletonList } from "@/components/ui/skeleton";
import { BottomSheet } from "@/components/ui/bottom-sheet";
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
  const tProjects = useTranslations("Projects");
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
  // Distinguishes "still loading" from "confirmed zero projects" — a brand-new account has no
  // project yet and nothing else in this app can create the first one, so this page must.
  const [projectsChecked, setProjectsChecked] = useState(false);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);

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

  function onOpenRun(run: RunFeedItem) {
    // A deep_analysis run whose auto-chained DeepAnalysis already exists opens its report
    // (Статистика/Рекомендации) directly instead of the base run's Резюме/Публикации view —
    // the DeepAnalysis isn't created until the base scrape finishes, so this still falls back
    // to the run detail page while it's in progress or if the auto-chain hasn't fired yet.
    if (run.run_type === "deep_analysis" && run.deep_analysis_id) {
      router.push(`/projects/${run.project_id}/deep-analyses/${run.deep_analysis_id}`);
    } else {
      router.push(`/projects/${run.project_id}/runs/${run.id}`);
    }
  }

  const loadDefaultProject = useCallback(async () => {
    try {
      const projects = await api.listProjects();
      const active = projects.filter((p) => p.archived_at === null);
      const proj = active[0] ?? projects[0] ?? null;
      setDefaultProject(proj);
      if (proj) {
        setAccounts(await api.listAccounts(proj.id));
      }
    } catch {
      // Loading state below just resolves to "no project" — a real error would already have
      // surfaced via loadFeed's own toast, no need to duplicate it here.
    } finally {
      setProjectsChecked(true);
    }
  }, []);

  // Load default project + accounts on mount
  useEffect(() => {
    void loadDefaultProject();
  }, [loadDefaultProject]);

  async function onCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreatingProject(true);
    try {
      await api.createProject(newProjectName.trim());
      setNewProjectName("");
      setCreateProjectOpen(false);
      await loadDefaultProject();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setCreatingProject(false);
    }
  }

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

  const deepAnalysisStatusLabel: Record<
    NonNullable<RunFeedItem["deep_analysis_status"]>,
    string
  > = {
    pending: t("statusPending"),
    extracting: t("statusExtracting"),
    synthesizing: t("statusSynthesizing"),
    done: t("statusDone"),
    failed: t("statusFailed"),
  };

  // A deep_analysis run can finish its base scrape cleanly (status=done) while the analysis
  // itself is still processing or has failed — once the DeepAnalysis exists, its own status is
  // what the user actually cares about, not the base run's.
  function effectiveStatus(run: RunFeedItem) {
    if (run.run_type === "deep_analysis" && run.deep_analysis_status) {
      return {
        label: deepAnalysisStatusLabel[run.deep_analysis_status],
        pillClass: DEEP_ANALYSIS_STATUS_PILL[run.deep_analysis_status],
        dotClass: DEEP_ANALYSIS_STATUS_DOT[run.deep_analysis_status],
      };
    }
    return {
      label: statusLabel[run.status],
      pillClass: RUN_STATUS_PILL[run.status],
      dotClass: RUN_STATUS_DOT[run.status],
    };
  }

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

          {/* No project yet — nothing else in the app can create the first one, so this is
              the only path a brand-new account has to get started. */}
          {projectsChecked && !defaultProject && (
            <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-card px-4 py-8 text-center">
              <p className="text-sm text-secondary">{tProjects("emptyHint")}</p>
              <button
                onClick={() => setCreateProjectOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-chip bg-lime px-4 py-2.5 text-sm font-semibold text-ink shadow-[0_6px_16px_rgba(140,170,20,0.28)] transition-all active:scale-[0.98] hover:opacity-90"
              >
                <Plus className="h-4 w-4" />
                {tProjects("createButton")}
              </button>
            </div>
          )}

          {/* Runs list */}
          {runs === null && <SkeletonList count={4} />}
          {runs !== null && (defaultProject || !projectsChecked) && filteredRuns.length === 0 && (
            <p className="py-8 text-center text-sm text-secondary">{t("emptyRuns")}</p>
          )}
          {filteredRuns.length > 0 && (
            <div className="flex flex-col gap-2">
              {filteredRuns.map((run) => {
                const status = effectiveStatus(run);
                return (
                <div
                  key={run.id}
                  className="flex overflow-hidden rounded-card border border-border bg-card"
                >
                  <div
                    className={`flex w-[5%] min-w-[22px] shrink-0 items-center justify-center ${
                      run.run_type === "deep_analysis" ? "bg-ink text-lime" : "bg-lime text-ink"
                    }`}
                  >
                    <span className="[writing-mode:vertical-rl] rotate-180 text-[10px] font-semibold tracking-wide">
                      {run.run_type === "deep_analysis" ? t("runTypeDeep") : t("runTypeStat")}
                    </span>
                  </div>
                  <button
                    onClick={() => onOpenRun(run)}
                    className="flex flex-1 flex-col gap-2 px-4 py-3.5 text-left transition-all active:scale-[0.99] hover:bg-bg"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-mono text-sm font-medium text-ink">
                        {formatDate(run.created_at)}
                      </p>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${status.pillClass}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${status.dotClass}`} />
                        {status.label}
                      </span>
                    </div>
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
                    {run.deep_analysis_skip_reason && (
                      <p className="text-xs font-medium text-danger">
                        {run.deep_analysis_skip_reason === "insufficient_tokens"
                          ? t("deepAnalysisSkipInsufficientTokens")
                          : t("deepAnalysisSkipError")}
                      </p>
                    )}
                  </button>
                </div>
                );
              })}
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
                      <span className="[writing-mode:vertical-rl] rotate-180 text-[10px] font-semibold tracking-wide">
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
                          <Badge variant={sr.active ? "success" : "muted"}>
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

      {/* FAB — available on both the feed and schedule views. A brand-new account has no
          project yet, and every run-creation path needs one, so the FAB opens project creation
          first instead of a picker that would silently go nowhere. */}
      <button
        onClick={() => (defaultProject ? setPickerOpen(true) : setCreateProjectOpen(true))}
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

      {/* First-project onboarding — shown once the initial project check resolves to zero
          projects; opened from the empty-state card below or directly from the FAB. */}
      <BottomSheet
        open={createProjectOpen}
        onClose={() => { setCreateProjectOpen(false); setNewProjectName(""); }}
        title={tProjects("createSheetTitle")}
      >
        <form onSubmit={(e) => void onCreateProject(e)} className="flex flex-col gap-3 px-4 pb-4">
          <input
            autoFocus
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder={tProjects("namePlaceholder")}
            className="w-full rounded-control border border-border bg-bg px-3 py-3 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={creatingProject || !newProjectName.trim()}
              className="flex-1 rounded-chip bg-lime py-3 text-sm font-semibold text-ink shadow-[0_6px_16px_rgba(140,170,20,0.28)] transition-all active:scale-[0.98] disabled:opacity-50 disabled:shadow-none"
            >
              {tProjects("createSubmit")}
            </button>
            <button
              type="button"
              onClick={() => { setCreateProjectOpen(false); setNewProjectName(""); }}
              className="flex-1 rounded-chip border border-border py-3 text-sm font-medium text-ink transition-all active:scale-[0.98] hover:bg-bg"
            >
              {tProjects("createCancel")}
            </button>
          </div>
        </form>
      </BottomSheet>

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
