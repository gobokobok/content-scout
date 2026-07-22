"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Info } from "lucide-react";
import { ContextMenu } from "@/components/ui/context-menu";

export function CompetitorsInfoButton() {
  const t = useTranslations("Competitors");
  const [open, setOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  return (
    <>
      <button
        onClick={(e) => {
          setAnchorEl(e.currentTarget);
          setOpen(true);
        }}
        aria-label={t("infoLabel")}
        className="rounded-control p-1.5 text-secondary hover:bg-bg transition-colors"
      >
        <Info className="h-5 w-5" />
      </button>
      <ContextMenu open={open} onClose={() => setOpen(false)} anchorEl={anchorEl}>
        <p className="px-4 py-3 text-sm text-secondary md:max-w-xs">{t("infoExplanation")}</p>
      </ContextMenu>
    </>
  );
}
