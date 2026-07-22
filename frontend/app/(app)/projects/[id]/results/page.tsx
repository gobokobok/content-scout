"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Info, Plus } from "lucide-react";
import { api, ApiError, type AccountResponse, type RunResponse } from "@/lib/api";
import { Badge } from "@/components/ui";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ContextMenu } from "@/components/ui/context-menu";
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

  const statusVariant: Record<RunResponse["status"], "success" | "danger" | "warning"> = {
    pending: "warning",
    scraping: "warning",
    summarizing: "warning",
    done: "success",
    failed: "danger",
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
            className="flex items-center gap-1.5 rounded-control border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-bg disabled:opacity-40 transition-colors"
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
                  className={`flex flex-col gap-2 rounded-card border border-border bg-card p-4 transition-colors ${
                    openable ? "cursor-pointer hover:bg-bg" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-ink">
                      {formatDate(run.created_at)}
                    </span>
                    <Badge variant={statusVariant[run.status]}>{statusLabel[run.status]}</Badge>
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
