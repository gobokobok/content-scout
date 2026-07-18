"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type AccountResponse } from "@/lib/api";

const MAX_ACCOUNTS = 50;

export default function CompetitorsTabPage() {
  const t = useTranslations("Competitors");
  const params = useParams<{ id: string }>();
  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ input: string; message_ru: string }[]>([]);
  const [addedCount, setAddedCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setAccounts(await api.listAccounts(params.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    const entries = text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (entries.length === 0) return;

    setSubmitting(true);
    setError(null);
    setErrors([]);
    setAddedCount(null);
    try {
      const result = await api.addAccounts(params.id, entries);
      setErrors(result.errors);
      setAddedCount(result.added.length);
      setText("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  async function onRemove(accountId: string) {
    try {
      await api.removeAccount(params.id, accountId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  const count = accounts?.length ?? 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
          {t("counter", { count, max: MAX_ACCOUNTS })}
        </span>
      </div>

      <form onSubmit={onAdd} className="flex flex-col gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("textareaPlaceholder")}
          rows={4}
          className="w-full resize-y rounded-md border border-gray-300 px-3 py-2 text-base dark:border-gray-700 dark:bg-gray-900"
        />
        <button
          type="submit"
          disabled={submitting || !text.trim()}
          className="self-start rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
        >
          {submitting ? t("adding") : t("addButton")}
        </button>
      </form>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {addedCount !== null && (
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {t("addedCount", { count: addedCount })}
        </p>
      )}

      {errors.length > 0 && (
        <ul className="flex flex-col gap-1">
          {errors.map((e, i) => (
            <li key={i} className="text-sm text-red-600 dark:text-red-400">
              {e.input}: {e.message_ru}
            </li>
          ))}
        </ul>
      )}

      {accounts === null && <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>}

      {accounts !== null && accounts.length === 0 && (
        <p className="text-gray-600 dark:text-gray-400">{t("empty")}</p>
      )}

      {accounts !== null && accounts.length > 0 && (
        <div className="overflow-x-auto">
          <ul className="flex min-w-max flex-col gap-2">
            {accounts.map((a) => (
              <li
                key={a.id}
                className="flex items-center gap-3 rounded-md border border-gray-200 px-4 py-2 dark:border-gray-800"
              >
                <a
                  href={a.normalized_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 hover:underline"
                >
                  @{a.handle}
                </a>
                <button
                  onClick={() => onRemove(a.id)}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700"
                >
                  {t("remove")}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
