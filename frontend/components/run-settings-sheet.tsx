"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle2, Users, XCircle } from "lucide-react";
import { api, type RunAccountResponse, type RunResponse } from "@/lib/api";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { SkeletonRows } from "@/components/ui/skeleton";

interface RunSettingsSheetProps {
  run: RunResponse;
  open: boolean;
  onClose: () => void;
}

// E15-S5: read-only run-settings drill-down, shared by the Review run-detail page (Summary
// tab) and the Analysis report page's summary card — both pass the same RunResponse shape
// (the Analysis page fetches its underlying run via api.getRun(analysis.run_id)). Scope
// (duration_days/item_limit) already lives on RunResponse; the account list is fetched lazily
// on open via GET /runs/{run_id}/accounts (new, E15-S5) since it's not needed on every page load.
export function RunSettingsSheet({ run, open, onClose }: RunSettingsSheetProps) {
  const t = useTranslations("RunSettingsSheet");
  const [accounts, setAccounts] = useState<RunAccountResponse[] | null>(null);

  useEffect(() => {
    if (!open || run.analysis_mode === "post") return;
    setAccounts(null);
    api
      .getRunAccounts(run.id)
      .then(setAccounts)
      .catch(() => setAccounts([]));
  }, [open, run.id, run.analysis_mode]);

  const scopeText =
    run.analysis_mode === "post"
      ? t("scopePost")
      : run.duration_days != null
        ? t("scopeDays", { count: run.duration_days })
        : run.item_limit != null
          ? t("scopeCount", { count: run.item_limit })
          : t("scopeUnknown");

  return (
    <BottomSheet open={open} onClose={onClose} title={t("title")}>
      <div className="flex flex-col gap-4 px-4 pb-4">
        <div className="flex items-center justify-between gap-2 rounded-control border border-border p-2.5">
          <span className="text-sm text-secondary">{t("scopeLabel")}</span>
          <span className="text-sm font-medium text-ink">{scopeText}</span>
        </div>

        {run.analysis_mode === "post" ? (
          run.target_post_url && (
            <a
              href={run.target_post_url}
              target="_blank"
              rel="noreferrer"
              className="truncate text-sm text-accent hover:underline"
            >
              {run.target_post_url}
            </a>
          )
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-semibold text-ink">{t("accountsLabel")}</p>
            {accounts === null && <SkeletonRows count={3} />}
            {accounts !== null && accounts.length === 0 && (
              <p className="text-sm text-secondary">{t("accountsEmpty")}</p>
            )}
            {accounts !== null && accounts.length > 0 && (
              <ul className="flex max-h-72 flex-col overflow-y-auto rounded-control border border-border">
                {accounts.map((a, idx) => (
                  <li
                    key={a.id}
                    className={`flex items-center gap-3 px-3 py-2.5 ${
                      idx < accounts.length - 1 ? "border-b border-border" : ""
                    }`}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-bg">
                      {a.avatar_url ? (
                        // eslint-disable-next-line @next/next/no-img-element -- external, unpredictable CDN host
                        <img src={a.avatar_url} alt="" className="h-full w-full object-cover" />
                      ) : (
                        <Users className="h-4 w-4 text-secondary" />
                      )}
                    </span>
                    <div className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-sm font-medium text-ink">
                        {a.display_name || `@${a.handle}`}
                      </span>
                      <span className="truncate text-xs text-secondary">@{a.handle}</span>
                    </div>
                    {a.succeeded ? (
                      <CheckCircle2
                        className="h-4 w-4 shrink-0 text-success"
                        aria-label={t("accountSucceeded")}
                      />
                    ) : (
                      <span title={a.fail_reason ?? t("accountFailed")}>
                        <XCircle className="h-4 w-4 shrink-0 text-danger" aria-label={t("accountFailed")} />
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </BottomSheet>
  );
}
