"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeft, CalendarClock, MoreVertical, Plus } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type RunResponse,
  type ScheduledRunResponse,
} from "@/lib/api";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ContextMenu } from "@/components/ui/context-menu";
import { useProject } from "@/lib/project-context";
import { ScheduledRunDialog } from "./scheduled-run-dialog";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ScheduledRunsPage() {
  const t = useTranslations("ScheduledRuns");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();
  const { isArchived } = useProject();

  const [scheduledRuns, setScheduledRuns] = useState<ScheduledRunResponse[] | null>(null);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [lastRuns, setLastRuns] = useState<Record<string, RunResponse>>({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ScheduledRunResponse | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);

  const load = useCallback(async () => {
    try {
      const [loadedSchedules, loadedAccounts] = await Promise.all([
        api.listScheduledRuns(params.id),
        api.listAccounts(params.id),
      ]);
      setScheduledRuns(loadedSchedules);
      setAccounts(loadedAccounts);

      const lastRunIds = [
        ...new Set(
          loadedSchedules
            .map((s) => s.last_run_id)
            .filter((id): id is string => id != null),
        ),
      ];
      const runs = await Promise.all(lastRunIds.map((id) => api.getRun(id).catch(() => null)));
      const map: Record<string, RunResponse> = {};
      runs.forEach((run) => {
        if (run) map[run.id] = run;
      });
      setLastRuns(map);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onToggleActive(schedule: ScheduledRunResponse) {
    try {
      await api.updateScheduledRun(params.id, schedule.id, {
        duration_days: schedule.duration_days ?? undefined,
        item_limit: schedule.item_limit ?? undefined,
        account_ids: schedule.account_ids ?? undefined,
        day_of_week: schedule.day_of_week,
        time_of_day: schedule.time_of_day,
        timezone: schedule.timezone,
        active: !schedule.active,
      });
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function onDelete(scheduleId: string) {
    setMenuId(null);
    try {
      await api.deleteScheduledRun(params.id, scheduleId);
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  const menuSchedule = scheduledRuns?.find((s) => s.id === menuId) ?? null;

  return (
    <div className="flex flex-col gap-4">
      <Link
        href={`/projects/${params.id}/details`}
        className="flex items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backToDetails")}
      </Link>

      {!isArchived && (
        <div className="flex items-center justify-end">
          <button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
            className="flex items-center gap-1.5 rounded-control border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-bg transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t("createButton")}
          </button>
        </div>
      )}

      {scheduledRuns === null && <SkeletonList count={3} />}

      {scheduledRuns !== null && scheduledRuns.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-card py-12 text-center">
          <CalendarClock className="h-10 w-10 text-border" />
          <p className="text-sm font-medium text-ink">{t("empty")}</p>
        </div>
      )}

      {scheduledRuns !== null && scheduledRuns.length > 0 && (
        <ul className="flex flex-col gap-2">
          {scheduledRuns.map((s) => {
            const lastRun = s.last_run_id ? lastRuns[s.last_run_id] : undefined;
            const scopeText =
              s.duration_days != null
                ? t("scopeDays", { count: s.duration_days })
                : t("scopeCount", { count: s.item_limit ?? 0 });
            const accountsText =
              s.account_ids == null
                ? t("allAccounts")
                : t("accountsCount", { count: s.account_ids.length });

            return (
              <li
                key={s.id}
                className="flex flex-col gap-2 rounded-card border border-border bg-card p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <button
                    onClick={() => {
                      setEditing(s);
                      setDialogOpen(true);
                    }}
                    className="flex flex-1 flex-col items-start gap-1 text-left"
                  >
                    <span className="text-sm font-semibold text-ink">
                      {t(`weekday${s.day_of_week}`)}, {s.time_of_day.slice(0, 5)}
                    </span>
                    <span className="text-xs text-secondary">
                      {scopeText} · {accountsText}
                    </span>
                    <span className="text-xs text-secondary">
                      {t("lastRunLabel")}:{" "}
                      {lastRun ? formatDate(lastRun.finished_at ?? lastRun.created_at) : t("never")}
                    </span>
                  </button>
                  {!isArchived && (
                    <button
                      onClick={(e) => {
                        setMenuId(s.id);
                        setMenuAnchorEl(e.currentTarget);
                      }}
                      className="rounded-control p-1.5 text-secondary hover:bg-border transition-colors"
                      aria-label="Действия"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={s.active}
                    disabled={isArchived}
                    onChange={() => void onToggleActive(s)}
                    className="h-4 w-4 rounded border-border accent-accent"
                  />
                  {t("activeLabel")}
                </label>
              </li>
            );
          })}
        </ul>
      )}

      {dialogOpen && (
        <ScheduledRunDialog
          projectId={params.id}
          accounts={accounts}
          existing={editing}
          onClose={() => setDialogOpen(false)}
          onSaved={() => {
            setDialogOpen(false);
            void load();
          }}
        />
      )}

      <ContextMenu
        open={menuId !== null}
        onClose={() => setMenuId(null)}
        title={menuSchedule ? `${t(`weekday${menuSchedule.day_of_week}`)}, ${menuSchedule.time_of_day.slice(0, 5)}` : undefined}
        anchorEl={menuAnchorEl}
      >
        <div className="flex flex-col py-1">
          <button
            onClick={() => menuSchedule && void onDelete(menuSchedule.id)}
            className="px-4 py-2.5 text-left text-sm text-danger hover:bg-bg transition-colors"
          >
            {t("deleteAction")}
          </button>
        </div>
      </ContextMenu>
    </div>
  );
}
