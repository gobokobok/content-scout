"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type AccountResponse, type ScheduledRunResponse } from "@/lib/api";
import { BottomSheet } from "@/components/ui/bottom-sheet";

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];
const ITEM_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
const DEFAULT_TIMEZONE = "Europe/Moscow";
type ScopeMode = "days" | "count";

function toTimeInputValue(timeOfDay: string): string {
  return timeOfDay.slice(0, 5);
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
  const [scopeMode, setScopeMode] = useState<ScopeMode>(
    existing?.item_limit != null ? "count" : "days",
  );
  const [duration, setDuration] = useState(existing?.duration_days ?? 3);
  const [itemLimit, setItemLimit] = useState(existing?.item_limit ?? 10);
  const [allAccounts, setAllAccounts] = useState(existing?.account_ids == null);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(
    existing?.account_ids ?? [],
  );
  const [dayOfWeek, setDayOfWeek] = useState(existing?.day_of_week ?? 0);
  const [timeOfDay, setTimeOfDay] = useState(
    existing ? toTimeInputValue(existing.time_of_day) : "09:00",
  );
  const [active, setActive] = useState(existing?.active ?? true);
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

  async function onSave() {
    setSaving(true);
    setError(null);
    const body = {
      duration_days: scopeMode === "days" ? duration : undefined,
      item_limit: scopeMode === "count" ? itemLimit : undefined,
      account_ids: allAccounts ? undefined : selectedAccountIds,
      day_of_week: dayOfWeek,
      time_of_day: `${timeOfDay}:00`,
      timezone: existing?.timezone ?? DEFAULT_TIMEZONE,
      active,
    };
    try {
      if (existing) {
        await api.updateScheduledRun(projectId, existing.id, body);
      } else {
        await api.createScheduledRun(projectId, body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheet open onClose={onClose} title={existing ? t("editTitle") : t("createTitle")}>
      <div className="flex flex-col gap-4 p-4">
        {/* Scope mode toggle: day window vs. last-N publications */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-secondary">{t("scopeLabel")}</span>
          <div className="inline-flex self-start rounded-control border border-border p-0.5">
            {(["days", "count"] as ScopeMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setScopeMode(mode)}
                className={`rounded-control px-3 py-1.5 text-sm font-medium transition-colors ${
                  scopeMode === mode ? "bg-accent text-white" : "text-secondary hover:text-ink"
                }`}
              >
                {mode === "days" ? t("scopeModeDays") : t("scopeModeCount")}
              </button>
            ))}
          </div>
          {scopeMode === "days" ? (
            <div className="flex flex-wrap gap-2">
              {DAY_OPTIONS.map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  className={`h-10 w-10 rounded-control text-sm font-medium transition-colors ${
                    duration === d
                      ? "bg-accent text-white"
                      : "border border-border text-ink hover:bg-bg"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {ITEM_LIMIT_OPTIONS.map((n) => (
                <button
                  key={n}
                  onClick={() => setItemLimit(n)}
                  className={`h-10 min-w-10 rounded-control px-2 text-sm font-medium transition-colors ${
                    itemLimit === n
                      ? "bg-accent text-white"
                      : "border border-border text-ink hover:bg-bg"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Competitor multiselect */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-secondary">{t("accountsLabel")}</span>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={allAccounts}
              onChange={(e) => setAllAccounts(e.target.checked)}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            {t("allAccounts")}
          </label>
          {!allAccounts && (
            <div className="flex max-h-48 flex-col gap-1 overflow-y-auto rounded-control border border-border p-2">
              {accounts.length === 0 && (
                <p className="text-sm text-secondary">{t("noAccounts")}</p>
              )}
              {accounts.map((a) => (
                <label key={a.id} className="flex items-center gap-2 py-1 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={selectedAccountIds.includes(a.id)}
                    onChange={() => toggleAccount(a.id)}
                    className="h-4 w-4 rounded border-border accent-accent"
                  />
                  {a.display_name || `@${a.handle}`}
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Day of week */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-secondary">{t("dayOfWeekLabel")}</span>
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map((d) => (
              <button
                key={d}
                onClick={() => setDayOfWeek(d)}
                className={`h-10 min-w-10 rounded-control px-2 text-sm font-medium transition-colors ${
                  dayOfWeek === d
                    ? "bg-accent text-white"
                    : "border border-border text-ink hover:bg-bg"
                }`}
              >
                {t(`weekday${d}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Time of day */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-secondary">{t("timeOfDayLabel")}</span>
          <input
            type="time"
            value={timeOfDay}
            onChange={(e) => setTimeOfDay(e.target.value)}
            className="w-full rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>

        {existing && (
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            {t("activeLabel")}
          </label>
        )}

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 rounded-control border border-border px-4 py-2.5 text-sm text-ink hover:bg-bg"
          >
            {t("cancel")}
          </button>
          <button
            onClick={() => void onSave()}
            disabled={saving}
            className="flex-1 rounded-control bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? t("saving") : t("saveButton")}
          </button>
        </div>
      </div>
    </BottomSheet>
  );
}
