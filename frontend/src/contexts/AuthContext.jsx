/**
 * AuthContext — manages Lumina session state.
 *
 * - access_token is stored in memory (never localStorage — XSS risk)
 * - refresh token lives in httpOnly cookie managed by backend
 * - on mount, tries /auth/refresh to restore session silently
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);          // { id, name, email, avatar_url, role, school_id }
  const [accessToken, setAccessToken] = useState(null);
  const [loading, setLoading] = useState(true);    // true while restoring session on mount

  // ---------------------------------------------------------------- //
  // Restore session on mount via refresh cookie                       //
  // ---------------------------------------------------------------- //
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",          // send httpOnly cookie
        });
        if (res.ok) {
          const data = await res.json();
          setAccessToken(data.access_token);
          // Fetch full user profile
          const meRes = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${data.access_token}` },
            credentials: "include",
          });
          if (meRes.ok) setUser(await meRes.json());
        }
      } catch {
        // Network error — stay logged out
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // ---------------------------------------------------------------- //
  // Login with Canvas API key                                         //
  // ---------------------------------------------------------------- //
  const loginWithApiKey = useCallback(async (canvasUrl, apiKey) => {
    const res = await fetch(`${API_BASE}/auth/apikey`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_url: canvasUrl, api_key: apiKey }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail ?? "Login failed");
    }

    const data = await res.json();
    setAccessToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  // ---------------------------------------------------------------- //
  // Logout                                                            //
  // ---------------------------------------------------------------- //
  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
    } catch {
      // Best-effort logout
    }
    setAccessToken(null);
    setUser(null);
  }, [accessToken]);

  // ---------------------------------------------------------------- //
  // Authenticated fetch helper — auto-refreshes on 401               //
  // ---------------------------------------------------------------- //
  const authFetch = useCallback(async (url, options = {}) => {
    const doFetch = (token) =>
      fetch(url, {
        ...options,
        credentials: "include",
        headers: {
          ...(options.headers ?? {}),
          Authorization: `Bearer ${token}`,
        },
      });

    let res = await doFetch(accessToken);

    if (res.status === 401) {
      // Try to refresh
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (refreshRes.ok) {
        const { access_token } = await refreshRes.json();
        setAccessToken(access_token);
        res = await doFetch(access_token);
      } else {
        // Refresh failed — force logout
        setAccessToken(null);
        setUser(null);
      }
    }

    return res;
  }, [accessToken]);

  return (
    <AuthContext.Provider value={{ user, accessToken, loading, loginWithApiKey, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
