"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeft, Users, MoreVertical, Plus } from "lucide-react";
import { api, ApiError, type AccountResponse } from "@/lib/api";
import { formatFollowers } from "@/lib/format";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ContextMenu } from "@/components/ui/context-menu";
import { useProject } from "@/lib/project-context";
import { CompetitorsInfoButton } from "@/components/competitors-info-button";

const MAX_ACCOUNTS = 50;

export default function CompetitorsTabPage() {
  const t = useTranslations("Competitors");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();
  const { isArchived } = useProject();
  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ input: string; message_ru: string }[]>([]);
  const [addSheetOpen, setAddSheetOpen] = useState(false);
  const [menuAccountId, setMenuAccountId] = useState<string | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);

  const load = useCallback(async () => {
    try {
      const loaded = await api.listAccounts(params.id);
      setAccounts(loaded);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

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
    setErrors([]);
    try {
      const result = await api.addAccounts(params.id, entries);
      setErrors(result.errors);
      setText("");
      if (result.added.length > 0) {
        setAddSheetOpen(false);
        addToast(t("addedCount", { count: result.added.length }));
      }
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  async function onRemove(accountId: string) {
    setMenuAccountId(null);
    try {
      await api.removeAccount(params.id, accountId);
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  const count = accounts?.length ?? 0;
  const menuAccount = accounts?.find((a) => a.id === menuAccountId) ?? null;

  return (
    <div className="flex flex-col gap-4">
      <Link
        href="/"
        className="flex w-fit items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backToDetails")}
      </Link>

      <h1 className="text-2xl font-semibold text-ink">{t("title")}</h1>

      {/* Info + action buttons */}
      <div className="flex items-center justify-between gap-2">
        <CompetitorsInfoButton />
        {!isArchived && count < MAX_ACCOUNTS && (
          <button
            onClick={() => setAddSheetOpen(true)}
            className="flex items-center gap-1.5 rounded-control border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-bg transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t("addCompetitorButton")}
          </button>
        )}
      </div>

      {/* Loading skeleton */}
      {accounts === null && <SkeletonList count={4} />}

      {/* Empty state */}
      {accounts !== null && accounts.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-card py-12 text-center">
          <Users className="h-10 w-10 text-border" />
          <p className="text-sm font-medium text-ink">{t("empty")}</p>
        </div>
      )}

      {accounts !== null && accounts.length > 0 && (
        <div className="flex flex-col gap-0 overflow-hidden rounded-card border border-border bg-card">
          {/* Competitor rows */}
          <ul className="flex flex-col">
            {accounts.map((a, idx) => {
              const hasProfile = a.display_name != null || a.followers_count != null;
              return (
                <li
                  key={a.id}
                  className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                    idx < accounts.length - 1 ? "border-b border-border" : ""
                  }`}
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-bg">
                    {a.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element -- external, unpredictable CDN host
                      <img src={a.avatar_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <Users className="h-4 w-4 text-secondary" />
                    )}
                  </span>
                  <a
                    href={a.normalized_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex min-w-0 flex-1 flex-col"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <span className="truncate text-sm font-medium text-ink hover:underline">
                      {a.display_name || `@${a.handle}`}
                    </span>
                    <span className="truncate text-xs text-secondary">
                      {hasProfile ? (
                        <>
                          @{a.handle}
                          {a.followers_count != null &&
                            ` · ${formatFollowers(a.followers_count)} ${t("followersShort")}`}
                        </>
                      ) : (
                        t("noData")
                      )}
                    </span>
                  </a>
                  {!isArchived && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuAccountId(a.id);
                        setMenuAnchorEl(e.currentTarget);
                      }}
                      className="rounded-control p-1.5 text-secondary hover:bg-border transition-colors"
                      aria-label="Действия"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Add competitor bottom sheet (always a sheet since it has a form) */}
      <BottomSheet
        open={addSheetOpen}
        onClose={() => {
          setAddSheetOpen(false);
          setErrors([]);
          setText("");
        }}
        title={t("addSheetTitle")}
      >
        <form onSubmit={onAdd} className="flex flex-col gap-3 p-4">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("textareaPlaceholder")}
            rows={5}
            autoFocus
            className="w-full resize-none rounded-control border border-border bg-bg px-3 py-2 text-base text-ink placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          {errors.length > 0 && (
            <ul className="flex flex-col gap-1">
              {errors.map((e, i) => (
                <li key={i} className="text-sm text-danger">
                  {e.input}: {e.message_ru}
                </li>
              ))}
            </ul>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting || !text.trim()}
              className="flex-1 rounded-control bg-accent py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {submitting ? t("adding") : t("addButton")}
            </button>
            <button
              type="button"
              onClick={() => {
                setAddSheetOpen(false);
                setErrors([]);
                setText("");
              }}
              className="rounded-control border border-border px-4 py-2.5 text-sm text-ink hover:bg-bg"
            >
              {t("cancel")}
            </button>
          </div>
        </form>
      </BottomSheet>

      {/* Competitor 3-dot context menu */}
      <ContextMenu
        open={menuAccountId !== null}
        onClose={() => setMenuAccountId(null)}
        title={menuAccount ? `@${menuAccount.handle}` : undefined}
        anchorEl={menuAnchorEl}
      >
        <div className="flex flex-col py-1">
          <button
            onClick={() => menuAccount && void onRemove(menuAccount.id)}
            className="px-4 py-2.5 text-left text-sm text-danger hover:bg-bg transition-colors"
          >
            {t("deleteAction")}
          </button>
        </div>
      </ContextMenu>
    </div>
  );
}
