"use client";

import { useState } from "react";
import { Film, ImageIcon, Images, Star } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ContentItemResponse, ItemSortField, ShortlistItemResponse } from "@/lib/api";
import { formatNumber, formatFollowers, formatPercent, VIRALITY_STYLE } from "@/lib/format";

type ShortlistSortField = "added_at" | "likes" | "published_at" | "account_handle";

function sortShortlist(
  items: ShortlistItemResponse[],
  sort: ShortlistSortField,
  order: "asc" | "desc"
): ShortlistItemResponse[] {
  return [...items].sort((a, b) => {
    let cmp = 0;
    if (sort === "added_at") cmp = new Date(a.added_at).getTime() - new Date(b.added_at).getTime();
    else if (sort === "published_at") cmp = new Date(a.published_at).getTime() - new Date(b.published_at).getTime();
    else if (sort === "likes") cmp = (a.likes ?? 0) - (b.likes ?? 0);
    else if (sort === "account_handle") cmp = a.account_handle.localeCompare(b.account_handle);
    return order === "desc" ? -cmp : cmp;
  });
}

const TYPE_ICON: Record<ContentItemResponse["type"], React.ReactNode> = {
  reel: <Film className="h-3.5 w-3.5" />,
  post: <ImageIcon className="h-3.5 w-3.5" />,
  carousel: <Images className="h-3.5 w-3.5" />,
  video: <Film className="h-3.5 w-3.5" />,
  short: <Film className="h-3.5 w-3.5" />,
};

function daysSince(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

// ---------------------------------------------------------------------------
// Sort bottom sheet
// ---------------------------------------------------------------------------

function SortBottomSheet({
  open,
  current,
  order,
  onClose,
  onSelect,
}: {
  open: boolean;
  current: ItemSortField;
  order: "asc" | "desc";
  onClose: () => void;
  onSelect: (field: ItemSortField) => void;
}) {
  const t = useTranslations("ResultsCards");

  const fields: { field: ItemSortField; label: string }[] = [
    { field: "likes_per_day", label: t("sortLikesPerDay") },
    { field: "likes", label: t("sortLikes") },
    { field: "published_at", label: t("sortPublishedAt") },
    { field: "account", label: t("sortAccount") },
  ];

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end md:hidden"
      onClick={onClose}
    >
      <div
        className="w-full rounded-t-card border-t border-border bg-card p-4 shadow-lg"
        style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 1rem)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <p className="mb-3 text-sm font-semibold text-ink">{t("sortTitle")}</p>
        <div className="flex flex-col gap-0.5">
          {fields.map(({ field, label }) => {
            const active = current === field;
            return (
              <button
                key={field}
                onClick={() => {
                  onSelect(field);
                  onClose();
                }}
                className={`flex min-h-[48px] items-center justify-between rounded-control px-3 py-3 text-base transition-colors ${
                  active
                    ? "bg-accent-soft font-medium text-accent"
                    : "text-ink hover:bg-bg"
                }`}
              >
                <span>{label}</span>
                {active && (
                  <span className="text-xs text-secondary">
                    {order === "desc" ? t("sortDesc") : t("sortAsc")}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shortlist sort bottom sheet
// ---------------------------------------------------------------------------

function ShortlistSortBottomSheet({
  open,
  current,
  order,
  onClose,
  onSelect,
}: {
  open: boolean;
  current: ShortlistSortField;
  order: "asc" | "desc";
  onClose: () => void;
  onSelect: (field: ShortlistSortField) => void;
}) {
  const t = useTranslations("ResultsCards");

  const fields: { field: ShortlistSortField; label: string }[] = [
    { field: "added_at", label: t("slSortAddedAt") },
    { field: "likes", label: t("slSortLikes") },
    { field: "published_at", label: t("slSortPublishedAt") },
    { field: "account_handle", label: t("slSortAccount") },
  ];

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end md:hidden" onClick={onClose}>
      <div
        className="w-full rounded-t-card border-t border-border bg-card p-4 shadow-lg"
        style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 1rem)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <p className="mb-3 text-sm font-semibold text-ink">{t("sortTitle")}</p>
        <div className="flex flex-col gap-0.5">
          {fields.map(({ field, label }) => {
            const active = current === field;
            return (
              <button
                key={field}
                onClick={() => { onSelect(field); onClose(); }}
                className={`flex min-h-[48px] items-center justify-between rounded-control px-3 py-3 text-base transition-colors ${
                  active ? "bg-accent-soft font-medium text-accent" : "text-ink hover:bg-bg"
                }`}
              >
                <span>{label}</span>
                {active && (
                  <span className="text-xs text-secondary">
                    {order === "desc" ? t("sortDesc") : t("sortAsc")}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Content item card (results tab)
// ---------------------------------------------------------------------------

function ContentCard({
  item,
  typeLabel,
  onShortlistToggle,
}: {
  item: ContentItemResponse;
  typeLabel: string;
  onShortlistToggle: (id: string, add: boolean) => Promise<void>;
}) {
  const t = useTranslations("ResultsCards");
  const [expanded, setExpanded] = useState(false);
  const hasSummary = !!item.summary;
  const followers = formatFollowers(item.followers_count);
  const viralityLabel: Record<"high" | "medium" | "low", string> = {
    high: t("viralityHigh"),
    medium: t("viralityMedium"),
    low: t("viralityLow"),
  };

  return (
    <div className="rounded-card border border-border bg-card p-4">
      {/* Header: type chip + handle + star */}
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex shrink-0 items-center gap-1 rounded-chip bg-accent-soft px-2 py-0.5 text-[10px] font-medium text-accent">
          {TYPE_ICON[item.type]}
          {typeLabel}
        </span>
        <span className="flex-1 truncate text-sm font-medium text-ink">
          @{item.account_handle}
          {followers && (
            <span className="ml-1 font-normal text-secondary">
              · {followers} {t("followersShort")}
            </span>
          )}
        </span>
        <button
          onClick={() => void onShortlistToggle(item.id, !item.in_shortlist)}
          className="shrink-0 p-0.5"
          aria-label={item.in_shortlist ? t("removeFromShortlist") : t("addToShortlist")}
        >
          {item.in_shortlist ? (
            <Star className="h-4 w-4 fill-warning text-warning" />
          ) : (
            <Star className="h-4 w-4 text-secondary" />
          )}
        </button>
      </div>

      {/* Summary — tap to expand/collapse */}
      {hasSummary && (
        <p
          className={`mb-3 cursor-pointer text-sm text-secondary ${expanded ? "" : "line-clamp-2"}`}
          onClick={() => setExpanded((v) => !v)}
        >
          {item.summary}
        </p>
      )}

      {/* Metrics + link */}
      <div className="flex flex-wrap items-center gap-1.5">
        {item.virality && (
          <span
            title={t("viralityTooltip")}
            className={`inline-flex items-center rounded-chip px-2 py-0.5 text-xs font-medium ${VIRALITY_STYLE[item.virality]}`}
          >
            {viralityLabel[item.virality]}
          </span>
        )}
        <span className="inline-flex items-center rounded-chip bg-bg border border-border px-2 py-0.5 text-xs text-secondary">
          {daysSince(item.published_at)}&nbsp;{t("metricsDaysSince")}
        </span>
        <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
          {formatNumber(item.likes)}&nbsp;{t("metricsLikes")}
        </span>
        <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
          {formatNumber(item.comments)}&nbsp;{t("metricsComments")}
        </span>
        {item.engagement_rate !== null && (
          <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
            {formatPercent(item.engagement_rate)}&nbsp;{t("metricsEngagementRate")}
          </span>
        )}
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="ml-auto text-xs text-accent hover:underline"
        >
          {t("openLink")}
        </a>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results cards (wraps ContentCard list + sort sheet)
// ---------------------------------------------------------------------------

export function ResultsCards({
  items,
  sort,
  order,
  onSortChange,
  onShortlistToggle,
  onExport,
  exporting,
}: {
  items: ContentItemResponse[];
  sort: ItemSortField;
  order: "asc" | "desc";
  onSortChange: (field: ItemSortField) => void;
  onShortlistToggle: (id: string, add: boolean) => Promise<void>;
  onExport?: () => void | Promise<void>;
  exporting?: boolean;
}) {
  const t = useTranslations("ResultsCards");
  const [sortSheetOpen, setSortSheetOpen] = useState(false);

  const TYPE_LABEL: Record<ContentItemResponse["type"], string> = {
    reel: t("typeReel"),
    post: t("typePost"),
    carousel: t("typeCarousel"),
    video: t("typeReel"),
    short: t("typeReel"),
  };

  const SORT_LABELS: Partial<Record<ItemSortField, string>> = {
    likes_per_day: t("sortLikesPerDay"),
    likes: t("sortLikes"),
    published_at: t("sortPublishedAt"),
    account: t("sortAccount"),
  };

  const currentLabel = SORT_LABELS[sort] ?? sort;

  return (
    <div className="flex flex-col gap-3">
      {/* Sort chip + export */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setSortSheetOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-chip bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent"
        >
          {currentLabel}
          <span className="opacity-70">{order === "desc" ? "↓" : "↑"}</span>
        </button>
        {onExport && (
          <button
            onClick={() => void onExport()}
            disabled={exporting}
            className="rounded-control border border-border px-3 py-1.5 text-xs font-medium text-ink disabled:opacity-50 hover:bg-bg whitespace-nowrap"
          >
            {exporting ? t("exporting") : t("exportButton")}
          </button>
        )}
      </div>

      {/* Cards */}
      {items.map((item) => (
        <ContentCard
          key={item.id}
          item={item}
          typeLabel={TYPE_LABEL[item.type]}
          onShortlistToggle={onShortlistToggle}
        />
      ))}

      <SortBottomSheet
        open={sortSheetOpen}
        current={sort}
        order={order}
        onClose={() => setSortSheetOpen(false)}
        onSelect={onSortChange}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shortlist item card
// ---------------------------------------------------------------------------

function ShortlistCard({
  item,
  typeLabel,
  onRemove,
}: {
  item: ShortlistItemResponse;
  typeLabel: string;
  onRemove: (contentItemId: string) => void;
}) {
  const t = useTranslations("ResultsCards");
  const [expanded, setExpanded] = useState(false);
  const hasSummary = !!item.summary;

  return (
    <div className="rounded-card border border-border bg-card p-4">
      {/* Header: type chip + handle + active star (remove) */}
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex shrink-0 items-center gap-1 rounded-chip bg-accent-soft px-2 py-0.5 text-[10px] font-medium text-accent">
          {TYPE_ICON[item.type]}
          {typeLabel}
        </span>
        <span className="flex-1 truncate text-sm font-medium text-ink">
          @{item.account_handle}
        </span>
        <button
          onClick={() => onRemove(item.content_item_id)}
          className="shrink-0 p-0.5"
          aria-label={t("removeBtn")}
        >
          <Star className="h-4 w-4 fill-warning text-warning" />
        </button>
      </div>

      {/* Summary — tap to expand/collapse */}
      {hasSummary && (
        <p
          className={`mb-3 cursor-pointer text-sm text-secondary ${expanded ? "" : "line-clamp-2"}`}
          onClick={() => setExpanded((v) => !v)}
        >
          {item.summary}
        </p>
      )}

      {/* Metrics + link */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
          {daysSince(item.published_at)}&nbsp;{t("metricsDaysSince")}
        </span>
        <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
          {formatNumber(item.likes)}&nbsp;{t("metricsLikes")}
        </span>
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="ml-auto text-xs text-accent hover:underline"
        >
          {t("openLink")}
        </a>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shortlist cards list
// ---------------------------------------------------------------------------

export function ShortlistCards({
  items,
  onRemove,
  onExport,
  exporting,
}: {
  items: ShortlistItemResponse[];
  onRemove: (contentItemId: string) => void;
  onExport?: () => void | Promise<void>;
  exporting?: boolean;
}) {
  const t = useTranslations("ResultsCards");
  const [sort, setSort] = useState<ShortlistSortField>("added_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [sortSheetOpen, setSortSheetOpen] = useState(false);

  const TYPE_LABEL: Record<ShortlistItemResponse["type"], string> = {
    reel: t("typeReel"),
    post: t("typePost"),
    carousel: t("typeCarousel"),
    video: t("typeReel"),
    short: t("typeReel"),
  };

  const SORT_LABELS: Record<ShortlistSortField, string> = {
    added_at: t("slSortAddedAt"),
    likes: t("slSortLikes"),
    published_at: t("slSortPublishedAt"),
    account_handle: t("slSortAccount"),
  };

  function onSortSelect(field: ShortlistSortField) {
    if (field === sort) setOrder((prev) => (prev === "desc" ? "asc" : "desc"));
    else { setSort(field); setOrder("desc"); }
  }

  const sorted = sortShortlist(items, sort, order);

  return (
    <div className="flex flex-col gap-3">
      {/* Sort chip + export */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setSortSheetOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-chip bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent"
        >
          {SORT_LABELS[sort]}
          <span className="opacity-70">{order === "desc" ? "↓" : "↑"}</span>
        </button>
        {onExport && (
          <button
            onClick={() => void onExport()}
            disabled={exporting}
            className="rounded-control border border-border px-3 py-1.5 text-xs font-medium text-ink disabled:opacity-50 hover:bg-bg whitespace-nowrap"
          >
            {exporting ? t("exporting") : t("exportButton")}
          </button>
        )}
      </div>

      {sorted.map((item) => (
        <ShortlistCard
          key={item.id}
          item={item}
          typeLabel={TYPE_LABEL[item.type]}
          onRemove={onRemove}
        />
      ))}

      <ShortlistSortBottomSheet
        open={sortSheetOpen}
        current={sort}
        order={order}
        onClose={() => setSortSheetOpen(false)}
        onSelect={onSortSelect}
      />
    </div>
  );
}
