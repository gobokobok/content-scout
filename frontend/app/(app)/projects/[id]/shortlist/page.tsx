"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { api, ApiError, type ShortlistItemResponse } from "@/lib/api";

const TYPE_ICON: Record<ShortlistItemResponse["type"], string> = {
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

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

function truncate(s: string | null, max: number): string {
  if (!s) return "—";
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

export default function ShortlistTabPage() {
  const t = useTranslations("Shortlist");
  const params = useParams<{ id: string }>();
  const [items, setItems] = useState<ShortlistItemResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.listShortlist(params.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRemove(contentItemId: string) {
    try {
      await api.removeFromShortlist(params.id, contentItemId);
      setItems((prev) => prev?.filter((i) => i.content_item_id !== contentItemId) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  const typeLabel: Record<ShortlistItemResponse["type"], string> = {
    reel: t("typeReel"),
    post: t("typePost"),
    carousel: t("typeCarousel"),
    video: t("typeReel"),
    short: t("typeReel"),
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <button
          disabled
          title={t("comingSoon")}
          className="cursor-not-allowed rounded-md border border-gray-300 px-4 py-2 text-sm font-medium opacity-40 dark:border-gray-700"
        >
          {t("createScript")}
        </button>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {items === null && !error && (
        <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>
      )}

      {items !== null && items.length === 0 && (
        <p className="text-gray-600 dark:text-gray-400">{t("empty")}</p>
      )}

      {items !== null && items.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-800">
          <table className="w-full min-w-max border-collapse text-sm">
            <thead>
              <tr>
                {[
                  t("colAccount"),
                  t("colAddedAt"),
                  t("colType"),
                  t("colTitle"),
                  t("colUrl"),
                  t("colSummary"),
                  t("colLikes"),
                  t("colViews"),
                  t("colActions"),
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
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="border-t border-gray-100 dark:border-gray-800"
                >
                  <td className="sticky left-0 whitespace-nowrap bg-white px-3 py-2 dark:bg-gray-950">
                    @{item.account_handle}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{formatDate(item.added_at)}</td>
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
                  <td className="whitespace-nowrap px-3 py-2">
                    <span title={item.summary ?? undefined}>{truncate(item.summary, 60)}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{formatNumber(item.likes)}</td>
                  <td className="whitespace-nowrap px-3 py-2">{formatNumber(item.views)}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <button
                      onClick={() => void handleRemove(item.content_item_id)}
                      className="text-sm text-red-600 hover:underline dark:text-red-400"
                    >
                      {t("remove")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
