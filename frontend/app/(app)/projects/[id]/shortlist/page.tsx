"use client";

import { useTranslations } from "next-intl";

export default function ShortlistTabPage() {
  const t = useTranslations("ProjectShell");
  return <p className="text-gray-600 dark:text-gray-400">{t("comingSoonShortlist")}</p>;
}
