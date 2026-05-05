/**
 * App.jsx — Root component.
 *
 * Auth gate:
 *   - Loading   → spinner (restoring session from cookie)
 *   - No user   → LoginScreen
 *   - User      → main app (Dashboard placeholder for now)
 */

import React from "react";
import { useAuth } from "./contexts/AuthContext.jsx";
import LoginScreen from "./components/LoginScreen.jsx";

function LoadingSpinner() {
  return (
    <div style={{
      height: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--color-text-muted)",
      fontSize: "14px",
    }}>
      Loading…
    </div>
  );
}

function Dashboard() {
  const { user, logout } = useAuth();
  return (
    <div style={{ padding: "40px", maxWidth: "800px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", marginBottom: "4px" }}>
            ✦ Lumina
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "14px" }}>
            Welcome, {user?.name}
          </p>
        </div>
        <button
          onClick={logout}
          style={{
            background: "transparent",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            color: "var(--color-text-muted)",
            padding: "8px 16px",
            fontSize: "13px",
          }}
        >
          Sign out
        </button>
      </div>

      <div style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius)",
        padding: "32px",
        textAlign: "center",
        color: "var(--color-text-muted)",
      }}>
        <p style={{ fontSize: "18px", marginBottom: "8px" }}>🚧 Dashboard coming soon</p>
        <p style={{ fontSize: "14px" }}>
          Auth is wired up. Next: Canvas course sync + AI chat.
        </p>
        <pre style={{
          marginTop: "24px",
          textAlign: "left",
          background: "var(--color-surface-2)",
          borderRadius: "8px",
          padding: "16px",
          fontSize: "12px",
          overflow: "auto",
        }}>
          {JSON.stringify(user, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (!user) return <LoginScreen />;
  return <Dashboard />;
}
