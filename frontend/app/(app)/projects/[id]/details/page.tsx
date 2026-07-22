"use client";

import { useTranslations } from "next-intl";

export default function DetailsPage() {
  const t = useTranslations("Details");

  return <p className="text-sm text-secondary">{t("comingSoon")}</p>;
}
