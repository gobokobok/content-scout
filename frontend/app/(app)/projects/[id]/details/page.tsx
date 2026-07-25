"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Users, CalendarClock, ChevronRight, TrendingUp } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type ProjectStatsResponse,
  type RunResponse,
  type ScheduledRunResponse,
} from "@/lib/api";
import { formatNumber, RUN_STATUS_DOT, RUN_STATUS_PILL } from "@/lib/format";
import { SkeletonCard } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

function NavLinkRow({
  href,
  icon,
  label,
  subtitle,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  subtitle: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3 transition-colors active:scale-[0.99] hover:bg-bg"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-chip bg-accent-soft text-accent">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[14.5px] font-semibold text-ink">{label}</span>
        <span className="block truncate text-xs text-secondary">{subtitle}</span>
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-secondary" />
    </Link>
  );
}

function formatRunDate(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DetailsPage() {
  const t = useTranslations("Details");
  const tw = useTranslations("RunDialog");
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { addToast } = useToast();

  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [stats, setStats] = useState<ProjectStatsResponse | null>(null);
  const [lastRun, setLastRun] = useState<RunResponse | null | undefined>(undefined);
  const [schedules, setSchedules] = useState<ScheduledRunResponse[] | null>(null);

  const load = useCallback(async () => {
    try {
      const [loadedAccounts, loadedStats, loadedRuns, loadedSchedules] = await Promise.all([
        api.listAccounts(params.id),
        api.getProjectStats(params.id),
        api.listRuns(params.id),
        api.listScheduledRuns(params.id),
      ]);
      setAccounts(loadedAccounts);
      setStats(loadedStats);
      const sorted = [...loadedRuns].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setLastRun(sorted[0] ?? null);
      setSchedules(loadedSchedules);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalSubscribers = accounts?.reduce((sum, a) => sum + (a.followers_count ?? 0), 0) ?? 0;
  const activeSchedule = schedules?.find((s) => s.active) ?? null;
  const scheduleSubtitle = activeSchedule
    ? t("scheduleActive", {
        day: [...activeSchedule.days_of_week]
          .sort((a, b) => a - b)
          .map((d) => tw(`weekday${d}`))
          .join(", "),
        time: activeSchedule.time_of_day.slice(0, 5),
      })
    : t("scheduleNone");

  return (
    <div className="flex flex-col gap-5">
      {/* Bento KPI grid */}
      {accounts === null || stats === null ? (
        <SkeletonCard />
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <div className="col-span-2 flex items-center justify-between rounded-card bg-ink px-5 py-4 text-white">
            <div className="flex flex-col gap-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9BA1AB]">
                {t("kpiItemsAnalyzed")}
              </span>
              <span className="font-mono text-[34px] font-semibold leading-none tracking-tight text-lime">
                {formatNumber(stats.lifetime_items_analyzed)}
              </span>
            </div>
            <TrendingUp className="h-7 w-7 text-[#3E4450]" />
          </div>
          <div className="flex flex-col gap-1.5 rounded-card border border-border bg-card px-4 py-3.5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {t("kpiCompetitors")}
            </span>
            <span className="font-mono text-2xl font-semibold tracking-tight text-ink">
              {accounts.length}
            </span>
          </div>
          <div className="flex flex-col gap-1.5 rounded-card border border-border bg-card px-4 py-3.5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {t("kpiSubscribers")}
            </span>
            <span className="font-mono text-2xl font-semibold tracking-tight text-ink">
              {formatNumber(totalSubscribers)}
            </span>
          </div>
        </div>
      )}

      {/* Last analysis — quick access to the most recent run, no action button */}
      <div className="flex flex-col gap-2">
        <span className="px-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
          {t("lastRunTitle")}
        </span>
        {lastRun === undefined && <SkeletonCard />}
        {lastRun === null && (
          <div className="rounded-card border border-border bg-card px-4 py-5 text-center">
            <p className="text-sm font-medium text-ink">{t("lastRunEmpty")}</p>
            <p className="mt-1 text-xs text-secondary">{t("lastRunEmptyHint")}</p>
          </div>
        )}
        {lastRun && (
          <button
            onClick={() => router.push(`/projects/${params.id}/runs/${lastRun.id}`)}
            className="flex flex-col gap-2.5 rounded-card border border-border bg-card px-4 py-3.5 text-left transition-colors active:scale-[0.99] hover:bg-bg"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-secondary">
                {formatRunDate(lastRun.started_at ?? lastRun.created_at)}
              </span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${RUN_STATUS_PILL[lastRun.status]}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${RUN_STATUS_DOT[lastRun.status]}`} />
                {t(`status_${lastRun.status}`)}
              </span>
            </div>
            <span className="font-mono text-sm font-semibold text-ink">
              {t("lastRunItems", { count: lastRun.progress_items })}
            </span>
          </button>
        )}
      </div>

      {/* Nav links */}
      <div className="flex flex-col gap-2">
        <NavLinkRow
          href={`/projects/${params.id}/competitors`}
          icon={<Users className="h-4 w-4" />}
          label={t("competitorsLink")}
          subtitle={accounts !== null ? t("competitorsSubtitle", { count: accounts.length }) : ""}
        />
        <NavLinkRow
          href={`/projects/${params.id}/scheduled`}
          icon={<CalendarClock className="h-4 w-4" />}
          label={t("scheduledLink")}
          subtitle={schedules !== null ? scheduleSubtitle : ""}
        />
      </div>
    </div>
  );
}
