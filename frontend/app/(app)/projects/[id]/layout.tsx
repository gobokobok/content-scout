"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type ProjectResponse } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { ProjectContext } from "@/lib/project-context";
import { useHeaderTitle } from "@/lib/header-context";

export default function ProjectShellLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("ProjectShell");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getProject(params.id)
      .then((p) => {
        if (!cancelled) setProject(p);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else {
          addToast(err instanceof ApiError ? err.messageRu : t("notFound"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [params.id, t, addToast]);

  const isArchived = project?.archived_at !== null && project?.archived_at !== undefined;

  useHeaderTitle(project?.name ?? null);

  return (
    <ProjectContext.Provider value={{ project, isArchived }}>
      <main className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-4">
        {notFound && <p className="text-sm text-danger">{t("notFound")}</p>}

        {!notFound && isArchived && (
          <span className="w-fit rounded-chip border border-border bg-bg px-2 py-0.5 text-xs font-medium text-secondary">
            {t("archivedBadge")}
          </span>
        )}

        {children}
      </main>
    </ProjectContext.Provider>
  );
}
