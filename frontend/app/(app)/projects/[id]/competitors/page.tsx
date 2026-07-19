"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type AccountResponse } from "@/lib/api";
import { RunDialog } from "../run-dialog";

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
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [runDialogOpen, setRunDialogOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const loaded = await api.listAccounts(params.id);
      setAccounts(loaded);
      setSelected(new Set(loaded.map((a) => a.id)));
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  function toggleSelected(accountId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(accountId)) next.delete(accountId);
      else next.add(accountId);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!accounts) return;
    setSelected((prev) =>
      prev.size === accounts.length ? new Set() : new Set(accounts.map((a) => a.id)),
    );
  }

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
        <span className="text-sm font-medium text-secondary">
          {t("counter", { count, max: MAX_ACCOUNTS })}
        </span>
        {count > 0 && (
          <button
            onClick={() => setRunDialogOpen(true)}
            disabled={selected.size === 0}
            className="rounded-control bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {t("runButton")}
          </button>
        )}
      </div>

      <form onSubmit={onAdd} className="flex flex-col gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("textareaPlaceholder")}
          rows={4}
          className="w-full resize-y rounded-control border border-border bg-card px-3 py-2 text-base text-ink placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <button
          type="submit"
          disabled={submitting || !text.trim()}
          className="self-start rounded-control bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {submitting ? t("adding") : t("addButton")}
        </button>
      </form>

      {error && <p className="text-sm text-danger">{error}</p>}

      {addedCount !== null && (
        <p className="text-sm text-secondary">{t("addedCount", { count: addedCount })}</p>
      )}

      {errors.length > 0 && (
        <ul className="flex flex-col gap-1">
          {errors.map((e, i) => (
            <li key={i} className="text-sm text-danger">
              {e.input}: {e.message_ru}
            </li>
          ))}
        </ul>
      )}

      {accounts === null && <p className="text-secondary">{t("loading")}</p>}

      {accounts !== null && accounts.length === 0 && (
        <p className="text-secondary">{t("empty")}</p>
      )}

      {accounts !== null && accounts.length > 0 && (
        <div className="overflow-x-auto">
          <div className="mb-1 flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-secondary">
              <input
                type="checkbox"
                checked={selected.size === accounts.length}
                onChange={toggleSelectAll}
              />
              {t("selectAll")}
            </label>
            <span className="text-sm text-secondary">
              {t("selectedCount", { count: selected.size })}
            </span>
          </div>
          <ul className="flex min-w-max flex-col gap-2">
            {accounts.map((a) => (
              <li
                key={a.id}
                className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-2"
              >
                <input
                  type="checkbox"
                  checked={selected.has(a.id)}
                  onChange={() => toggleSelected(a.id)}
                />
                <a
                  href={a.normalized_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 text-ink hover:underline"
                >
                  @{a.handle}
                </a>
                <button
                  onClick={() => onRemove(a.id)}
                  className="rounded-control border border-border px-3 py-1.5 text-sm text-ink hover:bg-bg"
                >
                  {t("remove")}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {runDialogOpen && (
        <RunDialog
          projectId={params.id}
          accountsCount={selected.size}
          accountIds={
            accounts && selected.size === accounts.length ? undefined : Array.from(selected)
          }
          onClose={() => setRunDialogOpen(false)}
        />
      )}
    </div>
  );
}
