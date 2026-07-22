"use client";

import { ArrowDownUp, Check, FileSpreadsheet, ListFilter, Star } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { ItemSortField, RunResponse } from "@/lib/api";
import { BottomSheet } from "@/components/ui/bottom-sheet";

const SORT_FIELDS: ItemSortField[] = ["likes_per_day", "likes", "published_at", "account"];

function iconButtonClass(active: boolean): string {
  return `inline-flex items-center justify-center rounded-control border p-2 transition-colors ${
    active
      ? "border-accent/30 bg-accent-soft text-accent"
      : "border-border text-secondary hover:bg-bg"
  }`;
}

export function ResultsControlsBar({
  sort,
  order,
  onSortChange,
  runs,
  selectedRunId,
  onRunSelect,
  runLabel,
  starredOnly,
  onToggleStarred,
  onExport,
  exporting,
}: {
  sort: ItemSortField;
  order: "asc" | "desc";
  onSortChange: (field: ItemSortField) => void;
  runs: RunResponse[];
  selectedRunId: string | null;
  onRunSelect: (id: string | null) => void;
  runLabel: (run: RunResponse) => string;
  starredOnly: boolean;
  onToggleStarred: () => void;
  onExport: () => void | Promise<void>;
  exporting: boolean;
}) {
  const t = useTranslations("ResultsCards");
  const tRuns = useTranslations("ResultsTable");
  const [sortOpen, setSortOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [runOpen, setRunOpen] = useState(false);

  const SORT_LABELS: Partial<Record<ItemSortField, string>> = {
    likes_per_day: t("sortLikesPerDay"),
    likes: t("sortLikes"),
    published_at: t("sortPublishedAt"),
    account: t("sortAccount"),
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => setSortOpen(true)}
        aria-label={t("sortIconLabel")}
        className={iconButtonClass(false)}
      >
        <ArrowDownUp className="h-4 w-4" />
      </button>
      <button
        onClick={() => setExportOpen(true)}
        aria-label={t("exportIconLabel")}
        className={iconButtonClass(false)}
      >
        <FileSpreadsheet className="h-4 w-4" />
      </button>
      {runs.length > 0 && (
        <button
          onClick={() => setRunOpen(true)}
          aria-label={t("runFilterIconLabel")}
          className={iconButtonClass(selectedRunId !== null)}
        >
          <ListFilter className="h-4 w-4" />
        </button>
      )}
      <button
        onClick={onToggleStarred}
        aria-label={t("starredOnlyIconLabel")}
        className={iconButtonClass(starredOnly)}
      >
        <Star className={`h-4 w-4 ${starredOnly ? "fill-accent" : ""}`} />
      </button>

      {/* Sort sheet */}
      <BottomSheet open={sortOpen} onClose={() => setSortOpen(false)} title={t("sortTitle")}>
        <div className="flex flex-col gap-0.5 px-2 pb-2">
          {SORT_FIELDS.map((field) => {
            const active = sort === field;
            return (
              <button
                key={field}
                onClick={() => {
                  onSortChange(field);
                  setSortOpen(false);
                }}
                className={`flex min-h-[48px] items-center justify-between rounded-control px-3 py-3 text-base transition-colors ${
                  active ? "bg-accent-soft font-medium text-accent" : "text-ink hover:bg-bg"
                }`}
              >
                <span>{SORT_LABELS[field] ?? field}</span>
                {active && (
                  <span className="text-xs text-secondary">
                    {order === "desc" ? t("sortDesc") : t("sortAsc")}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </BottomSheet>

      {/* Export sheet */}
      <BottomSheet open={exportOpen} onClose={() => setExportOpen(false)} title={t("exportSheetTitle")}>
        <div className="px-4 pb-2">
          <button
            onClick={() => {
              setExportOpen(false);
              void onExport();
            }}
            disabled={exporting}
            className="w-full rounded-control bg-accent px-4 py-3 text-base font-medium text-white disabled:opacity-50"
          >
            {exporting ? t("exporting") : t("exportButton")}
          </button>
        </div>
      </BottomSheet>

      {/* Run filter sheet */}
      <BottomSheet open={runOpen} onClose={() => setRunOpen(false)} title={tRuns("selectRunTitle")}>
        <ul className="flex flex-col px-2 pb-2">
          <li>
            <button
              onClick={() => {
                onRunSelect(null);
                setRunOpen(false);
              }}
              className="flex w-full items-center gap-3 rounded-control px-3 py-3.5 text-left text-base hover:bg-bg transition-colors"
            >
              <span className={`flex-1 ${selectedRunId === null ? "font-semibold text-accent" : "text-ink"}`}>
                {tRuns("allRuns")}
              </span>
              {selectedRunId === null && <Check className="h-4 w-4 shrink-0 text-accent" />}
            </button>
          </li>
          {runs.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => {
                  onRunSelect(r.id);
                  setRunOpen(false);
                }}
                className="flex w-full items-center gap-3 rounded-control px-3 py-3.5 text-left text-base hover:bg-bg transition-colors"
              >
                <span className={`flex-1 truncate ${selectedRunId === r.id ? "font-semibold text-accent" : "text-ink"}`}>
                  {runLabel(r)}
                </span>
                {selectedRunId === r.id && <Check className="h-4 w-4 shrink-0 text-accent" />}
              </button>
            </li>
          ))}
        </ul>
      </BottomSheet>
    </div>
  );
}
