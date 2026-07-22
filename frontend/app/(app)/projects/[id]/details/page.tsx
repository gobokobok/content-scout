"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Users, CalendarClock, ChevronRight, Plus } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type ProjectStatsResponse,
  type RunResponse,
} from "@/lib/api";
import { SkeletonCard, SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useProject } from "@/lib/project-context";
import { RunDialog } from "../run-dialog";

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function NavLinkRow({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3 transition-colors hover:bg-bg"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-bg text-secondary">
        {icon}
      </span>
      <span className="flex-1 text-sm font-medium text-ink">{label}</span>
      <ChevronRight className="h-4 w-4 shrink-0 text-secondary" />
    </Link>
  );
}

export default function DetailsPage() {
  const t = useTranslations("Details");
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { addToast } = useToast();
  const { project, isArchived } = useProject();

  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [stats, setStats] = useState<ProjectStatsResponse | null>(null);
  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [runDialogOpen, setRunDialogOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [loadedAccounts, loadedStats, loadedRuns] = await Promise.all([
        api.listAccounts(params.id),
        api.getProjectStats(params.id),
        api.listRuns(params.id),
      ]);
      setAccounts(loadedAccounts);
      setStats(loadedStats);
      setRuns(loadedRuns);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  useEffect(() => {
    void load();
  }, [load]);

  const statusLabel: Record<RunResponse["status"], string> = {
    pending: t("status_pending"),
    scraping: t("status_scraping"),
    summarizing: t("status_summarizing"),
    done: t("status_done"),
    failed: t("status_failed"),
  };

  const statusClass: Record<RunResponse["status"], string> = {
    pending: "text-secondary",
    scraping: "text-secondary",
    summarizing: "text-secondary",
    done: "text-success",
    failed: "text-danger",
  };

  return (
    <div className="flex flex-col gap-6">
      {/* KPI card */}
      {accounts === null || stats === null ? (
        <SkeletonCard />
      ) : (
        <div className="grid grid-cols-2 gap-4 rounded-card border border-border bg-card p-4">
          <div className="flex flex-col gap-1">
            <span className="text-2xl font-semibold text-ink">{accounts.length}</span>
            <span className="text-sm text-secondary">{t("kpiCompetitors")}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-2xl font-semibold text-ink">
              {stats.lifetime_items_analyzed}
            </span>
            <span className="text-sm text-secondary">{t("kpiItemsAnalyzed")}</span>
          </div>
        </div>
      )}

      {/* Nav links */}
      <div className="flex flex-col gap-2">
        <NavLinkRow
          href={`/projects/${params.id}/competitors`}
          icon={<Users className="h-4 w-4" />}
          label={t("competitorsLink")}
        />
        <NavLinkRow
          href={`/projects/${params.id}/scheduled`}
          icon={<CalendarClock className="h-4 w-4" />}
          label={t("scheduledLink")}
        />
      </div>

      {/* Create run entry */}
      {!isArchived && (
        <button
          onClick={() => setRunDialogOpen(true)}
          disabled={accounts === null || accounts.length === 0}
          className="flex items-center justify-center gap-1.5 rounded-control bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40 transition-opacity"
        >
          <Plus className="h-4 w-4" />
          {t("createRunButton")}
        </button>
      )}

      {/* Run history */}
      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-ink">{t("runsTitle")}</h2>

        {runs === null && <SkeletonList count={3} />}

        {runs !== null && runs.length === 0 && (
          <p className="text-sm text-secondary">{t("runsEmpty")}</p>
        )}

        {runs !== null && runs.length > 0 && (
          <div className="flex flex-col gap-2">
            {runs.map((run) => {
              const openable = run.status === "done";
              return (
                <div
                  key={run.id}
                  onClick={
                    openable
                      ? () => router.push(`/projects/${params.id}/results?run=${run.id}`)
                      : undefined
                  }
                  className={`flex flex-col gap-2 rounded-card border border-border bg-card p-4 transition-colors ${
                    openable ? "cursor-pointer hover:bg-bg" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-ink">
                      {formatDate(run.created_at)}
                    </span>
                    <span className={`text-sm ${statusClass[run.status]}`}>
                      {statusLabel[run.status]}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-secondary">
                    <span>{t("cardAccounts", { count: run.progress_accounts })}</span>
                    <span>{t("cardItems", { count: run.progress_items })}</span>
                    <span>{t("cardTokens", { count: run.progress_items })}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {runDialogOpen && (
        <RunDialog
          projectId={params.id}
          projectName={project?.name ?? ""}
          accountsCount={accounts?.length ?? 0}
          accountIds={undefined}
          onClose={() => {
            setRunDialogOpen(false);
            void load();
          }}
        />
      )}
    </div>
  );
}
