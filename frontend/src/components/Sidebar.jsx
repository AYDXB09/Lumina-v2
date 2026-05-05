/**
 * Sidebar — course list + session history.
 *
 * Props:
 *   courses          — [{ id, canvas_course_id, name }]
 *   selectedCourse   — course object | null
 *   onSelectCourse   — fn(course | null)
 *   onSync           — fn() triggers Canvas re-sync
 *   syncing          — bool
 */

import React from "react";
import { useAuth } from "../contexts/AuthContext.jsx";

export default function Sidebar({
  courses = [],
  selectedCourse,
  onSelectCourse,
  onSync,
  syncing,
}) {
  const { user, logout } = useAuth();

  return (
    <div style={styles.sidebar}>
      {/* Wordmark */}
      <div style={styles.brand}>
        <span style={styles.logo}>✦</span>
        <span style={styles.brandName}>Lumina</span>
      </div>

      {/* User */}
      <div style={styles.userRow}>
        {user?.avatar_url && (
          <img src={user.avatar_url} style={styles.avatar} alt="" />
        )}
        <div style={styles.userInfo}>
          <span style={styles.userName}>{user?.name}</span>
          <span style={styles.userRole}>{user?.role}</span>
        </div>
      </div>

      {/* Courses */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionLabel}>Courses</span>
          <button
            style={{ ...styles.syncBtn, opacity: syncing ? 0.5 : 1 }}
            onClick={onSync}
            disabled={syncing}
            title="Sync from Canvas"
          >
            {syncing ? "⟳" : "↻"}
          </button>
        </div>

        {courses.length === 0 ? (
          <p style={styles.emptyState}>
            No courses yet.{" "}
            <button style={styles.linkBtn} onClick={onSync}>
              Sync from Canvas
            </button>
          </p>
        ) : (
          <ul style={styles.courseList}>
            {/* "All courses" entry */}
            <li
              style={{
                ...styles.courseItem,
                ...(selectedCourse === null ? styles.courseItemActive : {}),
              }}
              onClick={() => onSelectCourse(null)}
            >
              <span style={styles.courseIcon}>◎</span>
              <span style={styles.courseName}>All courses</span>
            </li>

            {courses.map(c => (
              <li
                key={c.id}
                style={{
                  ...styles.courseItem,
                  ...(selectedCourse?.id === c.id ? styles.courseItemActive : {}),
                }}
                onClick={() => onSelectCourse(c)}
              >
                <span style={styles.courseIcon}>○</span>
                <span style={styles.courseName}>{c.name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Bottom — logout */}
      <div style={styles.bottom}>
        <button style={styles.logoutBtn} onClick={logout}>
          Sign out
        </button>
      </div>
    </div>
  );
}

const styles = {
  sidebar: {
    width: "240px",
    flexShrink: 0,
    height: "100vh",
    background: "var(--color-surface)",
    borderRight: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  brand: {
    padding: "20px 16px 12px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  logo: {
    fontSize: "18px",
    color: "var(--color-primary)",
  },
  brandName: {
    fontSize: "16px",
    fontWeight: "700",
    color: "var(--color-text)",
  },
  userRow: {
    padding: "8px 16px 16px",
    display: "flex",
    alignItems: "center",
    gap: "10px",
    borderBottom: "1px solid var(--color-border)",
  },
  avatar: {
    width: "32px",
    height: "32px",
    borderRadius: "50%",
    background: "var(--color-surface-2)",
  },
  userInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "1px",
    overflow: "hidden",
  },
  userName: {
    fontSize: "13px",
    fontWeight: "500",
    color: "var(--color-text)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  userRole: {
    fontSize: "11px",
    color: "var(--color-text-muted)",
    textTransform: "capitalize",
  },
  section: {
    flex: 1,
    overflowY: "auto",
    padding: "12px 0",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0 16px 8px",
  },
  sectionLabel: {
    fontSize: "11px",
    fontWeight: "600",
    color: "var(--color-text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  syncBtn: {
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    fontSize: "16px",
    cursor: "pointer",
    padding: "0 4px",
  },
  emptyState: {
    padding: "8px 16px",
    fontSize: "13px",
    color: "var(--color-text-muted)",
    lineHeight: "1.5",
  },
  linkBtn: {
    background: "none",
    border: "none",
    color: "var(--color-primary)",
    fontSize: "13px",
    cursor: "pointer",
    padding: 0,
    textDecoration: "underline",
  },
  courseList: {
    listStyle: "none",
    padding: "0",
  },
  courseItem: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 16px",
    cursor: "pointer",
    borderRadius: "6px",
    margin: "0 6px",
    transition: "background 0.1s",
    userSelect: "none",
  },
  courseItemActive: {
    background: "var(--color-surface-2)",
    color: "var(--color-primary)",
  },
  courseIcon: {
    fontSize: "10px",
    color: "var(--color-text-muted)",
    flexShrink: 0,
  },
  courseName: {
    fontSize: "13px",
    color: "var(--color-text)",
    overflow: "hidden",
    whiteSpace: "nowrap",
    textOverflow: "ellipsis",
  },
  bottom: {
    padding: "12px 16px",
    borderTop: "1px solid var(--color-border)",
  },
  logoutBtn: {
    width: "100%",
    background: "none",
    border: "1px solid var(--color-border)",
    borderRadius: "8px",
    color: "var(--color-text-muted)",
    padding: "8px",
    fontSize: "13px",
    cursor: "pointer",
  },
};
