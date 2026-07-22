"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type ProjectResponse } from "@/lib/api";
import { ProjectBottomNav } from "@/components/ui/bottom-nav";
import { SkeletonLine } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ProjectContext } from "@/lib/project-context";
import { CompetitorsInfoButton } from "@/components/competitors-info-button";

const TABS = [
  { segment: "competitors", labelKey: "tabCompetitors" as const },
  { segment: "results", labelKey: "tabResults" as const },
  { segment: "create", labelKey: "tabCreate" as const },
];

export default function ProjectShellLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("ProjectShell");
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
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

  function sectionHeading(): string {
    if (pathname?.includes("/competitors")) return t("sectionCompetitors");
    if (pathname?.includes("/results")) return t("sectionResults");
    if (pathname?.includes("/history")) return t("sectionHistory");
    if (pathname?.includes("/create")) return t("sectionCreate");
    return "";
  }

  return (
    <ProjectContext.Provider value={{ project, isArchived }}>
      <>
        <main className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-4 pb-20 md:pb-4">
          {/* Breadcrumb */}
          <nav className="flex flex-wrap items-center gap-1.5">
            <Link href="/" className="text-sm text-secondary hover:text-ink transition-colors">
              {t("breadcrumbProjects")}
            </Link>
            <span className="text-sm text-secondary">/</span>
            {project ? (
              <span className="max-w-[200px] truncate text-sm text-ink">{project.name}</span>
            ) : (
              <SkeletonLine className="inline-block h-4 w-32" />
            )}
            {isArchived && (
              <span className="rounded-chip border border-border bg-bg px-2 py-0.5 text-xs font-medium text-secondary">
                {t("archivedBadge")}
              </span>
            )}
          </nav>

          {notFound && <p className="text-sm text-danger">{t("notFound")}</p>}

          {!notFound && (
            <div className="flex items-center gap-1.5">
              <h1 className="text-2xl font-semibold text-ink">{sectionHeading()}</h1>
              {pathname?.includes("/competitors") && <CompetitorsInfoButton />}
            </div>
          )}

          {/* Desktop tab bar — hidden on mobile */}
          <nav className="-mx-4 hidden gap-1 overflow-x-auto border-b border-border px-4 md:flex">
            {TABS.map((tab) => {
              const href = `/projects/${params.id}/${tab.segment}`;
              const active = pathname?.startsWith(href);
              return (
                <Link
                  key={tab.segment}
                  href={href}
                  className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "border-accent text-accent"
                      : "border-transparent text-secondary hover:text-ink"
                  }`}
                >
                  {t(tab.labelKey)}
                </Link>
              );
            })}
          </nav>

          {children}
        </main>

        {/* Mobile bottom tab bar */}
        <ProjectBottomNav projectId={params.id} />
      </>
    </ProjectContext.Provider>
  );
}
