"use client";

import { useEffect } from "react";

interface SideDrawerProps {
  open: boolean;
  onClose: () => void;
  side: "left" | "right";
  children: React.ReactNode;
}

export function SideDrawer({ open, onClose, side, children }: SideDrawerProps) {
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
        {children}
      </div>
    </div>
  );
}
