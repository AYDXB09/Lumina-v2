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
  // Auth requests share one shape: POST body → { access_token, user }  //
  // ---------------------------------------------------------------- //
  const _authPost = useCallback(async (path, body) => {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      // FastAPI validation errors (422) return `detail` as an array of
      // {msg, loc, ...} objects, not a string -- stringifying that array
      // directly used to render as literal "[object Object]" in the UI.
      const detail = Array.isArray(err.detail)
        ? err.detail.map((d) => d.msg ?? JSON.stringify(d)).join("; ")
        : err.detail;
      throw new Error(detail ?? "Request failed");
    }
    return res.json();
  }, []);

  /** Create a Lumina account: email + password + one-time Canvas key. */
  const signup = useCallback(async (email, password, canvasUrl, apiKey) => {
    const data = await _authPost("/auth/signup", {
      email, password, canvas_url: canvasUrl, api_key: apiKey,
    });
    setAccessToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, [_authPost]);

  /** Sign in with email + password. */
  const login = useCallback(async (email, password) => {
    const data = await _authPost("/auth/login", { email, password });
    setAccessToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, [_authPost]);

  /** Request a password-reset email. Always resolves — backend never reveals if the email exists. */
  const forgotPassword = useCallback(async (email) => {
    await _authPost("/auth/forgot-password", { email });
  }, [_authPost]);

  /** Consume the token from the reset-link email and set a new password. */
  const resetPassword = useCallback(async (tokenHash, newPassword) => {
    await _authPost("/auth/reset-password", { token_hash: tokenHash, new_password: newPassword });
  }, [_authPost]);

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

  /** Replace the stored Canvas API key (Settings → Account). */
  const updateCanvasKey = useCallback(async (canvasUrl, apiKey) => {
    const res = await authFetch(`${API_BASE}/auth/canvas-key`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_url: canvasUrl, api_key: apiKey }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? "Failed to update Canvas key");
    }
    const data = await res.json();
    setUser(prev => prev ? { ...prev, canvas_key_last4: data.canvas_key_last4 } : prev);
    return data;
  }, [authFetch]);

  return (
    <AuthContext.Provider value={{
      user, accessToken, loading,
      signup, login, forgotPassword, resetPassword, updateCanvasKey,
      logout, authFetch,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
