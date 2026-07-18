"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  api,
  ApiError,
  type AccountResponse,
  type ContentItemResponse,
  type ItemSortField,
  type RunResponse,
} from "@/lib/api";
import { ResultsTable } from "@/components/results-table";
import { RunDialog } from "../run-dialog";

const DEFAULT_SORT: ItemSortField = "views_per_day";

export default function ResultsTabPage() {
  const t = useTranslations("ResultsTable");
  const params = useParams<{ id: string }>();

  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<ItemSortField>(DEFAULT_SORT);
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [itemsPage, setItemsPage] = useState<{ items: ContentItemResponse[]; total: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const loadRuns = useCallback(async () => {
    try {
      const loaded = await api.listRuns(params.id);
      setRuns(loaded);
      const latestDone = loaded.find((r) => r.status === "done");
      setSelectedRunId((current) => current ?? latestDone?.id ?? loaded[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t]);

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
    api
      .listRunItems(selectedRunId, { sort, order, page })
      .then((res) => {
        if (!cancelled) setItemsPage({ items: res.items, total: res.total });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.messageRu : t("genericError"));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, sort, order, page, t]);

  function onSortChange(field: ItemSortField) {
    if (field === sort) {
      setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSort(field);
      setOrder("desc");
    }
    setPage(1);
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
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setExporting(false);
    }
  }

  function onRunSelected(id: string) {
    setSelectedRunId(id);
    setPage(1);
  }

  const selectedRun = runs?.find((r) => r.id === selectedRunId) ?? null;
  const accountsCount = accounts?.length ?? 0;
  const totalPages = itemsPage ? Math.max(1, Math.ceil(itemsPage.total / 50)) : 1;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-400">{t("runSelector")}</label>
          <select
            value={selectedRunId ?? ""}
            onChange={(e) => onRunSelected(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
          >
            {runs?.map((r) => (
              <option key={r.id} value={r.id}>
                {new Date(r.created_at).toLocaleString("ru-RU")} — {t(`status_${r.status}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          {selectedRun?.status === "done" && itemsPage && itemsPage.items.length > 0 && (
            <button
              onClick={() => void handleExport()}
              disabled={exporting}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-gray-700"
            >
              {exporting ? t("exporting") : t("exportButton")}
            </button>
          )}
          {accountsCount > 0 && (
            <button
              onClick={() => setRunDialogOpen(true)}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-gray-900"
            >
              {t("runButton")}
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {runs !== null && runs.length === 0 && (
        <p className="text-gray-600 dark:text-gray-400">{t("noRuns")}</p>
      )}

      {selectedRun && selectedRun.status !== "done" && (
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {t(`status_${selectedRun.status}`)}
        </p>
      )}

      {selectedRun?.status === "done" && itemsPage && itemsPage.items.length === 0 && (
        <p className="text-gray-600 dark:text-gray-400">{t("empty")}</p>
      )}

      {selectedRun?.status === "done" && itemsPage && itemsPage.items.length > 0 && (
        <>
          <ResultsTable
            items={itemsPage.items}
            sort={sort}
            order={order}
            onSortChange={onSortChange}
          />
          <div className="flex items-center justify-between gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-gray-700"
            >
              {t("prevPage")}
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {t("pageInfo", { page, totalPages })}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-gray-700"
            >
              {t("nextPage")}
            </button>
          </div>
        </>
      )}

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
