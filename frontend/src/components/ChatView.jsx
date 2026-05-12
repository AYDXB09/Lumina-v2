/**
 * ChatView — main chat interface.
 *
 * Props:
 *   course              — { id, name } | null
 *   session             — { id } | null
 *   onSessionCreated    — fn(session)
 *   onToggleSidebar     — fn()   (hamburger button)
 *   onToggleRightPanel  — fn()   (assignments button)
 *   rightPanelOpen      — bool
 *   syncing             — bool   (show amber status when true)
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { useIsMobile } from "../hooks/useIsMobile.js";
import { streamChat, fetchSessions, fetchMessages } from "../api.js";
import ChatMessage from "./ChatMessage.jsx";

// ---- Icons ----
const MenuIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);

const PaperclipIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
  </svg>
);

const SendIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const AssignmentsIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const CloseIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const StopIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
);

const PLACEHOLDER = "Ask me anything… I'll guide you to the answer";

export default function ChatView({
  course = null,
  session = null,
  onSessionCreated,
  onToggleSidebar,
  onToggleRightPanel,
  rightPanelOpen = false,
  syncing = false,
  registerSend = null,   // fn(sendFn) — lets parent components trigger a send
}) {
  const { authFetch } = useAuth();
  const isMobile = useIsMobile();
  const [messages, setMessages]             = useState([]);
  const [input, setInput]                   = useState("");
  const [loading, setLoading]               = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [toolStatus, setToolStatus]         = useState(null);
  const [streamingText, setStreamingText]   = useState("");
  const [attachments, setAttachments]       = useState([]);   // [{id, name, type, content?, base64?, mimeType?}]
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [lastResponseMs, setLastResponseMs] = useState(null); // ms for last response
  const [elapsedMs, setElapsedMs]           = useState(null); // live counter while loading

  const bottomRef    = useRef(null);
  const inputRef     = useRef(null);
  const fileInputRef = useRef(null);
  const attachMenuRef = useRef(null);
  const sessionIdRef  = useRef(session?.id ?? null);
  const sendTimeRef   = useRef(null);  // Date.now() when message was sent
  const timerRef      = useRef(null);  // setInterval handle
  const messagesRef   = useRef([]);    // always-current messages (avoids stale closure in registerSend)
  const abortRef      = useRef(null);  // AbortController.abort fn — set during streaming

  // Keep messagesRef in sync so stale closures (registerSend) always see current messages
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  // Live elapsed-time counter while loading
  useEffect(() => {
    if (loading) {
      sendTimeRef.current = sendTimeRef.current ?? Date.now();
      timerRef.current = setInterval(() => {
        setElapsedMs(Date.now() - sendTimeRef.current);
      }, 100);
    } else {
      clearInterval(timerRef.current);
      timerRef.current = null;
      setElapsedMs(null);
    }
    return () => clearInterval(timerRef.current);
  }, [loading]);

  // Close attach menu on outside click
  useEffect(() => {
    function handleClick(e) {
      if (attachMenuRef.current && !attachMenuRef.current.contains(e.target)) {
        setShowAttachMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Load last session history when course changes
  useEffect(() => {
    let cancelled = false;
    sessionIdRef.current = session?.id ?? null;
    setMessages([]);
    setHistoryLoading(true);

    (async () => {
      try {
        const { sessions } = await fetchSessions(authFetch, course?.id ?? null);
        if (cancelled) return;
        if (sessions?.length > 0) {
          const last = sessions[0];
          sessionIdRef.current = last.id;
          const { messages: msgs } = await fetchMessages(authFetch, last.id);
          if (!cancelled) {
            // Restore timer badge from thinking.response_ms saved at send time
            const withTimers = (msgs ?? []).map(m =>
              m.role === "assistant" && m.thinking?.response_ms
                ? { ...m, _ms: m.thinking.response_ms }
                : m
            );
            setMessages(withTimers);
          }
        }
      } catch { /* No history — start fresh */ }
      finally { if (!cancelled) setHistoryLoading(false); }
    })();

    return () => { cancelled = true; };
  }, [course?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  // ---- File attachments ----
  const handleFileSelect = useCallback(async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const newAtts = [];
    for (const file of files) {
      const id = Math.random().toString(36).slice(2);
      if (file.type.startsWith("image/")) {
        const base64 = await toBase64(file);
        newAtts.push({ id, name: file.name, type: "image", base64, mimeType: file.type });
      } else if (file.name.endsWith(".pdf")) {
        newAtts.push({ id, name: file.name, type: "text", content: `[PDF attached: ${file.name} — send this message to include it as context]` });
      } else {
        try {
          const text = await file.text();
          newAtts.push({ id, name: file.name, type: "text", content: text });
        } catch {
          newAtts.push({ id, name: file.name, type: "text", content: `[Could not read ${file.name}]` });
        }
      }
    }
    setAttachments(prev => [...prev, ...newAtts]);
    e.target.value = "";
  }, []);

  function toBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(",")[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function removeAttachment(id) {
    setAttachments(prev => prev.filter(a => a.id !== id));
  }

  // ---- Send ----
  // overrideText: string → used by quick-action buttons (bypasses input state)
  const handleSend = async (overrideText) => {
    const isQuick = typeof overrideText === "string";
    const text = isQuick ? overrideText : input.trim();
    const currentAtts = isQuick ? [] : [...attachments];

    if ((!text && currentAtts.length === 0) || loading) return;

    if (!isQuick) {
      setAttachments([]);
      setInput("");
      if (inputRef.current) inputRef.current.style.height = "auto";
    }

    const textContent = text
      + currentAtts
          .filter(a => a.type === "text")
          .map(a => `\n\n[File: ${a.name}]\n${a.content}`)
          .join("");

    const userMsg = { role: "user", content: textContent || text };
    const newMessages = [...messagesRef.current, userMsg];
    setMessages(newMessages);
    setLoading(true);
    setStreamingText("");
    setToolStatus(null);
    setLastResponseMs(null);
    sendTimeRef.current = Date.now();

    try {
      let accumulated = "";
      await streamChat(
        authFetch,
        newMessages,
        {
          sessionId: sessionIdRef.current,
          courseId: course?.id ?? null,
          signal: (ctrl) => { abortRef.current = ctrl.abort.bind(ctrl); },
        },
        (chunk) => { accumulated += chunk; setStreamingText(accumulated); },
        (toolCall) => {
          const labels = {
            get_courses:           "Fetching your courses…",
            get_assignments:       "Loading assignments…",
            get_announcements:     "Checking announcements…",
            search_course_content: "Searching course materials…",
          };
          setToolStatus(labels[toolCall.name] ?? `Calling ${toolCall.name}…`);
        },
        (sessionId) => { sessionIdRef.current = sessionId; },
      );
      const elapsed = Date.now() - sendTimeRef.current;
      setLastResponseMs(elapsed);
      setMessages(prev => [...prev, { role: "assistant", content: accumulated, _ms: elapsed }]);
      setStreamingText("");
      setToolStatus(null);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: `Sorry, something went wrong: ${err.message}` }]);
      setStreamingText("");
      setToolStatus(null);
    } finally {
      abortRef.current = null;
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleStop = () => {
    abortRef.current?.();
  };

  // Quick-action alias used by WelcomeScreen and external callers (RightPanel MindMap)
  const fireQuickAction = (prompt) => handleSend(prompt);

  // Register with parent (App.jsx) so RightPanel can trigger messages
  useEffect(() => {
    registerSend?.(fireQuickAction);
  }, []); // eslint-disable-line

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + "px";
  };

  // ---- Accept type helpers ----
  const openFilePicker = (accept) => {
    if (!fileInputRef.current) return;
    fileInputRef.current.accept = accept;
    fileInputRef.current.click();
    setShowAttachMenu(false);
  };

  return (
    <div style={s.container}>

      {/* ===================== TOPBAR ===================== */}
      <header style={s.topbar}>
        <div style={s.topbarLeft}>
          {/* Hamburger — toggle sidebar */}
          <button style={s.iconBtn} onClick={onToggleSidebar} title="Toggle sidebar">
            <MenuIcon />
          </button>
          <span style={s.topbarTitle}>
            {course ? course.name : "Lumina"}
          </span>
        </div>

        <div style={s.topbarRight}>
          {/* Assignments panel toggle — only when course selected */}
          {course && (
            <button
              style={{
                ...s.assignBtn,
                ...(rightPanelOpen ? s.assignBtnActive : {}),
              }}
              onClick={onToggleRightPanel}
              title="Assignments & Announcements"
            >
              <AssignmentsIcon />
              <span>Assignments</span>
            </button>
          )}

          {/* Connection status pill */}
          <span style={{ ...s.statusPill, ...(syncing ? s.statusSyncing : s.statusConnected) }}>
            <span style={{ ...s.statusDot, background: syncing ? "var(--color-warning)" : "var(--color-success)" }} />
            {syncing ? "Syncing…" : "Connected"}
          </span>
        </div>
      </header>

      {/* ===================== MESSAGES ===================== */}
      <div className="graph-paper" style={s.messages}>
        {messages.length === 0 && !historyLoading ? (
          <WelcomeScreen course={course} onQuickAction={fireQuickAction} />
        ) : null}

        {historyLoading && (
          <div style={s.loadingHistory}>Loading history…</div>
        )}

        <div style={s.messageInner}>
          {messages.map((m, i) => (
            <React.Fragment key={i}>
              <ChatMessage role={m.role} content={m.content} />
              {m.role === "assistant" && m._ms && (
                <div style={s.timerBadge}>
                  ⏱ {m._ms >= 1000 ? `${(m._ms / 1000).toFixed(1)}s` : `${m._ms}ms`}
                </div>
              )}
            </React.Fragment>
          ))}

          {/* Thinking / tool status indicator */}
          {loading && !streamingText && (
            <div style={s.toolStatus}>
              <span style={s.toolDot} />
              <span>
                {toolStatus ?? "Thinking…"}
                {elapsedMs !== null && (
                  <span style={s.timerLive}> {(elapsedMs / 1000).toFixed(1)}s</span>
                )}
              </span>
            </div>
          )}

          {/* Streaming response */}
          {streamingText && (
            <ChatMessage role="assistant" content={streamingText} isStreaming />
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* ===================== INPUT AREA ===================== */}
      <div style={{ ...s.inputArea, padding: isMobile ? "8px 12px 16px" : s.inputArea.padding }}
           className="input-area-safe">

        {/* Attachment chips */}
        {attachments.length > 0 && (
          <div style={s.attachStrip}>
            {attachments.map(att => (
              <div key={att.id} style={s.attachChip}>
                {att.type === "image" ? (
                  <img
                    src={`data:${att.mimeType};base64,${att.base64}`}
                    alt={att.name}
                    style={s.attachThumb}
                  />
                ) : (
                  <span style={s.attachFileIcon}><PaperclipIcon /></span>
                )}
                <span style={s.attachName}>{att.name}</span>
                <button style={s.attachRemove} onClick={() => removeAttachment(att.id)}>
                  <CloseIcon />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Hidden file input */}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          multiple
          onChange={handleFileSelect}
        />

        {/* Dark pill input wrapper */}
        <div style={s.inputWrapper}>
          <div style={s.inputRow}>

            {/* Attach button + dropdown */}
            <div style={{ position: "relative" }} ref={attachMenuRef}>
              <button
                style={s.inputActionBtn}
                onClick={() => setShowAttachMenu(p => !p)}
                title="Attach file"
                disabled={loading}
              >
                <PaperclipIcon />
              </button>

              {showAttachMenu && (
                <div style={s.attachMenu}>
                  <button style={s.attachMenuItem} onClick={() => openFilePicker("*/*")}>
                    📄 Files
                  </button>
                  <button style={s.attachMenuItem} onClick={() => openFilePicker("image/*")}>
                    🖼️ Images
                  </button>
                  <button style={s.attachMenuItem} onClick={() => openFilePicker("audio/*,video/*")}>
                    🎵 Audio
                  </button>
                </div>
              )}
            </div>

            {/* Textarea */}
            <textarea
              ref={inputRef}
              style={s.textarea}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={PLACEHOLDER}
              rows={1}
              disabled={loading}
            />

            {/* Send / Stop button */}
            <button
              style={{
                ...s.sendBtn,
                opacity: loading ? 1 : (!input.trim() && attachments.length === 0) ? 0.45 : 1,
              }}
              onClick={loading ? handleStop : handleSend}
              disabled={!loading && !input.trim() && attachments.length === 0}
              title={loading ? "Stop" : "Send"}
            >
              {loading ? <StopIcon /> : <SendIcon />}
            </button>
          </div>
        </div>

        {/* Powered by footer */}
        <div style={s.inputFooter}>
          <span style={{ fontSize: "11px", color: "var(--color-text-faint)" }}>
            Powered by AI · Lumina · Canvas LMS
          </span>
        </div>
      </div>
    </div>
  );
}

// ---- Welcome screen ----
function WelcomeScreen({ course, onQuickAction }) {
  const courseActions = [
    { icon: "📅", label: "Study plan this week", prompt: "Create a personalised study plan for this week. Factor in my upcoming assignments, exams, and calendar events, and suggest daily study sessions that fit around my schedule." },
    { icon: "📋", label: "What's due soon?", prompt: "What assignments, quizzes, or exams do I have due in the next 7 days? List them with due dates." },
    { icon: "📚", label: "Summarise this course", prompt: "Give me a brief overview of the main topics covered in this course so far." },
    { icon: "💡", label: "Help me understand…", prompt: "I'd like to understand a concept from this course. Can you start by asking me which topic I'm finding difficult?" },
  ];
  const globalActions = [
    { icon: "📅", label: "Plan my week", prompt: "Create a study plan for this week across all my courses. Factor in my upcoming assignments, exams, and calendar events." },
    { icon: "📋", label: "What's due soon?", prompt: "What assignments, quizzes, or exams do I have due in the next 7 days across all my courses?" },
  ];
  const actions = course ? courseActions : globalActions;

  return (
    <div style={ws.container}>
      <div style={ws.logoWrap}>
        <svg width="56" height="56" viewBox="0 0 100 100" fill="none">
          <path d="M52 10C61 10 66 18 74 24C86 32 96 46 90 62C84 78 72 78 60 88C48 98 36 94 24 84C12 74 6 62 8 46C10 30 22 22 32 24C38 18 44 10 52 10Z" fill="#111111" />
          <ellipse cx="43" cy="53" rx="7.5" ry="10.5" fill="white" transform="rotate(-6,43,53)" />
          <ellipse cx="59" cy="53" rx="7.5" ry="10.5" fill="white" transform="rotate(6,59,53)" />
        </svg>
      </div>
      <h1 style={ws.title}>Lumina</h1>
      <p style={ws.subtitle}>
        {course
          ? `Your AI tutor for ${course.name}. Ask me anything.`
          : "Your intelligent study companion. Ask a question, or select a course from the left."}
      </p>
      {onQuickAction && (
        <div style={ws.quickActions}>
          {actions.map(a => (
            <button
              key={a.label}
              style={ws.quickBtn}
              onClick={() => onQuickAction(a.prompt)}
            >
              <span style={ws.quickIcon}>{a.icon}</span>
              <span>{a.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Styles ----
const s = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    background: "var(--color-bg)",
    overflow: "hidden",
  },

  // --- Topbar ---
  topbar: {
    height: "52px",
    padding: "0 16px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottom: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    flexShrink: 0,
    gap: "12px",
  },
  topbarLeft: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    minWidth: 0,
  },
  topbarRight: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    flexShrink: 0,
  },
  topbarTitle: {
    fontSize: "14px",
    fontWeight: "600",
    color: "var(--color-text)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    maxWidth: "340px",
  },
  iconBtn: {
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    padding: "6px",
    borderRadius: "8px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background var(--transition)",
    flexShrink: 0,
  },
  assignBtn: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "5px 12px",
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px",
    color: "var(--color-text-muted)",
    fontSize: "12px",
    fontWeight: "500",
    cursor: "pointer",
    transition: "all var(--transition)",
  },
  assignBtnActive: {
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    borderColor: "var(--color-primary)",
    boxShadow: "0 2px 8px var(--color-primary-glow)",
  },
  statusPill: {
    display: "flex",
    alignItems: "center",
    gap: "5px",
    padding: "4px 10px",
    borderRadius: "9999px",
    fontSize: "11px",
    fontWeight: "500",
    flexShrink: 0,
  },
  statusConnected: {
    background: "rgba(34,197,94,0.12)",
    color: "#166534",
  },
  statusSyncing: {
    background: "rgba(245,158,11,0.12)",
    color: "#92400e",
  },
  statusDot: {
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    flexShrink: 0,
  },

  // --- Messages ---
  messages: {
    flex: 1,
    overflowY: "auto",
    position: "relative",
    minHeight: 0,
  },
  messageInner: {
    maxWidth: "1100px",
    width: "100%",
    margin: "0 auto",
    padding: "28px 32px 12px",
  },
  loadingHistory: {
    textAlign: "center",
    padding: "40px",
    color: "var(--color-text-faint)",
    fontSize: "13px",
  },
  toolStatus: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 0 10px",
    color: "var(--color-text-muted)",
    fontSize: "13px",
  },
  toolDot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    background: "var(--color-primary)",
    animation: "pulse 1.2s ease-in-out infinite",
    flexShrink: 0,
  },
  timerLive: {
    color: "var(--color-text-faint)",
    fontSize: "11px",
    fontVariantNumeric: "tabular-nums",
  },
  timerBadge: {
    fontSize: "11px",
    color: "var(--color-text-faint)",
    fontVariantNumeric: "tabular-nums",
    textAlign: "right",
    paddingBottom: "8px",
    paddingRight: "4px",
    marginTop: "-6px",
  },

  // --- Input area ---
  inputArea: {
    padding: "10px 32px 18px",
    maxWidth: "1100px",
    width: "100%",
    margin: "0 auto",
    alignSelf: "stretch",
    flexShrink: 0,
  },

  // Attachment strip
  attachStrip: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
    marginBottom: "8px",
  },
  attachChip: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "8px",
    padding: "4px 8px",
    fontSize: "12px",
    color: "var(--color-text-muted)",
    maxWidth: "180px",
  },
  attachThumb: {
    width: "20px",
    height: "20px",
    objectFit: "cover",
    borderRadius: "3px",
    flexShrink: 0,
  },
  attachFileIcon: {
    color: "var(--color-text-faint)",
    display: "flex",
    flexShrink: 0,
  },
  attachName: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    flex: 1,
    minWidth: 0,
  },
  attachRemove: {
    background: "none",
    border: "none",
    color: "var(--color-text-faint)",
    cursor: "pointer",
    padding: "2px",
    display: "flex",
    alignItems: "center",
    flexShrink: 0,
  },

  // Dark pill input
  inputWrapper: {
    background: "#1e1e1e",
    border: "1px solid #333333",
    borderRadius: "9999px",
    padding: "8px 12px",
    boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
    transition: "border-color var(--transition), box-shadow var(--transition)",
  },
  inputRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  inputActionBtn: {
    background: "#333333",
    border: "none",
    color: "#ffffff",
    cursor: "pointer",
    padding: "8px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background var(--transition)",
    flexShrink: 0,
  },
  textarea: {
    flex: 1,
    background: "none",
    border: "none",
    color: "#ffffff",
    fontSize: "14px",
    lineHeight: "1.5",
    resize: "none",
    outline: "none",
    minHeight: "24px",
    maxHeight: "150px",
    padding: "2px 0",
    fontFamily: "var(--font)",
  },
  sendBtn: {
    background: "var(--color-primary)",
    border: "none",
    color: "var(--color-primary-text)",
    cursor: "pointer",
    padding: "8px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "opacity var(--transition), transform var(--transition)",
    flexShrink: 0,
  },

  // Attachment dropdown menu
  attachMenu: {
    position: "absolute",
    bottom: "calc(100% + 8px)",
    left: 0,
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "12px",
    boxShadow: "var(--shadow-md)",
    overflow: "hidden",
    zIndex: 50,
    minWidth: "140px",
    animation: "fadeInUp 0.15s ease",
  },
  attachMenuItem: {
    display: "block",
    width: "100%",
    padding: "10px 16px",
    background: "none",
    border: "none",
    textAlign: "left",
    fontSize: "13px",
    color: "var(--color-text)",
    cursor: "pointer",
    transition: "background var(--transition)",
  },

  inputFooter: {
    display: "flex",
    justifyContent: "center",
    marginTop: "10px",
  },
};

// Append inputFooter span style inline via JS (can't target span directly in style object)
s.inputFooter.fontSize = "11px";
const inputFooterSpanStyle = {
  fontSize: "11px",
  color: "var(--color-text-faint)",
};
// We'll style the span inside the JSX via inline style:
// Done above in the component.

const ws = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "60px 20px 40px",
    textAlign: "center",
    minHeight: "60vh",
  },
  logoWrap: {
    marginBottom: "20px",
  },
  title: {
    fontSize: "28px",
    fontWeight: "700",
    letterSpacing: "-0.5px",
    color: "var(--color-text)",
    marginBottom: "10px",
  },
  subtitle: {
    fontSize: "15px",
    color: "var(--color-text-muted)",
    maxWidth: "440px",
    lineHeight: "1.6",
    marginBottom: "28px",
  },
  quickActions: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    justifyContent: "center",
    maxWidth: "520px",
  },
  quickBtn: {
    display: "flex",
    alignItems: "center",
    gap: "7px",
    padding: "9px 16px",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px",
    fontSize: "13px",
    fontWeight: "500",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    transition: "all 0.15s",
    whiteSpace: "nowrap",
  },
  quickIcon: {
    fontSize: "15px",
    lineHeight: 1,
  },
};
