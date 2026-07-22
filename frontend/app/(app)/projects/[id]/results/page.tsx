"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { ChevronUp, Check, AlertCircle } from "lucide-react";
import {
  api,
  downloadXlsx,
  ApiError,
  type ContentItemResponse,
  type ItemSortField,
  type RunResponse,
} from "@/lib/api";
import { ResultsTable } from "@/components/results-table";
import { ResultsCards } from "@/components/results-cards";
import { ResultsControlsBar } from "@/components/results-controls";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ContextMenu } from "@/components/ui/context-menu";

const DEFAULT_SORT: ItemSortField = "likes_per_day";

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

  // ── Results state ──────────────────────────────────────────────────────────
  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<ItemSortField>(DEFAULT_SORT);
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [itemsPage, setItemsPage] = useState<{ items: ContentItemResponse[]; total: number } | null>(null);
  const [runSelectorOpen, setRunSelectorOpen] = useState(false);
  const [runSelectorAnchorEl, setRunSelectorAnchorEl] = useState<HTMLElement | null>(null);
  const [starredOnly, setStarredOnly] = useState(false);
  const [exporting, setExporting] = useState(false);

  // ── Load runs ─────────────────────────────────────────────────────────────
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

  useEffect(() => { void loadRuns(); }, [loadRuns]);

  // ── Load items (single run, or "all runs" when selectedRunId is null) ─────
  useEffect(() => {
    if (runs === null) return; // wait for the default run selection to settle first
    let cancelled = false;
    setItemsPage(null);
    api
      .listProjectItems(params.id, { runId: selectedRunId, starredOnly, sort, order, page })
      .then((res) => { if (!cancelled) setItemsPage({ items: res.items, total: res.total }); })
      .catch((err) => { if (cancelled) return; addToast(err instanceof ApiError ? err.messageRu : t("genericError")); });
    return () => { cancelled = true; };
  }, [runs, params.id, selectedRunId, starredOnly, sort, order, page, t, addToast]);

  // ── Sort / shortlist handlers ─────────────────────────────────────────────
  function onSortChange(field: ItemSortField) {
    if (field === sort) setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    else { setSort(field); setOrder("desc"); }
    setPage(1);
  }

  async function refreshItems() {
    const res = await api.listProjectItems(params.id, { runId: selectedRunId, starredOnly, sort, order, page });
    setItemsPage({ items: res.items, total: res.total });
  }

  async function handleShortlistToggle(contentItemId: string, add: boolean) {
    try {
      if (add) await api.addToShortlist(params.id, [contentItemId]);
      else await api.removeFromShortlist(params.id, contentItemId);
      await refreshItems();
    } catch (err) { addToast(err instanceof ApiError ? err.messageRu : t("genericError")); }
  }

  async function handleBulkShortlist(contentItemIds: string[]) {
    try {
      await api.addToShortlist(params.id, contentItemIds);
      await refreshItems();
    } catch (err) { addToast(err instanceof ApiError ? err.messageRu : t("genericError")); }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const qs = new URLSearchParams({ sort, order, starred_only: String(starredOnly) });
      if (selectedRunId) qs.set("run_id", selectedRunId);
      await downloadXlsx(
        `/projects/${params.id}/items/export.xlsx?${qs.toString()}`,
        () => api.mintProjectItemsExportToken(params.id),
        () => api.downloadProjectItemsXlsx(params.id, { runId: selectedRunId, starredOnly, sort, order }),
        "content-scout-results.xlsx",
      );
    } catch (err) { addToast(err instanceof ApiError ? err.messageRu : t("genericError")); }
    finally { setExporting(false); }
  }

  function onRunSelected(id: string) {
    setSelectedRunId(id);
    setRunSelectorOpen(false);
    setPage(1);
  }

  function onRunFilterChange(id: string | null) {
    setSelectedRunId(id);
    setPage(1);
  }

  const selectedRun = runs?.find((r) => r.id === selectedRunId) ?? null;
  // null selectedRunId means "all runs" (mobile filter) — the aggregated endpoint already
  // restricts to done runs server-side, so there's no run-status gate to wait on.
  const showItems = selectedRunId === null || selectedRun?.status === "done";
  const totalPages = itemsPage ? Math.max(1, Math.ceil(itemsPage.total / 50)) : 1;

  const paginationBar = (
    <div className="flex items-center justify-between gap-2">
      <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
        className="rounded-control border border-border px-3 py-1.5 text-sm text-ink disabled:opacity-50 hover:bg-bg">
        {t("prevPage")}
      </button>
      <span className="text-sm text-secondary">{t("pageInfo", { page, totalPages })}</span>
      <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
        className="rounded-control border border-border px-3 py-1.5 text-sm text-ink disabled:opacity-50 hover:bg-bg">
        {t("nextPage")}
      </button>
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Run selector — desktop only; mobile gets the filter icon in ResultsControlsBar below */}
      <div className="hidden md:flex flex-wrap items-center gap-2">
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
      </div>

      {/* Token exhaustion warning */}
      {selectedRun?.status === "done" && selectedRun.error_message && (
        <div className="flex items-start gap-2 rounded-card border border-warning bg-warning/10 px-4 py-3 text-sm text-warning">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{selectedRun.error_message}</span>
        </div>
      )}

      {runs === null && <SkeletonRows count={5} />}
      {runs !== null && runs.length === 0 && <p className="text-secondary">{t("noRuns")}</p>}
      {selectedRunId !== null && selectedRun && selectedRun.status !== "done" && (
        <p className="text-sm text-secondary">{t(`status_${selectedRun.status}`)}</p>
      )}

      {showItems && runs !== null && runs.length > 0 && (
        <div className="flex flex-col gap-3 md:hidden">
          <ResultsControlsBar
            sort={sort}
            order={order}
            onSortChange={onSortChange}
            runs={runs}
            selectedRunId={selectedRunId}
            onRunSelect={onRunFilterChange}
            runLabel={formatRunLabel}
            starredOnly={starredOnly}
            onToggleStarred={() => { setStarredOnly((v) => !v); setPage(1); }}
            onExport={handleExport}
            exporting={exporting}
          />
        </div>
      )}

      {showItems && itemsPage === null && <SkeletonRows count={5} />}
      {showItems && itemsPage && itemsPage.items.length === 0 && (
        <p className="text-secondary">{t("empty")}</p>
      )}

      {showItems && itemsPage && itemsPage.items.length > 0 && (
        <>
          <div className="flex flex-col gap-3 md:hidden">
            <ResultsCards items={itemsPage.items} onShortlistToggle={handleShortlistToggle} />
            {totalPages > 1 && paginationBar}
          </div>
          <div className="hidden md:flex md:flex-col md:gap-3">
            <ResultsTable items={itemsPage.items} sort={sort} order={order}
              onSortChange={onSortChange} onShortlistToggle={handleShortlistToggle}
              onBulkShortlist={handleBulkShortlist} />
            {paginationBar}
          </div>
        </>
      )}

      <ContextMenu open={runSelectorOpen} onClose={() => setRunSelectorOpen(false)}
        title={t("selectRunTitle")} anchorEl={runSelectorAnchorEl}>
        <ul className="flex flex-col py-1">
          {runs?.map((r) => (
            <li key={r.id}>
              <button onClick={() => onRunSelected(r.id)}
                className="flex w-full items-center gap-3 px-4 py-3.5 text-left text-base hover:bg-bg transition-colors">
                <span className={`flex-1 ${r.id === selectedRunId ? "font-semibold text-accent" : "text-ink"}`}>
                  {formatRunLabel(r)}
                </span>
                {r.id === selectedRunId && <Check className="h-4 w-4 shrink-0 text-accent" />}
              </button>
            </li>
          ))}
        </ul>
      </ContextMenu>
    </div>
  );
}
