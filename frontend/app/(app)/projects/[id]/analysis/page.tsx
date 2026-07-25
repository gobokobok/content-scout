"use client";

import { useTranslations } from "next-intl";
import { TrendingUp, Users, FileText } from "lucide-react";
import { Card, Badge } from "@/components/ui";

const INACTIVE_TEASER_CARDS = [
  { icon: Users, key: "competitor" },
  { icon: FileText, key: "publication" },
] as const;

export default function AnalysisPage() {
  const t = useTranslations("Analysis");

  return (
    <div className="flex flex-col gap-4">
      {/* Deep Analysis — launched via FAB on home screen */}
      <div className="flex items-center gap-4 rounded-card bg-ink p-5 text-left text-white">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-lime/15 text-lime">
          <TrendingUp className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-white">{t("cards.run.title")}</h3>
          <p className="mt-0.5 text-xs leading-relaxed text-[#9BA1AB]">
            {t("cards.run.description")}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {INACTIVE_TEASER_CARDS.map(({ icon: Icon, key }) => (
          <Card
            key={key}
            className="flex flex-col items-center gap-3 p-5 text-center opacity-60"
            aria-disabled
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-soft text-accent">
              <Icon className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-ink">{t(`cards.${key}.title`)}</h3>
            <p className="text-xs leading-relaxed text-secondary">
              {t(`cards.${key}.description`)}
            </p>
            <Badge>{t("cards.badge")}</Badge>
          </Card>
        ))}
      </div>
    </div>
  );
}
