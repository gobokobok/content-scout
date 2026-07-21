/** Helpers for Telegram Web App context (E8-S5). */

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        ready: () => void;
        expand: () => void;
        close: () => void;
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

export function closeTelegramWebApp(): void {
  window.Telegram?.WebApp?.close();
}
