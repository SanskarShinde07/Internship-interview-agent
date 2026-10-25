"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { loginUser, registerUser, setAuthToken } from "./api-client";
import type { AuthUser } from "./types";

const STORAGE_KEY = "intervue_auth";

interface StoredAuth {
  token: string;
  user: AuthUser;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredAuth(): StoredAuth | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null;
  }
}

function writeStoredAuth(value: StoredAuth | null): void {
  try {
    if (value) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // localStorage can throw (private browsing, quota, disabled) - auth
    // still works for the current tab via in-memory state either way.
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Reading localStorage needs `window`, unavailable during SSR - see
    // the matching comment in useVoiceTurn.ts for why this can't be a
    // useState initializer instead.
    const stored = readStoredAuth();
    if (stored) {
      setAuthToken(stored.token);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setUser(stored.user);
    }
    setIsLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const result = await loginUser({ email, password });
    setAuthToken(result.access_token);
    setUser(result.user);
    writeStoredAuth({ token: result.access_token, user: result.user });
  }

  async function register(email: string, password: string, displayName?: string) {
    const result = await registerUser({ email, password, display_name: displayName });
    setAuthToken(result.access_token);
    setUser(result.user);
    writeStoredAuth({ token: result.access_token, user: result.user });
  }

  function logout() {
    setAuthToken(null);
    setUser(null);
    writeStoredAuth(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
