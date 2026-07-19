"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { api, ApiError, type AdminUsageResponse, type UserUsageRowResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function monthStart(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function formatCost(cost: string): string {
  return `$${parseFloat(cost).toFixed(4)}`;
}

function toInputDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function fromInputDate(value: string): Date {
  const [y, m] = value.split("-").map(Number);
  return new Date(y, m - 1, 1);
}

export default function AdminPage() {
  const t = useTranslations("Admin");
  const router = useRouter();
  const { user, loading } = useAuth();

  const now = new Date();
  const [from, setFrom] = useState<Date>(monthStart(now));
  const [to, setTo] = useState<Date>(monthStart(new Date(now.getFullYear(), now.getMonth() + 1, 1)));
  const [data, setData] = useState<AdminUsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async (f: Date, until: Date) => {
    setPending(true);
    setError(null);
    try {
      setData(await api.getAdminUsage(f, until));
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        router.replace("/");
      } else {
        setError(err instanceof ApiError ? err.messageRu : t("genericError"));
      }
    } finally {
      setPending(false);
    }
  }, [router, t]);

  useEffect(() => {
    if (!loading && user && !user.is_admin) {
      router.replace("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (user?.is_admin) {
      void load(from, to);
    }
  }, [user]);  // eslint-disable-line react-hooks/exhaustive-deps

  if (loading || !user?.is_admin) return null;

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold text-ink">{t("title")}</h1>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm text-secondary">
          {t("fromLabel")}
          <input
            type="month"
            value={toInputDate(from)}
            onChange={(e) => setFrom(fromInputDate(e.target.value))}
            className="rounded-control border border-border bg-card px-3 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-secondary">
          {t("toLabel")}
          <input
            type="month"
            value={toInputDate(new Date(to.getFullYear(), to.getMonth() - 1, 1))}
            onChange={(e) => {
              const d = fromInputDate(e.target.value);
              setTo(new Date(d.getFullYear(), d.getMonth() + 1, 1));
            }}
            className="rounded-control border border-border bg-card px-3 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
        <button
          onClick={() => void load(from, to)}
          disabled={pending}
          className="rounded-control bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {t("applyButton")}
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      {pending && <p className="text-secondary">{t("loading")}</p>}

      {!pending && data && data.users.length === 0 && (
        <p className="text-secondary">{t("empty")}</p>
      )}

      {!pending && data && data.users.length > 0 && (
        <div className="overflow-x-auto rounded-card border border-border">
          <table className="w-full min-w-max border-collapse text-sm">
            <thead>
              <tr>
                {[
                  t("colEmail"),
                  t("colRuns"),
                  t("colApify"),
                  t("colInputTokens"),
                  t("colOutputTokens"),
                  t("colCost"),
                ].map((h) => (
                  <th
                    key={h}
                    scope="col"
                    className="sticky top-0 whitespace-nowrap bg-bg px-4 py-2 text-left font-medium text-secondary"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.users.map((row: UserUsageRowResponse) => (
                <tr key={row.user_id} className="border-t border-border">
                  <td className="whitespace-nowrap px-4 py-2 text-ink">{row.email}</td>
                  <td className="whitespace-nowrap px-4 py-2 tabular-nums">{row.runs}</td>
                  <td className="whitespace-nowrap px-4 py-2 tabular-nums">
                    {new Intl.NumberFormat("ru-RU").format(row.apify_units)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2 tabular-nums">
                    {new Intl.NumberFormat("ru-RU").format(row.claude_input_tokens)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2 tabular-nums">
                    {new Intl.NumberFormat("ru-RU").format(row.claude_output_tokens)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2 tabular-nums">
                    {formatCost(row.total_cost_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
