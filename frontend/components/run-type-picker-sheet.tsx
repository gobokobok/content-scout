"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { BarChart2, TrendingUp, Users, FileText, X, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui";

type RunType = "stat_collection" | "deep_analysis";

export function RunTypePickerSheet({
  onPick,
  onClose,
}: {
  onPick: (runType: RunType) => void;
  onClose: () => void;
}) {
  const t = useTranslations("RunTypePicker");

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-t-[22px] bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
      >
        {/* Drag handle */}
        <div className="flex justify-center px-4 pt-3 pb-1">
          <div className="h-1 w-10 rounded-full bg-border" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between gap-2 px-4 pb-3 pt-2">
          <p className="text-base font-semibold text-ink">{t("title")}</p>
          <button
            onClick={onClose}
            className="rounded-control p-1.5 text-secondary hover:bg-bg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Active run type cards */}
        <div className="flex flex-col gap-2 px-4 pb-2">
          <button
            onClick={() => onPick("stat_collection")}
            className="flex items-center gap-3.5 rounded-card border border-border bg-bg px-4 py-3.5 text-left transition-all active:scale-[0.99] hover:bg-bg/80"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
              <BarChart2 className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-ink">{t("statTitle")}</span>
              <span className="mt-0.5 block text-xs text-secondary">{t("statDescription")}</span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-secondary" />
          </button>

          <button
            onClick={() => onPick("deep_analysis")}
            className="flex items-center gap-3.5 rounded-card border border-border bg-ink px-4 py-3.5 text-left transition-all active:scale-[0.99]"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-lime/15 text-lime">
              <TrendingUp className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-white">{t("deepTitle")}</span>
              <span className="mt-0.5 block text-xs text-[#9BA1AB]">{t("deepDescription")}</span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-[#9BA1AB]" />
          </button>
        </div>

        {/* Inactive teaser cards */}
        <div className="grid grid-cols-2 gap-2 px-4 pt-1">
          {([
            { icon: Users, titleKey: "competitorTitle" as const, descKey: "competitorDescription" as const },
            { icon: FileText, titleKey: "publicationTitle" as const, descKey: "publicationDescription" as const },
          ] as const).map(({ icon: Icon, titleKey, descKey }) => (
            <div
              key={titleKey}
              className="flex flex-col items-center gap-2.5 rounded-card border border-border p-4 text-center opacity-50"
              aria-disabled
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-accent">
                <Icon className="h-4.5 w-4.5" />
              </span>
              <span className="text-xs font-semibold text-ink">{t(titleKey)}</span>
              <Badge>{t(descKey)}</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
