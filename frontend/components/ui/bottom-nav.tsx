"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Users, BarChart2, Star } from "lucide-react";

const TABS = [
  { segment: "competitors", labelKey: "tabCompetitors", Icon: Users },
  { segment: "results", labelKey: "tabResults", Icon: BarChart2 },
  { segment: "shortlist", labelKey: "tabShortlist", Icon: Star },
] as const;

export function ProjectBottomNav({ projectId }: { projectId: string }) {
  const t = useTranslations("ProjectShell");
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-border bg-card md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {TABS.map(({ segment, labelKey, Icon }) => {
        const href = `/projects/${projectId}/${segment}`;
        const active = pathname?.startsWith(href) ?? false;
        return (
          <Link
            key={segment}
            href={href}
            className={`flex min-h-[44px] flex-1 flex-col items-center justify-center gap-0.5 py-1.5 text-[10px] font-medium transition-colors ${
              active ? "text-accent" : "text-secondary"
            }`}
          >
            <Icon className="h-5 w-5" />
            <span>{t(labelKey)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
