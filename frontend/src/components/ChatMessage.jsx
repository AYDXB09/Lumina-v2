/**
 * ChatMessage — renders a single message bubble.
 * Supports markdown + LaTeX (via marked + KaTeX via CSS).
 *
 * For now: lightweight — just preserves line breaks and code blocks.
 * Full markdown rendering can be added with `marked` later.
 */

import React from "react";

export default function ChatMessage({ role, content, isStreaming = false }) {
  const isUser = role === "user";

  return (
    <div style={{ ...styles.row, justifyContent: isUser ? "flex-end" : "flex-start" }}>
      {!isUser && <div style={styles.avatar}>✦</div>}
      <div style={{
        ...styles.bubble,
        ...(isUser ? styles.userBubble : styles.aiBubble),
      }}>
        <MessageContent content={content} isStreaming={isStreaming} />
      </div>
    </div>
  );
}

function MessageContent({ content, isStreaming }) {
  // Very lightweight rendering — split on code blocks and newlines
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div style={styles.content}>
      {parts.map((part, i) => {
        if (part.startsWith("```")) {
          const lines = part.split("\n");
          const lang = lines[0].replace("```", "").trim();
          const code = lines.slice(1, -1).join("\n");
          return (
            <pre key={i} style={styles.code}>
              <code>{code}</code>
            </pre>
          );
        }
        // Render inline with newlines
        return (
          <span key={i} style={{ whiteSpace: "pre-wrap" }}>
            {part}
          </span>
        );
      })}
      {isStreaming && <span style={styles.cursor}>▊</span>}
    </div>
  );
}

const styles = {
  row: {
    display: "flex",
    gap: "10px",
    marginBottom: "16px",
    alignItems: "flex-start",
  },
  avatar: {
    flexShrink: 0,
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    background: "var(--color-primary)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "12px",
    color: "#fff",
    marginTop: "2px",
  },
  bubble: {
    maxWidth: "75%",
    padding: "12px 16px",
    borderRadius: "16px",
    fontSize: "14px",
    lineHeight: "1.6",
  },
  userBubble: {
    background: "var(--color-primary)",
    color: "#fff",
    borderBottomRightRadius: "4px",
  },
  aiBubble: {
    background: "var(--color-surface)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderBottomLeftRadius: "4px",
  },
  content: {
    display: "block",
  },
  code: {
    background: "var(--color-surface-2)",
    border: "1px solid var(--color-border)",
    borderRadius: "6px",
    padding: "10px 14px",
    fontSize: "12px",
    overflowX: "auto",
    margin: "8px 0",
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    whiteSpace: "pre",
  },
  cursor: {
    animation: "blink 1s step-end infinite",
    color: "var(--color-primary)",
  },
};
