/**
 * SettingsModal — left-tab layout with three sections:
 *   General   — AI Behaviour + Appearance
 *   Calendar  — Canvas auto-calendar + personal calendar URLs + sync settings
 *   Account   — User info, sign out, about
 */

import React, { useState, useEffect } from "react";
import { useSettings } from "../contexts/SettingsContext.jsx";
import { useAuth } from "../contexts/AuthContext.jsx";

const BASE = import.meta.env.VITE_API_BASE ?? "";

const CloseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);
const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
  </svg>
);
const CalendarIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);
const CheckIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const InfoIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);

// ---- Tooltip ----
function Tooltip({ label, children }) {
  const [show, setShow] = React.useState(false);
  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center" }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <span style={s.tooltipTrigger}><InfoIcon /></span>
      {show && (
        <span style={s.tooltipBox}>
          {children}
        </span>
      )}
    </span>
  );
}

// ---- Reusable sub-components ----
function Section({ title, children }) {
  return (
    <div style={s.section}>
      <h3 style={s.sectionTitle}>{title}</h3>
      {children}
    </div>
  );
}

function Row({ label, hint, children }) {
  return (
    <div style={s.row}>
      <div style={s.rowLabel}>
        <span style={{ ...s.rowLabelText, display: "flex", alignItems: "center", gap: "2px" }}>{label}</span>
        {hint && <span style={s.rowHint}>{hint}</span>}
      </div>
      <div style={s.rowControl}>{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{ ...s.toggle, background: checked ? "var(--color-primary)" : "var(--color-border)" }}
    >
      <span style={{
        ...s.toggleThumb,
        transform: checked ? "translateX(20px)" : "translateX(2px)",
        background: checked ? "var(--color-primary-text)" : "#ffffff",
      }} />
    </button>
  );
}

function SegmentedControl({ options, value, onChange }) {
  return (
    <div style={s.segmented}>
      {options.map(opt => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{ ...s.segBtn, ...(value === opt.value ? s.segBtnActive : {}) }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function ThemeBtn({ active, color, label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        ...s.themeBtn,
        border: active ? `2px solid ${color}` : "2px solid var(--color-border)",
        boxShadow: active ? `0 0 0 3px ${color}33` : "none",
      }}
    >
      <span style={{ ...s.themeSwatch, background: color }} />
      <span style={{ ...s.themeBtnLabel, fontWeight: active ? "700" : "500" }}>{label}</span>
    </button>
  );
}

// ---- Calendar Tab ----
function CalendarTab({ settings, update, authFetch }) {
  const [sources, setSources]         = useState([]);
  const [newLabel, setNewLabel]       = useState("");
  const [newUrl, setNewUrl]           = useState("");
  const [adding, setAdding]           = useState(false);
  const [syncing, setSyncing]         = useState(false);
  const [syncResult, setSyncResult]   = useState(null); // { total_events, errors }
  const [addResult, setAddResult]     = useState(null); // { events_loaded, fetch_error }
  const [error, setError]             = useState("");
  const [showForm, setShowForm]       = useState(false);

  // Load sources on mount
  useEffect(() => {
    authFetch(`${BASE}/api/calendar/sources`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setSources(d.sources || []); })
      .catch(() => {});
  }, []);

  const canvasSource = sources.find(s => s.id === "canvas");
  const personalSources = sources.filter(s => !s.auto);

  async function handleAdd() {
    if (!newUrl.trim()) return;
    setAdding(true);
    setError("");
    try {
      const res = await authFetch(`${BASE}/api/calendar/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: newLabel || "My Calendar", url: newUrl.trim() }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.detail || "Failed to add calendar");
      } else {
        const d = await res.json();
        setSources(d.sources || []);
        setAddResult({ events_loaded: d.events_loaded, fetch_error: d.fetch_error });
        setNewLabel("");
        setNewUrl("");
        setShowForm(false);
      }
    } catch {
      setError("Network error");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(sourceId) {
    try {
      const res = await authFetch(`${BASE}/api/calendar/sources/${sourceId}`, { method: "DELETE" });
      if (res.ok) {
        const d = await res.json();
        setSources(d.sources || []);
      }
    } catch {}
  }

  async function handleSync() {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await authFetch(
        `${BASE}/api/calendar/sync?fetch_window=${settings.calendarFetchWindow}`,
        { method: "POST" }
      );
      if (res.ok) {
        const d = await res.json();
        setSyncResult(d);
      }
    } catch {}
    setSyncing(false);
  }

  return (
    <div>
      {/* Canvas calendar */}
      <Section title="Canvas Calendar">
        <div style={s.calSourceCard}>
          <div style={s.calSourceIcon}><CalendarIcon /></div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={s.calSourceName}>Canvas Calendar</div>
            <div style={s.calSourceUrl}>
              {canvasSource
                ? <span style={s.connectedBadge}><CheckIcon /> Auto-connected</span>
                : <span style={s.notConnectedBadge}>Not yet connected — sync your courses first</span>
              }
            </div>
          </div>
        </div>
        <p style={s.calHint}>
          Connected automatically when you sync courses. Includes all assignment due dates and Canvas events.
        </p>
      </Section>

      {/* Personal calendars */}
      <Section title="Personal Calendars">
        <p style={s.calHint}>
          Add your calendar .ics feed so Lumina can factor in your schedule when planning study time.{" "}
          <Tooltip>
            <strong style={{ display: "block", marginBottom: "6px" }}>How to get your .ics URL:</strong>
            <span style={{ display: "block", marginBottom: "4px" }}>
              <strong>Google</strong> — Open calendar → ⋮ → Settings → "Secret address in iCal format"
            </span>
            <span style={{ display: "block", marginBottom: "4px" }}>
              <strong>Apple</strong> — Calendar app → right-click calendar → Share → Copy Link (enable Public Calendar)
            </span>
            <span style={{ display: "block", marginBottom: "4px" }}>
              <strong>Outlook</strong> — Settings → Calendar → Shared calendars → Publish → ICS link
            </span>
            <span style={{ display: "block" }}>
              <strong>Canvas</strong> — Account → Settings → Calendar Feed
            </span>
          </Tooltip>
        </p>

        {/* Existing personal calendars — 2×2 compact grid */}
        {personalSources.length > 0 && (
          <div style={s.calGrid}>
            {personalSources.map(src => (
              <div key={src.id} style={s.calGridCard}>
                <div style={s.calGridIcon}><CalendarIcon /></div>
                <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
                  <div style={s.calGridName}>{src.label}</div>
                  <div style={s.calSourceConnected}><CheckIcon /> Connected</div>
                </div>
                <button style={s.removeBtn} onClick={() => handleRemove(src.id)} title="Remove">
                  <TrashIcon />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add result feedback */}
        {addResult && !showForm && (
          addResult.fetch_error
            ? <div style={{ ...s.errorText, marginBottom: "8px" }}>
                ⚠ Calendar added but could not load events: {addResult.fetch_error}
              </div>
            : <div style={{ fontSize: "12px", color: "var(--pill-green-text)", marginBottom: "8px" }}>
                ✓ Calendar connected — {addResult.events_loaded} events loaded
              </div>
        )}

        {/* Add form */}
        {showForm ? (
          <div style={s.addForm}>
            <input
              style={s.input}
              placeholder="Label (e.g. Google Calendar)"
              value={newLabel}
              onChange={e => setNewLabel(e.target.value)}
            />
            <input
              style={s.input}
              placeholder="Paste .ics URL here"
              value={newUrl}
              onChange={e => setNewUrl(e.target.value)}
            />
            {error && <div style={s.errorText}>{error}</div>}
            <div style={{ display: "flex", gap: "8px" }}>
              <button style={s.primaryBtn} onClick={handleAdd} disabled={adding || !newUrl.trim()}>
                {adding ? "Adding…" : "Add Calendar"}
              </button>
              <button style={s.ghostBtn} onClick={() => { setShowForm(false); setError(""); }}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button style={s.ghostBtn} onClick={() => setShowForm(true)}>
            + Add Calendar
          </button>
        )}
      </Section>

      {/* Sync settings */}
      <Section title="Sync Settings">
        <Row
          label={<>Fetch window <Tooltip>How far ahead Lumina looks when retrieving calendar events for study planning. Wider windows give the AI more context for long-range study plans.</Tooltip></>}
        >
          <SegmentedControl
            value={settings.calendarFetchWindow}
            onChange={v => update({ calendarFetchWindow: v })}
            options={[
              { value: "1day",    label: "1 day" },
              { value: "1week",   label: "1 wk" },
              { value: "2weeks",  label: "2 wks" },
              { value: "1month",  label: "1 mo" },
              { value: "3months", label: "3 mo" },
              { value: "1year",   label: "1 yr" },
            ]}
          />
        </Row>
        <Row
          label={<>Sync frequency <Tooltip>"On query" is recommended — calendar is only fetched when you ask a scheduling question, keeping things fast. "Login" fetches once per session.</Tooltip></>}
        >
          <SegmentedControl
            value={settings.calendarSyncFrequency}
            onChange={v => update({ calendarSyncFrequency: v })}
            options={[
              { value: "query",   label: "On query" },
              { value: "login",   label: "Login" },
              { value: "daily",   label: "Daily" },
              { value: "weekly",  label: "Weekly" },
              { value: "monthly", label: "Monthly" },
            ]}
          />
        </Row>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "4px" }}>
          <button style={s.primaryBtn} onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing…" : "Sync Now"}
          </button>
          {syncResult && (
            syncResult.errors?.length > 0
              ? <span style={{ fontSize: "12px", color: "var(--pill-amber-text)" }}>
                  {syncResult.total_events} events · {syncResult.errors.length} error(s): {syncResult.errors.map(e => e.source).join(", ")}
                </span>
              : <span style={{ fontSize: "12px", color: "var(--pill-green-text)" }}>
                  ✓ {syncResult.total_events} events loaded
                </span>
          )}
        </div>
      </Section>
    </div>
  );
}

// ---- Upload icon ----
const UploadIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
    <path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/>
  </svg>
);
const FileIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
  </svg>
);

// ---- Materials Tab ----
function MaterialsTab({ authFetch }) {
  const [materials, setMaterials]     = useState([]);
  const [uploading, setUploading]     = useState(false);
  const [uploadResults, setUploadResults] = useState(null); // array of per-file results
  const [courseId, setCourseId]       = useState("");
  const [courses, setCourses]         = useState([]);
  const fileRef   = React.useRef(null);
  const folderRef = React.useRef(null);

  useEffect(() => {
    authFetch(`${BASE}/api/materials`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setMaterials(d.materials || []); })
      .catch(() => {});
    authFetch(`${BASE}/api/canvas/courses`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setCourses(d.courses || []); })
      .catch(() => {});
  }, []);

  async function handleUpload(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    setUploadResults(null);
    try {
      const form = new FormData();
      files.forEach(f => form.append("files", f));
      if (courseId) form.append("course_id", courseId);

      const res = await authFetch(`${BASE}/api/materials/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setUploadResults([{ filename: "Upload", ok: false, error: d.detail || "Upload failed" }]);
      } else {
        const d = await res.json();
        setUploadResults(d.results || []);
        // Add successful uploads to the list
        const newMats = (d.results || [])
          .filter(r => r.ok)
          .map(r => ({
            filename:    r.filename,
            course_id:   courseId || null,
            uploaded_at: new Date().toISOString(),
            auto_tags:   r.auto_tags || {},
          }));
        if (newMats.length > 0) {
          setMaterials(prev => {
            const nameSet = new Set(newMats.map(m => m.filename));
            return [...newMats, ...prev.filter(m => !nameSet.has(m.filename))];
          });
        }
      }
    } catch {
      setUploadResults([{ filename: "Upload", ok: false, error: "Network error" }]);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(filename) {
    try {
      const res = await authFetch(`${BASE}/api/materials/${encodeURIComponent(filename)}`, { method: "DELETE" });
      if (res.ok) setMaterials(prev => prev.filter(m => m.filename !== filename));
    } catch {}
  }

  // Summarise batch results
  const batchSummary = uploadResults && (() => {
    const ok  = uploadResults.filter(r => r.ok);
    const bad = uploadResults.filter(r => !r.ok);
    return { ok, bad, total: uploadResults.length };
  })();

  return (
    <div>
      <Section title="My Study Materials">
        <p style={s.calHint}>
          Upload PDFs, notes, or textbook chapters. Lumina indexes them so the AI can reference your personal materials.
          Subjects and grade levels are detected automatically from the filename.
        </p>

        {/* Course selector */}
        <div style={{ marginBottom: "10px" }}>
          <select
            style={{ ...s.input }}
            value={courseId}
            onChange={e => setCourseId(e.target.value)}
          >
            <option value="">No course (general)</option>
            {courses.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* Upload buttons */}
        <div style={s.materialsUploadRow}>
          {/* Multi-file picker */}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.md"
            multiple
            style={{ display: "none" }}
            onChange={handleUpload}
          />
          {/* Folder picker */}
          <input
            ref={folderRef}
            type="file"
            accept=".pdf,.txt,.md"
            multiple
            // eslint-disable-next-line react/no-unknown-property
            webkitdirectory=""
            style={{ display: "none" }}
            onChange={handleUpload}
          />
          <button
            style={s.primaryBtn}
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Indexing…" : <><UploadIcon /> Upload Files</>}
          </button>
          <button
            style={s.ghostBtn}
            onClick={() => folderRef.current?.click()}
            disabled={uploading}
            title="Upload all supported files from a folder"
          >
            📁 Upload Folder
          </button>
        </div>

        {/* Upload results */}
        {batchSummary && (
          <div style={{ marginBottom: "10px" }}>
            {batchSummary.ok.length > 0 && (
              <div style={{ fontSize: "12px", color: "var(--pill-green-text)", marginBottom: "4px" }}>
                ✓ {batchSummary.ok.length} file{batchSummary.ok.length !== 1 ? "s" : ""} indexed
                {batchSummary.ok.length <= 3 && batchSummary.ok.map(r => (
                  <span key={r.filename} style={{ marginLeft: "6px", opacity: 0.8 }}>
                    {r.filename}
                    {r.auto_tags?.subjects?.length > 0 && ` · ${r.auto_tags.subjects[0]}`}
                    {r.auto_tags?.doc_type && ` · ${r.auto_tags.doc_type.replace("_", " ")}`}
                  </span>
                ))}
              </div>
            )}
            {batchSummary.bad.length > 0 && (
              <div style={{ fontSize: "12px", color: "var(--pill-red-text)" }}>
                ⚠ {batchSummary.bad.length} failed:{" "}
                {batchSummary.bad.map(r => `${r.filename} (${r.error})`).join(" · ")}
              </div>
            )}
          </div>
        )}

        {/* Materials list */}
        {materials.length === 0 ? (
          <div style={{ fontSize: "13px", color: "var(--color-text-faint)", padding: "16px 0" }}>
            No materials uploaded yet.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {materials.map(m => {
              const tags = m.auto_tags || {};
              return (
                <div key={m.filename} style={s.materialCard}>
                  <div style={s.materialIcon}><FileIcon /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={s.materialName}>{m.filename}</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "3px" }}>
                      {m.course_id && (
                        <span style={s.materialMeta}>{courses.find(c => c.id === m.course_id)?.name || "course"}</span>
                      )}
                      {tags.doc_type && (
                        <span style={s.tagPill}>{tags.doc_type.replace(/_/g, " ")}</span>
                      )}
                      {(tags.grade_levels || []).map(g => (
                        <span key={g} style={s.tagPill}>Gr {g}</span>
                      ))}
                      {(tags.subjects || []).map(sub => (
                        <span key={sub} style={s.tagPill}>{sub}</span>
                      ))}
                    </div>
                  </div>
                  <button style={s.removeBtn} onClick={() => handleDelete(m.filename)} title="Remove">
                    <TrashIcon />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </div>
  );
}

// ---- Admin Knowledge Base Tab ----
const GRADE_LEVELS = [6, 7, 8, 9, 10, 11, 12];
const DOC_TYPES = [
  { value: "exam_paper", label: "Exam Paper / Past Paper" },
  { value: "notes",      label: "Notes / Summary" },
  { value: "textbook",   label: "Textbook / Chapter" },
  { value: "syllabus",   label: "Syllabus / Curriculum" },
  { value: "other",      label: "Other" },
];

function AdminTab({ authFetch }) {
  const [materials, setMaterials] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null);
  const [showForm, setShowForm]   = useState(false);
  const fileRef   = React.useRef(null);
  const folderRef = React.useRef(null);

  // Form state
  const [formTitle, setFormTitle]           = useState("");
  const [formDesc, setFormDesc]             = useState("");
  const [formDocType, setFormDocType]       = useState("other");
  const [formGrades, setFormGrades]         = useState([]);
  const [formSubjects, setFormSubjects]     = useState("");
  const [formExpiry, setFormExpiry]         = useState("");
  const [formApplicable, setFormApplicable] = useState(true);
  const [selectedFiles, setSelectedFiles]   = useState([]); // now an array

  useEffect(() => {
    authFetch(`${BASE}/api/admin/materials`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setMaterials(d.materials || []); })
      .catch(() => {});
  }, []);

  function toggleGrade(g) {
    setFormGrades(prev =>
      prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]
    );
  }

  function handleFileSelect(e) {
    const files = Array.from(e.target.files || []);
    setSelectedFiles(files);
  }

  async function handleUpload() {
    if (!selectedFiles.length) return;
    setUploading(true);
    setUploadMsg(null);
    const subjects = formSubjects.split(",").map(s => s.trim()).filter(Boolean);
    let okCount = 0, failCount = 0;

    for (const file of selectedFiles) {
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("grade_levels",  JSON.stringify(formGrades));
        form.append("subjects",      JSON.stringify(subjects));
        form.append("doc_type",      formDocType);
        form.append("expiry_date",   formExpiry);
        form.append("applicable",    String(formApplicable));
        form.append("title",         formTitle || file.name);
        form.append("description",   formDesc);

        const res = await authFetch(`${BASE}/api/admin/materials/upload`, { method: "POST", body: form });
        if (!res.ok) {
          failCount++;
        } else {
          const d = await res.json();
          okCount++;
          setMaterials(prev => [
            { filename: file.name, tags: d.tags, metadata: d.metadata, uploaded_at: new Date().toISOString() },
            ...prev.filter(m => m.filename !== file.name),
          ]);
        }
      } catch {
        failCount++;
      }
    }

    if (failCount === 0) {
      setUploadMsg({ ok: true, text: `✓ ${okCount} file${okCount !== 1 ? "s" : ""} uploaded & indexed successfully` });
    } else {
      setUploadMsg({ ok: okCount > 0, text: `${okCount} indexed · ${failCount} failed` });
    }
    setUploading(false);

    if (okCount > 0) {
      setShowForm(false);
      setSelectedFiles([]);
      setFormTitle(""); setFormDesc(""); setFormGrades([]); setFormSubjects("");
      setFormExpiry(""); setFormDocType("other"); setFormApplicable(true);
    }
  }

  async function handleDelete(materialId) {
    try {
      const res = await authFetch(`${BASE}/api/admin/materials/${materialId}`, { method: "DELETE" });
      if (res.ok) setMaterials(prev => prev.filter(m => m.id !== materialId));
    } catch {}
  }

  const fileLabel = selectedFiles.length === 0
    ? "Choose file(s)…"
    : selectedFiles.length === 1
      ? `📄 ${selectedFiles[0].name}`
      : `📁 ${selectedFiles.length} files selected`;

  return (
    <div>
      <Section title="Admin Knowledge Base">
        <p style={s.calHint}>
          Upload shared documents (past papers, notes, syllabuses) accessible to all students in your school.
          Tags apply to all selected files — useful for bulk-uploading a set of past papers for the same subject.
        </p>

        {uploadMsg && (
          <div style={{ fontSize: "12px", color: uploadMsg.ok ? "var(--pill-green-text)" : "var(--pill-red-text)", marginBottom: "8px" }}>
            {uploadMsg.text}
          </div>
        )}

        {!showForm && (
          <div style={{ display: "flex", gap: "8px" }}>
            <button style={s.primaryBtn} onClick={() => setShowForm(true)}>+ Upload Documents</button>
          </div>
        )}

        {showForm && (
          <div style={s.addForm}>
            {/* File / folder pickers */}
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.md"
              multiple
              style={{ display: "none" }}
              onChange={handleFileSelect}
            />
            <input
              ref={folderRef}
              type="file"
              accept=".pdf,.txt,.md"
              multiple
              // eslint-disable-next-line react/no-unknown-property
              webkitdirectory=""
              style={{ display: "none" }}
              onChange={handleFileSelect}
            />
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <button style={s.ghostBtn} onClick={() => fileRef.current?.click()}>
                {fileLabel}
              </button>
              <button style={{ ...s.ghostBtn, fontSize: "12px" }} onClick={() => folderRef.current?.click()}>
                📁 Folder
              </button>
              {selectedFiles.length > 0 && (
                <span style={{ fontSize: "11px", color: "var(--color-text-faint)" }}>
                  {(selectedFiles.reduce((sum, f) => sum + f.size, 0) / 1024).toFixed(0)} KB total
                </span>
              )}
            </div>

            <input style={s.input} placeholder="Title (optional — applied to all files)" value={formTitle} onChange={e => setFormTitle(e.target.value)} />
            <input style={s.input} placeholder="Description (optional)" value={formDesc} onChange={e => setFormDesc(e.target.value)} />
            <input style={s.input} placeholder="Subjects — comma separated (e.g. Mathematics, Physics)" value={formSubjects} onChange={e => setFormSubjects(e.target.value)} />

            {/* Doc type */}
            <select style={s.input} value={formDocType} onChange={e => setFormDocType(e.target.value)}>
              {DOC_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>

            {/* Grade levels */}
            <div>
              <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "6px" }}>Grade levels:</div>
              <div style={s.gradeGrid}>
                {GRADE_LEVELS.map(g => (
                  <button
                    key={g}
                    style={{ ...s.gradeBtn, ...(formGrades.includes(g) ? s.gradeBtnActive : {}) }}
                    onClick={() => toggleGrade(g)}
                    type="button"
                  >
                    Gr {g}
                  </button>
                ))}
              </div>
            </div>

            {/* Expiry date */}
            <div>
              <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "4px" }}>Expiry date (optional):</div>
              <input type="date" style={s.input} value={formExpiry} onChange={e => setFormExpiry(e.target.value)} />
            </div>

            {/* Applicable toggle */}
            <Row label="Applicable (visible to students)" hint="">
              <Toggle checked={formApplicable} onChange={setFormApplicable} />
            </Row>

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                style={s.primaryBtn}
                onClick={handleUpload}
                disabled={uploading || selectedFiles.length === 0}
              >
                {uploading
                  ? "Uploading…"
                  : `Upload & Index${selectedFiles.length > 1 ? ` (${selectedFiles.length})` : ""}`}
              </button>
              <button style={s.ghostBtn} onClick={() => { setShowForm(false); setSelectedFiles([]); }}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </Section>

      {/* Materials list */}
      {materials.length > 0 && (
        <Section title="Uploaded Documents">
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {materials.map(m => {
              const grades   = m.tags?.grade_levels || [];
              const subjects = m.tags?.subjects || [];
              const docType  = DOC_TYPES.find(d => d.value === m.tags?.doc_type)?.label || m.tags?.doc_type || "";
              const expired  = m.tags?.expiry_date && new Date(m.tags.expiry_date) < new Date();
              return (
                <div key={m.id || m.filename} style={{ ...s.materialCard, opacity: expired ? 0.6 : 1 }}>
                  <div style={s.materialIcon}><FileIcon /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={s.materialName}>{m.metadata?.title || m.filename}</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                      {docType && <span style={s.tagPill}>{docType}</span>}
                      {grades.map(g => <span key={g} style={s.tagPill}>Gr {g}</span>)}
                      {subjects.map(sub => <span key={sub} style={s.tagPill}>{sub}</span>)}
                      {expired && <span style={{ ...s.tagPill, background: "var(--pill-red-bg)", color: "var(--pill-red-text)" }}>Expired</span>}
                      {m.tags?.expiry_date && !expired && <span style={s.tagPill}>Expires {m.tags.expiry_date}</span>}
                    </div>
                  </div>
                  <button style={s.removeBtn} onClick={() => handleDelete(m.id)} title="Remove">
                    <TrashIcon />
                  </button>
                </div>
              );
            })}
          </div>
        </Section>
      )}
    </div>
  );
}

// ---- Main component ----
export default function SettingsModal({ onClose }) {
  const { settings, update } = useSettings();
  const { user, logout, authFetch } = useAuth();
  const [activeTab, setActiveTab] = useState("general");
  const [aiInfo, setAiInfo] = useState({ provider: "…", model: "…" });

  useEffect(() => {
    fetch(`${BASE}/health`)
      .then(r => r.json())
      .then(d => setAiInfo({ provider: d.provider ?? "unknown", model: d.model ?? "unknown" }))
      .catch(() => {});
  }, []);

  // Check if user is admin/teacher to show Admin tab
  const isAdmin = user && ["teacher", "teacherenrollment", "taenrollment", "accountadmin", "admin"].some(
    r => (user.canvas_role || user.role || "").toLowerCase().includes(r)
  );

  const tabs = [
    { id: "general",   label: "General" },
    { id: "calendar",  label: "Calendar" },
    { id: "materials", label: "Materials" },
    ...(isAdmin ? [{ id: "admin", label: "Admin KB" }] : []),
    { id: "account",   label: "Account" },
  ];

  return (
    <div style={s.overlay} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={s.modal}>

        {/* Header */}
        <div style={s.header}>
          <div>
            <h2 style={s.headerTitle}>Settings</h2>
            <p style={s.headerSub}>Customise your Lumina experience</p>
          </div>
          <button style={s.closeBtn} onClick={onClose}><CloseIcon /></button>
        </div>

        {/* Tab bar */}
        <div style={s.tabBar}>
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{ ...s.tabBtn, ...(activeTab === t.id ? s.tabBtnActive : {}) }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div style={s.body}>

          {/* ── GENERAL TAB ── */}
          {activeTab === "general" && <>
            <Section title="AI Behaviour">
              <Row
                label="Use emojis in responses"
                hint="The AI tutor will include relevant emojis to keep responses engaging."
              >
                <Toggle checked={settings.emojisEnabled} onChange={v => update({ emojisEnabled: v })} />
              </Row>
              <Row
                label="Full Canvas context"
                hint="Injects your upcoming assignments into every message so the AI always knows your workload."
              >
                <Toggle checked={settings.fullCanvasContext} onChange={v => update({ fullCanvasContext: v })} />
              </Row>
            </Section>

            <Section title="Appearance">
              <Row label="Colour theme" hint="Lumina Gold is the default. Dwight Navy matches Dwight Schools branding.">
                <div style={s.themeRow}>
                  <ThemeBtn active={settings.colorTheme === "lumina"} color="#f5c010" label="Lumina Gold" onClick={() => update({ colorTheme: "lumina" })} />
                  <ThemeBtn active={settings.colorTheme === "dwight"} color="#13234B" label="Dwight Navy" onClick={() => update({ colorTheme: "dwight" })} />
                </div>
              </Row>
              <Row label="Chat font" hint="Computer Modern is the classic LaTeX serif — great for maths and science.">
                <SegmentedControl
                  value={settings.fontFamily}
                  onChange={v => update({ fontFamily: v })}
                  options={[
                    { value: "computer-modern", label: "CM Serif" },
                    { value: "inter",           label: "Inter" },
                    { value: "system",          label: "System" },
                  ]}
                />
              </Row>
              <Row label="Chat font size" hint="Adjusts text size in the main chat window.">
                <SegmentedControl
                  value={settings.fontSize}
                  onChange={v => update({ fontSize: v })}
                  options={[{ value: "sm", label: "S" }, { value: "md", label: "M" }, { value: "lg", label: "L" }]}
                />
              </Row>
              <Row label="Panel text size" hint="Controls font size inside assignment and announcement details.">
                <SegmentedControl
                  value={settings.panelFontSize}
                  onChange={v => update({ panelFontSize: v })}
                  options={[{ value: "sm", label: "S" }, { value: "md", label: "M" }, { value: "lg", label: "L" }]}
                />
              </Row>
              <Row label="Show extra-curricular courses" hint="Displays clubs, activities, and non-academic courses in the sidebar.">
                <Toggle checked={settings.showExtracurriculars} onChange={v => update({ showExtracurriculars: v })} />
              </Row>
            </Section>
          </>}

          {/* ── CALENDAR TAB ── */}
          {activeTab === "calendar" && (
            <CalendarTab settings={settings} update={update} authFetch={authFetch} />
          )}

          {/* ── MATERIALS TAB ── */}
          {activeTab === "materials" && (
            <MaterialsTab authFetch={authFetch} />
          )}

          {/* ── ADMIN KNOWLEDGE BASE TAB ── */}
          {activeTab === "admin" && (
            <AdminTab authFetch={authFetch} />
          )}

          {/* ── ACCOUNT TAB ── */}
          {activeTab === "account" && <>
            <Section title="Account">
              {user && (
                <div style={s.accountCard}>
                  {user.avatar_url
                    ? <img src={user.avatar_url} style={s.accountAvatar} alt="" />
                    : <div style={s.accountAvatarFallback}>{(user.name || "?")[0].toUpperCase()}</div>
                  }
                  <div>
                    <div style={s.accountName}>{user.name}</div>
                    <div style={s.accountEmail}>{user.email || "Canvas student"}</div>
                    <div style={s.accountBadge}>Connected via Canvas API Key</div>
                  </div>
                </div>
              )}
              <Row label="Canvas connection" hint="To change your Canvas server or API key, sign out and log in again.">
                <button style={s.dangerBtn} onClick={logout}>Sign out</button>
              </Row>
            </Section>

            <Section title="About Lumina">
              <div style={s.aboutGrid}>
                <AboutItem label="Version" value="v2.0" />
                <AboutItem label="Model"   value={`${aiInfo.model} via ${aiInfo.provider}`} />
              </div>
            </Section>
          </>}

        </div>
      </div>
    </div>
  );
}

function AboutItem({ label, value }) {
  return (
    <div style={s.aboutItem}>
      <span style={s.aboutLabel}>{label}</span>
      <span style={s.aboutValue}>{value}</span>
    </div>
  );
}

// ---- Styles ----
const s = {
  overlay: {
    position: "fixed", inset: 0,
    background: "rgba(0,0,0,0.35)",
    backdropFilter: "blur(4px)",
    zIndex: 200,
    display: "flex", alignItems: "center", justifyContent: "center",
    padding: "20px",
    animation: "fadeInUp 0.18s ease",
  },
  modal: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "16px",
    width: "100%",
    maxWidth: "580px",
    maxHeight: "88vh",
    display: "flex",
    flexDirection: "column",
    boxShadow: "0 24px 64px rgba(0,0,0,0.15)",
    // overflow: "hidden" intentionally omitted — it would clip absolutely-positioned
    // tooltip boxes. The body's overflowY: auto handles scroll containment.
  },
  header: {
    padding: "20px 24px 16px",
    borderBottom: "1px solid var(--color-border)",
    display: "flex", alignItems: "flex-start", justifyContent: "space-between",
    flexShrink: 0,
  },
  headerTitle: { fontSize: "18px", fontWeight: "700", color: "var(--color-text)", marginBottom: "2px" },
  headerSub:   { fontSize: "13px", color: "var(--color-text-muted)" },
  closeBtn: {
    background: "none", border: "none",
    color: "var(--color-text-muted)", cursor: "pointer",
    padding: "4px", borderRadius: "8px",
    display: "flex", alignItems: "center", justifyContent: "center",
    marginLeft: "12px", flexShrink: 0,
  },

  // Tab bar
  tabBar: {
    display: "flex",
    borderBottom: "1px solid var(--color-border)",
    padding: "0 16px",
    flexShrink: 0,
    gap: "4px",
  },
  tabBtn: {
    padding: "10px 16px",
    background: "none", border: "none",
    borderBottom: "2px solid transparent",
    fontSize: "13px", fontWeight: "500",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    transition: "color 0.15s, border-color 0.15s",
    whiteSpace: "nowrap",
  },
  tabBtnActive: {
    color: "var(--color-text)",
    borderBottomColor: "var(--color-primary)",
    fontWeight: "700",
  },

  body: { flex: 1, overflowY: "auto", padding: "0 0 20px" },
  section: { padding: "20px 24px 0", marginBottom: "4px" },
  sectionTitle: {
    fontSize: "11px", fontWeight: "700",
    textTransform: "uppercase", letterSpacing: "0.1em",
    color: "var(--color-text-faint)",
    marginBottom: "12px", paddingBottom: "8px",
    borderBottom: "1px solid var(--color-border)",
  },
  row: {
    display: "flex", alignItems: "flex-start", justifyContent: "space-between",
    gap: "16px", paddingBottom: "16px", marginBottom: "4px",
  },
  rowLabel: { flex: 1, minWidth: 0 },
  rowLabelText: { display: "block", fontSize: "14px", fontWeight: "500", color: "var(--color-text)", marginBottom: "3px" },
  rowHint:      { display: "block", fontSize: "12px", color: "var(--color-text-muted)", lineHeight: "1.5" },
  rowControl:   { flexShrink: 0 },

  // Toggle
  toggle: {
    width: "44px", height: "26px", border: "none", borderRadius: "9999px",
    cursor: "pointer", padding: 0, position: "relative",
    transition: "background 0.2s", display: "flex", alignItems: "center",
  },
  toggleThumb: {
    position: "absolute", width: "20px", height: "20px",
    borderRadius: "50%", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
    transition: "transform 0.2s",
  },

  // Segmented
  segmented: {
    display: "flex", background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)", borderRadius: "9999px",
    padding: "3px", gap: "2px",
  },
  segBtn: {
    padding: "5px 10px", background: "none", border: "none",
    borderRadius: "9999px", fontSize: "12px", fontWeight: "500",
    color: "var(--color-text-muted)", cursor: "pointer",
    transition: "all 0.15s", whiteSpace: "nowrap",
  },
  segBtnActive: {
    background: "var(--color-surface)", color: "var(--color-text)",
    boxShadow: "0 1px 4px rgba(0,0,0,0.1)", fontWeight: "600",
  },

  // Theme picker
  themeRow: { display: "flex", gap: "8px" },
  themeBtn: {
    display: "flex", alignItems: "center", gap: "8px",
    padding: "7px 14px 7px 10px", background: "var(--color-surface)",
    borderRadius: "9999px", cursor: "pointer", transition: "all 0.15s",
  },
  themeSwatch: { width: "14px", height: "14px", borderRadius: "50%", flexShrink: 0 },
  themeBtnLabel: { fontSize: "12px", color: "var(--color-text)", whiteSpace: "nowrap" },

  // Calendar compact grid
  calGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
    marginBottom: "12px",
  },
  calGridCard: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "10px",
    padding: "8px 10px",
    minWidth: 0,
  },
  calGridIcon: {
    width: "24px",
    height: "24px",
    borderRadius: "6px",
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  calGridName: {
    fontSize: "12px",
    fontWeight: "600",
    color: "var(--color-text)",
    marginBottom: "1px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },

  // Calendar
  calHint: {
    fontSize: "12px", color: "var(--color-text-muted)",
    lineHeight: "1.6", marginBottom: "12px",
  },
  calSourceCard: {
    display: "flex", alignItems: "center", gap: "10px",
    background: "var(--color-bg)", border: "1px solid var(--color-border)",
    borderRadius: "10px", padding: "10px 12px", marginBottom: "8px",
  },
  calSourceIcon: {
    width: "28px", height: "28px", borderRadius: "8px",
    background: "var(--color-primary)", color: "var(--color-primary-text)",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0,
  },
  calSourceName: { fontSize: "13px", fontWeight: "600", color: "var(--color-text)", marginBottom: "2px" },
  calSourceUrl:  { fontSize: "11px", color: "var(--color-text-muted)", wordBreak: "break-all" },
  calSourceConnected: {
    display: "inline-flex", alignItems: "center", gap: "4px",
    fontSize: "11px", color: "var(--pill-green-text)",
    fontWeight: "600", marginTop: "2px",
  },
  tooltipTrigger: {
    display: "inline-flex", alignItems: "center",
    color: "var(--color-text-faint)", cursor: "help",
    marginLeft: "4px",
  },
  tooltipBox: {
    position: "absolute",
    bottom: "calc(100% + 8px)",
    left: "0",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "10px",
    padding: "12px 14px",
    fontSize: "12px",
    lineHeight: "1.6",
    color: "var(--color-text-muted)",
    whiteSpace: "normal",           // allow text to wrap
    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
    zIndex: 300,
    pointerEvents: "none",
    width: "300px",                 // fixed width so it doesn't collapse or overflow
    textAlign: "left",
  },
  connectedBadge: {
    display: "inline-flex", alignItems: "center", gap: "4px",
    background: "var(--pill-green-bg)", color: "var(--pill-green-text)",
    fontSize: "11px", fontWeight: "600", padding: "2px 8px", borderRadius: "9999px",
  },
  notConnectedBadge: {
    display: "inline-block",
    background: "var(--pill-amber-bg)", color: "var(--pill-amber-text)",
    fontSize: "11px", fontWeight: "500", padding: "2px 8px", borderRadius: "9999px",
  },
  removeBtn: {
    background: "none", border: "none",
    color: "var(--color-text-faint)", cursor: "pointer",
    padding: "4px", borderRadius: "6px", flexShrink: 0,
    display: "flex", alignItems: "center",
  },
  instructionBox: {
    background: "var(--color-surface-2)", border: "1px solid var(--color-border)",
    borderRadius: "10px", padding: "12px", marginBottom: "12px",
    fontSize: "12px", color: "var(--color-text-muted)", lineHeight: "1.8",
  },
  instructionRow: { display: "flex", gap: "8px", alignItems: "flex-start" },
  instructionApp: {
    fontSize: "11px", fontWeight: "700", color: "var(--color-text)",
    minWidth: "100px", flexShrink: 0,
  },
  addForm: {
    display: "flex", flexDirection: "column", gap: "8px",
    background: "var(--color-bg)", border: "1px solid var(--color-border)",
    borderRadius: "10px", padding: "12px", marginTop: "4px",
  },
  input: {
    padding: "8px 12px", fontSize: "13px",
    background: "var(--color-surface)", border: "1px solid var(--color-border)",
    borderRadius: "8px", color: "var(--color-text)", outline: "none", width: "100%",
    boxSizing: "border-box",
  },
  errorText: { fontSize: "12px", color: "var(--pill-red-text)" },
  primaryBtn: {
    padding: "7px 16px", background: "var(--color-primary)",
    color: "var(--color-primary-text)", border: "none",
    borderRadius: "9999px", fontSize: "13px", fontWeight: "600",
    cursor: "pointer", transition: "opacity 0.15s",
  },
  ghostBtn: {
    padding: "7px 16px", background: "none",
    color: "var(--color-text-muted)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px", fontSize: "13px", fontWeight: "500",
    cursor: "pointer", transition: "opacity 0.15s",
  },

  // Account
  accountCard: {
    display: "flex", alignItems: "center", gap: "14px",
    background: "var(--color-bg)", border: "1px solid var(--color-border)",
    borderRadius: "12px", padding: "14px", marginBottom: "16px",
  },
  accountAvatar: { width: "44px", height: "44px", borderRadius: "50%", objectFit: "cover", flexShrink: 0 },
  accountAvatarFallback: {
    width: "44px", height: "44px", borderRadius: "50%",
    background: "var(--color-primary)", color: "var(--color-primary-text)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: "18px", fontWeight: "700", flexShrink: 0,
  },
  accountName:  { fontSize: "15px", fontWeight: "600", color: "var(--color-text)", marginBottom: "2px" },
  accountEmail: { fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "5px" },
  accountBadge: {
    display: "inline-block", background: "var(--pill-green-bg)", color: "var(--pill-green-text)",
    fontSize: "10px", fontWeight: "600", padding: "2px 8px", borderRadius: "9999px",
  },
  dangerBtn: {
    padding: "7px 16px", background: "var(--pill-red-bg)", color: "var(--pill-red-text)",
    border: "1px solid rgba(185,28,28,0.2)", borderRadius: "9999px",
    fontSize: "13px", fontWeight: "600", cursor: "pointer", transition: "opacity 0.15s",
    whiteSpace: "nowrap",
  },

  // Materials
  materialsUploadRow: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
    marginBottom: "10px",
  },
  materialCard: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "10px",
    padding: "9px 12px",
  },
  materialIcon: {
    width: "28px",
    height: "28px",
    borderRadius: "8px",
    background: "var(--color-surface-2)",
    color: "var(--color-text-muted)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  materialName: {
    fontSize: "13px",
    fontWeight: "600",
    color: "var(--color-text)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    marginBottom: "1px",
  },
  materialMeta: {
    fontSize: "11px",
    color: "var(--color-text-faint)",
  },

  // Admin KB tags
  gradeGrid: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
  },
  gradeBtn: {
    padding: "4px 10px",
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px",
    fontSize: "11px",
    fontWeight: "600",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    transition: "all 0.12s",
  },
  gradeBtnActive: {
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    borderColor: "var(--color-primary)",
  },
  tagPill: {
    display: "inline-block",
    padding: "1px 7px",
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px",
    fontSize: "10px",
    fontWeight: "600",
    color: "var(--color-text-muted)",
  },

  // About
  aboutGrid:  { display: "flex", flexDirection: "column", gap: "8px" },
  aboutItem:  { display: "flex", justifyContent: "space-between", fontSize: "13px", padding: "6px 0", borderBottom: "1px solid var(--color-border)" },
  aboutLabel: { color: "var(--color-text-muted)", fontWeight: "500" },
  aboutValue: { color: "var(--color-text)", textAlign: "right" },
};
