"use client";

import { useTranslations } from "next-intl";

export default function CompetitorsTabPage() {
  const t = useTranslations("ProjectShell");
  return <p className="text-gray-600 dark:text-gray-400">{t("comingSoonCompetitors")}</p>;
}
