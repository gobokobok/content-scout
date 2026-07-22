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
