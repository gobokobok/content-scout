"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeft, Check, Link2, Plus, Users } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type AnalysisMode,
  type ScheduledRunResponse,
} from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { formatFollowers } from "@/lib/format";
import { detectLocalTimezone } from "@/lib/telegram-webapp";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Segmented } from "@/components/ui";

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];
const ITEM_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const COMMENTS_LIMIT_OPTIONS = [5, 10, 15, 25];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
type ScopeMode = "days" | "count";
type RepeatMode = "once" | "recurring";
type View = "form" | "pickCompetitors" | "addCompetitor";

function toTimeInputValue(timeOfDay: string): string {
  return timeOfDay.slice(0, 5);
}

function chipClass(active: boolean): string {
  return `h-10 min-w-10 rounded-[10px] px-2 font-mono text-[13px] font-medium transition-all active:scale-[0.98] ${
    active ? "bg-ink text-lime font-semibold" : "border border-border text-ink hover:bg-bg"
  }`;
}

function ToggleSwitch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-sm font-medium text-ink">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
          checked ? "bg-lime" : "bg-border"
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
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
  const tRunDialog = useTranslations("RunDialog");
  const tCompetitors = useTranslations("Competitors");
  const { addToast } = useToast();

  // New schedules are always created as stat_collection here (this page's own "+" button has
  // no mode picker) — deep_analysis schedules only ever originate from RunDialog's own
  // schedule option. This dialog still needs to correctly *edit* one, though.
  const isDeepAnalysis = existing?.run_type === "deep_analysis";
  const [view, setView] = useState<View>("form");
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>(existing?.analysis_mode ?? "account");
  const [postUrl, setPostUrl] = useState(existing?.target_post_url ?? "");
  const [commentsLimit, setCommentsLimit] = useState(existing?.comments_limit ?? 15);
  const [scopeMode, setScopeMode] = useState<ScopeMode>(
    existing?.item_limit != null ? "count" : "days",
  );
  const [duration, setDuration] = useState(existing?.duration_days ?? 3);
  const [itemLimit, setItemLimit] = useState(existing?.item_limit ?? 10);
  const [localAccounts, setLocalAccounts] = useState<AccountResponse[]>(accounts);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(
    existing?.account_ids ?? (isDeepAnalysis ? [] : accounts.map((a) => a.id)),
  );
  const [addText, setAddText] = useState("");
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addErrors, setAddErrors] = useState<{ input: string; message_ru: string }[]>([]);
  const [repeatMode, setRepeatMode] = useState<RepeatMode>(existing?.mode ?? "recurring");
  const [selectedDays, setSelectedDays] = useState<number[]>(existing?.days_of_week ?? []);
  const [timeOfDay, setTimeOfDay] = useState(
    existing ? toTimeInputValue(existing.time_of_day) : "09:00",
  );
  const [notifyEnabled, setNotifyEnabled] = useState(existing?.notify_enabled ?? false);
  // Existing schedules keep whatever timezone they were created with; new ones use the
  // device's own IANA zone (Telegram exposes no account-level timezone — see
  // lib/telegram-webapp.ts:detectLocalTimezone).
  const [timezone] = useState(() => existing?.timezone ?? detectLocalTimezone());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  function toggleAccount(id: string) {
    if (isDeepAnalysis && analysisMode === "account") {
      setSelectedAccountIds((prev) => (prev.includes(id) ? [] : [id]));
      return;
    }
    setSelectedAccountIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  async function onAddCompetitor(e: React.FormEvent) {
    e.preventDefault();
    const entries = addText.split("\n").map((line) => line.trim()).filter(Boolean);
    if (entries.length === 0) return;
    setAddSubmitting(true);
    setAddErrors([]);
    try {
      const result = await api.addAccounts(projectId, entries);
      setAddErrors(result.errors);
      setAddText("");
      if (result.added.length > 0) {
        setLocalAccounts((prev) => [...prev, ...result.added]);
        setSelectedAccountIds((prev) =>
          isDeepAnalysis && analysisMode === "account"
            ? [result.added[0].id]
            : [...prev, ...result.added.map((a) => a.id)],
        );
        addToast(tCompetitors("addedCount", { count: result.added.length }));
        setView("pickCompetitors");
      }
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : tCompetitors("genericError"));
    } finally {
      setAddSubmitting(false);
    }
  }

  function toggleDay(d: number) {
    if (repeatMode === "once") {
      setSelectedDays([d]);
      return;
    }
    setSelectedDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));
  }

  function onRepeatModeChange(mode: RepeatMode) {
    setRepeatMode(mode);
    if (mode === "once" && selectedDays.length > 1) {
      setSelectedDays((prev) => prev.slice(0, 1));
    }
  }

  async function onSave(active: boolean) {
    setError(null);
    if (selectedDays.length === 0) {
      setError(t("selectDayError"));
      return;
    }
    if (isDeepAnalysis && analysisMode === "account" && selectedAccountIds.length !== 1) {
      setError(tRunDialog("selectAccountError"));
      return;
    }
    if (isDeepAnalysis && analysisMode === "post" && !postUrl.trim()) {
      setError(tRunDialog("postUrlRequiredError"));
      return;
    }
    if (!isDeepAnalysis && selectedAccountIds.length === 0) {
      setError(t("selectCompetitorsError"));
      return;
    }
    setSaving(true);
    const scopeFields =
      isDeepAnalysis && analysisMode === "post"
        ? {
            duration_days: undefined,
            item_limit: undefined,
            account_ids: undefined,
            analysis_mode: "post" as const,
            target_post_url: postUrl.trim(),
            comments_limit: commentsLimit,
          }
        : {
            duration_days: scopeMode === "days" ? duration : undefined,
            item_limit: scopeMode === "count" ? itemLimit : undefined,
            account_ids: selectedAccountIds,
            analysis_mode: isDeepAnalysis ? ("account" as const) : undefined,
            target_post_url: undefined,
            comments_limit: undefined,
          };
    const base = {
      ...scopeFields,
      // Bug fix: this dialog never sent run_type on save, so ScheduledRunIn's default
      // ("stat_collection") silently overwrote a deep_analysis schedule's type on every edit.
      run_type: existing?.run_type ?? "stat_collection",
      mode: repeatMode,
      days_of_week: selectedDays,
      time_of_day: `${timeOfDay}:00`,
      timezone,
      active,
      notify_enabled: notifyEnabled,
    };
    try {
      if (existing) {
        await api.updateScheduledRun(projectId, existing.id, base);
      } else {
        await api.createScheduledRun(projectId, base);
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

          <button
            onClick={() => setView("addCompetitor")}
            className="flex items-center gap-3 rounded-card border border-dashed border-accent/40 bg-accent-soft px-4 py-3 text-left text-accent transition-colors active:scale-[0.99] hover:bg-accent-soft/80"
          >
            <Plus className="h-4 w-4 shrink-0" />
            <span className="text-sm font-semibold">{tCompetitors("addCompetitorButton")}</span>
          </button>

          <div className="flex shrink-0 flex-col overflow-hidden rounded-card border border-border">
            {localAccounts.length === 0 && (
              <p className="p-4 text-sm text-secondary">{t("noAccounts")}</p>
            )}
            {localAccounts.map((a, idx) => {
              const selected = selectedAccountIds.includes(a.id);
              return (
                <button
                  key={a.id}
                  onClick={() => toggleAccount(a.id)}
                  className={`flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg ${
                    idx < localAccounts.length - 1 ? "border-b border-border" : ""
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

  if (view === "addCompetitor") {
    return (
      <BottomSheet open onClose={onClose} title={tCompetitors("addSheetTitle")}>
        <div className="flex flex-col gap-3 p-4">
          <button
            onClick={() => {
              setView("pickCompetitors");
              setAddText("");
              setAddErrors([]);
            }}
            className="flex w-fit items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("backToForm")}
          </button>

          <form onSubmit={(e) => void onAddCompetitor(e)} className="flex flex-col gap-3">
            <textarea
              value={addText}
              onChange={(e) => setAddText(e.target.value)}
              placeholder={tCompetitors("textareaPlaceholder")}
              rows={5}
              autoFocus
              className="w-full resize-none rounded-control border border-border bg-bg px-3 py-2 text-base text-ink placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            {addErrors.length > 0 && (
              <ul className="flex flex-col gap-1">
                {addErrors.map((e, i) => (
                  <li key={i} className="text-sm text-danger">
                    {e.input}: {e.message_ru}
                  </li>
                ))}
              </ul>
            )}
            <button
              type="submit"
              disabled={addSubmitting || !addText.trim()}
              className="rounded-chip bg-lime px-4 py-3 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98] disabled:opacity-50"
            >
              {addSubmitting ? tCompetitors("adding") : tCompetitors("addButton")}
            </button>
          </form>
        </div>
      </BottomSheet>
    );
  }

  return (
    <BottomSheet open onClose={onClose} title={existing ? t("editTitle") : t("createTitle")}>
      <div className="flex flex-col gap-5 p-4">
        {/* Analysis mode (Analysis schedules only) */}
        {isDeepAnalysis && (
          <div className="flex flex-col gap-2.5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {tRunDialog("analysisModeLabel")}
            </span>
            <Segmented
              value={analysisMode}
              onChange={(mode) => {
                setAnalysisMode(mode);
                setSelectedAccountIds([]);
              }}
              options={[
                { value: "account", label: tRunDialog("analysisModeAccount") },
                { value: "post", label: tRunDialog("analysisModePost") },
              ]}
            />
          </div>
        )}

        {/* Period (account mode only) */}
        {(!isDeepAnalysis || analysisMode === "account") && (
          <div className="flex flex-col gap-2.5 pt-7 first:pt-0">
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
        )}

        {/* Competitors (account mode: pick exactly one for Analysis) */}
        {(!isDeepAnalysis || analysisMode === "account") && (
          <div className="flex flex-col gap-2.5 pt-7">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {isDeepAnalysis ? tRunDialog("accountStepLabel") : t("step2Title")}
            </span>
            <button
              onClick={() => setView("pickCompetitors")}
              className="flex items-center justify-between gap-2 rounded-control border border-border px-3.5 py-3 text-left transition-colors hover:bg-bg"
            >
              <span className="flex items-center gap-2 text-sm font-medium text-ink">
                <Users className="h-4 w-4 text-secondary" />
                {isDeepAnalysis ? tRunDialog("chooseAccountButton") : t("addCompetitorsButton")}
              </span>
              <span className="text-xs text-secondary">
                {isDeepAnalysis
                  ? (localAccounts.find((a) => a.id === selectedAccountIds[0])?.display_name ??
                    (selectedAccountIds[0]
                      ? `@${localAccounts.find((a) => a.id === selectedAccountIds[0])?.handle}`
                      : tRunDialog("noAccountSelected")))
                  : t("selectedCompetitorsCount", { count: selectedAccountIds.length })}
              </span>
            </button>
          </div>
        )}

        {/* Publication URL (post mode only) */}
        {isDeepAnalysis && analysisMode === "post" && (
          <div className="flex flex-col gap-2.5 pt-7">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {tRunDialog("postUrlLabel")}
            </span>
            <div className="flex items-center gap-2 rounded-control border border-border px-3.5 py-2.5">
              <Link2 className="h-4 w-4 shrink-0 text-secondary" />
              <input
                type="url"
                value={postUrl}
                onChange={(e) => setPostUrl(e.target.value)}
                placeholder={tRunDialog("postUrlPlaceholder")}
                className="w-full bg-transparent text-sm text-ink placeholder:text-secondary focus:outline-none"
              />
            </div>
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {tRunDialog("commentsLimitLabel")}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {COMMENTS_LIMIT_OPTIONS.map((n) => (
                <button
                  key={n}
                  onClick={() => setCommentsLimit(n)}
                  className={chipClass(commentsLimit === n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Schedule */}
        <div className="flex flex-col gap-2.5 pt-7">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
            {t("step3Title")}
          </span>
          <div className="flex flex-col gap-3 rounded-[14px] bg-bg p-3">
            <ToggleSwitch
              checked={repeatMode === "recurring"}
              onChange={() => onRepeatModeChange(repeatMode === "recurring" ? "once" : "recurring")}
              label={t("repeatModeToggleLabel")}
            />
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
            <p className="text-xs text-secondary">{t("timezoneHint", { timezone })}</p>
            <p className="text-xs text-secondary">
              {repeatMode === "once" ? t("repeatModeOnceHint") : t("repeatModeRecurringHint")}
            </p>
            <div className="pt-3">
              <ToggleSwitch
                checked={notifyEnabled}
                onChange={() => setNotifyEnabled((v) => !v)}
                label={t("notifyLabel")}
              />
            </div>
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
