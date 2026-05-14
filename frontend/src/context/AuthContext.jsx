"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const STORAGE_KEY = "titan-demo-auth";

function readStored() {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && parsed.v === 1 && typeof parsed.email === "string") {
      return parsed;
    }
  } catch {
    /* ignore */
  }
  return null;
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState(null);

  useEffect(() => {
    setSession(readStored());
    setMounted(true);
  }, []);

  /** Demo only: any email/password is accepted. */
  const login = useCallback((email, _password) => {
    const trimmed = (email || "").trim();
    const next = { v: 1, email: trimmed || "analyst@local" };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const value = useMemo(
    () => ({
      mounted,
      isAuthenticated: Boolean(session),
      email: session?.email ?? null,
      login,
      logout,
    }),
    [mounted, session, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
