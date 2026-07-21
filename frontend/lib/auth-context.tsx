"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearToken, getToken, setToken, type UserResponse } from "./api";
import { getTelegramInitData, initTelegramWebApp, isTelegramContext } from "./telegram-webapp";

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  isTelegram: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode?: string) => Promise<void>;
  telegramLogin: (data: Record<string, string | number>) => Promise<void>;
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
