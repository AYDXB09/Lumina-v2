/**
 * ChatMessage — renders a single message bubble.
 *
 * AI messages: full Markdown + LaTeX math (KaTeX).
 * User messages: plain text with line-break preservation.
 *
 * Markdown features:
 *   **bold**, *italic*, ~~strike~~, `code`, ```blocks```,
 *   # headings, - / * bullet lists, 1. ordered lists,
 *   > blockquotes, --- horizontal rule, | tables |,
 *   [link text](url) — rendered as styled non-hyperlink spans to keep students on Lumina.
 *
 * Math:
 *   Inline:  $...$  or  \(...\)
 *   Block:   $$...$$  or  \[...\]
 */

import React, { useMemo } from "react";
import katex from "katex";
import "katex/contrib/mhchem"; // registers \ce{...} for chemical formulas/equations
import { marked } from "marked";
import DOMPurify from "dompurify";
import LuminaLogo from "./LuminaLogo.jsx";
import InteractiveWidget from "./InteractiveWidget.jsx";
import EconSVGWidget from "./EconSVGWidget.jsx";
import { useSettings } from "../contexts/SettingsContext.jsx";
import { useSpeech } from "../hooks/useSpeech.js";

// ---- Speak button icons ----
const SpeakerIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M15.54 8.46a5 5 0 010 7.07" />
    <path d="M19.07 4.93a10 10 0 010 14.14" />
  </svg>
);
const SpeakerStopIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <line x1="23" y1="9" x2="17" y2="15" />
    <line x1="17" y1="9" x2="23" y2="15" />
  </svg>
);

// ---- Configure marked ----
marked.setOptions({ breaks: true, gfm: true });

// ---- Math pre-processing helpers ----
// Replace $$...$$ and $...$ before passing to marked so they survive HTML escaping.

const BLOCK_MATH_RE  = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g;
const INLINE_MATH_RE = /\$([^$\n]+?)\$|\\\((.+?)\\\)/g;

function renderMath(tex, displayMode) {
  try {
    return katex.renderToString(tex, {
      displayMode,
      throwOnError: false,
      output: "html",
    });
  } catch {
    return `<code>${tex}</code>`;
  }
}

// Math is rendered to real HTML (including inline <svg> for KaTeX constructs
// like \vec{}) — but that HTML must never be handed to marked() directly.
// marked's tokenizer (especially the table-cell splitter) re-parses whatever
// text it's given, and re-parsing already-rendered SVG markup as markdown
// corrupts it — an SVG <path>'s "d" attribute can end up dumped as visible
// text. This only showed up inside tables, not prose, because marked's table
// parser is far more aggressive about re-tokenizing cell content.
//
// Fix: replace math with an inert placeholder token (letters/digits only —
// nothing marked could ever treat as markdown syntax) before marked() runs,
// then swap the real KaTeX HTML back in afterwards, once marked is done.
function processMath(raw) {
  const rendered = new Map();
  let i = 0;
  const placeholder = (html) => {
    const token = `LUMINAMATHTOKEN${i++}ENDTOKEN`;
    rendered.set(token, html);
    return token;
  };

  // Block math first ($$...$$), then inline ($...$)
  let out = raw.replace(BLOCK_MATH_RE, (_, m1, m2) => {
    const tex = (m1 ?? m2).trim();
    return placeholder(`<span class="math-block">${renderMath(tex, true)}</span>`);
  });
  out = out.replace(INLINE_MATH_RE, (_, m1, m2) => {
    const tex = (m1 ?? m2).trim();
    return placeholder(`<span class="math-inline">${renderMath(tex, false)}</span>`);
  });
  return { text: out, rendered };
}

function restoreMath(html, rendered) {
  let out = html;
  for (const [token, mathHtml] of rendered) {
    out = out.replaceAll(token, mathHtml);
  }
  return out;
}

// ---- Strip raw think tags (K2 / DeepSeek style) ----
function stripThinking(text) {
  return text
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<think>[\s\S]*$/gi, "")
    .trim();
}

// ---- Custom marked renderer: open links in same page as text (no nav) ----
const renderer = new marked.Renderer();
renderer.link = ({ href, title, text }) => {
  // Render links as styled inline text to prevent navigation away from Lumina
  return `<span class="md-link" title="${href}" data-href="${href}">${text}</span>`;
};
renderer.image = ({ href, title, text }) => {
  return `<span class="md-link" title="${href}">[Image: ${text || title || href}]</span>`;
};

// ---- Main render pipeline ----
function renderMarkdown(raw) {
  if (!raw) return "";
  const stripped = stripThinking(raw);
  const { text: withPlaceholders, rendered } = processMath(stripped);
  const parsedHtml = marked.parse(withPlaceholders, { renderer });
  const html = restoreMath(parsedHtml, rendered);
  return DOMPurify.sanitize(html, {
    ADD_TAGS: ["span"],
    ADD_ATTR: ["class", "style", "data-href", "title", "aria-hidden"],
    FORCE_BODY: false,
  });
}

// ------------------------------------------------------------------ //
// Interactive widget marker parser                                    //
// Splits AI content into text segments and [MARKER: id] segments.    //
// Supports: ECONGRAPH, DESMOS, PHET, KINETIC, LIFESCIENCE, EXPLORABLES //
// (iframe-based, see InteractiveWidget.jsx) and ECONSVG (native React //
// SVG, see EconSVGWidget.jsx — no iframe needed for static diagrams). //
// ------------------------------------------------------------------ //

const WIDGET_RE = /\[(ECONGRAPH|DESMOS|PHET|KINETIC|LIFESCIENCE|EXPLORABLES|ECONSVG):\s*([^\]]+)\]/g;

function parseSegments(content) {
  const segments = [];
  let last = 0;
  WIDGET_RE.lastIndex = 0;
  let m;
  while ((m = WIDGET_RE.exec(content)) !== null) {
    if (m.index > last) {
      segments.push({ type: "text", content: content.slice(last, m.index) });
    }
    segments.push({ type: "widget", marker: m[1], id: m[2].trim() });
    last = m.index + m[0].length;
  }
  if (last < content.length) {
    segments.push({ type: "text", content: content.slice(last) });
  }
  return segments;
}

// ---- Component ----
export default function ChatMessage({ id, role, content, isStreaming = false, images = null }) {
  const isUser = role === "user";
  const { settings } = useSettings();
  const { speakingId, speak, supported: speechSupported } = useSpeech();
  const isSpeakingThis = speakingId === id;

  const segments = useMemo(() => {
    if (isUser) return null;
    return parseSegments(content);
  }, [content, isUser]);

  return (
    <div className={`msg-row ${isUser ? "user-row" : "ai-row"}`}>
      {!isUser && (
        <div className="msg-avatar">
          <LuminaLogo size={18} color="#ffffff" />
        </div>
      )}

      <div
        className={`msg-bubble ${isUser ? "user" : "ai"}`}
        style={{
          fontFamily: "var(--chat-font)",
          fontSize:   "var(--chat-font-size)",
        }}
      >
        {isUser ? (
          <>
            {/* Pasted / attached images */}
            {images?.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: content ? 8 : 0 }}>
                {images.map((img, i) => (
                  <img
                    key={i}
                    src={`data:${img.mimeType};base64,${img.base64}`}
                    alt="pasted screenshot"
                    style={{
                      maxWidth: 320,
                      maxHeight: 220,
                      borderRadius: 8,
                      objectFit: "contain",
                      border: "1px solid rgba(255,255,255,0.12)",
                      background: "#0f172a",
                    }}
                  />
                ))}
              </div>
            )}
            {content && <span style={{ whiteSpace: "pre-wrap" }}>{content}</span>}
          </>
        ) : (
          <>
            {segments?.map((seg, i) =>
              seg.type === "widget" ? (
                seg.marker === "ECONSVG" ? (
                  <EconSVGWidget key={i} id={seg.id} />
                ) : (
                  <InteractiveWidget key={i} marker={seg.marker} id={seg.id} />
                )
              ) : (
                <div
                  key={i}
                  className="md-body"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(seg.content) }}
                />
              )
            )}
            {isStreaming && <span className="msg-cursor">▊</span>}
            {!isStreaming && content && speechSupported && (
              <button
                className={`msg-speak-btn ${isSpeakingThis ? "speaking" : ""}`}
                onClick={() => speak(id, content)}
                title={isSpeakingThis ? "Stop reading aloud" : "Read aloud"}
                aria-label={isSpeakingThis ? "Stop reading aloud" : "Read aloud"}
              >
                {isSpeakingThis ? <SpeakerStopIcon /> : <SpeakerIcon />}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
