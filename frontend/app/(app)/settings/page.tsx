"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const t = useTranslations("Settings");
  const { user, isTelegram } = useAuth();

  const [tgConfig, setTgConfig] = useState<{ enabled: boolean; bot_username: string } | null>(
    null,
  );
  const [linked, setLinked] = useState(user?.has_telegram ?? false);
  const [error, setError] = useState<string | null>(null);
  const tgContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLinked(user?.has_telegram ?? false);
  }, [user]);

  useEffect(() => {
    api.getTelegramConfig().then(setTgConfig).catch(() => {});
  }, []);

  const handleTelegramLink = useCallback(
    async (widgetData: Record<string, string | number>) => {
      setError(null);
      try {
        await api.telegramLink(widgetData);
        setLinked(true);
      } catch (err) {
        setError(err instanceof ApiError ? err.messageRu : t("genericError"));
      }
    },
    [t],
  );

  // Mount the Telegram Login Widget for linking (only when not yet linked)
  useEffect(() => {
    if (linked || !tgConfig?.enabled || !tgContainerRef.current) return;
    const container = tgContainerRef.current;
    if (container.querySelector("script")) return;

    (window as unknown as Record<string, unknown>)["onTelegramLink"] = (
      user: Record<string, string | number>,
    ) => {
      void handleTelegramLink(user);
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", tgConfig.bot_username);
    script.setAttribute("data-size", "medium");
    script.setAttribute("data-onauth", "onTelegramLink(user)");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    container.appendChild(script);

    return () => {
      delete (window as unknown as Record<string, unknown>)["onTelegramLink"];
    };
  }, [tgConfig, linked, handleTelegramLink]);

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      <h1 className="mb-6 text-2xl font-semibold text-ink">{t("title")}</h1>

      <section className="flex flex-col gap-4 rounded-card border border-border bg-card p-5">
        <h2 className="text-base font-medium text-ink">{t("telegramSection")}</h2>

        {linked ? (
          <div className="flex items-center gap-2 text-success">
            <CheckCircle className="h-5 w-5" />
            <span className="text-sm">{t("telegramLinked")}</span>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-secondary">{t("telegramLinkHint")}</p>
            {error && <p className="text-sm text-danger">{error}</p>}
            {tgConfig?.enabled ? (
              <div ref={tgContainerRef} />
            ) : (
              <p className="text-sm text-secondary">{t("telegramNotConfigured")}</p>
            )}
          </div>
        )}

        {/* Inside Telegram the account is already linked automatically */}
        {isTelegram && linked && (
          <p className="text-xs text-secondary">{t("telegramAutoLinked")}</p>
        )}
      </section>
    </div>
  );
}
