"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const MIN_PASSWORD_LEN = 8;

export default function RegisterPage() {
  const t = useTranslations("Auth");
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [requireInvite, setRequireInvite] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.getRegisterConfig().then(({ require_invite }) => setRequireInvite(require_invite));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD_LEN) {
      setError(t("passwordTooShort", { min: MIN_PASSWORD_LEN }));
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, requireInvite ? inviteCode : undefined);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">{t("registerTitle")}</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">{t("emailLabel")}</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-base dark:border-gray-700 dark:bg-gray-900"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">{t("passwordLabel")}</span>
          <input
            type="password"
            required
            minLength={MIN_PASSWORD_LEN}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-base dark:border-gray-700 dark:bg-gray-900"
          />
        </label>
        {requireInvite && (
          <label className="flex flex-col gap-1">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {t("inviteCodeLabel")}
            </span>
            <input
              type="text"
              required
              autoComplete="off"
              placeholder={t("inviteCodePlaceholder")}
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-base dark:border-gray-700 dark:bg-gray-900"
            />
          </label>
        )}
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-gray-900 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
        >
          {submitting ? t("registering") : t("registerButton")}
        </button>
      </form>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {t("haveAccount")}{" "}
        <Link href="/login" className="font-medium underline">
          {t("loginLink")}
        </Link>
      </p>
    </div>
  );
}
