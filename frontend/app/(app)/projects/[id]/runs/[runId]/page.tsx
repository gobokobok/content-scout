"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, Film, ImageIcon, Images } from "lucide-react";
import {
  api,
  downloadXlsx,
  ApiError,
  type ContentItemResponse,
  type ItemSortField,
  type RunResponse,
} from "@/lib/api";
import { ResultsTable } from "@/components/results-table";
import { ResultsCards, ContentCard } from "@/components/results-cards";
import { ResultsControlsBar } from "@/components/results-controls";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { TabChip } from "@/components/ui";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { VIRALITY_STYLE } from "@/lib/format";

const DEFAULT_SORT: ItemSortField = "likes_per_day";

type Tab = "summary" | "publications";

const TYPE_ICON: Record<ContentItemResponse["type"], React.ReactNode> = {
  reel: <Film className="h-3.5 w-3.5" />,
  post: <ImageIcon className="h-3.5 w-3.5" />,
  carousel: <Images className="h-3.5 w-3.5" />,
  video: <Film className="h-3.5 w-3.5" />,
  short: <Film className="h-3.5 w-3.5" />,
};

function formatRunDate(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RunDetailPage() {
  const t = useTranslations("RunDetail");
  const tCards = useTranslations("ResultsCards");
  const params = useParams<{ id: string; runId: string }>();
  const router = useRouter();
  const { addToast } = useToast();

  const [tab, setTab] = useState<Tab>("summary");
  const [run, setRun] = useState<RunResponse | null>(null);
  const [topVirality, setTopVirality] = useState<ContentItemResponse[] | null>(null);
  const [selectedItem, setSelectedItem] = useState<ContentItemResponse | null>(null);

  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<ItemSortField>(DEFAULT_SORT);
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [itemsPage, setItemsPage] = useState<{ items: ContentItemResponse[]; total: number } | null>(null);
  const [starredOnly, setStarredOnly] = useState(false);
  const [exporting, setExporting] = useState(false);

  const TYPE_LABEL: Record<ContentItemResponse["type"], string> = {
    reel: tCards("typeReel"),
    post: tCards("typePost"),
    carousel: tCards("typeCarousel"),
    video: tCards("typeReel"),
    short: tCards("typeReel"),
  };
  const VIRALITY_LABEL: Record<"high" | "medium" | "low", string> = {
    high: tCards("viralityHigh"),
    medium: tCards("viralityMedium"),
    low: tCards("viralityLow"),
  };

  // ── Load the run ────────────────────────────────────────────────────────
  const loadRun = useCallback(async () => {
    try {
      const loaded = await api.getRun(params.runId);
      setRun(loaded);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.runId, t, addToast]);

  useEffect(() => { void loadRun(); }, [loadRun]);

  // ── Top-5 by virality (Summary tab) ────────────────────────────────────
  useEffect(() => {
    if (run?.status !== "done") return;
    let cancelled = false;
    api
      .getTopVirality(params.runId, 5)
      .then((res) => { if (!cancelled) setTopVirality(res.items); })
      .catch(() => { if (!cancelled) setTopVirality([]); });
    return () => { cancelled = true; };
  }, [run?.status, params.runId]);

  // ── Publications tab — reuses the project items endpoint scoped to this run ──
  useEffect(() => {
    if (tab !== "publications" || run?.status !== "done") return;
    let cancelled = false;
    setItemsPage(null);
    api
      .listProjectItems(params.id, { runId: params.runId, starredOnly, sort, order, page })
      .then((res) => { if (!cancelled) setItemsPage({ items: res.items, total: res.total }); })
      .catch((err) => { if (cancelled) return; addToast(err instanceof ApiError ? err.messageRu : t("genericError")); });
    return () => { cancelled = true; };
  }, [tab, run?.status, params.id, params.runId, starredOnly, sort, order, page, t, addToast]);

  function onSortChange(field: ItemSortField) {
    if (field === sort) setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    else { setSort(field); setOrder("desc"); }
    setPage(1);
  }

  async function refreshItems() {
    const res = await api.listProjectItems(params.id, { runId: params.runId, starredOnly, sort, order, page });
    setItemsPage({ items: res.items, total: res.total });
  }

  async function handleShortlistToggle(contentItemId: string, add: boolean) {
    try {
      if (add) await api.addToShortlist(params.id, [contentItemId]);
      else await api.removeFromShortlist(params.id, contentItemId);
      await refreshItems();
    } catch (err) { addToast(err instanceof ApiError ? err.messageRu : t("genericError")); }
  }

  // Shortlist toggle from the Summary tab's top-5 list / its detail sheet —
  // keeps that local state in sync too, and refreshes the paginated list only if already loaded.
  async function handleTopViralityShortlistToggle(contentItemId: string, add: boolean) {
    try {
      if (add) await api.addToShortlist(params.id, [contentItemId]);
      else await api.removeFromShortlist(params.id, contentItemId);
      setTopVirality((prev) =>
        prev?.map((i) => (i.id === contentItemId ? { ...i, in_shortlist: add } : i)) ?? prev,
      );
      setSelectedItem((prev) => (prev && prev.id === contentItemId ? { ...prev, in_shortlist: add } : prev));
      if (itemsPage) await refreshItems();
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
      const qs = new URLSearchParams({
        sort,
        order,
        starred_only: String(starredOnly),
        run_id: params.runId,
      });
      await downloadXlsx(
        `/projects/${params.id}/items/export.xlsx?${qs.toString()}`,
        () => api.mintProjectItemsExportToken(params.id),
        () => api.downloadProjectItemsXlsx(params.id, { runId: params.runId, starredOnly, sort, order }),
        "content-scout-run.xlsx",
      );
    } catch (err) { addToast(err instanceof ApiError ? err.messageRu : t("genericError")); }
    finally { setExporting(false); }
  }

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
      <button
        onClick={() => router.push(`/projects/${params.id}/results`)}
        className="flex w-fit items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backToResults")}
      </button>

      <h1 className="text-2xl font-semibold text-ink">{t("title")}</h1>

      {!run && <SkeletonRows count={5} />}

      {run && (
        <>
          <div className="flex gap-2">
            {(["summary", "publications"] as const).map((key) => (
              <TabChip key={key} active={tab === key} onClick={() => setTab(key)}>
                {key === "summary" ? t("tabSummary") : t("tabPublications")}
              </TabChip>
            ))}
          </div>

          {run.status !== "done" && (
            <p className="text-sm text-secondary">
              {run.status === "failed" ? t("status_failed") : t(`status_${run.status}`)}
            </p>
          )}

          {run.status === "done" && tab === "summary" && (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col divide-y divide-border rounded-card border border-border bg-card px-4">
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("dateLabel")}</span>
                  <span className="text-sm font-medium text-ink">
                    {formatRunDate(run.started_at ?? run.created_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("accountsAnalyzed")}</span>
                  <span className="text-sm font-medium text-ink">{run.progress_accounts}</span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("publicationsAnalyzed")}</span>
                  <span className="text-sm font-medium text-ink">{run.progress_items}</span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("tokensSpent")}</span>
                  <span className="text-sm font-medium text-ink">{run.progress_items}</span>
                </div>
              </div>

              <div className="rounded-card border border-border bg-card p-4">
                <p className="mb-2 text-sm font-semibold text-ink">{t("aiSummaryTitle")}</p>
                {run.summary_status === "done" && (
                  <>
                    <p className="text-sm text-secondary">{run.summary_text}</p>
                    {run.summary_topics && run.summary_topics.length > 0 && (
                      <div className="mt-3">
                        <p className="mb-1.5 text-xs text-secondary">{t("topicsTitle")}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {run.summary_topics.map((topic) => (
                            <span
                              key={topic}
                              className="inline-flex items-center rounded-chip bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent"
                            >
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
                {run.summary_status === "failed" && (
                  <p className="text-sm text-secondary">{t("aiSummaryFailed")}</p>
                )}
                {run.summary_status === "pending" && (
                  <p className="text-sm text-secondary">{t("aiSummaryPending")}</p>
                )}
              </div>

              <div className="rounded-card border border-border bg-card p-4">
                <p className="mb-3 text-sm font-semibold text-ink">{t("topViralityTitle")}</p>
                {topVirality === null && <SkeletonRows count={3} />}
                {topVirality !== null && topVirality.length === 0 && (
                  <p className="text-sm text-secondary">{t("topViralityEmpty")}</p>
                )}
                {topVirality !== null && topVirality.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {topVirality.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => setSelectedItem(item)}
                        className="flex flex-col gap-1.5 rounded-control border border-border p-2.5 text-left transition-colors active:scale-[0.99] hover:bg-bg"
                      >
                        <div className="flex items-center gap-2">
                          <span className="inline-flex shrink-0 items-center gap-1 rounded-chip bg-accent-soft px-2 py-0.5 text-[10px] font-medium text-accent">
                            {TYPE_ICON[item.type]}
                            {TYPE_LABEL[item.type]}
                          </span>
                          <span className="flex-1 truncate text-sm text-ink">
                            @{item.account_handle}
                          </span>
                          {item.virality && (
                            <span
                              className={`inline-flex shrink-0 items-center rounded-chip px-2 py-0.5 text-xs font-medium ${VIRALITY_STYLE[item.virality]}`}
                            >
                              {VIRALITY_LABEL[item.virality]}
                            </span>
                          )}
                        </div>
                        {item.summary && (
                          <p className="line-clamp-2 text-xs text-secondary">{item.summary}</p>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {run.status === "done" && tab === "publications" && (
            <div className="flex flex-col gap-3">
              <div className="md:hidden">
                <ResultsControlsBar
                  sort={sort}
                  order={order}
                  onSortChange={onSortChange}
                  runs={[]}
                  selectedRunId={null}
                  onRunSelect={() => {}}
                  runLabel={() => ""}
                  starredOnly={starredOnly}
                  onToggleStarred={() => { setStarredOnly((v) => !v); setPage(1); }}
                  onExport={handleExport}
                  exporting={exporting}
                />
              </div>

              {itemsPage === null && <SkeletonRows count={5} />}
              {itemsPage && itemsPage.items.length === 0 && (
                <p className="text-secondary">{t("empty")}</p>
              )}
              {itemsPage && itemsPage.items.length > 0 && (
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
            </div>
          )}
        </>
      )}

      <BottomSheet open={selectedItem !== null} onClose={() => setSelectedItem(null)}>
        {selectedItem && (
          <div className="px-4 pb-4">
            <ContentCard
              item={selectedItem}
              typeLabel={TYPE_LABEL[selectedItem.type]}
              onShortlistToggle={handleTopViralityShortlistToggle}
            />
          </div>
        )}
      </BottomSheet>
    </div>
  );
}
