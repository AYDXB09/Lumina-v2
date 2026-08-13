/**
 * ResetPasswordScreen — lands here from the password-reset email link
 * (?token_hash=...&type=recovery). Rendered by App.jsx outside the normal
 * auth gate, since the user isn't signed in yet at this point.
 */

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import LuminaLogo from "./LuminaLogo.jsx";

export default function ResetPasswordScreen({ tokenHash, linkError }) {
  const { resetPassword } = useAuth();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(
    linkError || (!tokenHash ? "This reset link is missing its token — request a new one from Settings." : null)
  );
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!tokenHash) return; // link itself is bad -- nothing to submit against
    setError(null);
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(tokenHash, password);
      setDone(true);
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
          <h1 style={styles.title}>Reset your password</h1>
        </div>

        {done ? (
          <>
            <p style={styles.notice}>Your password has been updated.</p>
            <a href="/" style={styles.button}>Go to sign in</a>
          </>
        ) : (
          <form onSubmit={handleSubmit} style={styles.form}>
            <label style={styles.label}>
              New password
              <input
                style={styles.input}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </label>
            <label style={styles.label}>
              Confirm new password
              <input
                style={styles.input}
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </label>

            {error && <p style={styles.error}>{error}</p>}

            <button type="submit" style={styles.button} disabled={loading || !tokenHash}>
              {loading ? "Updating…" : "Update password"}
            </button>
          </form>
        )}
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
  header: { textAlign: "center", marginBottom: "28px" },
  logoWrap: { display: "flex", justifyContent: "center", marginBottom: "14px" },
  title: { fontSize: "20px", fontWeight: "700", color: "var(--color-text)", margin: 0 },
  form: { display: "flex", flexDirection: "column", gap: "20px" },
  label: {
    display: "flex", flexDirection: "column", gap: "6px",
    fontSize: "13px", fontWeight: "500", color: "var(--color-text-muted)",
    textTransform: "uppercase", letterSpacing: "0.05em",
  },
  input: {
    background: "var(--color-surface-2)", border: "1px solid var(--color-border)",
    borderRadius: "8px", padding: "10px 14px", color: "var(--color-text)",
    fontSize: "14px", outline: "none", boxSizing: "border-box", width: "100%",
  },
  button: {
    background: "var(--color-primary)", color: "var(--color-primary-text)",
    border: "none", borderRadius: "9999px", padding: "12px", fontSize: "15px",
    fontWeight: "600", cursor: "pointer", textAlign: "center", textDecoration: "none",
    display: "block",
  },
  error: {
    color: "var(--color-error)", fontSize: "14px", background: "rgba(248,113,113,0.1)",
    border: "1px solid rgba(248,113,113,0.25)", borderRadius: "8px", padding: "10px 14px",
  },
  notice: {
    color: "var(--color-text)", fontSize: "14px", marginBottom: "20px",
  },
};
