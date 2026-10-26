/**
 * PriceCeilingFloor — labeled supply/demand diagram showing a price ceiling
 * (below equilibrium → shortage) and a price floor (above equilibrium → surplus).
 * Pure SVG, no external dependencies.
 */
import React, { useState } from "react";

const W = 460, H = 340;
const PAD = { l: 56, r: 20, t: 20, b: 44 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

// Supply: P = 10 + Q ; Demand: P = 90 - Q  → equilibrium at Q=40, P=50
const supplyAt = q => 10 + q;
const demandAt = q => 90 - q;
const xOf = q => PAD.l + (q / 100) * plotW;
const yOf = p => PAD.t + (1 - p / 100) * plotH;

const EQ_Q = 40, EQ_P = 50;
const CEILING_P = 30;   // below equilibrium
const FLOOR_P = 70;     // above equilibrium

export default function PriceCeilingFloor() {
  const [mode, setMode] = useState("ceiling");

  const targetP = mode === "ceiling" ? CEILING_P : FLOOR_P;
  // At the controlled price, read off Qs (supplied) and Qd (demanded)
  const qsAtTarget = targetP - 10;   // from supply: P = 10 + Q
  const qdAtTarget = 90 - targetP;   // from demand: P = 90 - Q
  const shortageOrSurplus = mode === "ceiling"
    ? { label: "Shortage", from: qsAtTarget, to: qdAtTarget }
    : { label: "Surplus", from: qdAtTarget, to: qsAtTarget };

  return (
    <div style={s.wrap}>
      <div style={s.toggleRow}>
        <button style={{ ...s.toggle, ...(mode === "ceiling" ? s.toggleActive : {}) }} onClick={() => setMode("ceiling")}>
          Price Ceiling
        </button>
        <button style={{ ...s.toggle, ...(mode === "floor" ? s.toggleActive : {}) }} onClick={() => setMode("floor")}>
          Price Floor
        </button>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={s.svg}>
        {/* Axes */}
        <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <line x1={PAD.l} y1={H - PAD.b} x2={W - PAD.r} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <text x={PAD.l - 12} y={PAD.t + 4} textAnchor="end" fontSize="11" fill="var(--color-text-muted)">P</text>
        <text x={W - PAD.r + 4} y={H - PAD.b + 14} fontSize="11" fill="var(--color-text-muted)">Q</text>

        {/* Shortage/surplus shaded region */}
        <line
          x1={xOf(shortageOrSurplus.from)} y1={yOf(targetP)}
          x2={xOf(shortageOrSurplus.to)} y2={yOf(targetP)}
          stroke="var(--pill-amber-text)" strokeWidth="6" strokeLinecap="round" opacity="0.55"
        />

        {/* Supply curve */}
        <line x1={xOf(0)} y1={yOf(supplyAt(0))} x2={xOf(80)} y2={yOf(supplyAt(80))} stroke="var(--color-primary)" strokeWidth="2" />
        <text x={xOf(80) + 4} y={yOf(supplyAt(80))} fontSize="11" fill="var(--color-primary)">S</text>

        {/* Demand curve */}
        <line x1={xOf(0)} y1={yOf(demandAt(0))} x2={xOf(80)} y2={yOf(demandAt(80))} stroke="var(--pill-red-text)" strokeWidth="2" />
        <text x={xOf(80) + 4} y={yOf(demandAt(80))} fontSize="11" fill="var(--pill-red-text)">D</text>

        {/* Equilibrium */}
        <circle cx={xOf(EQ_Q)} cy={yOf(EQ_P)} r="3.5" fill="var(--color-text)" />
        <line x1={xOf(EQ_Q)} y1={yOf(EQ_P)} x2={xOf(EQ_Q)} y2={H - PAD.b} stroke="var(--color-border)" strokeDasharray="3,3" strokeWidth="1" />
        <line x1={PAD.l} y1={yOf(EQ_P)} x2={xOf(EQ_Q)} y2={yOf(EQ_P)} stroke="var(--color-border)" strokeDasharray="3,3" strokeWidth="1" />
        <text x={PAD.l - 12} y={yOf(EQ_P) + 4} textAnchor="end" fontSize="10" fill="var(--color-text-faint)">Pe</text>
        <text x={xOf(EQ_Q)} y={H - PAD.b + 14} textAnchor="middle" fontSize="10" fill="var(--color-text-faint)">Qe</text>

        {/* Controlled price line */}
        <line x1={PAD.l} y1={yOf(targetP)} x2={W - PAD.r} y2={yOf(targetP)} stroke="var(--color-text)" strokeWidth="1.5" strokeDasharray="5,3" />
        <text x={PAD.l - 12} y={yOf(targetP) + 4} textAnchor="end" fontSize="10" fontWeight="600" fill="var(--color-text)">
          {mode === "ceiling" ? "Pceiling" : "Pfloor"}
        </text>

        {/* Label */}
        <text x={(xOf(shortageOrSurplus.from) + xOf(shortageOrSurplus.to)) / 2} y={yOf(targetP) - 8} textAnchor="middle" fontSize="11" fontWeight="600" fill="var(--pill-amber-text)">
          {shortageOrSurplus.label}
        </text>
      </svg>
      <p style={s.caption}>
        {mode === "ceiling"
          ? "Price ceiling set below equilibrium → quantity demanded exceeds quantity supplied → shortage."
          : "Price floor set above equilibrium → quantity supplied exceeds quantity demanded → surplus."}
      </p>
    </div>
  );
}

const s = {
  wrap: { display: "flex", flexDirection: "column", gap: "8px" },
  toggleRow: { display: "flex", gap: "6px" },
  toggle: {
    fontSize: "11px", padding: "4px 10px", borderRadius: "6px",
    background: "var(--color-surface)", border: "1px solid var(--color-border)",
    color: "var(--color-text-muted)", cursor: "pointer",
  },
  toggleActive: {
    background: "var(--color-primary)", color: "var(--color-primary-text)", borderColor: "var(--color-primary)",
  },
  svg: { width: "100%", height: "auto", background: "var(--color-surface)", borderRadius: "10px", border: "1px solid var(--color-border)" },
  caption: { fontSize: "12px", color: "var(--color-text-faint)", margin: 0 },
};
