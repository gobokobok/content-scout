"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const MIN_PASSWORD_LEN = 8;

export default function RegisterPage() {
  const t = useTranslations("Auth");
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD_LEN) {
      setError(t("passwordTooShort", { min: MIN_PASSWORD_LEN }));
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-ink">{t("registerTitle")}</h1>
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
            minLength={MIN_PASSWORD_LEN}
            autoComplete="new-password"
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
          {submitting ? t("registering") : t("registerButton")}
        </button>
      </form>
      <p className="text-sm text-secondary">
        {t("haveAccount")}{" "}
        <Link href="/login" className="font-medium text-accent underline">
          {t("loginLink")}
        </Link>
      </p>
    </div>
  );
}
