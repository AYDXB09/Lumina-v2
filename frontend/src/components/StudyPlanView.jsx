/**
 * StudyPlanView — cross-course study plan (not scoped to a single course).
 *
 * Shows a day-by-day schedule generated from upcoming assignments/exams
 * across ALL enrolled courses, plus calendar events. Each task carries a
 * plain-language "reason" so the student can see why it was prioritized
 * and push back if it's wrong — the schedule placement itself is
 * deterministic (backend), only the task text/reasoning comes from the AI.
 *
 * Props:
 *   onAskAI — fn(prompt)  fires a chat message when a task's "Ask AI" is clicked
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { fetchStudyPlan, regenerateStudyPlan } from "../api.js";

function fmtDayHeading(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.round((d - today) / 86400000);
  const weekday = d.toLocaleDateString("en-US", { weekday: "long" });
  const dateLabel = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  if (diffDays === 0) return `Today · ${dateLabel}`;
  if (diffDays === 1) return `Tomorrow · ${dateLabel}`;
  return `${weekday} · ${dateLabel}`;
}

export default function StudyPlanView({ onAskAI }) {
  const { authFetch } = useAuth();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchStudyPlan(authFetch);
        if (!cancelled) setPlan(res.plan_data);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  async function handleRegenerate() {
    setRegenerating(true);
    setError(null);
    try {
      const res = await regenerateStudyPlan(authFetch);
      setPlan(res.plan_data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRegenerating(false);
    }
  }

  if (loading) {
    return (
      <div style={sp.centered}>
        <p style={{ color: "var(--color-text-faint)", fontSize: "13px" }}>Building your study plan…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={sp.centered}>
        <p style={{ color: "var(--pill-red-text)", fontSize: "13px" }}>{error}</p>
        <button style={sp.regenBtn} onClick={handleRegenerate} disabled={regenerating}>
          {regenerating ? "Retrying…" : "Try again"}
        </button>
      </div>
    );
  }

  const days = plan?.days ?? [];

  return (
    <div style={sp.wrap}>
      <div style={sp.header}>
        <p style={sp.summary}>{plan?.summary}</p>
        <button style={sp.regenBtn} onClick={handleRegenerate} disabled={regenerating} title="Regenerate">
          {regenerating ? "Regenerating…" : "↻ Regenerate"}
        </button>
      </div>

      {days.length === 0 && (
        <p style={{ color: "var(--color-text-muted)", fontSize: "13px", padding: "16px" }}>
          Nothing due in the next 30 days — nothing to plan yet.
        </p>
      )}

      <div style={sp.days}>
        {days.map(day => (
          <div key={day.date} style={sp.dayCard}>
            <div style={sp.dayHeading}>{fmtDayHeading(day.date)}</div>
            {(day.tasks || []).map((task, i) => (
              <div key={i} style={sp.task}>
                <div style={sp.taskTop}>
                  <span style={sp.taskCourse}>{task.course}</span>
                  {task.duration_min != null && (
                    <span style={sp.taskDuration}>{task.duration_min} min</span>
                  )}
                </div>
                <div style={sp.taskTitle}>{task.title}</div>
                {task.reason && <div style={sp.taskReason}>{task.reason}</div>}
                {onAskAI && (
                  <button
                    style={sp.askBtn}
                    onClick={() => onAskAI(`Help me with: ${task.title} (${task.course})`)}
                  >
                    Ask AI about this
                  </button>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

const sp = {
  wrap: {
    display: "flex", flexDirection: "column", height: "100%", overflowY: "auto",
  },
  centered: {
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    height: "100%", gap: "10px", padding: "24px",
  },
  header: {
    padding: "14px 16px", borderBottom: "1px solid var(--color-border)",
    display: "flex", flexDirection: "column", gap: "10px",
  },
  summary: {
    fontSize: "13px", color: "var(--color-text-muted)", lineHeight: 1.5, margin: 0,
  },
  regenBtn: {
    alignSelf: "flex-start", fontSize: "12px", padding: "6px 12px", borderRadius: "8px",
    background: "var(--color-surface)", border: "1px solid var(--color-border)",
    color: "var(--color-text-muted)", cursor: "pointer",
  },
  days: {
    display: "flex", flexDirection: "column", gap: "12px", padding: "12px 16px",
  },
  dayCard: {
    display: "flex", flexDirection: "column", gap: "8px",
  },
  dayHeading: {
    fontSize: "12px", fontWeight: 600, color: "var(--color-text)",
    textTransform: "uppercase", letterSpacing: "0.02em",
  },
  task: {
    background: "var(--color-surface)", border: "1px solid var(--color-border)",
    borderRadius: "10px", padding: "10px 12px", display: "flex", flexDirection: "column", gap: "4px",
  },
  taskTop: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  taskCourse: {
    fontSize: "11px", fontWeight: 600, color: "var(--color-primary)",
    textTransform: "uppercase", letterSpacing: "0.02em",
  },
  taskDuration: {
    fontSize: "11px", color: "var(--color-text-faint)",
  },
  taskTitle: {
    fontSize: "13px", color: "var(--color-text)", lineHeight: 1.4,
  },
  taskReason: {
    fontSize: "12px", color: "var(--color-text-faint)", fontStyle: "italic",
  },
  askBtn: {
    alignSelf: "flex-start", marginTop: "2px", fontSize: "11px", padding: "4px 10px",
    borderRadius: "6px", background: "var(--color-surface-2)", border: "1px solid var(--color-border)",
    color: "var(--color-text-muted)", cursor: "pointer",
  },
};
