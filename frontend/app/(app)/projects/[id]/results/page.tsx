"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { ChevronUp, Check } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type ContentItemResponse,
  type ItemSortField,
  type RunResponse,
} from "@/lib/api";
import { ResultsTable } from "@/components/results-table";
import { ResultsCards } from "@/components/results-cards";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ContextMenu } from "@/components/ui/context-menu";
import { useProject } from "@/lib/project-context";
import { RunDialog } from "../run-dialog";

const DEFAULT_SORT: ItemSortField = "views_per_day";

function formatRunLabel(run: RunResponse): string {
  const date = new Date(run.created_at).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const statusMap: Record<RunResponse["status"], string> = {
    pending: "Ожидание",
    scraping: "Сбор",
    summarizing: "Анализ",
    done: "Готово",
    failed: "Ошибка",
  };
  return `${date} — ${statusMap[run.status]}`;
}

export default function ResultsTabPage() {
  const t = useTranslations("ResultsTable");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();

  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<ItemSortField>(DEFAULT_SORT);
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [itemsPage, setItemsPage] = useState<{ items: ContentItemResponse[]; total: number } | null>(
    null,
  );
  const { isArchived } = useProject();
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [runSelectorOpen, setRunSelectorOpen] = useState(false);
  const [runSelectorAnchorEl, setRunSelectorAnchorEl] = useState<HTMLElement | null>(null);
  const [exporting, setExporting] = useState(false);

  const loadRuns = useCallback(async () => {
    try {
      const loaded = await api.listRuns(params.id);
      setRuns(loaded);
      const urlRunId = new URLSearchParams(window.location.search).get("run");
      const latestDone = loaded.find((r) => r.status === "done");
      setSelectedRunId((current) => current ?? urlRunId ?? latestDone?.id ?? loaded[0]?.id ?? null);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  const loadAccounts = useCallback(async () => {
    try {
      setAccounts(await api.listAccounts(params.id));
    } catch {
      // non-fatal: run button just won't have an accurate count
    }
  }, [params.id]);

  useEffect(() => {
    void loadRuns();
    void loadAccounts();
  }, [loadRuns, loadAccounts]);

  useEffect(() => {
    if (!selectedRunId) return;
    let cancelled = false;
    setItemsPage(null);
    api
      .listRunItems(selectedRunId, { sort, order, page })
      .then((res) => {
        if (!cancelled) setItemsPage({ items: res.items, total: res.total });
      })
      .catch((err) => {
        if (cancelled) return;
        addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, sort, order, page, t, addToast]);

  function onSortChange(field: ItemSortField) {
    if (field === sort) {
      setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSort(field);
      setOrder("desc");
    }
    setPage(1);
  }

  async function handleShortlistToggle(contentItemId: string, add: boolean) {
    try {
      if (add) {
        await api.addToShortlist(params.id, [contentItemId]);
      } else {
        await api.removeFromShortlist(params.id, contentItemId);
      }
      if (selectedRunId) {
        const res = await api.listRunItems(selectedRunId, { sort, order, page });
        setItemsPage({ items: res.items, total: res.total });
      }
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function handleBulkShortlist(contentItemIds: string[]) {
    try {
      await api.addToShortlist(params.id, contentItemIds);
      if (selectedRunId) {
        const res = await api.listRunItems(selectedRunId, { sort, order, page });
        setItemsPage({ items: res.items, total: res.total });
      }
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function handleExport() {
    if (!selectedRunId) return;
    setExporting(true);
    try {
      const { blob, filename } = await api.downloadRunXlsx(selectedRunId, sort, order);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setExporting(false);
    }
  }

  function onRunSelected(id: string) {
    setSelectedRunId(id);
    setRunSelectorOpen(false);
    setPage(1);
  }

  const selectedRun = runs?.find((r) => r.id === selectedRunId) ?? null;
  const accountsCount = accounts?.length ?? 0;
  const totalPages = itemsPage ? Math.max(1, Math.ceil(itemsPage.total / 50)) : 1;

  const paginationBar = (
    <div className="flex items-center justify-between gap-2">
      <button
        onClick={() => setPage((p) => Math.max(1, p - 1))}
        disabled={page <= 1}
        className="rounded-control border border-border px-3 py-1.5 text-sm text-ink disabled:opacity-50 hover:bg-bg"
      >
        {t("prevPage")}
      </button>
      <span className="text-sm text-secondary">
        {t("pageInfo", { page, totalPages })}
      </span>
      <button
        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
        disabled={page >= totalPages}
        className="rounded-control border border-border px-3 py-1.5 text-sm text-ink disabled:opacity-50 hover:bg-bg"
      >
        {t("nextPage")}
      </button>
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Run selector trigger */}
        {runs !== null && runs.length > 0 && (
          <button
            onClick={(e) => { setRunSelectorAnchorEl(e.currentTarget); setRunSelectorOpen(true); }}
            className="flex items-center gap-2 rounded-control border border-border bg-card px-3 py-2 text-sm text-ink hover:bg-bg transition-colors max-w-full"
          >
            <span className="truncate">
              {selectedRun ? formatRunLabel(selectedRun) : t("runSelector")}
            </span>
            <ChevronUp className="h-4 w-4 shrink-0 text-secondary" />
          </button>
        )}

        <div className="flex items-center gap-2 ml-auto">
          {selectedRun?.status === "done" && itemsPage && itemsPage.items.length > 0 && (
            <button
              onClick={() => void handleExport()}
              disabled={exporting}
              className="rounded-control border border-border px-4 py-2 text-sm font-medium text-ink disabled:opacity-50 hover:bg-bg"
            >
              {exporting ? t("exporting") : t("exportButton")}
            </button>
          )}
          {accountsCount > 0 && !isArchived && (
            <button
              onClick={() => setRunDialogOpen(true)}
              className="rounded-control bg-accent px-4 py-2 text-sm font-medium text-white"
            >
              {t("runButton")}
            </button>
          )}
        </div>
      </div>

      {/* Runs loading */}
      {runs === null && <SkeletonRows count={5} />}

      {runs !== null && runs.length === 0 && (
        <p className="text-secondary">{t("noRuns")}</p>
      )}

      {selectedRun && selectedRun.status !== "done" && (
        <p className="text-sm text-secondary">{t(`status_${selectedRun.status}`)}</p>
      )}

      {/* Items loading */}
      {selectedRun?.status === "done" && itemsPage === null && <SkeletonRows count={5} />}

      {selectedRun?.status === "done" && itemsPage && itemsPage.items.length === 0 && (
        <p className="text-secondary">{t("empty")}</p>
      )}

      {selectedRun?.status === "done" && itemsPage && itemsPage.items.length > 0 && (
        <>
          {/* Mobile: cards + pagination */}
          <div className="flex flex-col gap-3 md:hidden">
            <ResultsCards
              items={itemsPage.items}
              sort={sort}
              order={order}
              onSortChange={onSortChange}
              onShortlistToggle={handleShortlistToggle}
            />
            {totalPages > 1 && paginationBar}
          </div>

          {/* Desktop: table + pagination */}
          <div className="hidden md:flex md:flex-col md:gap-3">
            <ResultsTable
              items={itemsPage.items}
              sort={sort}
              order={order}
              onSortChange={onSortChange}
              onShortlistToggle={handleShortlistToggle}
              onBulkShortlist={handleBulkShortlist}
            />
            {paginationBar}
          </div>
        </>
      )}

      {/* Run selector — context menu (popover on desktop, sheet on mobile) */}
      <ContextMenu
        open={runSelectorOpen}
        onClose={() => setRunSelectorOpen(false)}
        title={t("selectRunTitle")}
        anchorEl={runSelectorAnchorEl}
      >
        <ul className="flex flex-col py-1">
          {runs?.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => onRunSelected(r.id)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-bg transition-colors"
              >
                <span
                  className={`flex-1 ${r.id === selectedRunId ? "font-semibold text-accent" : "text-ink"}`}
                >
                  {formatRunLabel(r)}
                </span>
                {r.id === selectedRunId && (
                  <Check className="h-4 w-4 shrink-0 text-accent" />
                )}
              </button>
            </li>
          ))}
        </ul>
      </ContextMenu>

      {runDialogOpen && (
        <RunDialog
          projectId={params.id}
          accountsCount={accountsCount}
          accountIds={undefined}
          onClose={() => {
            setRunDialogOpen(false);
            void loadRuns();
          }}
        />
      )}
    </div>
  );
}
