"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/lib/auth-context";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("App");
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <p className="text-gray-600 dark:text-gray-400">{t("loading")}</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-4 py-3 dark:border-gray-800">
        <span className="text-lg font-semibold">content-scout</span>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600 dark:text-gray-400">{user.email}</span>
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700"
          >
            {t("logout")}
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}
