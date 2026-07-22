"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProjectIndexPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();

  useEffect(() => {
    router.replace(`/projects/${params.id}/details`);
  }, [router, params.id]);

  return null;
}
