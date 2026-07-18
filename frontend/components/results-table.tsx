"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { ContentItemResponse, ItemSortField } from "@/lib/api";

const TYPE_ICON: Record<ContentItemResponse["type"], string> = {
  reel: "🎬",
  post: "🖼️",
  carousel: "🖼️🖼️",
  video: "🎬",
  short: "🎬",
};

function formatNumber(n: number | null): string {
  if (n === null) return "—";
  return new Intl.NumberFormat("ru-RU").format(Math.round(n));
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

export function ResultsTable({
  items,
  projectId,
  sort,
  order,
  onSortChange,
  onShortlistToggle,
  onBulkShortlist,
}: {
  items: ContentItemResponse[];
  projectId: string;
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
            e.target.checked ? next.add(row.original.id) : next.delete(row.original.id);
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
          className="text-lg leading-none"
        >
          {row.original.in_shortlist ? "★" : "☆"}
        </button>
      ),
    },
    {
      id: "account",
      header: t("colAccount"),
      cell: ({ row }) => `@${row.original.account_handle}`,
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
        <span>
          {TYPE_ICON[row.original.type]} {typeLabel[row.original.type]}
        </span>
      ),
    },
    {
      id: "title",
      header: t("colTitle"),
      cell: ({ row }) => (
        <span title={row.original.title ?? undefined}>{truncate(row.original.title, 60)}</span>
      ),
    },
    {
      id: "url",
      header: t("colUrl"),
      cell: ({ row }) => (
        <a
          href={row.original.url}
          target="_blank"
          rel="noreferrer"
          className="text-blue-600 hover:underline dark:text-blue-400"
        >
          {t("openLink")}
        </a>
      ),
    },
    {
      id: "summary",
      header: t("colSummary"),
      cell: ({ row }) => (
        <span title={row.original.summary ?? undefined}>
          {truncate(row.original.summary, 60)}
        </span>
      ),
    },
    {
      id: "likes",
      header: t("colLikes"),
      cell: ({ row }) => formatNumber(row.original.likes),
    },
    {
      id: "views",
      header: t("colViews"),
      cell: ({ row }) => formatNumber(row.original.views),
    },
    {
      id: "days_since_published",
      header: t("colDaysSincePublished"),
      cell: ({ row }) => formatNumber(row.original.days_since_published),
    },
    {
      id: "views_per_day",
      header: t("colViewsPerDay"),
      cell: ({ row }) => formatNumber(row.original.views_per_day),
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
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {t("selectedCount", { count: selected.size })}
          </span>
          <button
            onClick={() => void handleBulkShortlist()}
            disabled={bulkPending}
            className="rounded-md bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
          >
            {bulkPending ? t("adding") : t("addSelectedToShortlist")}
          </button>
        </div>
      )}
      <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-800">
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
                      className={`sticky top-0 z-10 select-none whitespace-nowrap bg-gray-50 px-3 py-2 text-left font-medium text-gray-600 dark:bg-gray-900 dark:text-gray-400 ${
                        isSortable ? "cursor-pointer" : ""
                      } ${field === "account" ? "sticky left-0 z-20" : ""}`}
                    >
                      <span className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {active && <span>{order === "asc" ? "▲" : "▼"}</span>}
                      </span>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-gray-100 dark:border-gray-800">
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className={`whitespace-nowrap px-3 py-2 ${
                      cell.column.id === "account"
                        ? "sticky left-0 z-10 bg-white dark:bg-gray-950"
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
