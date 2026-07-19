"use client";

import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";

export default function CreatePage() {
  const t = useTranslations("Create");

  return (
    <div className="flex flex-col items-center justify-center gap-6 px-4 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft text-accent">
        <Sparkles className="h-8 w-8" />
      </div>
      <div className="max-w-sm">
        <h2 className="mb-2 text-lg font-semibold text-ink">{t("title")}</h2>
        <p className="text-sm leading-relaxed text-secondary">{t("comingSoon")}</p>
      </div>
    </div>
  );
}
