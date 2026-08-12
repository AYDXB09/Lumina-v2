/**
 * LoginScreen — email + password authentication (Supabase Auth).
 *
 * Two modes:
 *   - Sign in: email + password
 *   - Create account: email + password + Canvas URL + Canvas API key,
 *     captured once so it never needs pasting again (see SettingsModal
 *     for where it's viewed/replaced afterwards).
 *
 * "Forgot password?" sends a reset-link email; the link lands on
 * ResetPasswordScreen (rendered by App.jsx based on the URL, outside
 * this auth gate since the user isn't signed in yet).
 */

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import LuminaLogo from "./LuminaLogo.jsx";

const DEFAULT_CANVAS_URL = import.meta.env.VITE_CANVAS_URL ?? "https://dwight.instructure.com";

export default function LoginScreen() {
  const { login, signup, forgotPassword } = useAuth();

  const [mode, setMode] = useState("signin"); // "signin" | "signup" | "forgot"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [canvasUrl, setCanvasUrl] = useState(DEFAULT_CANVAS_URL);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      if (mode === "signin") {
        await login(email.trim(), password);
      } else if (mode === "signup") {
        await signup(email.trim(), password, canvasUrl.trim(), apiKey.trim());
      } else if (mode === "forgot") {
        await forgotPassword(email.trim());
        setNotice("If an account exists for that email, a reset link is on its way.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.logoWrap}><LuminaLogo size={52} /></div>
          <h1 style={styles.title}>Lumina</h1>
          <p style={styles.subtitle}>Your AI study companion for Canvas</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Email
            <input
              style={styles.input}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@school.edu"
              required
              autoComplete="email"
            />
          </label>

          {mode !== "forgot" && (
            <label style={styles.label}>
              Password
              <input
                style={styles.input}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "signup" ? "Choose a password" : "Your password"}
                required
                minLength={8}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
              />
            </label>
          )}

          {mode === "signup" && (
            <>
              <label style={styles.label}>
                Canvas URL
                <input
                  style={styles.input}
                  type="url"
                  value={canvasUrl}
                  onChange={(e) => setCanvasUrl(e.target.value)}
                  placeholder="https://yourschool.instructure.com"
                  required
                  autoComplete="url"
                />
              </label>

              <label style={styles.label}>
                Canvas API Key
                <input
                  style={styles.input}
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Paste your Canvas access token"
                  required
                  autoComplete="off"
                />
                <span style={styles.hint}>
                  Canvas → Account → Settings → New Access Token. You'll only paste this once —
                  it's stored encrypted and shown masked afterwards in Settings.
                </span>
              </label>
            </>
          )}

          {error && <p style={styles.error}>{error}</p>}
          {notice && <p style={styles.notice}>{notice}</p>}

          <button type="submit" style={styles.button} disabled={loading}>
            {loading
              ? "Please wait…"
              : mode === "signin" ? "Sign in"
              : mode === "signup" ? "Create account"
              : "Send reset link"}
          </button>
        </form>

        <div style={styles.switchRow}>
          {mode === "signin" && (
            <>
              <button style={styles.linkBtn} onClick={() => { setMode("forgot"); setError(null); setNotice(null); }}>
                Forgot password?
              </button>
              <button style={styles.linkBtn} onClick={() => { setMode("signup"); setError(null); setNotice(null); }}>
                Create an account
              </button>
            </>
          )}
          {mode !== "signin" && (
            <button style={styles.linkBtn} onClick={() => { setMode("signin"); setError(null); setNotice(null); }}>
              ← Back to sign in
            </button>
          )}
        </div>

        <p style={styles.footer}>
          Your Canvas key is encrypted and never shared with anyone.
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--color-bg)",
    backgroundImage: "linear-gradient(var(--color-border) 1px, transparent 1px), linear-gradient(90deg, var(--color-border) 1px, transparent 1px)",
    backgroundSize: "40px 40px",
    padding: "24px",
  },
  card: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "40px 36px",
    width: "100%",
    maxWidth: "420px",
    boxShadow: "0 8px 32px rgba(0,0,0,0.1)",
  },
  header: {
    textAlign: "center",
    marginBottom: "32px",
  },
  logoWrap: {
    display: "flex",
    justifyContent: "center",
    marginBottom: "14px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "700",
    color: "var(--color-text)",
    margin: "0 0 6px",
  },
  subtitle: {
    fontSize: "14px",
    color: "var(--color-text-muted)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "20px",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    fontSize: "13px",
    fontWeight: "500",
    color: "var(--color-text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  input: {
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "8px",
    padding: "10px 14px",
    color: "var(--color-text)",
    fontSize: "14px",
    outline: "none",
    transition: "border-color 0.15s",
    boxSizing: "border-box",
    width: "100%",
  },
  hint: {
    fontSize: "12px",
    color: "var(--color-text-muted)",
    fontWeight: "400",
    textTransform: "none",
    letterSpacing: "normal",
  },
  button: {
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    border: "none",
    borderRadius: "9999px",
    padding: "12px",
    fontSize: "15px",
    fontWeight: "600",
    marginTop: "4px",
    transition: "background 0.15s",
    cursor: "pointer",
  },
  error: {
    color: "var(--color-error)",
    fontSize: "14px",
    background: "rgba(248,113,113,0.1)",
    border: "1px solid rgba(248,113,113,0.25)",
    borderRadius: "8px",
    padding: "10px 14px",
  },
  notice: {
    color: "var(--color-text)",
    fontSize: "14px",
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "8px",
    padding: "10px 14px",
  },
  switchRow: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: "18px",
  },
  linkBtn: {
    background: "none",
    border: "none",
    color: "var(--color-primary)",
    fontSize: "13px",
    fontWeight: "500",
    cursor: "pointer",
    padding: 0,
  },
  footer: {
    marginTop: "24px",
    textAlign: "center",
    fontSize: "12px",
    color: "var(--color-text-muted)",
  },
};
