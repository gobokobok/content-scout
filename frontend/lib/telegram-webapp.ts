/** Helpers for Telegram Web App context (E8-S5). */

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        ready: () => void;
        expand: () => void;
        // Bot API 8.0+ — may be absent on older Telegram clients, check before calling.
        downloadFile?: (
          params: { url: string; file_name: string },
          callback?: (accepted: boolean) => void,
        ) => void;
        // Opens Telegram's native invoice sheet for a link from createInvoiceLink (E8-S3).
        openInvoice?: (
          url: string,
          callback?: (status: "paid" | "cancelled" | "failed" | "pending") => void,
        ) => void;
      };
    };
  }
}

export function isTelegramContext(): boolean {
  if (typeof window === "undefined") return false;
  return !!(window.Telegram?.WebApp?.initData);
}

export function getTelegramInitData(): string {
  return window.Telegram?.WebApp?.initData ?? "";
}

export function initTelegramWebApp(): void {
  if (!isTelegramContext()) return;
  window.Telegram!.WebApp!.ready();
  window.Telegram!.WebApp!.expand();
}

/** True when the Telegram client supports the native downloadFile popup (Bot API 8.0+). Regular
 * blob/<a download> links don't trigger a save prompt inside Telegram's iOS/Android WebView. */
export function canDownloadViaTelegram(): boolean {
  return isTelegramContext() && typeof window.Telegram?.WebApp?.downloadFile === "function";
}

export function downloadFileViaTelegram(url: string, fileName: string): void {
  window.Telegram!.WebApp!.downloadFile!({ url, file_name: fileName });
}

export type TelegramInvoiceStatus = "paid" | "cancelled" | "failed" | "pending";

/** Opens a Stars invoice link (from POST /billing/purchase-invoice, E8-S3) in Telegram's
 * native sheet and resolves with the payment outcome. Only callable inside a real Mini App —
 * callers must check isTelegramContext() first. */
export function openTelegramInvoice(url: string): Promise<TelegramInvoiceStatus> {
  return new Promise((resolve) => {
    window.Telegram!.WebApp!.openInvoice!(url, (status) => resolve(status));
  });
}

// Telegram's Bot API / WebApp initData exposes no timezone field for the account — this
// reads the device's own IANA zone via Intl instead, since the Mini App runs inside the
// user's own client. Used as the scheduled-run timezone (E14-S6 follow-up) instead of the
// hardcoded "Europe/Moscow" default. Falls back to Moscow only if Intl itself is unavailable
// (practically never, but keeps schedule creation from throwing in that edge case).
export function detectLocalTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";
  } catch {
    return "Europe/Moscow";
  }
}
