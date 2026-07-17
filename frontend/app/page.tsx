import { useTranslations } from "next-intl";

export default function HomePage() {
  const t = useTranslations("HomePage");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-2 p-4 text-center">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="text-base text-gray-600 dark:text-gray-400">{t("placeholder")}</p>
    </main>
  );
}
