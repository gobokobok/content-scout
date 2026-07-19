"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Film, ImageIcon, Images } from "lucide-react";
import { api, ApiError, type ShortlistItemResponse } from "@/lib/api";

const TYPE_ICON: Record<ShortlistItemResponse["type"], React.ReactNode> = {
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
        <h2 className="text-lg font-semibold text-ink">{t("title")}</h2>
        <button
          disabled
          title={t("comingSoon")}
          className="cursor-not-allowed rounded-control border border-border px-4 py-2 text-sm font-medium text-ink opacity-40"
        >
          {t("createScript")}
        </button>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {items === null && !error && <p className="text-secondary">{t("loading")}</p>}

      {items !== null && items.length === 0 && <p className="text-secondary">{t("empty")}</p>}

      {items !== null && items.length > 0 && (
        <div className="overflow-x-auto rounded-card border border-border">
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
                    className="sticky top-0 whitespace-nowrap bg-bg px-3 py-2 text-left font-medium text-secondary"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="sticky left-0 whitespace-nowrap bg-card px-3 py-2">
                    @{item.account_handle}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{formatDate(item.added_at)}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span className="inline-flex items-center gap-1 text-secondary">
                      {TYPE_ICON[item.type]}
                      {typeLabel[item.type]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span title={item.title ?? undefined}>{truncate(item.title, 60)}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent hover:underline"
                    >
                      {t("openLink")}
                    </a>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span title={item.summary ?? undefined}>{truncate(item.summary, 60)}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                    {formatNumber(item.likes)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                    {formatNumber(item.views)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <button
                      onClick={() => void handleRemove(item.content_item_id)}
                      className="text-sm text-danger hover:underline"
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
