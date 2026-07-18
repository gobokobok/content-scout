"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type ProjectResponse } from "@/lib/api";

export default function WorkspaceHomePage() {
  const t = useTranslations("Projects");
  const [projects, setProjects] = useState<ProjectResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const load = useCallback(async () => {
    try {
      setProjects(await api.listProjects());
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [t]);

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
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function onArchive(id: string) {
    try {
      await api.archiveProject(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createProject(newName.trim());
      setNewName("");
      setCreating(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        {!creating && (
          <button
            onClick={() => setCreating(true)}
            className="rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white dark:bg-white dark:text-gray-900"
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
            className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-base dark:border-gray-700 dark:bg-gray-900"
          />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
          >
            {t("createSubmit")}
          </button>
          <button
            type="button"
            onClick={() => {
              setCreating(false);
              setNewName("");
            }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700"
          >
            {t("createCancel")}
          </button>
        </form>
      )}

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {projects === null && <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>}

      {projects !== null && projects.length === 0 && (
        <p className="text-gray-600 dark:text-gray-400">{t("empty")}</p>
      )}

      {projects !== null && projects.length > 0 && (
        <ul className="flex flex-col gap-2">
          {projects.map((p) => (
            <li
              key={p.id}
              className="flex flex-wrap items-center gap-2 rounded-md border border-gray-200 px-4 py-3 dark:border-gray-800"
            >
              {renamingId === p.id ? (
                <>
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    className="min-w-0 flex-1 rounded-md border border-gray-300 px-2 py-1 text-base dark:border-gray-700 dark:bg-gray-900"
                  />
                  <button
                    onClick={() => onRename(p.id)}
                    className="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-white dark:text-gray-900"
                  >
                    {t("createSubmit")}
                  </button>
                  <button
                    onClick={() => setRenamingId(null)}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700"
                  >
                    {t("createCancel")}
                  </button>
                </>
              ) : (
                <>
                  <Link href={`/projects/${p.id}`} className="flex-1 hover:underline">
                    {p.name}
                  </Link>
                  <button
                    onClick={() => {
                      setRenamingId(p.id);
                      setRenameValue(p.name);
                    }}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700"
                  >
                    {t("rename")}
                  </button>
                  <button
                    onClick={() => onArchive(p.id)}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700"
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
