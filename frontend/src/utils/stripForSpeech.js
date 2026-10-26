/**
 * stripForSpeech — strips Markdown/LaTeX/widget-marker syntax from AI
 * message content so text-to-speech reads clean prose instead of literal
 * symbols ("asterisk asterisk bold asterisk asterisk").
 *
 * Ported from v1's stripMarkdown() (App.jsx), extended for v2-only syntax:
 * interactive widget markers ([ECONGRAPH: id] etc.) and LaTeX delimiters.
 */

const THINK_RE = /<think>[\s\S]*?<\/think>/gi;
const WIDGET_MARKER_RE = /\[(ECONGRAPH|DESMOS|PHET|KINETIC|LIFESCIENCE|EXPLORABLES|ECONSVG):\s*[^\]]+\]/g;

export function stripForSpeech(text) {
  if (!text) return "";
  return text
    .replace(THINK_RE, "")
    .replace(WIDGET_MARKER_RE, "") // widget markers are visual, nothing to speak
    .replace(/#{1,6}\s/g, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/~~(.+?)~~/g, "$1")
    .replace(/`{1,3}[^`]*`{1,3}/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^\s*[-*>|]\s*/gm, "")
    .replace(/\$\$[\s\S]*?\$\$/g, " formula ")
    .replace(/\\\[[\s\S]*?\\\]/g, " formula ")
    .replace(/\$[^$]*\$/g, " formula ")
    .replace(/\\\([^)]*\\\)/g, " formula ")
    .replace(/\n{2,}/g, ". ")
    .replace(/\n/g, " ")
    .trim();
}

/** Split cleaned text into sentences for one-at-a-time TTS playback. */
export function splitSentences(text) {
  const sentences = text.match(/[^.!?]+[.!?]+/g);
  return sentences && sentences.length ? sentences : [text];
}
