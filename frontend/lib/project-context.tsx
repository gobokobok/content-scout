"use client";

import { createContext, useContext } from "react";
import type { ProjectResponse } from "@/lib/api";

interface ProjectContextValue {
  project: ProjectResponse | null;
  isArchived: boolean;
}

export const ProjectContext = createContext<ProjectContextValue>({
  project: null,
  isArchived: false,
});

export function useProject(): ProjectContextValue {
  return useContext(ProjectContext);
}
