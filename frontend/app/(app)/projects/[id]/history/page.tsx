"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  api,
  ApiError,
  type RunResponse,
  type ShortlistHistoryItemResponse,
} from "@/lib/api";

const TYPE_ICON: Record<ShortlistHistoryItemResponse["type"], string> = {
  reel: "🎬",
  post: "🖼️",
  carousel: "🖼️🖼️",
  video: "🎬",
  short: "🎬",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function truncate(s: string | null, max: number): string {
  if (!s) return "—";
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

function formatCost(cost: string | null): string {
  if (!cost) return "—";
  const n = parseFloat(cost);
  return `$${n.toFixed(4)}`;
}

export default function HistoryTabPage() {
  const t = useTranslations("History");
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [shortlistHistory, setShortlistHistory] = useState<ShortlistHistoryItemResponse[] | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [loadedRuns, loadedHistory] = await Promise.all([
        api.listRuns(params.id),
        api.listShortlistHistory(params.id),
      ]);
      setRuns(loadedRuns);
      setShortlistHistory(loadedHistory);
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  function openRunResults(runId: string) {
    router.push(`/projects/${params.id}/results?run=${runId}`);
  }

  const typeLabel: Record<ShortlistHistoryItemResponse["type"], string> = {
    reel: t("typeReel"),
    post: t("typePost"),
    carousel: t("typeCarousel"),
    video: t("typeReel"),
    short: t("typeReel"),
  };

  return (
    <div className="flex flex-col gap-8">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {/* Run history */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">{t("runsTitle")}</h2>

        {runs === null && !error && (
          <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>
        )}

        {runs !== null && runs.length === 0 && (
          <p className="text-gray-600 dark:text-gray-400">{t("runsEmpty")}</p>
        )}

        {runs !== null && runs.length > 0 && (
          <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-800">
            <table className="w-full min-w-max border-collapse text-sm">
              <thead>
                <tr>
                  {[
                    t("colStartedAt"),
                    t("colDuration"),
                    t("colAccounts"),
                    t("colItems"),
                    t("colStatus"),
                    t("colCost"),
                    "",
                  ].map((h, i) => (
                    <th
                      key={i}
                      scope="col"
                      className="sticky top-0 whitespace-nowrap bg-gray-50 px-3 py-2 text-left font-medium text-gray-600 dark:bg-gray-900 dark:text-gray-400"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className="border-t border-gray-100 dark:border-gray-800"
                  >
                    <td className="whitespace-nowrap px-3 py-2">
                      {run.started_at ? formatDate(run.started_at) : formatDate(run.created_at)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">{run.duration_days}</td>
                    <td className="whitespace-nowrap px-3 py-2">{run.progress_accounts}</td>
                    <td className="whitespace-nowrap px-3 py-2">{run.progress_items}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span
                        className={
                          run.status === "failed"
                            ? "text-red-600 dark:text-red-400"
                            : run.status === "done"
                              ? "text-green-700 dark:text-green-400"
                              : ""
                        }
                      >
                        {t(`status_${run.status}`)}
                      </span>
                      {run.status === "failed" && run.error_message && (
                        <span
                          className="ml-1 text-xs text-red-500 dark:text-red-400"
                          title={run.error_message}
                        >
                          ({truncate(run.error_message, 40)})
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">{formatCost(run.total_cost_usd)}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {run.status === "done" && (
                        <button
                          onClick={() => openRunResults(run.id)}
                          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
                        >
                          {t("openResults")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Shortlist history */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">{t("shortlistTitle")}</h2>

        {shortlistHistory === null && !error && (
          <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>
        )}

        {shortlistHistory !== null && shortlistHistory.length === 0 && (
          <p className="text-gray-600 dark:text-gray-400">{t("shortlistEmpty")}</p>
        )}

        {shortlistHistory !== null && shortlistHistory.length > 0 && (
          <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-800">
            <table className="w-full min-w-max border-collapse text-sm">
              <thead>
                <tr>
                  {[
                    t("colAccount"),
                    t("colType"),
                    t("colTitle"),
                    t("colUrl"),
                    t("colAddedAt"),
                    t("colRemovedAt"),
                  ].map((h) => (
                    <th
                      key={h}
                      scope="col"
                      className="sticky top-0 whitespace-nowrap bg-gray-50 px-3 py-2 text-left font-medium text-gray-600 dark:bg-gray-900 dark:text-gray-400"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shortlistHistory.map((item) => (
                  <tr
                    key={item.id}
                    className="border-t border-gray-100 dark:border-gray-800"
                  >
                    <td className="whitespace-nowrap px-3 py-2">@{item.account_handle}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {TYPE_ICON[item.type]} {typeLabel[item.type]}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span title={item.title ?? undefined}>{truncate(item.title, 60)}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline dark:text-blue-400"
                      >
                        {t("openLink")}
                      </a>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">{formatDate(item.added_at)}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {item.removed_at ? (
                        <span className="text-red-600 dark:text-red-400">
                          {formatDate(item.removed_at)}
                        </span>
                      ) : (
                        <span className="text-green-700 dark:text-green-400">
                          {t("statusActive")}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
