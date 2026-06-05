/**
 * InteractiveWidget — renders widget markers as collapsible iframes inline
 * inside AI chat messages.
 *
 * Supported markers:
 *   [ECONGRAPH: id]   — econgraphs.org (economics diagrams)
 *   [DESMOS: id]      — desmos.com (graphing calculator)
 *   [PHET: id]        — phet.colorado.edu (science simulations) — CC-BY 4.0
 *   [KINETIC: id]     — kineticgraphs.org (economics / game theory)
 *   [LIFESCIENCE: id] — EPAM LifeScience Miew (molecular viewer)
 *   [EXPLORABLES: id] — explorabl.es (interactive math/science)
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
    molecule_shapes: {
      url: "https://phet.colorado.edu/sims/html/molecule-shapes/latest/molecule-shapes_en.html",
      title: "Molecule Shapes (VSEPR)",
    },
    acid_base: {
      url: "https://phet.colorado.edu/sims/html/acid-base-solutions/latest/acid-base-solutions_en.html",
      title: "Acid-Base Solutions",
    },
    reactions: {
      url: "https://phet.colorado.edu/sims/html/reactants-products-and-leftovers/latest/reactants-products-and-leftovers_en.html",
      title: "Reactants, Products and Leftovers",
    },
    natural_selection: {
      url: "https://phet.colorado.edu/sims/html/natural-selection/latest/natural-selection_en.html",
      title: "Natural Selection",
    },
    gene_expression: {
      url: "https://phet.colorado.edu/sims/html/gene-expression-essentials/latest/gene-expression-essentials_en.html",
      title: "Gene Expression Essentials",
    },
    membrane_channels: {
      url: "https://phet.colorado.edu/sims/html/membrane-channels/latest/membrane-channels_en.html",
      title: "Membrane Channels",
    },
  },

  KINETIC: {
    supply_demand_game: {
      url: "https://kineticgraphs.org/consumers_producers.html",
      title: "Consumers, Producers & Market Equilibrium",
    },
    prisoners_dilemma: {
      url: "https://kineticgraphs.org/prisoners_dilemma.html",
      title: "Prisoner's Dilemma (Game Theory)",
    },
    cobb_douglas: {
      url: "https://kineticgraphs.org/cobb_douglas.html",
      title: "Cobb-Douglas Production Function",
    },
    budget_constraint: {
      url: "https://kineticgraphs.org/budget_constraint.html",
      title: "Budget Constraint & Indifference Curves",
    },
  },

  LIFESCIENCE: {
    dna: {
      url: "https://lifescience.opensource.epam.com/miew.html?load=mmtf:1BNA",
      title: "DNA Double Helix (B-form)",
    },
    hemoglobin: {
      url: "https://lifescience.opensource.epam.com/miew.html?load=mmtf:1HHO",
      title: "Hemoglobin — Oxygen Transport",
    },
    insulin: {
      url: "https://lifescience.opensource.epam.com/miew.html?load=mmtf:4INS",
      title: "Insulin — Peptide Hormone",
    },
    lysozyme: {
      url: "https://lifescience.opensource.epam.com/miew.html?load=mmtf:1LYZ",
      title: "Lysozyme — Enzyme Structure",
    },
    antibody: {
      url: "https://lifescience.opensource.epam.com/miew.html?load=mmtf:1IGT",
      title: "Antibody (IgG) — Immune System",
    },
    collagen: {
      url: "https://lifescience.opensource.epam.com/miew.html?load=mmtf:1CGD",
      title: "Collagen Triple Helix",
    },
  },

  EXPLORABLES: {
    prisoners: {
      url: "https://ncase.me/prisoners-dilemma/",
      title: "Evolution of Trust (Game Theory)",
    },
    crowds: {
      url: "https://ncase.me/crowds/",
      title: "The Wisdom and/or Madness of Crowds",
    },
    ballot: {
      url: "https://ncase.me/ballot/",
      title: "Voting Systems Explained",
    },
    loopy: {
      url: "https://ncase.me/loopy/",
      title: "Loopy — Systems Thinking Tool",
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
  KINETIC: {
    text: "KineticGraphs — Christopher Makler, Stanford University",
    href: "https://kineticgraphs.org",
  },
  LIFESCIENCE: {
    text: "EPAM LifeScience — Miew Molecular Viewer (open source)",
    href: "https://lifescience.opensource.epam.com",
  },
  EXPLORABLES: {
    text: "Explorable Explanations — explorabl.es",
    href: "https://explorabl.es",
  },
};

const ICON = {
  ECONGRAPH:   "📈",
  DESMOS:      "🔢",
  PHET:        "🔬",
  KINETIC:     "🎮",
  LIFESCIENCE: "🧬",
  EXPLORABLES: "🔍",
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
