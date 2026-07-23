"use client";

import Link from "next/link";
import { ChevronRight, FolderOpen, MoreVertical, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type ProjectResponse } from "@/lib/api";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ContextMenu } from "@/components/ui/context-menu";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { TabChip } from "@/components/ui";

type Tab = "active" | "archived";

export default function WorkspaceHomePage() {
  const t = useTranslations("Projects");
  const { addToast } = useToast();
  const [allProjects, setAllProjects] = useState<ProjectResponse[] | null>(null);
  const [tab, setTab] = useState<Tab>("active");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [menuProjectId, setMenuProjectId] = useState<string | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);

  const load = useCallback(async () => {
    try {
      setAllProjects(await api.listProjects(true));
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [t, addToast]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onRename(id: string) {
    if (!renameValue.trim()) return;
    try {
      await api.renameProject(id, renameValue.trim());
      setRenamingId(null);
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function onArchive(id: string) {
    setMenuProjectId(null);
    try {
      await api.archiveProject(id);
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function onUnarchive(id: string) {
    setMenuProjectId(null);
    try {
      await api.unarchiveProject(id);
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSubmitting(true);
    try {
      await api.createProject(newName.trim());
      setNewName("");
      setCreating(false);
      await load();
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  const activeProjects = allProjects?.filter((p) => p.archived_at === null) ?? null;
  const archivedProjects = allProjects?.filter((p) => p.archived_at !== null) ?? null;
  const projects = tab === "active" ? activeProjects : archivedProjects;
  const menuProject = allProjects?.find((p) => p.id === menuProjectId) ?? null;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("title")}</h1>
        {!creating && tab === "active" && (
          <button
            onClick={() => setCreating(true)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-lime px-4 py-2.5 text-sm font-semibold text-ink shadow-[0_6px_16px_rgba(140,170,20,0.28)] transition-all active:scale-[0.98] hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            {t("createButton")}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="inline-flex w-fit gap-0.5 rounded-chip bg-[#E9EBE6] p-[3px]">
        {(["active", "archived"] as const).map((t2) => (
          <button
            key={t2}
            onClick={() => setTab(t2)}
            className={`rounded-chip px-4 py-2 text-sm transition-all active:scale-[0.98] ${
              tab === t2 ? "bg-ink font-semibold text-white" : "font-medium text-secondary hover:text-ink"
            }`}
          >
            {t2 === "active" ? t("activeTab") : t("archivedTab")}
          </button>
        ))}
      </div>

      <BottomSheet
        open={creating}
        onClose={() => { setCreating(false); setNewName(""); }}
        title={t("createSheetTitle")}
      >
        <form onSubmit={onCreate} className="flex flex-col gap-3 px-4 pb-4">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("namePlaceholder")}
            className="w-full rounded-control border border-border bg-bg px-3 py-3 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-control bg-accent py-3 text-sm font-medium text-white disabled:opacity-50"
            >
              {t("createSubmit")}
            </button>
            <button
              type="button"
              onClick={() => { setCreating(false); setNewName(""); }}
              className="flex-1 rounded-control border border-border py-3 text-sm text-ink hover:bg-bg"
            >
              {t("createCancel")}
            </button>
          </div>
        </form>
      </BottomSheet>

      {/* Loading skeleton */}
      {projects === null && <SkeletonRows count={3} />}

      {/* Empty states */}
      {projects !== null && projects.length === 0 && tab === "active" && (
        <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-card py-12 text-center">
          <FolderOpen className="h-10 w-10 text-border" />
          <p className="text-sm font-medium text-ink">{t("empty")}</p>
          <p className="text-xs text-secondary">{t("emptyHint")}</p>
        </div>
      )}

      {projects !== null && projects.length === 0 && tab === "archived" && (
        <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-card py-12 text-center">
          <FolderOpen className="h-10 w-10 text-border" />
          <p className="text-sm font-medium text-ink">{t("emptyArchived")}</p>
        </div>
      )}

      {projects !== null && projects.length > 0 && (
        <ul className="flex flex-col gap-2">
          {projects.map((p) => (
            <li key={p.id} className="flex items-center overflow-hidden rounded-card border border-border bg-card">
              {renamingId === p.id ? (
                <div className="flex flex-1 flex-wrap items-center gap-2 px-4 py-3">
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void onRename(p.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    className="min-w-0 flex-1 rounded-control border border-border bg-bg px-2 py-1 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                  <button
                    onClick={() => void onRename(p.id)}
                    className="rounded-control bg-accent px-3 py-1.5 text-sm font-medium text-white"
                  >
                    {t("renameSave")}
                  </button>
                  <button
                    onClick={() => setRenamingId(null)}
                    className="rounded-control border border-border px-3 py-1.5 text-sm text-ink hover:bg-bg"
                  >
                    {t("createCancel")}
                  </button>
                </div>
              ) : (
                <>
                  <Link
                    href={`/projects/${p.id}`}
                    className="flex flex-1 items-center gap-2 px-4 py-3.5 text-base font-medium text-ink transition-colors hover:bg-bg"
                  >
                    <span className="min-w-0 flex-1 truncate">{p.name}</span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-secondary" />
                  </Link>
                  <button
                    onClick={(e) => {
                      setMenuProjectId(p.id);
                      setMenuAnchorEl(e.currentTarget);
                    }}
                    className="m-2 flex-shrink-0 rounded-control p-2 text-secondary hover:bg-bg transition-colors"
                    aria-label="Действия"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Context menu for project */}
      <ContextMenu
        open={menuProjectId !== null}
        onClose={() => setMenuProjectId(null)}
        title={menuProject?.name}
        anchorEl={menuAnchorEl}
      >
        <div className="flex flex-col py-1">
          {tab === "active" && (
            <>
              <button
                onClick={() => {
                  if (!menuProject) return;
                  setMenuProjectId(null);
                  setRenamingId(menuProject.id);
                  setRenameValue(menuProject.name);
                }}
                className="px-4 py-3.5 text-left text-base text-ink hover:bg-bg transition-colors"
              >
                {t("rename")}
              </button>
              <button
                onClick={() => menuProject && void onArchive(menuProject.id)}
                className="px-4 py-3.5 text-left text-base text-ink hover:bg-bg transition-colors"
              >
                {t("archive")}
              </button>
            </>
          )}
          {tab === "archived" && (
            <button
              onClick={() => menuProject && void onUnarchive(menuProject.id)}
              className="px-4 py-3.5 text-left text-base text-ink hover:bg-bg transition-colors"
            >
              {t("unarchive")}
            </button>
          )}
        </div>
      </ContextMenu>
    </main>
  );
}
