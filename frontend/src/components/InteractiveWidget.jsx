/**
 * InteractiveWidget — renders [ECONGRAPH: id], [DESMOS: id], [PHET: id] markers
 * as collapsible iframes inline inside AI chat messages.
 *
 * Attributions:
 *   EconGraphs  — Christopher Makler, Stanford University (econgraphs.org)
 *   PhET Sims   — University of Colorado Boulder (phet.colorado.edu) — CC-BY 4.0
 *   Desmos      — Desmos Inc. (desmos.com)
 */

import React, { useState } from "react";

// ------------------------------------------------------------------ //
// Widget registry — mirrors backend subject_prompts/*.py              //
// ------------------------------------------------------------------ //

const REGISTRY = {
  ECONGRAPH: {
    supply_demand: {
      url: "https://www.econgraphs.org/graphs/competition/equilibrium/supply_and_demand",
      title: "Supply & Demand Equilibrium",
    },
    tax_incidence: {
      url: "https://www.econgraphs.org/graphs/competition/taxes/tax_equilibrium",
      title: "Tax Incidence",
    },
    negative_externality: {
      url: "https://www.econgraphs.org/graphs/competition/externalities/pigovian_taxes",
      title: "Negative Externality & Pigouvian Tax",
    },
    cost_curves: {
      url: "https://www.econgraphs.org/graphs/firm/costs/marginal_and_average",
      title: "Marginal & Average Cost Curves",
    },
    monopoly: {
      url: "https://www.econgraphs.org/graphs/market_power/profit_max/downward_sloping_demand",
      title: "Monopoly Diagram",
    },
    adas_phillips: {
      url: "https://www.econgraphs.org/graphs/fluctuations/phillips/adas_phillips",
      title: "AD-AS & Phillips Curve",
    },
  },

  DESMOS: {
    graphing: {
      url: "https://www.desmos.com/calculator",
      title: "Desmos Graphing Calculator",
    },
  },

  PHET: {
    projectile: {
      url: "https://phet.colorado.edu/sims/html/projectile-motion/latest/projectile-motion_en.html",
      title: "Projectile Motion",
    },
    waves: {
      url: "https://phet.colorado.edu/sims/html/wave-on-a-string/latest/wave-on-a-string_en.html",
      title: "Wave on a String",
    },
    circuit: {
      url: "https://phet.colorado.edu/sims/html/circuit-construction-kit-dc/latest/circuit-construction-kit-dc_en.html",
      title: "Circuit Construction Kit (DC)",
    },
    energy_skate: {
      url: "https://phet.colorado.edu/sims/html/energy-skate-park/latest/energy-skate-park_en.html",
      title: "Energy Skate Park",
    },
    photoelectric: {
      url: "https://phet.colorado.edu/sims/html/photoelectric/latest/photoelectric_en.html",
      title: "Photoelectric Effect",
    },
  },
};

const ATTRIBUTION = {
  ECONGRAPH: {
    text: "Christopher Makler — econgraphs.org",
    href: "https://www.econgraphs.org",
  },
  DESMOS: {
    text: "Desmos Graphing Calculator",
    href: "https://www.desmos.com",
  },
  PHET: {
    text: "PhET Interactive Simulations, University of Colorado Boulder (CC-BY 4.0)",
    href: "https://phet.colorado.edu",
  },
};

const ICON = {
  ECONGRAPH: "📈",
  DESMOS:    "🔢",
  PHET:      "🔬",
};

// ------------------------------------------------------------------ //
// Component                                                           //
// ------------------------------------------------------------------ //

export default function InteractiveWidget({ marker, id }) {
  const [open, setOpen] = useState(true);

  const entry   = REGISTRY[marker]?.[id];
  const attrib  = ATTRIBUTION[marker];
  const icon    = ICON[marker] ?? "🖼️";

  if (!entry) {
    // Unknown ID — render a small warning so we can catch missing mappings
    return (
      <div className="iwidget-unknown">
        ⚠️ Unknown interactive widget: [{marker}: {id}]
      </div>
    );
  }

  return (
    <div className="iwidget-wrap">
      {/* Header bar */}
      <button
        className="iwidget-header"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <span className="iwidget-icon">{icon}</span>
        <span className="iwidget-title">{entry.title}</span>
        <span className="iwidget-chevron">{open ? "▲" : "▼"}</span>
      </button>

      {/* iframe */}
      {open && (
        <div className="iwidget-body">
          <iframe
            src={entry.url}
            title={entry.title}
            className="iwidget-frame"
            allowFullScreen
            loading="lazy"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
          {/* Attribution */}
          <div className="iwidget-attrib">
            <a
              href={attrib.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {attrib.text}
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
