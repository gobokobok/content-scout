"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type ProjectResponse } from "@/lib/api";

const TABS = [
  { segment: "competitors", labelKey: "tabCompetitors" as const },
  { segment: "results", labelKey: "tabResults" as const },
  { segment: "shortlist", labelKey: "tabShortlist" as const },
  { segment: "history", labelKey: "tabHistory" as const },
];

export default function ProjectShellLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("ProjectShell");
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getProject(params.id)
      .then((p) => {
        if (!cancelled) setProject(p);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.messageRu : t("notFound"));
      });
    return () => {
      cancelled = true;
    };
  }, [params.id, t]);

  return (
    <main className="flex flex-col gap-4 p-4">
      <Link href="/" className="text-sm text-secondary hover:text-ink hover:underline">
        {t("back")}
      </Link>

      {error && <p className="text-sm text-danger">{error}</p>}
      {!error && (
        <h1 className="text-2xl font-semibold text-ink">{project?.name ?? " "}</h1>
      )}

      <nav className="-mx-4 flex gap-1 overflow-x-auto border-b border-border px-4">
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
  );
}
