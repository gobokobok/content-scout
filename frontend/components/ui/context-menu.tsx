"use client";

import { useEffect, useLayoutEffect, useState } from "react";
import { BottomSheet } from "./bottom-sheet";

interface ContextMenuProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  anchorEl?: HTMLElement | null;
  children: React.ReactNode;
}

export function ContextMenu({ open, onClose, title, anchorEl, children }: ContextMenuProps) {
  const [isMobile, setIsMobile] = useState(true);
  const [pos, setPos] = useState({ top: 0, right: 0 });

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useLayoutEffect(() => {
    if (!open || !anchorEl) return;
    const rect = anchorEl.getBoundingClientRect();
    setPos({
      top: rect.bottom + 4,
      right: window.innerWidth - rect.right,
    });
  }, [open, anchorEl]);

  useEffect(() => {
    if (!open || isMobile) return;
    const handle = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [open, isMobile, onClose]);

  if (!open) return null;

  if (isMobile) {
    return (
      <BottomSheet open onClose={onClose} title={title}>
        {children}
      </BottomSheet>
    );
  }

  return (
    <div className="fixed inset-0 z-50" onClick={onClose}>
      <div
        className="absolute min-w-[200px] rounded-card border border-border bg-card py-1 shadow-lg"
        style={{ top: pos.top, right: pos.right }}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="border-b border-border px-4 pb-2.5 pt-2">
            <p className="text-sm font-semibold text-ink">{title}</p>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
