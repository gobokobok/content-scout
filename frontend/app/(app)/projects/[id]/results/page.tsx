"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { api, ApiError, type AccountResponse, type RunResponse } from "@/lib/api";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useProject } from "@/lib/project-context";
import { RunDialog } from "../run-dialog";

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function ResultsTabPage() {
  const t = useTranslations("ResultsTable");
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { addToast } = useToast();
  const { project, isArchived } = useProject();

  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [runDialogOpen, setRunDialogOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [loadedAccounts, loadedRuns] = await Promise.all([
        api.listAccounts(params.id),
        api.listRuns(params.id),
      ]);
      setAccounts(loadedAccounts);
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
    <div className="flex flex-col gap-4">
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
        {runs === null && <SkeletonList count={3} />}

        {runs !== null && runs.length === 0 && (
          <p className="text-sm text-secondary">{t("noRuns")}</p>
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
                      ? () => router.push(`/projects/${params.id}/runs/${run.id}`)
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
