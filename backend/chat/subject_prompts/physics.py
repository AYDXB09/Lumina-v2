"""
Physics subject prompt — IBDP Physics, AP Physics 1/2/C.

Primary tool: PhET Interactive Simulations (University of Colorado Boulder)
  https://phet.colorado.edu — free, embeddable HTML5 simulations
  License: CC-BY 4.0 — attribution required

Marker syntax: [PHET: sim_id]
Frontend renders as a PhET iframe.

Pilot set: 5 most-used simulations for IBDP / AP Physics.
"""

PHET_BASE = "https://phet.colorado.edu/sims/html"

PHET_SIMS: dict[str, dict] = {
    "projectile": {
        "url": f"{PHET_BASE}/projectile-motion/latest/projectile-motion_en.html",
        "title": "Projectile Motion",
        "ibdp": "Unit A — Space, Time and Motion",
    },
    "waves": {
        "url": f"{PHET_BASE}/wave-on-a-string/latest/wave-on-a-string_en.html",
        "title": "Wave on a String",
        "ibdp": "Unit C — Wave Behaviour",
    },
    "circuit": {
        "url": f"{PHET_BASE}/circuit-construction-kit-dc/latest/circuit-construction-kit-dc_en.html",
        "title": "Circuit Construction Kit (DC)",
        "ibdp": "Unit B — The Particulate Nature of Matter / Electricity",
    },
    "energy_skate": {
        "url": f"{PHET_BASE}/energy-skate-park/latest/energy-skate-park_en.html",
        "title": "Energy Skate Park",
        "ibdp": "Unit A — Work, Energy and Power",
    },
    "photoelectric": {
        "url": f"{PHET_BASE}/photoelectric/latest/photoelectric_en.html",
        "title": "Photoelectric Effect",
        "ibdp": "Unit E — Nuclear and Quantum Physics",
    },
}

_KEYWORDS = ("physics", "phys")


def inject_if_match(course_name: str, extra: str) -> str:
    """Standard interface — called by subject_prompts dispatcher."""
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    sim_list = "\n".join(
        f"  [{sid}] — {meta['title']} ({meta['ibdp']})"
        for sid, meta in PHET_SIMS.items()
    )
    return f"""
## Interactive Physics Simulations

You can embed PhET interactive simulations inline using:

[PHET: sim_id]

Use when a concept is easier to grasp through direct experimentation
(projectile motion, wave behaviour, circuit building, energy conservation).

Available simulations (pilot set):
{sim_list}

*(PhET Interactive Simulations, University of Colorado Boulder —
  https://phet.colorado.edu, CC-BY 4.0)*

## Advanced LaTeX notation

Beyond basic inline/block math (already required everywhere), use these
constructs where they apply — do not fall back to plain text or ASCII art:
- Vectors: $\\vec{{F}}$ or $\\mathbf{{F}}$, with components as $\\begin{{pmatrix}} F_x \\\\ F_y \\end{{pmatrix}}$
- Units: use \\, as a thin space before units, e.g. $9.8\\,\\text{{m/s}}^2$ — never bare "m/s^2"
- Vector operations: dot product $\\vec{{a}} \\cdot \\vec{{b}}$, cross product $\\vec{{a}} \\times \\vec{{b}}$
- Derivatives in kinematics: $v = \\frac{{dx}}{{dt}}$, $a = \\frac{{dv}}{{dt}}$

IBDP Physics exam technique:
- Always define symbols before using them in equations
- Show substitution with units — unit errors cost marks
- Data-based questions: read uncertainty from the graph, not from recall
- Paper 3 (HL): experimental design questions — state variables (independent,
  dependent, controlled) explicitly
- SL vs HL: HL requires derivations; SL can quote results directly

## IBDP Physics IA — Individual Investigation

**Format:** Written report, 6–12 pages | **Weight:** 20% of final grade | **Assessed by:** Teacher, moderated by IB

### Assessment criteria (total 24 marks)

| Criterion | Marks | What it tests |
|---|---|---|
| A — Personal engagement | 2 | Is there a genuine personal reason for choosing this topic? Does the student show intellectual curiosity beyond the basic brief? |
| B — Exploration | 6 | Well-defined research question; clear method; variables (IV, DV, controlled) identified; relevant background theory; assessment of safety and ethics |
| C — Analysis | 6 | Correctly processed data; appropriate graphs (with error bars); correct calculation of uncertainties; trend analysis |
| D — Evaluation | 6 | Discusses limitations of method; explains sources of systematic and random error; suggests realistic improvements |
| E — Communication | 4 | Clear structure; appropriate scientific language; correctly cited sources; figures/tables labelled |

### What makes a strong IA
- **Research question**: specific and measurable — "How does X affect Y?" with a defined range
- **Criterion B trap**: vague variables ("I will measure temperature") lose marks — be precise ("water temperature varied from 20°C to 60°C in 10°C steps")
- **Criterion C**: always show a sample calculation; propagate uncertainties through calculations; use appropriate significant figures
- **Criterion D**: distinguish random error (scatter around line) from systematic error (offset of line); suggest improvements that are feasible, not just "use better equipment"
- **Criterion A**: one or two sentences explaining why this topic interests you personally — don't skip this, it's free marks

### Topic selection guidance
Good topics: anything the student can measure directly with school equipment, with a clear independent variable.
Strong examples: pendulum period vs length/mass, viscosity vs temperature, sound intensity vs distance, spring constant measurement, RC circuit time constant.
Avoid topics requiring equipment the school doesn't have — check lab resources first.

### Official resources
- IB Physics subject page: https://www.ibo.org/programmes/diploma-programme/curriculum/sciences/
- PhET simulations (can be used for preliminary modelling): https://phet.colorado.edu
"""
