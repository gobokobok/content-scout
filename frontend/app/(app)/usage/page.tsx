"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type KindTotalResponse, type UsageResponse } from "@/lib/api";

const KIND_I18N_KEY: Record<string, string> = {
  apify_result: "kindApifyResult",
  claude_input_tokens: "kindClaudeInputTokens",
  claude_output_tokens: "kindClaudeOutputTokens",
};

function formatCost(cost: string): string {
  const n = parseFloat(cost);
  return `$${n.toFixed(6)}`;
}

function formatQuantity(kind: string, quantity: number): string {
  return new Intl.NumberFormat("ru-RU").format(quantity);
}

function monthRange(): { from: Date; to: Date } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return { from, to };
}

export default function UsagePage() {
  const t = useTranslations("Usage");
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { from, to } = monthRange();
      setUsage(await api.getMyUsage(from, to));
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const kindLabel = (kind: string): string => {
    const key = KIND_I18N_KEY[kind];
    return key ? t(key as Parameters<typeof t>[0]) : kind;
  };

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">{t("title")}</h1>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {!usage && !error && (
        <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>
      )}

      {usage && (
        <section className="flex flex-col gap-4">
          <h2 className="text-base font-medium text-gray-600 dark:text-gray-400">
            {t("currentMonth")}
          </h2>

          {usage.by_kind.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400">{t("empty")}</p>
          ) : (
            <>
              <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-800">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr>
                      {[t("colResource"), t("colQuantity"), t("colCost")].map((h) => (
                        <th
                          key={h}
                          scope="col"
                          className="sticky top-0 whitespace-nowrap bg-gray-50 px-4 py-2 text-left font-medium text-gray-600 dark:bg-gray-900 dark:text-gray-400"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {usage.by_kind.map((row: KindTotalResponse) => (
                      <tr
                        key={row.kind}
                        className="border-t border-gray-100 dark:border-gray-800"
                      >
                        <td className="whitespace-nowrap px-4 py-2">{kindLabel(row.kind)}</td>
                        <td className="whitespace-nowrap px-4 py-2 tabular-nums">
                          {formatQuantity(row.kind, row.quantity)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-2 tabular-nums">
                          {formatCost(row.cost_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-gray-200 dark:border-gray-700">
                      <td
                        colSpan={2}
                        className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300"
                      >
                        {t("totalCost")}
                      </td>
                      <td className="px-4 py-2 font-medium tabular-nums">
                        {formatCost(usage.total_cost_usd)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
