"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Users, MoreVertical, Plus, Info } from "lucide-react";
import { api, ApiError, type AccountResponse } from "@/lib/api";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ContextMenu } from "@/components/ui/context-menu";
import { useProject } from "@/lib/project-context";
import { RunDialog } from "../run-dialog";

const MAX_ACCOUNTS = 50;

function formatFollowerCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function CompetitorsTabPage() {
  const t = useTranslations("Competitors");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();
  const { project, isArchived } = useProject();
  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ input: string; message_ru: string }[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [addSheetOpen, setAddSheetOpen] = useState(false);
  const [menuAccountId, setMenuAccountId] = useState<string | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);
  const [infoAnchorEl, setInfoAnchorEl] = useState<HTMLElement | null>(null);

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
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(accountId);
        return next;
      });
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  const count = accounts?.length ?? 0;
  const allSelected = accounts !== null && accounts.length > 0 && selected.size === accounts.length;
  const menuAccount = accounts?.find((a) => a.id === menuAccountId) ?? null;

  return (
    <div className="flex flex-col gap-4">
      {/* Top bar: info popover + action buttons */}
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={(e) => {
            setInfoAnchorEl(e.currentTarget);
            setInfoOpen(true);
          }}
          aria-label={t("infoLabel")}
          className="rounded-control p-2 text-secondary hover:bg-bg transition-colors"
        >
          <Info className="h-5 w-5" />
        </button>
        {!isArchived && (
          <div className="flex items-center gap-2">
            {count < MAX_ACCOUNTS && (
              <button
                onClick={() => setAddSheetOpen(true)}
                className="flex items-center gap-1.5 rounded-control border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-bg transition-colors"
              >
                <Plus className="h-4 w-4" />
                {t("addCompetitorButton")}
              </button>
            )}
            {count > 0 && (
              <button
                onClick={() => setRunDialogOpen(true)}
                disabled={selected.size === 0}
                className="rounded-control bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40 transition-opacity"
              >
                {t("runButton")}
              </button>
            )}
          </div>
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
          {/* Select-all header row — hidden in archived view */}
          {!isArchived && (
            <div
              className="flex cursor-pointer items-center gap-3 border-b border-border px-4 py-3 hover:bg-bg transition-colors"
              onClick={toggleSelectAll}
            >
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleSelectAll}
                onClick={(e) => e.stopPropagation()}
                className="h-4 w-4 accent-accent"
              />
              <span className="flex-1 text-sm font-medium text-secondary">{t("selectAll")}</span>
              {selected.size > 0 && (
                <span className="text-sm text-secondary">
                  {t("selectedCount", { count: selected.size })}
                </span>
              )}
            </div>
          )}

          {/* Competitor rows */}
          <ul className="flex flex-col">
            {accounts.map((a, idx) => {
              const isSelected = selected.has(a.id);
              return (
                <li
                  key={a.id}
                  className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                    idx < accounts.length - 1 ? "border-b border-border" : ""
                  } ${!isArchived ? "cursor-pointer" : ""} ${
                    isSelected ? "bg-accent-soft" : !isArchived ? "hover:bg-bg" : ""
                  }`}
                  onClick={!isArchived ? () => toggleSelected(a.id) : undefined}
                >
                  {!isArchived && (
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelected(a.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="h-4 w-4 shrink-0 accent-accent"
                    />
                  )}
                  <a
                    href={a.normalized_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex-1 text-sm font-medium text-ink hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    @{a.handle}
                  </a>
                  {a.follower_count != null && (
                    <span className="text-xs text-secondary">
                      {formatFollowerCount(a.follower_count)} {t("followersShort")}
                    </span>
                  )}
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

      {/* Info popover: competitor limit + selection explanation */}
      <ContextMenu open={infoOpen} onClose={() => setInfoOpen(false)} anchorEl={infoAnchorEl}>
        <p className="max-w-xs px-4 py-3 text-sm text-secondary">{t("infoExplanation")}</p>
      </ContextMenu>

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

      {runDialogOpen && (
        <RunDialog
          projectId={params.id}
          projectName={project?.name ?? ""}
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
