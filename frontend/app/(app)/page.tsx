"use client";

import Link from "next/link";
import { FolderOpen } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type ProjectResponse } from "@/lib/api";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

export default function WorkspaceHomePage() {
  const t = useTranslations("Projects");
  const { addToast } = useToast();
  const [projects, setProjects] = useState<ProjectResponse[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const load = useCallback(async () => {
    try {
      setProjects(await api.listProjects());
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
    try {
      await api.archiveProject(id);
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

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-ink">{t("title")}</h1>
        {!creating && (
          <button
            onClick={() => setCreating(true)}
            className="rounded-control bg-accent px-3 py-2 text-sm font-medium text-white"
          >
            {t("createButton")}
          </button>
        )}
      </div>

      {creating && (
        <form onSubmit={onCreate} className="flex flex-wrap items-center gap-2">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("namePlaceholder")}
            className="min-w-0 flex-1 rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-control bg-accent px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {t("createSubmit")}
          </button>
          <button
            type="button"
            onClick={() => {
              setCreating(false);
              setNewName("");
            }}
            className="rounded-control border border-border px-3 py-2 text-sm text-ink hover:bg-bg"
          >
            {t("createCancel")}
          </button>
        </form>
      )}

      {/* Loading skeleton */}
      {projects === null && <SkeletonRows count={3} />}

      {/* Designed empty state */}
      {projects !== null && projects.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-card py-12 text-center">
          <FolderOpen className="h-10 w-10 text-border" />
          <p className="text-sm font-medium text-ink">{t("empty")}</p>
          <p className="text-xs text-secondary">{t("emptyHint")}</p>
        </div>
      )}

      {projects !== null && projects.length > 0 && (
        <ul className="flex flex-col gap-2">
          {projects.map((p) => (
            <li
              key={p.id}
              className="flex flex-wrap items-center gap-2 rounded-card border border-border bg-card px-4 py-3"
            >
              {renamingId === p.id ? (
                <>
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    className="min-w-0 flex-1 rounded-control border border-border bg-bg px-2 py-1 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                  <button
                    onClick={() => onRename(p.id)}
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
                </>
              ) : (
                <>
                  <Link href={`/projects/${p.id}`} className="flex-1 text-ink hover:underline">
                    {p.name}
                  </Link>
                  <button
                    onClick={() => {
                      setRenamingId(p.id);
                      setRenameValue(p.name);
                    }}
                    className="rounded-control border border-border px-3 py-1.5 text-sm text-ink hover:bg-bg"
                  >
                    {t("rename")}
                  </button>
                  <button
                    onClick={() => onArchive(p.id)}
                    className="rounded-control border border-border px-3 py-1.5 text-sm text-ink hover:bg-bg"
                  >
                    {t("archive")}
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
