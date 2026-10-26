/**
 * useSpeech — text-to-speech playback, one message at a time, shared across
 * every ChatMessage instance.
 *
 * Ported from v1's speakMessage() (App.jsx) — same voice-preference cascade
 * (prefer natural/premium voices, fall back to any local English voice) and
 * sentence-by-sentence playback (long responses don't feel like one
 * unbroken monologue, and can be interrupted cleanly).
 *
 * Module-level singleton state, not per-component state: window.speechSynthesis
 * is a single global instance, so if useSpeech() held state per ChatMessage,
 * starting playback on message B wouldn't reset message A's "speaking" icon
 * even though A's actual audio does stop (cancel() is also global). A tiny
 * subscriber pattern keeps every mounted ChatMessage in sync without needing
 * a Context provider higher up the tree.
 *
 * Browser support caveat: Web Speech API (SpeechSynthesis) works reliably
 * on Chrome/desktop; support is inconsistent on Safari/iOS. Not something
 * this hook can work around — flag to the user if it silently does nothing.
 */

import { useState, useEffect, useCallback } from "react";
import { stripForSpeech, splitSentences } from "../utils/stripForSpeech.js";

let speakingId = null;
let cancelled = false;
const listeners = new Set();

function setSpeakingId(id) {
  speakingId = id;
  listeners.forEach(fn => fn(id));
}

function pickVoice() {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find(v => v.name.includes("Online (Natural)") && v.lang.startsWith("en")) ||
    voices.find(v => (v.name.includes("Google") || v.name.includes("Premium")) && v.lang.startsWith("en")) ||
    voices.find(v => v.lang.startsWith("en") && v.localService) ||
    voices.find(v => v.lang.startsWith("en")) ||
    null
  );
}

function stopSpeaking() {
  cancelled = true;
  window.speechSynthesis.cancel();
  setSpeakingId(null);
}

function startSpeaking(id, rawText) {
  if (speakingId === id) {
    stopSpeaking();
    return;
  }
  window.speechSynthesis.cancel();
  cancelled = false;

  const text = stripForSpeech(rawText);
  if (!text) return;

  const sentences = splitSentences(text);
  let i = 0;

  const speakNext = () => {
    if (cancelled || i >= sentences.length) {
      setSpeakingId(null);
      return;
    }
    const sentence = sentences[i++].trim();
    if (!sentence) { speakNext(); return; }

    const utt = new SpeechSynthesisUtterance(sentence);
    utt.rate = 1.05;
    utt.pitch = 1.0;
    const voice = pickVoice();
    if (voice) utt.voice = voice;
    utt.onend = speakNext;
    utt.onerror = () => setSpeakingId(null);
    window.speechSynthesis.speak(utt);
  };

  setSpeakingId(id);
  if (window.speechSynthesis.getVoices().length === 0) {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.onvoiceschanged = null;
      speakNext();
    };
  } else {
    speakNext();
  }
}

export function useSpeech() {
  const [id, setId] = useState(speakingId);

  useEffect(() => {
    listeners.add(setId);
    return () => listeners.delete(setId);
  }, []);

  const speak = useCallback((messageId, rawText) => startSpeaking(messageId, rawText), []);
  const stop = useCallback(() => stopSpeaking(), []);

  return {
    speakingId: id,
    speak,
    stop,
    supported: typeof window !== "undefined" && "speechSynthesis" in window,
  };
}
