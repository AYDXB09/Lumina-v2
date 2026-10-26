/**
 * Sidebar — left navigation panel.
 *
 * Course categorisation strategy:
 *   REVERSE detection — if a course name contains academic subject keywords it is
 *   classified as "core". Everything else (counseling, game night, internship,
 *   resource centre, clubs, projects…) falls into "extra-curricular".
 *   This is more reliable than trying to list all possible extracurricular names.
 *
 * Canvas note: Canvas has no native "extracurricular" flag. The most reliable
 * Canvas-native identifier would be the sub-account (account_id in canvas_data).
 * If Dwight organises activities under a separate sub-account we can add a
 * backend filter — tracked as a future improvement.
 *
 * Props:
 *   open             — bool
 *   courses          — [{ id, canvas_course_id, name }]
 *   selectedCourse   — course object | null
 *   onSelectCourse   — fn(course | null)
 *   onSync           — fn()
 *   syncing          — bool
 *   onToggle         — fn()
 *   onOpenSettings   — fn()
 */

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { useSettings } from "../contexts/SettingsContext.jsx";
import { useIsMobile } from "../hooks/useIsMobile.js";
import LuminaLogo from "./LuminaLogo.jsx";

// ---------- Course categorisation ----------
//
// Strategy: EXPLICIT extracurricular keywords — if a course name matches any
// of these, it's an extra-curricular. Everything else is a core subject.
//
// Why not reverse detection (academic keywords → core)?
// Lower school course names like "General Science", "European History",
// "Design", "Art" would not match academic keywords and get misclassified.
// An explicit blocklist is safer: it catches known activity types while
// leaving all ambiguous/academic names as core subjects.
//
// Canvas API note: Canvas has no native "extracurricular" field. The most
// reliable long-term approach is filtering by Canvas sub-account (account_id
// in canvas_data) if Dwight organises activities under a separate sub-account.
// That's tracked as a future improvement. For school-specific opaque names
// (e.g. "The Color Cloud"), the Settings → "Show extra-curricular courses"
// toggle combined with user expectation is the practical solution.
//
const EXTRA_KEYWORDS = [
  // Admin / counseling / support
  "advisory", "homeroom", "orientation",
  "counseling", "college counseling", "academic advising",
  "resource center", "learning resource", "lrc",
  "study skills", "study hall", "tutorial", "extra help",
  // Programs / experiences
  "internship", "shadowing", "shadow", "mentorship", "mentor",
  "service learning", "community service", "volunteer",
  "exchange program", "field trip",
  // Clubs & extracurricular activities
  "club", "clubs", "activity", "activities",
  "student council", "student government", "student life",
  "leadership", "yearbook", "newspaper", "journalism",
  "debate", "model un", "model united nations",
  "robotics club", "coding club", "stem club",
  // Sports & wellness
  "sport", "sports", "athletics", "physical ed",
  "wellness", "mindfulness", "yoga", "meditation",
  "soccer", "basketball", "tennis", "swimming", "volleyball",
  "football", "baseball", "softball", "lacrosse", "rowing",
  // Events / programs (school-specific patterns)
  "game night", "game day",
  "enrichment", "elective support",
  // Dwight-specific
  "spark", "color cloud",
];

function isExtracurricular(course) {
  const lower = (course.name || "").toLowerCase();
  const keywordMatch = EXTRA_KEYWORDS.some(kw => lower.includes(kw));
  if (keywordMatch) return true;

  // Secondary signal: Canvas meeting frequency (stored after sync)
  // If weekly_meeting_frequency < 1 AND the course has no regular schedule
  // it is a strong hint of an extra-curricular.
  // NOTE: for online schools that use Zoom (not Canvas calendar), frequency
  // may be 0 for legitimate core subjects. Only apply this when frequency
  // is explicitly populated AND > 0 for at least one course in the school,
  // confirming that teachers ARE using Canvas calendar events.
  const freq = course.canvas_data?.weekly_meeting_frequency;
  if (typeof freq === "number" && freq > 0 && freq < 0.5) {
    // < 0.5 meetings/week = less than once every 2 weeks = sporadic
    return true;
  }

  return false;
}

function categorizeCourses(courses) {
  const core  = [];
  const extra = [];
  for (const c of courses) {
    if (isExtracurricular(c)) extra.push(c);
    else core.push(c);
  }
  return { core, extra };
}

// ---------- SVG icons ----------
const GearIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
  </svg>
);

const HelpIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const SyncIcon = ({ spinning }) => (
  <svg
    width="14" height="14" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2.5"
    strokeLinecap="round" strokeLinejoin="round"
    style={{ animation: spinning ? "spin 1s linear infinite" : "none" }}
  >
    <polyline points="23 4 23 10 17 10" />
    <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
  </svg>
);

const ChevronIcon = ({ open }) => (
  <svg
    width="11" height="11" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2.5"
    strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s ease" }}
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

// ---------- Course list item ----------
function CourseItem({ course, active, onSelect }) {
  return (
    <li
      style={{ ...s.item, ...(active ? s.itemActive : {}) }}
      onClick={() => onSelect(course)}
    >
      <span style={{ ...s.dot, ...(active ? s.dotActive : {}) }}>○</span>
      <span style={{ ...s.itemName, ...(active ? s.itemNameActive : {}) }}>
        {course.name}
      </span>
    </li>
  );
}

// ---------- Main component ----------
export default function Sidebar({
  open = true,
  courses = [],
  selectedCourse,
  onSelectCourse,
  onSync,
  syncing,
  onToggle,
  onOpenSettings,
}) {
  const { user, logout } = useAuth();
  const { settings } = useSettings();
  const isMobile = useIsMobile();
  const [extrasOpen, setExtrasOpen] = useState(false);

  const { core, extra } = categorizeCourses(courses);
  const extrasVisible = settings.showExtracurriculars || extrasOpen;

  // On mobile the sidebar floats over content
  const mobileOverlayStyle = isMobile ? {
    position: "fixed",
    top: 0,
    left: 0,
    zIndex: 150,
    boxShadow: "4px 0 24px rgba(0,0,0,0.18)",
  } : {};

  return (
    <>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

      <aside
        style={{
          ...s.sidebar,
          ...mobileOverlayStyle,
          width: open ? "260px" : "0px",
          minWidth: open ? "260px" : "0px",
          transform: open ? "translateX(0)" : "translateX(-260px)",
        }}
      >
        {/* ---- HEADER ---- */}
        <div style={s.header}>
          <div style={s.logoRow}>
            <LuminaLogo size={28} />
            <span style={s.brandName}>Lumina</span>
          </div>
        </div>

        {/* ---- USER ROW ---- */}
        {user && (
          <div style={s.userRow}>
            {user.avatar_url
              ? <img src={user.avatar_url} style={s.avatar} alt="" />
              : <div style={s.avatarFallback}>{(user.name || "?")[0].toUpperCase()}</div>
            }
            <div style={s.userInfo}>
              <span style={s.userName}>{user.name}</span>
              <span style={s.userRole}>Student</span>
            </div>
          </div>
        )}

        {/* ---- COURSES (scrollable, fills all remaining space) ---- */}
        <div style={s.section}>
          <div style={s.sectionHeader}>
            <span style={s.sectionLabel}>Courses</span>
            <button
              style={{ ...s.syncBtn, opacity: syncing ? 0.5 : 1 }}
              onClick={onSync}
              disabled={syncing}
              title={syncing ? "Syncing…" : "Sync from Canvas"}
            >
              <SyncIcon spinning={syncing} />
            </button>
          </div>

          {courses.length === 0 ? (
            <div style={s.empty}>
              No courses yet.{" "}
              <button style={s.linkBtn} onClick={onSync}>Sync now</button>
            </div>
          ) : (
            <ul style={s.list}>
              {/* Core academic courses */}
              {core.map(c => (
                <CourseItem
                  key={c.id}
                  course={c}
                  active={selectedCourse?.id === c.id}
                  onSelect={onSelectCourse}
                />
              ))}

              {/* Extra-curricular collapsible section */}
              {extra.length > 0 && (
                <>
                  <li
                    style={s.extraHeader}
                    onClick={() => setExtrasOpen(p => !p)}
                  >
                    <span style={s.extraLabel}>Extra-curricular</span>
                    <span style={s.extraCount}>{extra.length}</span>
                    <ChevronIcon open={extrasVisible} />
                  </li>

                  {extrasVisible && extra.map(c => (
                    <CourseItem
                      key={c.id}
                      course={c}
                      active={selectedCourse?.id === c.id}
                      onSelect={onSelectCourse}
                    />
                  ))}
                </>
              )}
            </ul>
          )}
        </div>

        {/* ---- FOOTER ---- */}
        <div style={s.footer}>
          <button style={s.footerBtn} onClick={onOpenSettings} title="Settings">
            <GearIcon />
            <span>Settings</span>
          </button>
          <button style={s.footerBtn} title="Help (coming soon)">
            <HelpIcon />
            <span>Help</span>
          </button>
          <button style={{ ...s.footerBtn, ...s.logoutBtn }} onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}

// ---------- Styles ----------
const s = {
  sidebar: {
    height: "100vh",
    background: "var(--color-surface)",
    borderRight: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
    overflow: "hidden",
    transition: "width 220ms cubic-bezier(0.4,0,0.2,1), min-width 220ms cubic-bezier(0.4,0,0.2,1), transform 220ms cubic-bezier(0.4,0,0.2,1)",
  },
  header: {
    padding: "18px 16px 14px",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  logoRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  brandName: {
    fontSize: "17px",
    fontWeight: "700",
    color: "var(--color-text)",
    letterSpacing: "-0.3px",
  },
  userRow: {
    padding: "12px 16px",
    display: "flex",
    alignItems: "center",
    gap: "10px",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  avatar: {
    width: "30px",
    height: "30px",
    borderRadius: "50%",
    objectFit: "cover",
    flexShrink: 0,
  },
  avatarFallback: {
    width: "30px",
    height: "30px",
    borderRadius: "50%",
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "13px",
    fontWeight: "600",
    flexShrink: 0,
  },
  userInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "1px",
    overflow: "hidden",
    minWidth: 0,
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
  },

  // Courses section — flex:1 fills all space between user row and footer, no spacer needed
  section: {
    flex: 1,
    overflowY: "auto",
    padding: "10px 0",
    minHeight: 0,
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0 16px 6px",
  },
  sectionLabel: {
    fontSize: "10px",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    color: "var(--color-text-faint)",
  },
  syncBtn: {
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    padding: "4px",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background var(--transition)",
  },
  empty: {
    padding: "8px 16px",
    fontSize: "13px",
    color: "var(--color-text-muted)",
    lineHeight: 1.6,
  },
  linkBtn: {
    background: "none",
    border: "none",
    color: "var(--color-primary-hover)",
    fontSize: "13px",
    cursor: "pointer",
    padding: 0,
    textDecoration: "underline",
  },
  list: {
    listStyle: "none",
    padding: "0 6px",
    margin: 0,
  },
  item: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "7px 10px",
    cursor: "pointer",
    borderRadius: "9999px",
    margin: "1px 0",
    transition: "background var(--transition)",
    userSelect: "none",
  },
  itemActive: {
    background: "var(--color-primary)",
    boxShadow: "0 2px 8px var(--color-primary-glow)",
  },
  dot: {
    fontSize: "9px",
    color: "var(--color-text-faint)",
    flexShrink: 0,
    lineHeight: 1,
  },
  dotActive: {
    color: "var(--color-primary-text)",
    opacity: 0.75,
  },
  itemName: {
    fontSize: "13px",
    color: "var(--color-text)",
    overflow: "hidden",
    whiteSpace: "nowrap",
    textOverflow: "ellipsis",
    lineHeight: 1.3,
  },
  itemNameActive: {
    color: "var(--color-primary-text)",
    fontWeight: "600",
  },

  // Extra-curricular section header row
  extraHeader: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "10px 10px 5px 10px",
    cursor: "pointer",
    userSelect: "none",
    listStyle: "none",
    marginTop: "6px",
    borderTop: "1px solid var(--color-border)",
  },
  extraLabel: {
    fontSize: "10px",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--color-text-faint)",
    flex: 1,
  },
  extraCount: {
    fontSize: "10px",
    fontWeight: "600",
    color: "var(--color-text-faint)",
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px",
    padding: "0px 6px",
    lineHeight: "16px",
  },

  footer: {
    padding: "10px 8px 16px",
    borderTop: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    flexShrink: 0,
  },
  footerBtn: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "9px 12px",
    background: "none",
    border: "none",
    borderRadius: "9999px",
    color: "var(--color-text-muted)",
    fontSize: "13px",
    fontWeight: "500",
    cursor: "pointer",
    transition: "background var(--transition), color var(--transition)",
    textAlign: "left",
    width: "100%",
  },
  logoutBtn: {
    marginTop: "4px",
    color: "var(--color-text-faint)",
    fontSize: "12px",
    paddingLeft: "12px",
  },
};
