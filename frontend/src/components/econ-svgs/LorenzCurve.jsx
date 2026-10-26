/**
 * LorenzCurve — cumulative population % vs cumulative income %, with the
 * line of perfect equality and the Gini-coefficient area shaded between
 * the two. Pure SVG.
 */
import React from "react";

const W = 380, H = 380;
const PAD = { l: 56, r: 20, t: 20, b: 44 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

// Sample Lorenz curve points (cumulative % population, cumulative % income)
const POINTS = [
  [0, 0], [20, 5], [40, 14], [60, 28], [80, 50], [100, 100],
];

const xOf = pct => PAD.l + (pct / 100) * plotW;
const yOf = pct => PAD.t + (1 - pct / 100) * plotH;

const lorenzPath = POINTS.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${xOf(x)} ${yOf(y)}`).join(" ");
const equalityPath = `M ${xOf(0)} ${yOf(0)} L ${xOf(100)} ${yOf(100)}`;
const giniAreaPath = `${lorenzPath} L ${xOf(100)} ${yOf(100)} L ${xOf(0)} ${yOf(0)} Z`;

export default function LorenzCurve() {
  return (
    <div style={s.wrap}>
      <svg viewBox={`0 0 ${W} ${H}`} style={s.svg}>
        {/* Axes */}
        <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <line x1={PAD.l} y1={H - PAD.b} x2={W - PAD.r} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <text x={PAD.l - 12} y={PAD.t + 4} textAnchor="end" fontSize="10" fill="var(--color-text-muted)">
          Cumulative % Income
        </text>
        <text x={W - PAD.r} y={H - PAD.b + 28} textAnchor="end" fontSize="10" fill="var(--color-text-muted)">
          Cumulative % Population
        </text>

        {/* Gini area (between line of equality and Lorenz curve) */}
        <path d={giniAreaPath} fill="var(--pill-amber-text)" opacity="0.18" />

        {/* Line of perfect equality */}
        <path d={equalityPath} stroke="var(--color-border)" strokeWidth="1.5" strokeDasharray="4,4" fill="none" />
        <text x={xOf(70)} y={yOf(70) - 6} fontSize="10" fill="var(--color-text-faint)" transform={`rotate(-38 ${xOf(70)} ${yOf(70)})`}>
          Line of perfect equality
        </text>

        {/* Lorenz curve */}
        <path d={lorenzPath} stroke="var(--color-primary)" strokeWidth="2.5" fill="none" />
        {POINTS.map(([x, y], i) => (
          <circle key={i} cx={xOf(x)} cy={yOf(y)} r="2.5" fill="var(--color-primary)" />
        ))}
        <text x={xOf(55)} y={yOf(20) + 16} fontSize="11" fontWeight="600" fill="var(--color-primary)">
          Lorenz curve
        </text>

        {/* Gini label */}
        <text x={xOf(38)} y={yOf(38) - 4} fontSize="11" fontWeight="600" fill="var(--pill-amber-text)">
          Gini area
        </text>
      </svg>
      <p style={s.caption}>
        Gini coefficient = (area between the line of equality and the Lorenz curve) ÷ (total area under the line of equality). Closer to 0 = more equal; closer to 1 = more unequal.
      </p>
    </div>
  );
}

const s = {
  wrap: { display: "flex", flexDirection: "column", gap: "8px" },
  svg: { width: "100%", height: "auto", background: "var(--color-surface)", borderRadius: "10px", border: "1px solid var(--color-border)" },
  caption: { fontSize: "12px", color: "var(--color-text-faint)", margin: 0 },
};
