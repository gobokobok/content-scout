"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Users, CalendarClock, ChevronRight } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type ProjectStatsResponse,
} from "@/lib/api";
import { SkeletonCard } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

function NavLinkRow({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3 transition-colors hover:bg-bg"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-bg text-secondary">
        {icon}
      </span>
      <span className="flex-1 text-sm font-medium text-ink">{label}</span>
      <ChevronRight className="h-4 w-4 shrink-0 text-secondary" />
    </Link>
  );
}

export default function DetailsPage() {
  const t = useTranslations("Details");
  const params = useParams<{ id: string }>();
  const { addToast } = useToast();

  const [accounts, setAccounts] = useState<AccountResponse[] | null>(null);
  const [stats, setStats] = useState<ProjectStatsResponse | null>(null);

  const load = useCallback(async () => {
    try {
      const [loadedAccounts, loadedStats] = await Promise.all([
        api.listAccounts(params.id),
        api.getProjectStats(params.id),
      ]);
      setAccounts(loadedAccounts);
      setStats(loadedStats);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex flex-col gap-6">
      {/* KPI card */}
      {accounts === null || stats === null ? (
        <SkeletonCard />
      ) : (
        <div className="grid grid-cols-2 gap-4 rounded-card border border-border bg-card p-4">
          <div className="flex flex-col gap-1">
            <span className="text-2xl font-semibold text-ink">{accounts.length}</span>
            <span className="text-sm text-secondary">{t("kpiCompetitors")}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-2xl font-semibold text-ink">
              {stats.lifetime_items_analyzed}
            </span>
            <span className="text-sm text-secondary">{t("kpiItemsAnalyzed")}</span>
          </div>
        </div>
      )}

      {/* Nav links */}
      <div className="flex flex-col gap-2">
        <NavLinkRow
          href={`/projects/${params.id}/competitors`}
          icon={<Users className="h-4 w-4" />}
          label={t("competitorsLink")}
        />
        <NavLinkRow
          href={`/projects/${params.id}/scheduled`}
          icon={<CalendarClock className="h-4 w-4" />}
          label={t("scheduledLink")}
        />
      </div>
    </div>
  );
}
