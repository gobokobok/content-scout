"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/lib/auth-context";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("App");
  const router = useRouter();
  const { user, loading, logout, isTelegram } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
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
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-display text-lg font-semibold text-ink">content-scout</span>
        <div className="flex items-center gap-3">
          {!isTelegram && <span className="text-sm text-secondary">{user.email}</span>}
          <Link href="/usage" className="text-sm text-secondary hover:text-ink hover:underline">
            {t("usage")}
          </Link>
          {user.is_admin && (
            <Link href="/admin" className="text-sm text-secondary hover:text-ink hover:underline">
              {t("admin")}
            </Link>
          )}
          {!isTelegram && (
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="rounded-control border border-border px-3 py-1.5 text-sm text-ink hover:bg-bg"
            >
              {t("logout")}
            </button>
          )}
        </div>
      </header>
      {children}
    </div>
  );
}
