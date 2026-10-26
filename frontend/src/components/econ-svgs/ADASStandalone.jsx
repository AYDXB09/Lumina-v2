/**
 * ADASStandalone — Aggregate Demand / Short-Run & Long-Run Aggregate Supply
 * diagram, standalone (no Phillips curve — see [adas_phillips] ECONGRAPH
 * for that combined version). Pure SVG.
 */
import React from "react";

const W = 420, H = 340;
const PAD = { l: 56, r: 20, t: 24, b: 44 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

const xOf = q => PAD.l + (q / 100) * plotW;
const yOf = p => PAD.t + (1 - p / 100) * plotH;

// AD: downward sloping. SRAS: upward sloping. LRAS: vertical at potential output.
const adAt = q => 90 - 0.7 * q;
const srasAt = q => 15 + 0.65 * q;
const LRAS_Q = 55;

// Equilibrium where AD meets SRAS: solve 90 - 0.7q = 15 + 0.65q → q ≈ 55.6
const EQ_Q = (90 - 15) / (0.7 + 0.65);
const EQ_P = adAt(EQ_Q);

export default function ADASStandalone() {
  return (
    <div style={s.wrap}>
      <svg viewBox={`0 0 ${W} ${H}`} style={s.svg}>
        {/* Axes */}
        <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <line x1={PAD.l} y1={H - PAD.b} x2={W - PAD.r} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <text x={PAD.l - 12} y={PAD.t + 4} textAnchor="end" fontSize="11" fill="var(--color-text-muted)">PL</text>
        <text x={W - PAD.r + 4} y={H - PAD.b + 14} fontSize="11" fill="var(--color-text-muted)">Real GDP</text>

        {/* LRAS (vertical, at potential output) */}
        <line x1={xOf(LRAS_Q)} y1={PAD.t} x2={xOf(LRAS_Q)} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="2" strokeDasharray="6,3" />
        <text x={xOf(LRAS_Q)} y={PAD.t - 6} textAnchor="middle" fontSize="11" fill="var(--color-text-faint)">LRAS</text>
        <text x={xOf(LRAS_Q)} y={H - PAD.b + 14} textAnchor="middle" fontSize="10" fill="var(--color-text-faint)">Yp</text>

        {/* SRAS */}
        <line x1={xOf(0)} y1={yOf(srasAt(0))} x2={xOf(95)} y2={yOf(srasAt(95))} stroke="var(--pill-amber-text)" strokeWidth="2.5" />
        <text x={xOf(90) + 4} y={yOf(srasAt(90))} fontSize="11" fontWeight="600" fill="var(--pill-amber-text)">SRAS</text>

        {/* AD */}
        <line x1={xOf(5)} y1={yOf(adAt(5))} x2={xOf(95)} y2={yOf(adAt(95))} stroke="var(--color-primary)" strokeWidth="2.5" />
        <text x={xOf(90) + 4} y={yOf(adAt(90))} fontSize="11" fontWeight="600" fill="var(--color-primary)">AD</text>

        {/* Equilibrium */}
        <circle cx={xOf(EQ_Q)} cy={yOf(EQ_P)} r="3.5" fill="var(--color-text)" />
        <line x1={xOf(EQ_Q)} y1={yOf(EQ_P)} x2={xOf(EQ_Q)} y2={H - PAD.b} stroke="var(--color-border)" strokeDasharray="3,3" strokeWidth="1" />
        <line x1={PAD.l} y1={yOf(EQ_P)} x2={xOf(EQ_Q)} y2={yOf(EQ_P)} stroke="var(--color-border)" strokeDasharray="3,3" strokeWidth="1" />
        <text x={PAD.l - 12} y={yOf(EQ_P) + 4} textAnchor="end" fontSize="10" fill="var(--color-text-faint)">PL*</text>
      </svg>
      <p style={s.caption}>
        Short-run equilibrium where AD intersects SRAS. LRAS marks potential output (Yp) — the economy shown is at short-run equilibrium slightly beyond potential, illustrating an inflationary gap.
      </p>
    </div>
  );
}

const s = {
  wrap: { display: "flex", flexDirection: "column", gap: "8px" },
  svg: { width: "100%", height: "auto", background: "var(--color-surface)", borderRadius: "10px", border: "1px solid var(--color-border)" },
  caption: { fontSize: "12px", color: "var(--color-text-faint)", margin: 0 },
};
