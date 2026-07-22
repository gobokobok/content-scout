"use client";

import { useTranslations } from "next-intl";
import { Sparkles, Users, TrendingUp, FileText } from "lucide-react";
import { Card, Badge } from "@/components/ui";

const TEASER_CARDS = [
  { icon: Users, key: "competitor" },
  { icon: TrendingUp, key: "run" },
  { icon: FileText, key: "publication" },
] as const;

export default function AnalysisPage() {
  const t = useTranslations("Analysis");

  return (
    <div className="flex flex-col items-center gap-8 px-4 py-16 text-center">
      <div className="flex flex-col items-center gap-6">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft text-accent">
          <Sparkles className="h-8 w-8" />
        </div>
        <div className="max-w-sm">
          <h2 className="mb-2 text-lg font-semibold text-ink">{t("title")}</h2>
          <p className="text-sm leading-relaxed text-secondary">{t("comingSoon")}</p>
        </div>
      </div>

      <div className="grid w-full max-w-2xl gap-4 sm:grid-cols-3">
        {TEASER_CARDS.map(({ icon: Icon, key }) => (
          <Card
            key={key}
            className="flex cursor-not-allowed flex-col items-center gap-3 p-5 text-center opacity-60"
            aria-disabled="true"
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
