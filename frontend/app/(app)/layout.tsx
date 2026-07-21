"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Menu, Pencil, Bell, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRunTracker, type TrackedRun } from "@/lib/run-tracker";
import { ContextMenu } from "@/components/ui/context-menu";

const STATUS_KEYS = {
  pending: "statusPending",
  scraping: "statusScraping",
  summarizing: "statusSummarizing",
  done: "statusDone",
  failed: "statusFailed",
} as const;

function RunStatusIcon({ status }: { status: TrackedRun["run"]["status"] }) {
  if (status === "done") return <CheckCircle className="h-4 w-4 shrink-0 text-success" />;
  if (status === "failed") return <AlertCircle className="h-4 w-4 shrink-0 text-danger" />;
  return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-secondary" />;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("App");
  const tRun = useTranslations("RunDialog");
  const router = useRouter();
  const { user, loading, logout, telegramLogout, isTelegram } = useAuth();
  const { trackedRuns, unseenCount, markAllSeen } = useRunTracker();
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifAnchorEl, setNotifAnchorEl] = useState<HTMLElement | null>(null);

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
        <div className="flex items-center gap-1">
          {trackedRuns.length > 0 && (
            <button
              onClick={(e) => {
                setNotifAnchorEl(e.currentTarget);
                setNotifOpen(true);
                markAllSeen();
              }}
              className="relative rounded-control p-2 text-secondary hover:bg-bg transition-colors"
              aria-label={t("notificationsLabel")}
            >
              <Bell className="h-5 w-5" />
              {unseenCount > 0 && (
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger" />
              )}
            </button>
          )}
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
        </div>
      </header>

      {children}

      <ContextMenu
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        anchorEl={menuAnchorEl}
      >
        <div className="flex flex-col py-1">
          <Link
            href="/settings"
            onClick={() => setMenuOpen(false)}
            className="flex items-center justify-between gap-2 border-b border-border px-4 pb-2.5 pt-2 hover:bg-bg transition-colors"
          >
            <div>
              <p className="text-sm font-medium text-ink">{user.display_name}</p>
              {!isTelegram && <p className="text-xs text-secondary">{user.email}</p>}
            </div>
            <Pencil className="h-3.5 w-3.5 shrink-0 text-secondary" />
          </Link>
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
          <button
            onClick={() => {
              setMenuOpen(false);
              if (isTelegram) telegramLogout();
              else logout();
              router.push("/login");
            }}
            className="px-4 py-3.5 text-left text-base text-danger hover:bg-bg transition-colors"
          >
            {t("logout")}
          </button>
        </div>
      </ContextMenu>

      <ContextMenu
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
        title={t("notificationsLabel")}
        anchorEl={notifAnchorEl}
      >
        <div className="flex max-w-xs flex-col py-1">
          {trackedRuns.length === 0 && (
            <p className="px-4 py-3 text-sm text-secondary">{t("noRuns")}</p>
          )}
          {trackedRuns.map((tracked) => (
            <button
              key={tracked.run.id}
              onClick={() => {
                setNotifOpen(false);
                router.push(`/projects/${tracked.projectId}/results?run=${tracked.run.id}`);
              }}
              className="flex items-center gap-2.5 px-4 py-3 text-left hover:bg-bg transition-colors"
            >
              <RunStatusIcon status={tracked.run.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink">{tracked.projectName}</p>
                <p className="text-xs text-secondary">{tRun(STATUS_KEYS[tracked.run.status])}</p>
              </div>
            </button>
          ))}
        </div>
      </ContextMenu>
    </div>
  );
}
