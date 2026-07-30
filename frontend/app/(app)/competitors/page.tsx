"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { SkeletonList } from "@/components/ui/skeleton";

export default function CompetitorsRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    api
      .listProjects()
      .then((projects) => {
        const active = projects.filter((p) => p.archived_at === null);
        const target = active[0] ?? projects[0];
        // No project yet — nothing to redirect to. Send back home, which now prompts a
        // brand-new account to create its first project instead of hanging on this skeleton.
        router.replace(target ? `/projects/${target.id}/competitors` : "/");
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          router.replace("/");
        }
      });
  }, [router]);

  return (
    <main className="mx-auto max-w-2xl p-4">
      <SkeletonList count={3} />
    </main>
  );
}
