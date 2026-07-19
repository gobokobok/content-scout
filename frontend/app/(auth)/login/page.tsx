"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, api, setToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const t = useTranslations("Auth");
  const router = useRouter();
  const { login, isTelegram } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [tgConfig, setTgConfig] = useState<{ enabled: boolean; bot_username: string } | null>(
    null,
  );
  const tgContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getTelegramConfig().then(setTgConfig).catch(() => {});
  }, []);

  // Mount the Telegram Login Widget once bot_username is known
  useEffect(() => {
    if (!tgConfig?.enabled || !tgContainerRef.current) return;
    const container = tgContainerRef.current;
    if (container.querySelector("script")) return;

    (window as unknown as Record<string, unknown>)["onTelegramAuth"] = async (
      user: Record<string, string | number>,
    ) => {
      setError(null);
      setSubmitting(true);
      try {
        const { access_token } = await api.telegramLogin(user);
        setToken(access_token);
        router.push("/");
      } catch (err) {
        setError(err instanceof ApiError ? err.messageRu : t("genericError"));
      } finally {
        setSubmitting(false);
      }
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", tgConfig.bot_username);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    container.appendChild(script);

    return () => {
      delete (window as unknown as Record<string, unknown>)["onTelegramAuth"];
    };
  }, [tgConfig, router, t]);

  // Inside Telegram the Mini App auto-authenticates via initData — no form needed
  if (isTelegram) return null;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-ink">{t("loginTitle")}</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-secondary">{t("emailLabel")}</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-secondary">{t("passwordLabel")}</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
        {error && <p className="text-sm text-danger">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-control bg-accent px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
        >
          {submitting ? t("loggingIn") : t("loginButton")}
        </button>
      </form>

      {tgConfig?.enabled && (
        <div className="flex flex-col items-center gap-3">
          <div className="flex w-full items-center gap-2">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-secondary">{t("orSeparator")}</span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <div ref={tgContainerRef} />
        </div>
      )}

      <p className="text-sm text-secondary">
        {t("noAccount")}{" "}
        <Link href="/register" className="font-medium text-accent underline">
          {t("registerLink")}
        </Link>
      </p>
    </div>
  );
}
