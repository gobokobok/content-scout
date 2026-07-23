"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Menu, Bell, Coins, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRunTracker, type TrackedRun } from "@/lib/run-tracker";
import { useHeader } from "@/lib/header-context";
import { SideDrawer } from "@/components/ui/side-drawer";

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
  const { centerTitle } = useHeader();
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

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
      <header
        className="sticky top-0 z-30 flex items-center gap-2 border-b border-border/60 bg-bg/80 px-4 py-3 backdrop-blur-lg"
        style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
      >
        <button
          onClick={() => setMenuOpen(true)}
          className="shrink-0 rounded-chip border border-border bg-card p-2.5 text-ink transition-colors active:scale-[0.98] hover:bg-bg"
          aria-label={t("menuLabel")}
        >
          <Menu className="h-4.5 w-4.5" />
        </button>

        <div className="min-w-0 flex-1 px-2 text-center">
          {centerTitle && (
            <p className="truncate text-[17px] font-semibold tracking-tight text-ink">
              {centerTitle}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <button
            onClick={() => {
              setNotifOpen(true);
              markAllSeen();
            }}
            className="relative shrink-0 rounded-chip border border-border bg-card p-2.5 text-ink transition-colors active:scale-[0.98] hover:bg-bg"
            aria-label={t("notificationsLabel")}
          >
            <Bell className="h-4.5 w-4.5" />
            {unseenCount > 0 && (
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger" />
            )}
          </button>
          <button
            onClick={() => router.push("/usage")}
            className="inline-flex items-center gap-1.5 rounded-chip border border-[#DCE9B8] bg-accent-soft px-3 py-2 font-mono text-xs font-semibold tabular-nums text-accent transition-colors active:scale-[0.98] hover:opacity-90"
            aria-label={t("tokensLabel")}
          >
            <Coins className="h-3.5 w-3.5" />
            {new Intl.NumberFormat("ru-RU").format(user.token_balance)}
          </button>
        </div>
      </header>

      {children}

      <SideDrawer open={menuOpen} onClose={() => setMenuOpen(false)} side="left">
        <div className="border-b border-border px-4 py-4">
          <p className="truncate text-base font-semibold text-ink">{user.display_name}</p>
          {!isTelegram && <p className="mt-0.5 truncate text-xs text-secondary">{user.email}</p>}
        </div>
        <nav className="flex flex-1 flex-col overflow-y-auto py-2">
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
        </nav>
        <div className="border-t border-border p-3">
          <button
            onClick={() => {
              setMenuOpen(false);
              if (isTelegram) telegramLogout();
              else logout();
              router.push("/login");
            }}
            className="w-full rounded-control px-4 py-3 text-left text-base text-danger hover:bg-bg transition-colors"
          >
            {t("logout")}
          </button>
        </div>
      </SideDrawer>

      <SideDrawer open={notifOpen} onClose={() => setNotifOpen(false)} side="right">
        <div className="border-b border-border px-4 py-4">
          <p className="text-base font-semibold text-ink">{t("notificationsLabel")}</p>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {trackedRuns.length === 0 && (
            <p className="px-4 py-6 text-sm text-secondary">{t("noRuns")}</p>
          )}
          {trackedRuns.map((tracked) => (
            <button
              key={tracked.run.id}
              onClick={() => {
                setNotifOpen(false);
                router.push(`/projects/${tracked.projectId}/runs/${tracked.run.id}`);
              }}
              className="flex w-full items-center gap-2.5 px-4 py-3 text-left hover:bg-bg transition-colors"
            >
              <RunStatusIcon status={tracked.run.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink">{tracked.projectName}</p>
                <p className="text-xs text-secondary">{tRun(STATUS_KEYS[tracked.run.status])}</p>
              </div>
            </button>
          ))}
        </div>
      </SideDrawer>
    </div>
  );
}
