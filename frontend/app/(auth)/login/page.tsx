"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const t = useTranslations("Auth");
  const router = useRouter();
  const { login, telegramLogin, telegramSignIn, user, isTelegram } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [tgProcessing, setTgProcessing] = useState(false);
  const [tgSignInError, setTgSignInError] = useState<string | null>(null);
  const [tgSigningIn, setTgSigningIn] = useState(false);

  const [tgConfig, setTgConfig] = useState<{ enabled: boolean; bot_username: string } | null>(
    null,
  );
  const tgContainerRef = useRef<HTMLDivElement>(null);
  const tgRedirectHandled = useRef(false);

  // Navigate as soon as auth-context has a user (reactive — avoids state-commit race)
  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  useEffect(() => {
    api.getTelegramConfig().then(setTgConfig).catch(() => {});
  }, []);

  // Handle Telegram redirect-auth: widget uses data-auth-url, so after the user confirms
  // in Telegram, the browser is redirected back to /login with id, hash, auth_date, … as
  // query params. Read them once on mount and exchange for a session.
  useEffect(() => {
    if (tgRedirectHandled.current) return;
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    const hash = params.get("hash");
    const authDate = params.get("auth_date");
    if (!id || !hash || !authDate) return;

    tgRedirectHandled.current = true;
    window.history.replaceState({}, "", "/login");

    const data: Record<string, string | number> = {
      id: parseInt(id, 10),
      auth_date: parseInt(authDate, 10),
      hash,
    };
    const firstName = params.get("first_name");
    const lastName = params.get("last_name");
    const username = params.get("username");
    const photoUrl = params.get("photo_url");
    if (firstName) data.first_name = firstName;
    if (lastName) data.last_name = lastName;
    if (username) data.username = username;
    if (photoUrl) data.photo_url = photoUrl;

    setSubmitting(true);
    setTgProcessing(true);
    telegramLogin(data)
      .catch((err) => setError(err instanceof ApiError ? err.messageRu : t("genericError")))
      .finally(() => { setSubmitting(false); setTgProcessing(false); });
  }, [telegramLogin, t]);

  // Mount the Telegram Login Widget using redirect flow (data-auth-url) so it works on
  // mobile where the JS callback approach breaks when Telegram opens as a separate app.
  useEffect(() => {
    if (!tgConfig?.enabled || !tgContainerRef.current) return;
    const container = tgContainerRef.current;
    if (container.querySelector("script")) return;

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", tgConfig.bot_username);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-auth-url", window.location.origin + "/login");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    container.appendChild(script);
  }, [tgConfig]);

  async function onTelegramSignIn() {
    setTgSigningIn(true);
    setTgSignInError(null);
    try {
      await telegramSignIn();
    } catch (err) {
      setTgSignInError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setTgSigningIn(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
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

      {tgProcessing && (
        <p className="text-sm text-secondary">{t("tgProcessing")}</p>
      )}

      {/* Inside the Mini App we already have initData — a direct sign-in beats mounting the
          external widget script, which assumes a browser redirect flow. */}
      {isTelegram && !tgProcessing && (
        <div className="flex flex-col items-center gap-3">
          <div className="flex w-full items-center gap-2">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-secondary">{t("orSeparator")}</span>
            <div className="h-px flex-1 bg-border" />
          </div>
          {tgSignInError && <p className="text-sm text-danger">{tgSignInError}</p>}
          <button
            onClick={() => void onTelegramSignIn()}
            disabled={tgSigningIn}
            className="w-full rounded-control bg-accent px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
          >
            {tgSigningIn ? t("loggingIn") : t("tgSignInButton")}
          </button>
        </div>
      )}

      {!isTelegram && tgConfig?.enabled && !tgProcessing && (
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
