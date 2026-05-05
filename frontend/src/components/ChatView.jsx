/**
 * ChatView — the main chat interface.
 *
 * Props:
 *   course   — { id, name } | null   (null = general chat, no course scoping)
 *   session  — { id, title } | null  (null = auto-create on first message)
 *   onSessionCreated(session) — called when a new session is created
 */

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { streamChat } from "../api.js";
import ChatMessage from "./ChatMessage.jsx";

const PLACEHOLDER = "Ask me anything about your courses…";

export default function ChatView({ course = null, session = null, onSessionCreated }) {
  const { authFetch } = useAuth();
  const [messages, setMessages]   = useState([]);    // { role, content }
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [toolStatus, setToolStatus] = useState(null); // "Searching Canvas…"
  const [streamingText, setStreamingText] = useState("");
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);
  const sessionIdRef = useRef(session?.id ?? null);

  // Scroll to bottom whenever messages or streaming text changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    const newMessages = [...messages, userMsg];

    setMessages(newMessages);
    setInput("");
    setLoading(true);
    setStreamingText("");
    setToolStatus(null);

    try {
      let accumulated = "";

      await streamChat(
        authFetch,
        newMessages,
        {
          sessionId: sessionIdRef.current,
          courseId:  course?.id ?? null,
        },
        (chunk) => {
          accumulated += chunk;
          setStreamingText(accumulated);
        },
        (toolCall) => {
          const labels = {
            get_courses:          "Fetching your courses…",
            get_assignments:      "Loading assignments…",
            get_announcements:    "Checking announcements…",
            search_course_content: "Searching course materials…",
          };
          setToolStatus(labels[toolCall.name] ?? `Calling ${toolCall.name}…`);
        },
      );

      // Commit streamed response to messages
      setMessages(prev => [...prev, { role: "assistant", content: accumulated }]);
      setStreamingText("");
      setToolStatus(null);

    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `Sorry, something went wrong: ${err.message}`,
      }]);
      setStreamingText("");
      setToolStatus(null);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerTitle}>
          {course ? `✦ ${course.name}` : "✦ Lumina"}
        </span>
        {course && (
          <span style={styles.headerSub}>AI tutor · Socratic mode</span>
        )}
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.empty}>
            <p style={styles.emptyTitle}>What are you studying today?</p>
            <p style={styles.emptyHint}>
              {course
                ? `I have access to your ${course.name} course materials.`
                : "Ask me about any of your Canvas courses."}
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <ChatMessage key={i} role={m.role} content={m.content} />
        ))}

        {/* In-progress streaming response */}
        {(streamingText || toolStatus) && (
          <div>
            {toolStatus && !streamingText && (
              <div style={styles.toolStatus}>
                <span style={styles.toolDot} />
                {toolStatus}
              </div>
            )}
            {streamingText && (
              <ChatMessage role="assistant" content={streamingText} isStreaming />
            )}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={styles.inputRow}>
        <textarea
          ref={inputRef}
          style={styles.input}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={PLACEHOLDER}
          rows={1}
          disabled={loading}
        />
        <button
          style={{
            ...styles.sendButton,
            opacity: (!input.trim() || loading) ? 0.4 : 1,
          }}
          onClick={handleSend}
          disabled={!input.trim() || loading}
          aria-label="Send"
        >
          ↑
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    background: "var(--color-bg)",
  },
  header: {
    padding: "16px 20px",
    borderBottom: "1px solid var(--color-border)",
    display: "flex",
    alignItems: "baseline",
    gap: "10px",
  },
  headerTitle: {
    fontSize: "15px",
    fontWeight: "600",
    color: "var(--color-text)",
  },
  headerSub: {
    fontSize: "12px",
    color: "var(--color-text-muted)",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "24px 20px",
    display: "flex",
    flexDirection: "column",
  },
  empty: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    padding: "60px 20px",
  },
  emptyTitle: {
    fontSize: "20px",
    fontWeight: "600",
    color: "var(--color-text)",
    marginBottom: "8px",
  },
  emptyHint: {
    fontSize: "14px",
    color: "var(--color-text-muted)",
  },
  toolStatus: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 16px",
    marginBottom: "8px",
    color: "var(--color-text-muted)",
    fontSize: "13px",
  },
  toolDot: {
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: "var(--color-primary)",
    animation: "pulse 1.2s ease-in-out infinite",
  },
  inputRow: {
    display: "flex",
    gap: "10px",
    padding: "16px 20px",
    borderTop: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    alignItems: "flex-end",
  },
  input: {
    flex: 1,
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "12px",
    padding: "12px 16px",
    color: "var(--color-text)",
    fontSize: "14px",
    resize: "none",
    outline: "none",
    lineHeight: "1.5",
    maxHeight: "120px",
    overflowY: "auto",
  },
  sendButton: {
    width: "40px",
    height: "40px",
    borderRadius: "50%",
    background: "var(--color-primary)",
    color: "#fff",
    border: "none",
    fontSize: "18px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    transition: "opacity 0.15s",
  },
};
