/**
 * SettingsContext — persists user preferences in localStorage.
 *
 * Settings:
 *   emojisEnabled          bool   — allow AI to use emojis in responses
 *   fullCanvasContext       bool   — inject full Canvas assignments into system prompt
 *   fontFamily             string — 'inter' | 'computer-modern' | 'system'
 *   fontSize               string — 'sm' | 'md' | 'lg'
 *   panelFontSize          string — 'sm' | 'md' | 'lg'  (assignments panel text)
 *   colorTheme             string — 'lumina' | 'dwight'
 *   showExtracurriculars   bool   — show extra-curricular courses in sidebar
 *   calendarFetchWindow    string — '1day'|'1week'|'2weeks'|'1month'|'3months'|'1year'
 *   calendarSyncFrequency  string — 'query'|'login'|'daily'|'weekly'|'monthly'
 */

import React, { createContext, useContext, useState, useEffect } from "react";

const STORAGE_KEY = "lumina-settings";

const DEFAULTS = {
  emojisEnabled:           false,
  fullCanvasContext:        true,
  fontFamily:               "computer-modern",
  fontSize:                 "md",
  panelFontSize:            "md",   // md = 14px (2 notches up from old 12px default)
  colorTheme:               "dwight",
  showExtracurriculars:     false,
  calendarFetchWindow:      "1week",
  calendarSyncFrequency:    "query",
};

const FONT_MAP = {
  "inter":           '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  "computer-modern": '"Computer Modern", "CMU Serif", Georgia, serif',
  "system":          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const SIZE_MAP = {
  sm: "13px",
  md: "15px",
  lg: "17px",
};

// Assignments / right-panel font sizes (sm=12, md=14, lg=16)
const PANEL_SIZE_MAP = {
  sm: "12px",
  md: "14px",
  lg: "16px",
};

// Lumina golden theme (default)
const LUMINA_THEME = {
  "--color-primary":      "#f5c010",
  "--color-primary-hover":"#dea80b",
  "--color-primary-glow": "rgba(245, 192, 16, 0.22)",
  "--color-primary-text": "#111111",
};

// Dwight navy theme
const DWIGHT_THEME = {
  "--color-primary":      "#13234B",
  "--color-primary-hover":"#25355B",
  "--color-primary-glow": "rgba(19, 35, 75, 0.18)",
  "--color-primary-text": "#ffffff",
};

function applyTheme(theme) {
  const root = document.documentElement;
  const vars = theme === "dwight" ? DWIGHT_THEME : LUMINA_THEME;
  Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : { ...DEFAULTS };
  } catch {
    return { ...DEFAULTS };
  }
}

function save(settings) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch {}
}

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(load);

  // Apply CSS variables whenever settings change
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--chat-font",       FONT_MAP[settings.fontFamily]    ?? FONT_MAP["inter"]);
    root.style.setProperty("--chat-font-size",   SIZE_MAP[settings.fontSize]      ?? SIZE_MAP["md"]);
    root.style.setProperty("--panel-font-size",  PANEL_SIZE_MAP[settings.panelFontSize] ?? PANEL_SIZE_MAP["md"]);
    applyTheme(settings.colorTheme);
    save(settings);
  }, [settings]);

  function update(patch) {
    setSettings(prev => ({ ...prev, ...patch }));
  }

  return (
    <SettingsContext.Provider value={{ settings, update }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be inside SettingsProvider");
  return ctx;
}
