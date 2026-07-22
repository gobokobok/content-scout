"use client";

import { createContext, useContext, useEffect, useState } from "react";

interface HeaderContextValue {
  centerTitle: string | null;
  setCenterTitle: (title: string | null) => void;
}

const HeaderContext = createContext<HeaderContextValue | null>(null);

export function HeaderProvider({ children }: { children: React.ReactNode }) {
  const [centerTitle, setCenterTitle] = useState<string | null>(null);
  return (
    <HeaderContext.Provider value={{ centerTitle, setCenterTitle }}>
      {children}
    </HeaderContext.Provider>
  );
}

export function useHeader(): HeaderContextValue {
  const ctx = useContext(HeaderContext);
  if (!ctx) throw new Error("useHeader must be used within HeaderProvider");
  return ctx;
}

/** Pushes `title` into the app top bar's center slot for as long as the calling component is mounted. */
export function useHeaderTitle(title: string | null): void {
  const { setCenterTitle } = useHeader();
  useEffect(() => {
    setCenterTitle(title);
    return () => setCenterTitle(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title]);
}
