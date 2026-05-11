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

IBDP Physics exam technique:
- Always define symbols before using them in equations
- Show substitution with units — unit errors cost marks
- Data-based questions: read uncertainty from the graph, not from recall
- Paper 3 (HL): experimental design questions — state variables (independent,
  dependent, controlled) explicitly
- SL vs HL: HL requires derivations; SL can quote results directly
"""
