"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearToken, getToken, setToken, type UserResponse } from "./api";
import { getTelegramInitData, initTelegramWebApp, isTelegramContext } from "./telegram-webapp";

// Telegram always hands us initData for the account currently signed into the Telegram app —
// there's no "log out of Telegram" concept we can hook into. To make "Выйти" behave like a
// real logout, we remember that the user explicitly signed out and skip auto-login on the next
// mount until they tap a sign-in button again (telegramSignIn clears this).
const TG_LOGGED_OUT_KEY = "content-scout-tg-logged-out";

function isTelegramLoggedOut(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(TG_LOGGED_OUT_KEY) === "1";
}

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  isTelegram: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode?: string) => Promise<void>;
  telegramLogin: (data: Record<string, string | number>) => Promise<void>;
  telegramSignIn: () => Promise<void>;
  telegramLogout: () => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isTelegram, setIsTelegram] = useState(false);

  const loadUser = useCallback(async () => {
    const tokenAtEntry = getToken();
    if (!tokenAtEntry) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.me());
    } catch (err) {
      if (getToken() === tokenAtEntry) {
        // Definitive failure — no concurrent login replaced the token.
        clearToken();
        setUser(null);
        throw err; // propagate so callers (login, telegramLogin) can show the error
      }
      // A concurrent login replaced the token while this call was in-flight;
      // don't interfere — its own loadUser will complete and set the user.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const tg = isTelegramContext();
    setIsTelegram(tg);

    if (tg) {
      initTelegramWebApp();
    }

    if (tg && !getToken()) {
      if (isTelegramLoggedOut()) {
        // User explicitly logged out last time — wait for a manual telegramSignIn() tap
        // instead of silently re-authenticating via initData.
        setLoading(false);
        return;
      }
      // Auto-authenticate via initData — no login form shown inside Telegram
      const initData = getTelegramInitData();
      if (initData) {
        api
          .telegramWebappLogin(initData)
          .then(({ access_token }) => {
            setToken(access_token);
            return loadUser();
          })
          .catch(() => {
            // If auto-auth fails, fall through to the normal loading state
            setLoading(false);
          });
        return;
      }
    }

    void loadUser().catch(() => {
      // Initial session restore failed — state already cleared inside loadUser.
    });
  }, [loadUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      await loadUser();
    },
    [loadUser],
  );

  const register = useCallback(
    async (email: string, password: string, inviteCode?: string) => {
      const { access_token } = await api.register(email, password, inviteCode);
      setToken(access_token);
      await loadUser();
    },
    [loadUser],
  );

  const telegramLogin = useCallback(
    async (data: Record<string, string | number>) => {
      const { access_token } = await api.telegramLogin(data);
      setToken(access_token);
      await loadUser();
    },
    [loadUser],
  );

  const telegramSignIn = useCallback(async () => {
    const initData = getTelegramInitData();
    if (!initData) return;
    window.localStorage.removeItem(TG_LOGGED_OUT_KEY);
    const { access_token } = await api.telegramWebappLogin(initData);
    setToken(access_token);
    await loadUser();
  }, [loadUser]);

  const telegramLogout = useCallback(() => {
    window.localStorage.setItem(TG_LOGGED_OUT_KEY, "1");
    clearToken();
    setUser(null);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isTelegram,
        login,
        register,
        telegramLogin,
        telegramSignIn,
        telegramLogout,
        logout,
        refreshUser: loadUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
