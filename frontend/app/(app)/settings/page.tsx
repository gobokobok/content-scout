"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ToggleSwitch } from "@/components/ui";

export default function SettingsPage() {
  const t = useTranslations("Settings");
  const { user, isTelegram, refreshUser } = useAuth();

  const [tgConfig, setTgConfig] = useState<{ enabled: boolean; bot_username: string } | null>(
    null,
  );
  const [linked, setLinked] = useState(user?.has_telegram ?? false);
  const [error, setError] = useState<string | null>(null);
  const tgContainerRef = useRef<HTMLDivElement>(null);

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameSaved, setNameSaved] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    setDisplayName(user?.display_name ?? "");
  }, [user]);

  // E22-S3: global notify toggles, replacing the per-run/per-schedule field entirely — no
  // per-run override, this Settings section is the single place to control it.
  const [notifyReview, setNotifyReview] = useState(user?.notify_review_enabled ?? true);
  const [notifyAnalysis, setNotifyAnalysis] = useState(user?.notify_analysis_enabled ?? true);
  const [notifySaving, setNotifySaving] = useState(false);
  const [notifySaved, setNotifySaved] = useState(false);
  const [notifyError, setNotifyError] = useState<string | null>(null);

  useEffect(() => {
    setNotifyReview(user?.notify_review_enabled ?? true);
    setNotifyAnalysis(user?.notify_analysis_enabled ?? true);
  }, [user]);

  const saveNotifyPrefs = useCallback(
    async (next: { notify_review_enabled: boolean; notify_analysis_enabled: boolean }) => {
      setNotifySaving(true);
      setNotifyError(null);
      setNotifySaved(false);
      try {
        await api.updateNotifyPrefs(next);
        await refreshUser();
        setNotifySaved(true);
      } catch (err) {
        setNotifyError(err instanceof ApiError ? err.messageRu : t("genericError"));
      } finally {
        setNotifySaving(false);
      }
    },
    [refreshUser, t],
  );

  const handleSaveName = useCallback(async () => {
    const trimmed = displayName.trim();
    if (!trimmed) {
      setNameError(t("displayNameEmpty"));
      return;
    }
    setNameSaving(true);
    setNameError(null);
    setNameSaved(false);
    try {
      await api.updateDisplayName(trimmed);
      await refreshUser();
      setNameSaved(true);
    } catch (err) {
      setNameError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setNameSaving(false);
    }
  }, [displayName, refreshUser, t]);

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

      <section className="mb-4 flex flex-col gap-3 rounded-card border border-border bg-card p-5">
        <h2 className="text-base font-medium text-ink">{t("displayNameSection")}</h2>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-secondary">{t("displayNameLabel")}</span>
          <input
            type="text"
            value={displayName}
            maxLength={50}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setNameSaved(false);
            }}
            className="rounded-control border border-border bg-bg px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
          />
        </label>
        {nameError && <p className="text-sm text-danger">{nameError}</p>}
        {nameSaved && !nameError && (
          <p className="flex items-center gap-2 text-sm text-success">
            <CheckCircle className="h-4 w-4" />
            {t("displayNameSaved")}
          </p>
        )}
        <button
          onClick={handleSaveName}
          disabled={nameSaving || displayName.trim() === user?.display_name}
          className="self-start rounded-control bg-accent px-4 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-50"
        >
          {t("displayNameSave")}
        </button>
      </section>

      <section className="mb-4 flex flex-col gap-3 rounded-card border border-border bg-card p-5">
        <h2 className="text-base font-medium text-ink">{t("notifySection")}</h2>
        <p className="text-sm text-secondary">{t("notifySectionHint")}</p>
        <ToggleSwitch
          checked={notifyReview}
          onChange={() => {
            const next = !notifyReview;
            setNotifyReview(next);
            void saveNotifyPrefs({
              notify_review_enabled: next,
              notify_analysis_enabled: notifyAnalysis,
            });
          }}
          label={t("notifyReviewLabel")}
        />
        <ToggleSwitch
          checked={notifyAnalysis}
          onChange={() => {
            const next = !notifyAnalysis;
            setNotifyAnalysis(next);
            void saveNotifyPrefs({
              notify_review_enabled: notifyReview,
              notify_analysis_enabled: next,
            });
          }}
          label={t("notifyAnalysisLabel")}
        />
        {notifyError && <p className="text-sm text-danger">{notifyError}</p>}
        {notifySaved && !notifyError && !notifySaving && (
          <p className="flex items-center gap-2 text-sm text-success">
            <CheckCircle className="h-4 w-4" />
            {t("notifySaved")}
          </p>
        )}
      </section>

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
