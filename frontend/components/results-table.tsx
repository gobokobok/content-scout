"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ChevronUp, ChevronDown, Film, ImageIcon, Images, Star, X, Maximize2 } from "lucide-react";
import type { ContentItemResponse, ItemSortField } from "@/lib/api";

const TYPE_ICON: Record<ContentItemResponse["type"], React.ReactNode> = {
  reel: <Film className="inline h-4 w-4" />,
  post: <ImageIcon className="inline h-4 w-4" />,
  carousel: <Images className="inline h-4 w-4" />,
  video: <Film className="inline h-4 w-4" />,
  short: <Film className="inline h-4 w-4" />,
};

function formatNumber(n: number | null): string {
  if (n === null) return "—";
  return new Intl.NumberFormat("ru-RU").format(Math.round(n));
}

function formatFollowers(n: number | null): string | null {
  if (n === null) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")} млн`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".", ",")} тыс.`;
  return new Intl.NumberFormat("ru-RU").format(n);
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function truncate(s: string | null, max: number): string {
  if (!s) return "—";
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

function TextExpandCell({ text }: { text: string | null }) {
  const [open, setOpen] = useState(false);
  if (!text) return <span className="text-secondary">—</span>;
  const needsExpand = text.length > 60;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="truncate">{truncate(text, 60)}</span>
      {needsExpand && (
        <button
          onClick={() => setOpen(true)}
          className="inline-flex shrink-0 items-center text-secondary hover:text-accent transition-colors"
          aria-label="Раскрыть"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      )}
      {open && (
        /* Responsive: bottom sheet on mobile, centered modal on desktop */
        <div
          className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/40"
          onClick={() => setOpen(false)}
        >
          <div
            className="relative w-full md:max-w-lg max-h-[80vh] overflow-y-auto rounded-t-2xl md:rounded-2xl bg-card p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setOpen(false)}
              className="absolute right-4 top-4 text-secondary hover:text-ink"
              aria-label="Закрыть"
            >
              <X className="h-4 w-4" />
            </button>
            <p className="pr-8 text-sm leading-relaxed whitespace-pre-wrap text-ink">{text}</p>
          </div>
        </div>
      )}
    </span>
  );
}

export function ResultsTable({
  items,
  sort,
  order,
  onSortChange,
  onShortlistToggle,
  onBulkShortlist,
}: {
  items: ContentItemResponse[];
  sort: ItemSortField;
  order: "asc" | "desc";
  onSortChange: (field: ItemSortField) => void;
  onShortlistToggle: (contentItemId: string, add: boolean) => Promise<void>;
  onBulkShortlist: (contentItemIds: string[]) => Promise<void>;
}) {
  const t = useTranslations("ResultsTable");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkPending, setBulkPending] = useState(false);

  const typeLabel: Record<ContentItemResponse["type"], string> = {
    reel: t("typeReel"),
    post: t("typePost"),
    carousel: t("typeCarousel"),
    video: t("typeReel"),
    short: t("typeReel"),
  };

  const SORTABLE_FIELDS = new Set<string>([
    "account",
    "published_at",
    "type",
    "title",
    "summary",
    "likes",
    "views",
    "comments",
    "days_since_published",
    "views_per_day",
    "likes_per_day",
  ]);

  const columns: ColumnDef<ContentItemResponse>[] = [
    {
      id: "select",
      header: () => (
        <input
          type="checkbox"
          checked={selected.size === items.length && items.length > 0}
          onChange={(e) =>
            setSelected(e.target.checked ? new Set(items.map((i) => i.id)) : new Set())
          }
          className="cursor-pointer"
          aria-label={t("selectAll")}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selected.has(row.original.id)}
          onChange={(e) => {
            const next = new Set(selected);
            if (e.target.checked) {
              next.add(row.original.id);
            } else {
              next.delete(row.original.id);
            }
            setSelected(next);
          }}
          className="cursor-pointer"
        />
      ),
    },
    {
      id: "shortlist",
      header: "",
      cell: ({ row }) => (
        <button
          onClick={() =>
            void onShortlistToggle(row.original.id, !row.original.in_shortlist)
          }
          title={row.original.in_shortlist ? t("removeFromShortlist") : t("addToShortlist")}
          className="leading-none"
        >
          {row.original.in_shortlist ? (
            <Star className="h-4 w-4 fill-warning text-warning" />
          ) : (
            <Star className="h-4 w-4 text-secondary" />
          )}
        </button>
      ),
    },
    {
      id: "account",
      header: t("colAccount"),
      cell: ({ row }) => {
        const followers = formatFollowers(row.original.followers_count);
        return (
          <span className="flex flex-col">
            <span>@{row.original.account_handle}</span>
            {followers && (
              <span className="text-xs font-normal text-secondary">
                {followers} {t("followersShort")}
              </span>
            )}
          </span>
        );
      },
    },
    {
      id: "published_at",
      header: t("colPublishedAt"),
      cell: ({ row }) => formatDateTime(row.original.published_at),
    },
    {
      id: "type",
      header: t("colType"),
      cell: ({ row }) => (
        <span className="inline-flex items-center gap-1 text-secondary">
          {TYPE_ICON[row.original.type]}
          {typeLabel[row.original.type]}
        </span>
      ),
    },
    {
      id: "title",
      header: () => (
        <span className="inline-flex items-center gap-1">
          {t("colTitle")}
          <Maximize2 className="h-3 w-3 text-secondary opacity-60" />
        </span>
      ),
      cell: ({ row }) => <TextExpandCell text={row.original.title} />,
    },
    {
      id: "url",
      header: t("colUrl"),
      cell: ({ row }) => (
        <a
          href={row.original.url}
          target="_blank"
          rel="noreferrer"
          className="text-accent hover:underline"
        >
          {t("openLink")}
        </a>
      ),
    },
    {
      id: "summary",
      header: () => (
        <span className="inline-flex items-center gap-1">
          {t("colSummary")}
          <Maximize2 className="h-3 w-3 text-secondary opacity-60" />
        </span>
      ),
      cell: ({ row }) => <TextExpandCell text={row.original.summary} />,
    },
    {
      id: "likes",
      header: t("colLikes"),
      cell: ({ row }) => formatNumber(row.original.likes),
    },
    {
      id: "comments",
      header: t("colComments"),
      cell: ({ row }) => formatNumber(row.original.comments),
    },
    {
      id: "days_since_published",
      header: t("colDaysSincePublished"),
      cell: ({ row }) => formatNumber(row.original.days_since_published),
    },
    {
      id: "likes_per_day",
      header: t("colLikesPerDay"),
      cell: ({ row }) => formatNumber(row.original.likes_per_day),
    },
  ];

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  async function handleBulkShortlist() {
    if (selected.size === 0) return;
    setBulkPending(true);
    try {
      await onBulkShortlist([...selected]);
      setSelected(new Set());
    } finally {
      setBulkPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {selected.size > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-secondary">
            {t("selectedCount", { count: selected.size })}
          </span>
          <button
            onClick={() => void handleBulkShortlist()}
            disabled={bulkPending}
            className="rounded-control bg-accent px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            {bulkPending ? t("adding") : t("addSelectedToShortlist")}
          </button>
        </div>
      )}
      <div className="overflow-x-auto rounded-card border border-border">
        <table className="w-full min-w-max border-collapse text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const field = header.column.id as ItemSortField;
                  const isSortable = SORTABLE_FIELDS.has(header.column.id);
                  const active = sort === field;
                  return (
                    <th
                      key={header.id}
                      onClick={isSortable ? () => onSortChange(field) : undefined}
                      scope="col"
                      className={`sticky top-0 z-10 select-none whitespace-nowrap bg-bg px-3 py-2 text-left font-medium text-secondary ${
                        isSortable ? "cursor-pointer hover:text-ink" : ""
                      } ${field === "account" ? "sticky left-0 z-20" : ""}`}
                    >
                      <span className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {active && (
                          order === "asc"
                            ? <ChevronUp className="h-3 w-3" />
                            : <ChevronDown className="h-3 w-3" />
                        )}
                      </span>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-border">
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className={`whitespace-nowrap px-3 py-2 text-ink ${
                      cell.column.id === "account"
                        ? "sticky left-0 z-10 bg-card"
                        : ""
                    }`}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
