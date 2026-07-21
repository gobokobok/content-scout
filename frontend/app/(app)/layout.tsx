"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Menu } from "lucide-react";
import { getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { closeTelegramWebApp } from "@/lib/telegram-webapp";
import { ContextMenu } from "@/components/ui/context-menu";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("App");
  const router = useRouter();
  const { user, loading, logout, isTelegram } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    // Don't redirect if a token exists — loadUser may still be committing its
    // setUser() update (React batches async state updates, so user can briefly
    // be null even after a successful telegramLogin/login call).
    if (!loading && !user && !getToken()) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <p className="text-secondary">{t("loading")}</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between gap-2 border-b border-border bg-card px-4 py-3">
        <Link
          href="/"
          className="font-display text-lg font-semibold text-ink hover:text-accent transition-colors"
        >
          content-scout
        </Link>
        <button
          onClick={(e) => {
            setMenuAnchorEl(e.currentTarget);
            setMenuOpen(true);
          }}
          className="rounded-control p-2 text-secondary hover:bg-bg transition-colors"
          aria-label="Меню"
        >
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {children}

      <ContextMenu
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        anchorEl={menuAnchorEl}
      >
        <div className="flex flex-col py-1">
          <div className="border-b border-border px-4 pb-2.5 pt-2">
            <p className="text-sm font-medium text-ink">{user.display_name}</p>
            {!isTelegram && <p className="text-xs text-secondary">{user.email}</p>}
          </div>
          <Link
            href="/"
            onClick={() => setMenuOpen(false)}
            className="px-4 py-3.5 text-base text-ink hover:bg-bg transition-colors"
          >
            {t("projects")}
          </Link>
          <Link
            href="/usage"
            onClick={() => setMenuOpen(false)}
            className="px-4 py-3.5 text-base text-ink hover:bg-bg transition-colors"
          >
            {t("usage")}
          </Link>
          <Link
            href="/settings"
            onClick={() => setMenuOpen(false)}
            className="px-4 py-3.5 text-base text-ink hover:bg-bg transition-colors"
          >
            {t("settings")}
          </Link>
          {user.is_admin && (
            <Link
              href="/admin"
              onClick={() => setMenuOpen(false)}
              className="px-4 py-3.5 text-base text-ink hover:bg-bg transition-colors"
            >
              {t("admin")}
            </Link>
          )}
          {isTelegram ? (
            <button
              onClick={() => {
                setMenuOpen(false);
                closeTelegramWebApp();
              }}
              className="px-4 py-3.5 text-left text-base text-danger hover:bg-bg transition-colors"
            >
              {t("closeApp")}
            </button>
          ) : (
            <button
              onClick={() => {
                setMenuOpen(false);
                logout();
                router.push("/login");
              }}
              className="px-4 py-3.5 text-left text-base text-danger hover:bg-bg transition-colors"
            >
              {t("logout")}
            </button>
          )}
        </div>
      </ContextMenu>
    </div>
  );
}
