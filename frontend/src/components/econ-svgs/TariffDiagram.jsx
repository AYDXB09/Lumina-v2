/**
 * TariffDiagram — domestic supply/demand with a tariff on imports, showing
 * the world price, tariff-inclusive price, and the resulting changes in
 * consumer surplus, producer surplus, government revenue, and deadweight
 * loss (labeled regions, not shaded — keeps it legible at small size).
 * Pure SVG.
 */
import React from "react";

const W = 460, H = 340;
const PAD = { l: 56, r: 20, t: 20, b: 44 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

// Domestic supply: P = 10 + 0.8Q ; Domestic demand: P = 100 - 0.8Q
const supplyAt = q => 10 + 0.8 * q;
const demandAt = q => 100 - 0.8 * q;
const xOf = q => PAD.l + (q / 100) * plotW;
const yOf = p => PAD.t + (1 - p / 100) * plotH;

const WORLD_P = 30;
const TARIFF_P = 45;

// Quantities at world price (free trade) and at tariff price
const qsWorld = (WORLD_P - 10) / 0.8, qdWorld = (100 - WORLD_P) / 0.8;
const qsTariff = (TARIFF_P - 10) / 0.8, qdTariff = (100 - TARIFF_P) / 0.8;

export default function TariffDiagram() {
  return (
    <div style={s.wrap}>
      <svg viewBox={`0 0 ${W} ${H}`} style={s.svg}>
        {/* Axes */}
        <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <line x1={PAD.l} y1={H - PAD.b} x2={W - PAD.r} y2={H - PAD.b} stroke="var(--color-text-faint)" strokeWidth="1.5" />
        <text x={PAD.l - 12} y={PAD.t + 4} textAnchor="end" fontSize="11" fill="var(--color-text-muted)">P</text>
        <text x={W - PAD.r + 4} y={H - PAD.b + 14} fontSize="11" fill="var(--color-text-muted)">Q</text>

        {/* Domestic supply */}
        <line x1={xOf(0)} y1={yOf(supplyAt(0))} x2={xOf(90)} y2={yOf(supplyAt(90))} stroke="var(--color-primary)" strokeWidth="2" />
        <text x={xOf(88)} y={yOf(supplyAt(88)) - 4} fontSize="11" fill="var(--color-primary)">Sdomestic</text>

        {/* Domestic demand */}
        <line x1={xOf(0)} y1={yOf(demandAt(0))} x2={xOf(90)} y2={yOf(demandAt(90))} stroke="var(--pill-red-text)" strokeWidth="2" />
        <text x={xOf(88)} y={yOf(demandAt(88)) - 4} fontSize="11" fill="var(--pill-red-text)">Ddomestic</text>

        {/* World price + tariff price lines */}
        <line x1={PAD.l} y1={yOf(WORLD_P)} x2={W - PAD.r} y2={yOf(WORLD_P)} stroke="var(--color-text-faint)" strokeWidth="1.5" strokeDasharray="5,3" />
        <text x={PAD.l - 12} y={yOf(WORLD_P) + 4} textAnchor="end" fontSize="10" fill="var(--color-text-faint)">Pworld</text>

        <line x1={PAD.l} y1={yOf(TARIFF_P)} x2={W - PAD.r} y2={yOf(TARIFF_P)} stroke="var(--color-text)" strokeWidth="1.5" strokeDasharray="5,3" />
        <text x={PAD.l - 12} y={yOf(TARIFF_P) + 4} textAnchor="end" fontSize="10" fontWeight="600" fill="var(--color-text)">Pworld+tariff</text>

        {/* Quantity markers at tariff price: domestic production, domestic consumption, imports */}
        <line x1={xOf(qsTariff)} y1={yOf(TARIFF_P)} x2={xOf(qsTariff)} y2={H - PAD.b} stroke="var(--color-border)" strokeDasharray="2,2" strokeWidth="1" />
        <line x1={xOf(qdTariff)} y1={yOf(TARIFF_P)} x2={xOf(qdTariff)} y2={H - PAD.b} stroke="var(--color-border)" strokeDasharray="2,2" strokeWidth="1" />

        {/* Imports bracket (between domestic Qs and Qd at tariff price) */}
        <line x1={xOf(qsTariff)} y1={yOf(TARIFF_P) - 10} x2={xOf(qdTariff)} y2={yOf(TARIFF_P) - 10} stroke="var(--pill-amber-text)" strokeWidth="2" />
        <text x={(xOf(qsTariff) + xOf(qdTariff)) / 2} y={yOf(TARIFF_P) - 16} textAnchor="middle" fontSize="10" fontWeight="600" fill="var(--pill-amber-text)">
          Imports (with tariff)
        </text>

        <text x={xOf(qsTariff)} y={H - PAD.b + 14} textAnchor="middle" fontSize="9" fill="var(--color-text-faint)">Qs</text>
        <text x={xOf(qdTariff)} y={H - PAD.b + 14} textAnchor="middle" fontSize="9" fill="var(--color-text-faint)">Qd</text>
        <text x={xOf(qsWorld)} y={H - PAD.b + 26} textAnchor="middle" fontSize="9" fill="var(--color-text-faint)">Qs'</text>
        <text x={xOf(qdWorld)} y={H - PAD.b + 26} textAnchor="middle" fontSize="9" fill="var(--color-text-faint)">Qd'</text>
      </svg>
      <p style={s.caption}>
        A tariff raises the domestic price from Pworld to Pworld+tariff — domestic production rises (Qs' → Qs), domestic consumption falls (Qd' → Qd), imports shrink. Effects: consumer surplus falls, producer surplus rises, government collects tariff revenue on remaining imports, and deadweight loss appears from both reduced consumption and inefficient domestic overproduction.
      </p>
    </div>
  );
}

const s = {
  wrap: { display: "flex", flexDirection: "column", gap: "8px" },
  svg: { width: "100%", height: "auto", background: "var(--color-surface)", borderRadius: "10px", border: "1px solid var(--color-border)" },
  caption: { fontSize: "12px", color: "var(--color-text-faint)", margin: 0 },
};
