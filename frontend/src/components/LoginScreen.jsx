/**
 * LoginScreen — Canvas API Key authentication.
 *
 * Student enters:
 *   1. Their Canvas URL  (defaults to Dwight's)
 *   2. Their Canvas API key (generated in Canvas → Account → Settings → New Access Token)
 */

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import LuminaLogo from "./LuminaLogo.jsx";

const DEFAULT_CANVAS_URL = import.meta.env.VITE_CANVAS_URL ?? "https://dwight.instructure.com";

export default function LoginScreen() {
  const { loginWithApiKey } = useAuth();
  const [canvasUrl, setCanvasUrl] = useState(DEFAULT_CANVAS_URL);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginWithApiKey(canvasUrl.trim(), apiKey.trim());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {/* Logo / wordmark */}
        <div style={styles.header}>
          <div style={styles.logoWrap}><LuminaLogo size={52} /></div>
          <h1 style={styles.title}>Lumina</h1>
          <p style={styles.subtitle}>Your AI study companion for Canvas</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
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
              autoComplete="current-password"
            />
            <span style={styles.hint}>
              Canvas → Account → Settings → New Access Token
            </span>
          </label>

          {error && <p style={styles.error}>{error}</p>}

          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? "Signing in…" : "Sign in with Canvas"}
          </button>
        </form>

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
  footer: {
    marginTop: "24px",
    textAlign: "center",
    fontSize: "12px",
    color: "var(--color-text-muted)",
  },
};
