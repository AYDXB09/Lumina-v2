/**
 * RightPanel — Assignments & Announcements slide-in panel.
 *
 * Assignment ordering:
 *   1. Future due dates  — nearest first (soonest due at top)
 *   2. No due date       — alphabetical
 *   3. Past due dates    — most recent overdue at top
 *
 * Click an assignment card to expand its full description inline.
 * No links to Canvas — keeps students inside Lumina.
 *
 * Props:
 *   course    — { id, name }
 *   onClose   — fn()
 *   onAskAI   — fn(prompt)   fires a chat message (for Mind Map "Ask AI" button)
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { useIsMobile } from "../hooks/useIsMobile.js";
import { fetchAssignments, fetchAnnouncements, fetchQuizzes, fetchFeedback } from "../api.js";
import MindMapView from "./MindMapView.jsx";
import StudyPlanView from "./StudyPlanView.jsx";
import QuizView from "./QuizView.jsx";

// ---- Helpers ----
function classifyAssignment(due_at) {
  if (!due_at) return { group: 1, label: "No due date", bg: "var(--pill-grey-bg)",   color: "var(--pill-grey-text)"  };
  const diff = new Date(due_at) - Date.now();
  const days = diff / 86400000;
  if (diff < 0)   return { group: 2, label: "Overdue",   bg: "var(--pill-red-bg)",   color: "var(--pill-red-text)"   };
  if (days <= 3)  return { group: 0, label: "Due soon",  bg: "var(--pill-amber-bg)", color: "var(--pill-amber-text)" };
  if (days <= 14) return { group: 0, label: "Upcoming",  bg: "var(--pill-green-bg)", color: "var(--pill-green-text)" };
  return              { group: 0, label: "Scheduled",  bg: "var(--pill-green-bg)", color: "var(--pill-green-text)" };
}

function sortAssignments(list) {
  return [...list].sort((a, b) => {
    const ac = classifyAssignment(a.due_at);
    const bc = classifyAssignment(b.due_at);
    // group 0 = future, group 1 = no date, group 2 = overdue
    if (ac.group !== bc.group) return ac.group - bc.group;
    // Within future: nearest first (asc)
    if (ac.group === 0) return new Date(a.due_at) - new Date(b.due_at);
    // Within overdue: most recent first (desc)
    if (ac.group === 2) return new Date(b.due_at) - new Date(a.due_at);
    // No date: alpha
    return (a.title || "").localeCompare(b.title || "");
  });
}

function fmtDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    weekday: "short", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
  });
}

function daysUntil(iso) {
  if (!iso) return null;
  const diff = new Date(iso) - Date.now();
  const days = Math.ceil(diff / 86400000);
  if (days < 0)  return `${Math.abs(days)}d overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `${days} days left`;
}

// ---- Icons ----
const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const ChevronDown = ({ open }) => (
  <svg
    width="14" height="14" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

// ---- Plain-text → readable HTML ----
// The backend strips all HTML tags; we get plain text with \n for line breaks.
// This function converts that back to readable paragraphs without any XSS risk
// (the source is our own backend — no user HTML ever reaches here).
function formatDescription(text) {
  if (!text) return "";
  // Split into paragraphs on double newline, then handle single newlines within paragraphs
  const paragraphs = text.split(/\n{2,}/);
  return paragraphs
    .map(para => {
      // Within a paragraph: convert single \n to <br>
      const lines = para.split("\n").map(line => {
        const trimmed = line.trim();
        if (!trimmed) return null;
        // Style bullet points
        if (trimmed.startsWith("• ")) {
          return `<span style="display:flex;gap:6px;margin:2px 0"><span style="color:#13234B;font-weight:700;flex-shrink:0">•</span><span>${trimmed.slice(2)}</span></span>`;
        }
        return trimmed;
      }).filter(Boolean);
      if (!lines.length) return null;
      return `<p style="margin:0 0 10px 0;line-height:1.7">${lines.join("<br>")}</p>`;
    })
    .filter(Boolean)
    .join("");
}

// ---- Assignment card ----
function AssignmentCard({ a }) {
  const [open, setOpen] = useState(false);
  const pill = classifyAssignment(a.due_at);
  const countdown = daysUntil(a.due_at);

  return (
    <div
      style={{ ...s.card, ...(open ? s.cardOpen : {}) }}
      onClick={() => setOpen(p => !p)}
    >
      <div style={s.cardHeader}>
        <div style={s.cardTitleRow}>
          <span style={s.cardTitle}>{a.title}</span>
          <ChevronDown open={open} />
        </div>

        {/* Status + date + countdown — all on one line */}
        <div style={s.cardMeta}>
          <span style={{ ...s.pill, background: pill.bg, color: pill.color }}>
            {pill.label}
          </span>
          {a.due_at ? (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>{fmtDateTime(a.due_at)}</span>
              <span style={{ ...s.countdownBadge, color: pill.color, background: pill.bg }}>
                {countdown}
              </span>
            </>
          ) : (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>No due date</span>
            </>
          )}
        </div>
      </div>

      {/* Expanded description */}
      {open && a.description && (
        <div style={s.cardDesc} onClick={e => e.stopPropagation()}>
          <div style={s.descDivider} />
          <div
            style={s.descText}
            dangerouslySetInnerHTML={{ __html: formatDescription(a.description) }}
          />
        </div>
      )}
      {open && !a.description && (
        <div style={s.cardDesc}>
          <div style={s.descDivider} />
          <p style={{ ...s.descText, color: "var(--color-text-faint)", fontStyle: "italic" }}>
            No description indexed yet — sync the course to load assignment details.
          </p>
        </div>
      )}
    </div>
  );
}

// ---- Announcement card ----
function AnnouncementCard({ ann }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ ...s.card, ...(open ? s.cardOpen : {}) }} onClick={() => setOpen(p => !p)}>
      <div style={s.cardHeader}>
        <div style={s.cardTitleRow}>
          <span style={s.cardTitle}>{ann.title}</span>
          <ChevronDown open={open} />
        </div>
        {ann.posted_at && (
          <span style={s.dueDateMain}>{fmtDate(ann.posted_at)}</span>
        )}
      </div>
      {open && ann.content && (
        <div style={s.cardDesc} onClick={e => e.stopPropagation()}>
          <div style={s.descDivider} />
          <div
            style={s.descText}
            dangerouslySetInnerHTML={{ __html: formatDescription(ann.content) }}
          />
        </div>
      )}
    </div>
  );
}

// ---- Quiz card ----
function QuizCard({ q }) {
  const [open, setOpen] = useState(false);
  const pill = classifyAssignment(q.due_at);
  const countdown = daysUntil(q.due_at);

  return (
    <div style={{ ...s.card, ...(open ? s.cardOpen : {}) }} onClick={() => setOpen(p => !p)}>
      <div style={s.cardHeader}>
        <div style={s.cardTitleRow}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flex: 1, minWidth: 0 }}>
            {q.is_exam && (
              <span style={s.examBadge}>EXAM</span>
            )}
            <span style={s.cardTitle}>{q.title}</span>
          </div>
          <ChevronDown open={open} />
        </div>
        <div style={s.cardMeta}>
          {q.quiz_type && (
            <span style={{ ...s.pill, background: "var(--pill-grey-bg)", color: "var(--pill-grey-text)" }}>
              {q.quiz_type.replace("_", " ")}
            </span>
          )}
          {q.due_at ? (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>{fmtDateTime(q.due_at)}</span>
              <span style={{ ...s.countdownBadge, color: pill.color, background: pill.bg }}>{countdown}</span>
            </>
          ) : (
            <span style={s.dueDateMain}>No due date</span>
          )}
          {q.time_limit && (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>⏱ {q.time_limit} min</span>
            </>
          )}
          {q.points && (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>{q.points} pts</span>
            </>
          )}
        </div>
      </div>
      {open && q.description && (
        <div style={s.cardDesc} onClick={e => e.stopPropagation()}>
          <div style={s.descDivider} />
          <div style={s.descText} dangerouslySetInnerHTML={{ __html: formatDescription(q.description) }} />
        </div>
      )}
    </div>
  );
}

// ---- Feedback card ----
function FeedbackCard({ fb }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ ...s.card, ...(open ? s.cardOpen : {}) }} onClick={() => setOpen(p => !p)}>
      <div style={s.cardHeader}>
        <div style={s.cardTitleRow}>
          <span style={s.cardTitle}>Assignment feedback</span>
          <ChevronDown open={open} />
        </div>
        <div style={s.cardMeta}>
          {fb.grade && (
            <span style={{ ...s.pill, background: "var(--pill-green-bg)", color: "var(--pill-green-text)" }}>
              {fb.grade}
            </span>
          )}
          {fb.score != null && (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>{fb.score} pts</span>
            </>
          )}
          {fb.submitted_at && (
            <>
              <span style={s.metaDot}>·</span>
              <span style={s.dueDateMain}>Submitted {fmtDate(fb.submitted_at)}</span>
            </>
          )}
        </div>
      </div>
      {open && fb.feedback_text && (
        <div style={s.cardDesc} onClick={e => e.stopPropagation()}>
          <div style={s.descDivider} />
          <div style={s.descText} dangerouslySetInnerHTML={{ __html: formatDescription(fb.feedback_text) }} />
        </div>
      )}
    </div>
  );
}

// ---- Main component ----
export default function RightPanel({ course, onClose, onAskAI }) {
  const { authFetch } = useAuth();
  const isMobile = useIsMobile();
  const [tab, setTab]                     = useState("assignments");
  const [assignments, setAssignments]     = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [quizzes, setQuizzes]             = useState([]);
  const [feedback, setFeedback]           = useState([]);
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState(null);

  useEffect(() => {
    if (!course?.id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const [asgRes, annRes, quizRes, fbRes] = await Promise.all([
          fetchAssignments(authFetch, course.id),
          fetchAnnouncements(authFetch, course.id),
          fetchQuizzes(authFetch, course.id).catch(() => ({ quizzes: [] })),
          fetchFeedback(authFetch, course.id).catch(() => ({ feedback: [] })),
        ]);
        if (!cancelled) {
          setAssignments(sortAssignments(asgRes.assignments ?? []));
          setAnnouncements(annRes.announcements ?? []);
          setQuizzes(quizRes.quizzes ?? []);
          setFeedback(fbRes.feedback ?? []);
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [course?.id]);

  const mobilePanelStyle = isMobile ? {
    position: "fixed", top: 0, right: 0,
    height: "100vh", zIndex: 140,
    boxShadow: "-4px 0 24px rgba(0,0,0,0.18)",
    width: "min(442px, 100vw)",
  } : {};

  function emptyMsg() {
    if (tab === "assignments")   return "No assignments indexed yet. Use the ↻ sync button in the sidebar.";
    if (tab === "announcements") return "No announcements indexed yet.";
    if (tab === "quizzes")       return "No quizzes or exams indexed yet.";
    if (tab === "feedback")      return "No teacher feedback found yet.";
    return "";
  }

  function currentItems() {
    if (tab === "assignments")   return assignments;
    if (tab === "announcements") return announcements;
    if (tab === "quizzes")       return quizzes;
    if (tab === "feedback")      return feedback;
    return [];
  }

  const TABS = [
    { id: "assignments",   label: "Assignments",  count: assignments.length },
    { id: "announcements", label: "Notices",       count: announcements.length },
    { id: "quizzes",       label: "Quizzes",       count: quizzes.length },
    { id: "feedback",      label: "Feedback",      count: feedback.length },
    // Mind Map tab hidden (2026-08-07) — deemed too complex / not worthwhile. Feature code
    // (MindMapView.jsx, backend/mindmap/routes.py) left intact, just unreachable from the UI.
    { id: "studyplan",     label: "Plan",          count: 0 },
    { id: "practicequiz",  label: "Practice",      count: 0 },
  ];

  return (
    <div style={{ ...s.panel, ...mobilePanelStyle }}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerLeft}>
          <span style={s.headerCourse}>{course?.name ?? "Course"}</span>
          <span style={s.headerSub}>Course Details</span>
        </div>
        <button style={s.closeBtn} onClick={onClose} title="Close"><CloseIcon /></button>
      </div>

      {/* Tabs */}
      <div style={s.tabs}>
        {TABS.map(t => (
          <button
            key={t.id}
            style={{ ...s.tab, ...(tab === t.id ? s.tabActive : {}) }}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.count > 0 && <span style={s.badge}>{t.count}</span>}
          </button>
        ))}
      </div>

      {/* Hint — hidden for mind map / study plan / practice quiz tabs */}
      {tab !== "mindmap" && tab !== "studyplan" && tab !== "practicequiz" && <div style={s.hint}>Tap any card to see full details</div>}

      {/* Body */}
      {tab === "mindmap" ? (
        <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
          <MindMapView course={course} onAskAI={onAskAI} />
        </div>
      ) : tab === "studyplan" ? (
        <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
          <StudyPlanView onAskAI={onAskAI} />
        </div>
      ) : tab === "practicequiz" ? (
        <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
          <QuizView course={course} />
        </div>
      ) : (
        <div style={s.body}>
          {loading && <div style={s.status}>Loading…</div>}
          {error && !loading && (
            <div style={{ ...s.status, color: "var(--color-error)" }}>
              Could not load — sync the course first.
            </div>
          )}

          {!loading && !error && currentItems().length === 0 && (
            <div style={s.status}>{emptyMsg()}</div>
          )}

          {!loading && !error && tab === "assignments" &&
            assignments.map(a => <AssignmentCard key={a.id} a={a} />)}
          {!loading && !error && tab === "announcements" &&
            announcements.map(ann => <AnnouncementCard key={ann.id} ann={ann} />)}
          {!loading && !error && tab === "quizzes" &&
            quizzes.map(q => <QuizCard key={q.id} q={q} />)}
          {!loading && !error && tab === "feedback" &&
            feedback.map((fb, i) => <FeedbackCard key={i} fb={fb} />)}
        </div>
      )}
    </div>
  );
}

// ---- Styles ----
const s = {
  panel: {
    width: "442px",
    flexShrink: 0,
    height: "100%",
    background: "var(--color-surface)",
    borderLeft: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    animation: "slideInRight 0.22s ease",
    overflow: "hidden",
  },
  header: {
    padding: "14px 14px 12px",
    borderBottom: "1px solid var(--color-border)",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    flexShrink: 0,
  },
  headerLeft: {
    minWidth: 0,
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  headerCourse: {
    fontSize: "13px",
    fontWeight: "700",
    color: "var(--color-text)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    display: "block",
  },
  headerSub: {
    fontSize: "11px",
    color: "var(--color-text-faint)",
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    padding: "4px",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    flexShrink: 0,
    marginLeft: "8px",
  },
  tabs: {
    display: "flex",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  tab: {
    flex: 1,
    padding: "9px 8px",
    background: "none",
    border: "none",
    borderBottom: "2px solid transparent",
    fontSize: "12px",
    fontWeight: "500",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "6px",
    transition: "color 0.15s, border-color 0.15s",
  },
  tabActive: {
    color: "var(--color-text)",
    borderBottomColor: "var(--color-primary)",
    fontWeight: "700",
  },
  badge: {
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    borderRadius: "9999px",
    fontSize: "10px",
    fontWeight: "700",
    padding: "1px 6px",
    lineHeight: "1.4",
  },
  hint: {
    padding: "6px 12px",
    fontSize: "10px",
    color: "var(--color-text-faint)",
    textAlign: "center",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
    letterSpacing: "0.02em",
  },
  body: {
    flex: 1,
    overflowY: "auto",
    padding: "10px",
  },
  status: {
    padding: "28px 8px",
    textAlign: "center",
    color: "var(--color-text-muted)",
    fontSize: "13px",
    lineHeight: "1.6",
  },
  card: {
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "10px",
    marginBottom: "8px",
    cursor: "pointer",
    transition: "border-color 0.15s, box-shadow 0.15s",
    overflow: "hidden",
  },
  cardOpen: {
    borderColor: "var(--color-primary)",
    boxShadow: "0 0 0 2px var(--color-primary-glow)",
  },
  cardHeader: {
    padding: "10px 12px",
  },
  cardTitleRow: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "8px",
    marginBottom: "6px",
  },
  cardTitle: {
    fontSize: "13px",
    fontWeight: "600",
    color: "var(--color-text)",
    lineHeight: "1.4",
    flex: 1,
    minWidth: 0,
  },
  cardMeta: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: "6px",
    flexWrap: "wrap",
    marginTop: "4px",
  },
  metaDot: {
    color: "var(--color-text-faint)",
    fontSize: "13px",
    lineHeight: 1,
    flexShrink: 0,
  },
  pill: {
    display: "inline-flex",
    alignItems: "center",
    padding: "2px 9px",
    borderRadius: "9999px",
    fontSize: "12px",
    fontWeight: "700",
    letterSpacing: "0.02em",
    alignSelf: "flex-start",
    flexShrink: 0,
  },
  dueDateMain: {
    fontSize: "12px",
    color: "var(--color-text-muted)",
    fontWeight: "500",
  },
  countdownBadge: {
    fontSize: "11px",
    fontWeight: "600",
    padding: "2px 8px",
    borderRadius: "9999px",
    flexShrink: 0,
  },
  cardDesc: {
    padding: "0 12px 12px",
  },
  descDivider: {
    height: "1px",
    background: "var(--color-border)",
    marginBottom: "10px",
  },
  descText: {
    fontSize: "var(--panel-font-size, 14px)",
    color: "var(--color-text-muted)",
    lineHeight: "1.7",
    whiteSpace: "pre-wrap",
  },
  examBadge: {
    display: "inline-block",
    background: "var(--pill-red-bg)",
    color: "var(--pill-red-text)",
    fontSize: "9px",
    fontWeight: "800",
    letterSpacing: "0.06em",
    padding: "2px 6px",
    borderRadius: "4px",
    flexShrink: 0,
    textTransform: "uppercase",
  },
};
