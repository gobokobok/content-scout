/** Helpers for Telegram Web App context (E8-S5). */

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        ready: () => void;
        expand: () => void;
        // Bot API 7.7+ — without this, Telegram's own swipe-to-close gesture competes with
        // (and usually wins over) touch scrolling inside nested scrollable elements like the
        // competitor-picker bottom sheet, so vertical drags never reach it.
        disableVerticalSwipes?: () => void;
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
        // Bot API 6.1+ (E18-S7) — colors Telegram's own native chrome (the top bar outside
        // this app's own DOM) and the Mini App's outer background respectively. Accepts either
        // 'bg_color'/'secondary_bg_color' (always supported, every client since 6.1) or an
        // arbitrary #rrggbb hex (client-version-dependent — newer clients only; older ones
        // silently ignore an unsupported value rather than erroring, per Telegram's docs).
        setHeaderColor?: (color: string) => void;
        setBackgroundColor?: (color: string) => void;
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
  window.Telegram!.WebApp!.disableVerticalSwipes?.();
  applyTelegramChrome();
}

/** E18-S7: first-user report — on a light-theme phone, the side drawers' white bg-card read
 * as continuous with Telegram's own native top chrome bar (outside this app's DOM), so the
 * instinct to tap "close" hit Telegram's native X and exited the whole Mini App instead of the
 * drawer. Telegram's own light theme's default header color is typically 'bg_color' (white,
 * same as our drawer) — explicitly requesting the theme's 'secondary_bg_color' key (its own
 * light-gray surface color, distinct from white) separates the two without picking an
 * arbitrary hex outside the palette the client itself defines. Uses the theme-key form (not a
 * literal hex) since it's supported by every client since Bot API 6.1 — a raw hex needs a
 * newer client and would otherwise silently no-op on the collision it's meant to fix. Live
 * verification across Telegram clients/themes deferred — no Telegram client in this sandbox,
 * same established constraint as every other Telegram-behavior change in this project. */
export function applyTelegramChrome(): void {
  const app = window.Telegram?.WebApp;
  app?.setHeaderColor?.("secondary_bg_color");
  app?.setBackgroundColor?.("secondary_bg_color");
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
