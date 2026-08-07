"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

interface SideDrawerProps {
  open: boolean;
  onClose: () => void;
  side: "left" | "right";
  children: React.ReactNode;
  // E18-S7: real accidental-exit trap reported by the first outside user — the drawer had no
  // in-drawer close control, only a ~10% backdrop-tap sliver, and on a light-theme phone the
  // drawer's white bg-card read as continuous with Telegram's own native chrome bar, so the
  // user's instinct to tap "close" hit Telegram's native X and exited the whole Mini App.
  // Required (not optional) so no future call site can ship without an explicit close control.
  closeLabel: string;
}

export function SideDrawer({ open, onClose, side, children, closeLabel }: SideDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <div
      className={`fixed inset-0 z-50 transition-opacity duration-200 ${
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!open}
    >
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div
        className={`absolute top-0 bottom-0 flex w-[90%] max-w-sm flex-col bg-card shadow-2xl transition-transform duration-200 ${
          side === "left"
            ? `left-0 ${open ? "translate-x-0" : "-translate-x-full"}`
            : `right-0 ${open ? "translate-x-0" : "translate-x-full"}`
        }`}
        style={{
          paddingTop: "env(safe-area-inset-top)",
          paddingBottom: "env(safe-area-inset-bottom)",
        }}
      >
        {/* Dedicated close row, once here rather than duplicated per call site — sits above
            each drawer's own header content, so it never overlaps an existing tap target
            (e.g. the left drawer's full-width profile link). */}
        <div className="flex shrink-0 items-center justify-end px-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            aria-label={closeLabel}
            className="flex h-9 w-9 items-center justify-center rounded-full text-secondary transition-colors hover:bg-bg hover:text-ink active:scale-[0.98]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
