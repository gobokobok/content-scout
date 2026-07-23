"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeft, Check, Users } from "lucide-react";
import { api, ApiError, type AccountResponse, type ScheduledRunResponse } from "@/lib/api";
import { formatFollowers } from "@/lib/format";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Segmented } from "@/components/ui";

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];
const ITEM_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
const DEFAULT_TIMEZONE = "Europe/Moscow";
type ScopeMode = "days" | "count";
type View = "form" | "pickCompetitors";

function toTimeInputValue(timeOfDay: string): string {
  return timeOfDay.slice(0, 5);
}

function chipClass(active: boolean): string {
  return `h-10 min-w-10 rounded-[10px] px-2 font-mono text-[13px] font-medium transition-all active:scale-[0.98] ${
    active ? "bg-ink text-lime font-semibold" : "border border-border text-ink hover:bg-bg"
  }`;
}

export function ScheduledRunDialog({
  projectId,
  accounts,
  existing,
  onClose,
  onSaved,
}: {
  projectId: string;
  accounts: AccountResponse[];
  existing: ScheduledRunResponse | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("ScheduledRuns");
  const isEdit = existing != null;

  const [view, setView] = useState<View>("form");
  const [scopeMode, setScopeMode] = useState<ScopeMode>(
    existing?.item_limit != null ? "count" : "days",
  );
  const [duration, setDuration] = useState(existing?.duration_days ?? 3);
  const [itemLimit, setItemLimit] = useState(existing?.item_limit ?? 10);
  const [allAccounts, setAllAccounts] = useState(existing?.account_ids == null);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(
    existing?.account_ids ?? [],
  );
  // Create mode: multi-day selection (one ScheduledRun row is created per day).
  // Edit mode: a single existing row only ever has one day.
  const [selectedDays, setSelectedDays] = useState<number[]>(
    existing ? [existing.day_of_week] : [],
  );
  const [timeOfDay, setTimeOfDay] = useState(
    existing ? toTimeInputValue(existing.time_of_day) : "09:00",
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  function toggleAccount(id: string) {
    setSelectedAccountIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function toggleDay(d: number) {
    if (isEdit) {
      setSelectedDays([d]);
      return;
    }
    setSelectedDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));
  }

  async function onSave(active: boolean) {
    setError(null);
    if (selectedDays.length === 0) {
      setError(t("selectDayError"));
      return;
    }
    if (!allAccounts && selectedAccountIds.length === 0) {
      setError(t("selectCompetitorsError"));
      return;
    }
    setSaving(true);
    const base = {
      duration_days: scopeMode === "days" ? duration : undefined,
      item_limit: scopeMode === "count" ? itemLimit : undefined,
      account_ids: allAccounts ? undefined : selectedAccountIds,
      time_of_day: `${timeOfDay}:00`,
      timezone: existing?.timezone ?? DEFAULT_TIMEZONE,
      active,
    };
    try {
      if (existing) {
        await api.updateScheduledRun(projectId, existing.id, {
          ...base,
          day_of_week: selectedDays[0],
        });
      } else {
        // One row per selected weekday — the API has no concept of a multi-day schedule.
        for (const day of selectedDays) {
          await api.createScheduledRun(projectId, { ...base, day_of_week: day });
        }
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSaving(false);
    }
  }

  if (view === "pickCompetitors") {
    return (
      <BottomSheet open onClose={onClose} title={t("selectCompetitorsTitle")}>
        <div className="flex flex-col gap-3 p-4">
          <button
            onClick={() => setView("form")}
            className="flex w-fit items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("backToForm")}
          </button>

          <div className="flex flex-col overflow-hidden rounded-card border border-border">
            {accounts.length === 0 && (
              <p className="p-4 text-sm text-secondary">{t("noAccounts")}</p>
            )}
            {accounts.map((a, idx) => {
              const selected = selectedAccountIds.includes(a.id);
              return (
                <button
                  key={a.id}
                  onClick={() => toggleAccount(a.id)}
                  className={`flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg ${
                    idx < accounts.length - 1 ? "border-b border-border" : ""
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                      selected ? "border-ink bg-ink text-lime" : "border-border text-transparent"
                    }`}
                  >
                    <Check className="h-3.5 w-3.5" />
                  </span>
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-bg">
                    {a.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element -- external, unpredictable CDN host
                      <img src={a.avatar_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <Users className="h-4 w-4 text-secondary" />
                    )}
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-sm font-medium text-ink">
                      {a.display_name || `@${a.handle}`}
                    </span>
                    <span className="truncate text-xs text-secondary">
                      @{a.handle}
                      {a.followers_count != null &&
                        ` · ${formatFollowers(a.followers_count)} ${t("followersShort")}`}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setView("form")}
            className="rounded-chip bg-lime px-4 py-3 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98]"
          >
            {t("selectedCompetitorsCount", { count: selectedAccountIds.length })} · {t("doneButton")}
          </button>
        </div>
      </BottomSheet>
    );
  }

  return (
    <BottomSheet open onClose={onClose} title={existing ? t("editTitle") : t("createTitle")}>
      <div className="flex flex-col gap-5 p-4">
        {/* Period */}
        <div className="flex flex-col gap-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
            {t("step1Title")}
          </span>
          <Segmented
            value={scopeMode}
            onChange={setScopeMode}
            options={[
              { value: "days", label: t("scopeModeDays") },
              { value: "count", label: t("scopeModeCount") },
            ]}
          />
          {scopeMode === "days" ? (
            <div className="grid grid-cols-7 gap-1.5">
              {DAY_OPTIONS.map((d) => (
                <button key={d} onClick={() => setDuration(d)} className={chipClass(duration === d)}>
                  {d}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {ITEM_LIMIT_OPTIONS.map((n) => (
                <button key={n} onClick={() => setItemLimit(n)} className={chipClass(itemLimit === n)}>
                  {n}
                </button>
              ))}
            </div>
          )}
          <p className="text-xs text-secondary">
            {scopeMode === "days"
              ? t("scopeDaysExplanation", { count: duration })
              : t("scopeCountExplanation", { count: itemLimit })}
          </p>
        </div>

        {/* Competitors */}
        <div className="flex flex-col gap-2.5 border-t border-border pt-5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
            {t("step2Title")}
          </span>
          <Segmented
            value={allAccounts ? "all" : "select"}
            onChange={(v) => {
              if (v === "all") setAllAccounts(true);
              else { setAllAccounts(false); setView("pickCompetitors"); }
            }}
            options={[
              { value: "all", label: t("allAccounts") },
              { value: "select", label: t("selectCompetitorsButton") },
            ]}
          />
          {!allAccounts && (
            <button
              onClick={() => setView("pickCompetitors")}
              className="w-fit text-sm font-medium text-accent hover:underline"
            >
              {t("selectedCompetitorsCount", { count: selectedAccountIds.length })}
            </button>
          )}
        </div>

        {/* Schedule */}
        <div className="flex flex-col gap-2.5 border-t border-border pt-5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
            {t("step3Title")}
          </span>
          <div className="flex flex-col gap-3 rounded-[14px] bg-bg p-3">
            <div className="grid grid-cols-7 gap-1.5">
              {WEEKDAYS.map((d) => (
                <button key={d} onClick={() => toggleDay(d)} className={chipClass(selectedDays.includes(d))}>
                  {t(`weekday${d}`)}
                </button>
              ))}
            </div>
            <input
              type="time"
              value={timeOfDay}
              onChange={(e) => setTimeOfDay(e.target.value)}
              className="w-full rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="flex flex-col gap-2">
          <button
            onClick={() => void onSave(true)}
            disabled={saving}
            className="w-full rounded-chip bg-lime px-4 py-3 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {saving ? t("saving") : t("saveAndActivate")}
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              disabled={saving}
              className="flex-1 rounded-chip border border-border px-4 py-2 text-sm font-medium text-ink transition-all active:scale-[0.98] hover:bg-bg disabled:opacity-50"
            >
              {t("cancel")}
            </button>
            <button
              onClick={() => void onSave(false)}
              disabled={saving}
              className="flex-1 rounded-chip border border-border px-4 py-2 text-sm font-medium text-ink transition-all active:scale-[0.98] hover:bg-bg disabled:opacity-50"
            >
              {t("saveAsDraft")}
            </button>
          </div>
        </div>
      </div>
    </BottomSheet>
  );
}
