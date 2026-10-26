/**
 * LegalPage — renders the Terms of Service (/terms) and Privacy Policy (/privacy).
 *
 * Public: App.jsx routes to this before the auth gate (like /reset-password), so
 * the links on the sign-up form work for people who don't have an account yet.
 *
 * The text lives in src/legal/*.md, which must stay identical to docs/TERMS.md
 * and docs/PRIVACY.md (the copies GitHub readers see). It is bundled with the app
 * rather than imported from docs/ because the Docker build only copies frontend/.
 */

import React, { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import LuminaLogo from "./LuminaLogo.jsx";
import termsMd from "../legal/terms.md?raw";
import privacyMd from "../legal/privacy.md?raw";

const PAGES = {
  terms:   { title: "Terms of Service", md: termsMd,   other: { href: "/privacy", label: "Privacy Policy" } },
  privacy: { title: "Privacy Policy",   md: privacyMd, other: { href: "/terms",   label: "Terms of Service" } },
};

// GitHub-style heading slug, so in-document links like (#7-students-and-age) work.
function slug(text) {
  return text
    .replace(/<[^>]+>/g, "")
    .trim()
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-");
}

function render(md) {
  // The markdown links to its sibling by file name (right for GitHub); in the app
  // those must point at the in-app routes instead.
  const localised = md
    .replace(/\]\(PRIVACY\.md\)/g, "](/privacy)")
    .replace(/\]\(TERMS\.md\)/g, "](/terms)");
  // Explicit options: ChatMessage calls marked.setOptions({ breaks: true }) globally.
  const html = marked.parse(localised, { gfm: true, breaks: false })
    .replace(/<h([23])>([\s\S]*?)<\/h\1>/g, (_, level, inner) => `<h${level} id="${slug(inner)}">${inner}</h${level}>`);
  return DOMPurify.sanitize(html);
}

export default function LegalPage({ page }) {
  const { title, md, other } = PAGES[page];
  const html = useMemo(() => render(md), [md]);

  return (
    <div className="legal-root">
      <style>{css}</style>
      <header className="legal-bar">
        <a href="/" className="legal-brand" aria-label="Back to Lumina">
          <LuminaLogo size={28} />
          <span>Lumina</span>
        </a>
        <nav className="legal-nav">
          <a href={other.href}>{other.label}</a>
          <a href="/">← Back to the app</a>
        </nav>
      </header>
      <main className="legal-main" aria-label={title}>
        <article className="legal-doc" dangerouslySetInnerHTML={{ __html: html }} />
      </main>
    </div>
  );
}

const css = `
.legal-root { min-height: 100vh; background: var(--color-bg); color: var(--color-text); overflow-y: auto; height: 100vh; }
.legal-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 14px 24px; background: var(--color-surface); border-bottom: 1px solid var(--color-border);
  position: sticky; top: 0; z-index: 5; flex-wrap: wrap; }
.legal-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 17px;
  color: var(--color-text); text-decoration: none; }
.legal-nav { display: flex; gap: 20px; font-size: 14px; }
.legal-nav a { color: var(--color-text); font-weight: 600; text-decoration: underline; text-underline-offset: 3px; }
.legal-main { padding: 32px 24px 80px; }
.legal-doc { max-width: 780px; margin: 0 auto; background: var(--color-surface);
  border: 1px solid var(--color-border); border-radius: var(--radius, 12px); padding: 36px 40px;
  font-size: 15px; line-height: 1.65; }
.legal-doc h1 { font-size: 28px; margin: 0 0 4px; }
.legal-doc h2 { font-size: 19px; margin: 32px 0 8px; padding-top: 4px; scroll-margin-top: 80px; }
.legal-doc p, .legal-doc ul, .legal-doc ol { margin: 10px 0; }
.legal-doc ul, .legal-doc ol { padding-left: 22px; }
.legal-doc li { margin: 4px 0; }
.legal-doc a { color: var(--color-text); font-weight: 600; text-decoration: underline; text-underline-offset: 2px; }
.legal-doc code { background: var(--color-surface-2); padding: 1px 6px; border-radius: 5px; font-size: 13px; }
.legal-doc blockquote { margin: 16px 0; padding: 12px 16px; background: var(--color-surface-2);
  border-left: 4px solid var(--color-primary); border-radius: 6px; }
.legal-doc blockquote p { margin: 0; }
.legal-doc table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; display: block; overflow-x: auto; }
.legal-doc th, .legal-doc td { text-align: left; vertical-align: top; padding: 9px 12px; border: 1px solid var(--color-border); }
.legal-doc th { background: var(--color-surface-2); font-weight: 600; }
@media (max-width: 640px) {
  .legal-bar { padding: 12px 16px; }
  .legal-main { padding: 16px 12px 60px; }
  .legal-doc { padding: 22px 18px; font-size: 14.5px; }
}
`;
