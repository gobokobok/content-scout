"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { LayoutDashboard, BarChart2, Sparkles } from "lucide-react";

const TABS = [
  { segment: "details", labelKey: "tabDetails", Icon: LayoutDashboard },
  { segment: "results", labelKey: "tabResults", Icon: BarChart2 },
  { segment: "analysis", labelKey: "tabAnalysis", Icon: Sparkles },
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
        const active =
          (pathname?.startsWith(href) ?? false) ||
          (segment === "results" && (pathname?.includes("/runs/") ?? false));
        return (
          <Link
            key={segment}
            href={href}
            className={`flex min-h-[58px] flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] font-medium transition-colors ${
              active ? "text-accent" : "text-secondary"
            }`}
          >
            <Icon className="h-6 w-6" />
            <span>{t(labelKey)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
