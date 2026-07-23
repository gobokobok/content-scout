import type { Metadata } from "next";
import Script from "next/script";
import { Golos_Text, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { AuthProvider } from "@/lib/auth-context";
import { RunTrackerProvider } from "@/lib/run-tracker";
import { ToastProvider } from "@/components/ui/toast";
import { HeaderProvider } from "@/lib/header-context";
import "./globals.css";

const golos = Golos_Text({
  subsets: ["latin", "cyrillic"],
  variable: "--font-golos",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-jetbrains-mono",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "content-scout",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const messages = await getMessages();

  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        {/* Telegram does not inject window.Telegram.WebApp on its own — the Mini App
            must load this script itself. beforeInteractive guarantees it runs before
            AuthProvider's mount effect checks isTelegramContext(). */}
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
      </head>
      <body
        className={`${golos.variable} ${jetbrainsMono.variable} antialiased bg-bg text-ink font-sans`}
      >
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <RunTrackerProvider>
              <ToastProvider>
                <HeaderProvider>{children}</HeaderProvider>
              </ToastProvider>
            </RunTrackerProvider>
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
