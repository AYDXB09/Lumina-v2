/**
 * EconSVGWidget — renders [ECONSVG: id] markers as collapsible native React
 * SVG diagrams (no iframe — these are static/labeled diagrams we own,
 * unlike InteractiveWidget's external embeds).
 */

import React, { useState } from "react";
import PriceCeilingFloor from "./econ-svgs/PriceCeilingFloor.jsx";
import LorenzCurve from "./econ-svgs/LorenzCurve.jsx";
import ADASStandalone from "./econ-svgs/ADASStandalone.jsx";
import TariffDiagram from "./econ-svgs/TariffDiagram.jsx";

const REGISTRY = {
  price_ceiling_floor: { title: "Price Ceiling & Price Floor", Component: PriceCeilingFloor },
  lorenz_curve:         { title: "Lorenz Curve & Gini Coefficient", Component: LorenzCurve },
  adas_standalone:      { title: "AD-AS Diagram", Component: ADASStandalone },
  tariff:                { title: "Tariff Diagram", Component: TariffDiagram },
};

export default function EconSVGWidget({ id }) {
  const [open, setOpen] = useState(true);
  const entry = REGISTRY[id];

  if (!entry) {
    return (
      <div className="iwidget-unknown">
        ⚠️ Unknown diagram: [ECONSVG: {id}]
      </div>
    );
  }

  const { title, Component } = entry;

  return (
    <div className="iwidget-wrap">
      <button className="iwidget-header" onClick={() => setOpen(o => !o)} aria-expanded={open}>
        <span className="iwidget-icon">📊</span>
        <span className="iwidget-title">{title}</span>
        <span className="iwidget-chevron">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="iwidget-body" style={{ padding: "12px" }}>
          <Component />
        </div>
      )}
    </div>
  );
}
