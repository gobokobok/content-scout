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
  type ShortlistItemResponse,
} from "@/lib/api";
import { ResultsTable } from "@/components/results-table";
import { ResultsCards, ShortlistCards } from "@/components/results-cards";
import { ResultsControlsBar } from "@/components/results-controls";
import { SkeletonRows, SkeletonList } from "@/components/ui/skeleton";
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

// ──────────────────────────────────────────────────────────────────────────────
// Sub-tab types
// ──────────────────────────────────────────────────────────────────────────────
type SubTab = "results" | "shortlist";

export default function ResultsTabPage() {
  const t = useTranslations("ResultsTable");
  const tSl = useTranslations("Shortlist");
  const tCards = useTranslations("ResultsCards");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();

  const [subTab, setSubTab] = useState<SubTab>("results");

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

  // ── Shortlist state ────────────────────────────────────────────────────────
  const [shortlistItems, setShortlistItems] = useState<ShortlistItemResponse[] | null>(null);
  const [shortlistExporting, setShortlistExporting] = useState(false);

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

  // ── Load shortlist ────────────────────────────────────────────────────────
  const loadShortlist = useCallback(async () => {
    try {
      setShortlistItems(await api.listShortlist(params.id));
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  useEffect(() => { void loadRuns(); }, [loadRuns]);
  useEffect(() => { if (subTab === "shortlist") void loadShortlist(); }, [subTab, loadShortlist]);

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

  async function handleShortlistExport() {
    setShortlistExporting(true);
    try {
      await downloadXlsx(
        `/projects/${params.id}/shortlist/export.xlsx`,
        () => api.mintShortlistExportToken(params.id),
        () => api.downloadShortlistXlsx(params.id),
        "content-scout-shortlist.xlsx",
      );
    } catch (err) { addToast(err instanceof ApiError ? err.messageRu : t("genericError")); }
    finally { setShortlistExporting(false); }
  }

  function handleShortlistRemove(contentItemId: string) {
    setShortlistItems((prev) => prev?.filter((i) => i.content_item_id !== contentItemId) ?? null);
    api.removeFromShortlist(params.id, contentItemId).catch((err) => {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
      void loadShortlist();
    });
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

  // ── Sub-tab bar ────────────────────────────────────────────────────────────
  const subTabBar = (
    <div className="flex gap-1 border-b border-border">
      {(["results", "shortlist"] as SubTab[]).map((tab) => (
        <button
          key={tab}
          onClick={() => setSubTab(tab)}
          className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
            subTab === tab
              ? "border-accent text-accent"
              : "border-transparent text-secondary hover:text-ink"
          }`}
        >
          {tab === "results" ? t("tabAll") : tSl("tabLabel")}
        </button>
      ))}
    </div>
  );

  // ── Results tab ────────────────────────────────────────────────────────────
  const resultsContent = (
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

  // ── Shortlist tab ──────────────────────────────────────────────────────────
  const shortlistContent = (
    <div className="flex flex-col gap-4">
      {shortlistItems === null && <SkeletonList count={4} />}
      {shortlistItems !== null && shortlistItems.length === 0 && (
        <p className="text-secondary">{tSl("empty")}</p>
      )}

      {shortlistItems !== null && shortlistItems.length > 0 && (
        <>
          {/* Mobile cards */}
          <div className="md:hidden">
            <ShortlistCards items={shortlistItems} onRemove={handleShortlistRemove}
              onExport={handleShortlistExport} exporting={shortlistExporting} />
          </div>

          {/* Desktop export */}
          <div className="hidden md:flex md:items-center md:gap-2">
            <button
              onClick={() => void handleShortlistExport()}
              disabled={shortlistExporting}
              className="rounded-control border border-border px-3 py-2 text-sm font-medium text-ink disabled:opacity-50 hover:bg-bg"
            >
              {shortlistExporting ? tCards("exporting") : tCards("exportButton")}
            </button>
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto rounded-card border border-border">
            <table className="w-full min-w-max border-collapse text-sm">
              <thead>
                <tr>
                  {[tSl("colAccount"), tSl("colAddedAt"), tSl("colType"), tSl("colTitle"),
                    tSl("colUrl"), tSl("colSummary"), tSl("colLikes"), tSl("colActions")].map((h) => (
                    <th key={h} scope="col"
                      className="sticky top-0 whitespace-nowrap bg-bg px-3 py-2 text-left font-medium text-secondary">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shortlistItems.map((item) => (
                  <tr key={item.id} className="border-t border-border">
                    <td className="sticky left-0 whitespace-nowrap bg-card px-3 py-2">@{item.account_handle}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {new Date(item.added_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-secondary">{item.type}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span title={item.title ?? undefined}>{item.title ? item.title.slice(0, 60) + (item.title.length > 60 ? "…" : "") : "—"}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <a href={item.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">{tSl("openLink")}</a>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span title={item.summary ?? undefined}>{item.summary ? item.summary.slice(0, 60) + (item.summary.length > 60 ? "…" : "") : "—"}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                      {item.likes !== null ? new Intl.NumberFormat("ru-RU").format(item.likes) : "—"}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <button onClick={() => handleShortlistRemove(item.content_item_id)}
                        className="text-sm text-danger hover:underline">{tSl("remove")}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      {subTabBar}
      {subTab === "results" ? resultsContent : shortlistContent}
    </div>
  );
}
