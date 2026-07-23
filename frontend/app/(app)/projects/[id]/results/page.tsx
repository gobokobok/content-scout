"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Coins, FileText, Info, Plus, Users } from "lucide-react";
import { api, ApiError, type AccountResponse, type RunResponse } from "@/lib/api";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ContextMenu } from "@/components/ui/context-menu";
import { useProject } from "@/lib/project-context";
import { RUN_STATUS_DOT, RUN_STATUS_PILL } from "@/lib/format";
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

  const [infoOpen, setInfoOpen] = useState(false);
  const [infoAnchorEl, setInfoAnchorEl] = useState<HTMLElement | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold text-ink">{t("title")}</h1>

      <div className="flex items-center justify-between gap-2">
        <button
          onClick={(e) => {
            setInfoAnchorEl(e.currentTarget);
            setInfoOpen(true);
          }}
          aria-label={t("infoLabel")}
          className="rounded-control p-1.5 text-secondary hover:bg-bg transition-colors"
        >
          <Info className="h-5 w-5" />
        </button>
        {!isArchived && (
          <button
            onClick={() => setRunDialogOpen(true)}
            disabled={accounts === null || accounts.length === 0}
            className="flex items-center gap-1.5 rounded-chip bg-lime px-3.5 py-2 text-sm font-semibold text-ink shadow-[0_6px_16px_rgba(140,170,20,0.28)] transition-all active:scale-[0.98] disabled:opacity-40 disabled:shadow-none"
          >
            <Plus className="h-4 w-4" />
            {t("createRunButton")}
          </button>
        )}
      </div>

      <ContextMenu open={infoOpen} onClose={() => setInfoOpen(false)} anchorEl={infoAnchorEl}>
        <p className="px-4 py-3 text-sm text-secondary md:max-w-xs">{t("infoExplanation")}</p>
      </ContextMenu>

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
                  className={`flex flex-col gap-2.5 rounded-card border border-border bg-card px-4 py-3.5 transition-all active:scale-[0.99] ${
                    openable ? "cursor-pointer hover:bg-bg" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm font-medium text-ink">
                      {formatDate(run.created_at)}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${RUN_STATUS_PILL[run.status]}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${RUN_STATUS_DOT[run.status]}`} />
                      {statusLabel[run.status]}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-secondary">
                    <span className="inline-flex items-center gap-1.5 font-mono text-xs">
                      <Users className="h-3.5 w-3.5" />
                      {run.progress_accounts}
                    </span>
                    <span className="inline-flex items-center gap-1.5 font-mono text-xs">
                      <FileText className="h-3.5 w-3.5" />
                      {run.progress_items}
                    </span>
                    <span className="inline-flex items-center gap-1.5 font-mono text-xs">
                      <Coins className="h-3.5 w-3.5" />
                      {run.progress_items}
                    </span>
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
          accounts={accounts ?? []}
          onClose={() => {
            setRunDialogOpen(false);
            void load();
          }}
        />
      )}
    </div>
  );
}
