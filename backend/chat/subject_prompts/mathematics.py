"""
Mathematics subject prompt — IBDP Math AA / AI, AP Calculus, AP Statistics.

Primary tool: Desmos (free, embeddable graphing calculator)
  https://www.desmos.com — no API key required for basic embedding

Marker syntax: [DESMOS: preset_id]
Frontend renders as a Desmos iframe with the preset pre-loaded.

TODO (Phase 2):
- GeoGebra for geometry / 3D (https://www.geogebra.org/calculator)
- Custom SVG for number lines, probability trees, Venn diagrams
"""

# Preset Desmos graphs for IBDP / AP topics
# URL format: https://www.desmos.com/calculator/[hash]
# Each hash links to a pre-configured Desmos state shared publicly.
#
# NOTE: For the pilot, we use blank Desmos + tell the AI to suggest
# expressions. Phase 2 will add pre-configured presets per topic.

DESMOS_BASE = "https://www.desmos.com/calculator"

DESMOS_PRESETS: dict[str, dict] = {
    # Blank calculator — AI tells the student what to type in
    "graphing": {
        "url": DESMOS_BASE,
        "title": "Desmos Graphing Calculator",
        "ibdp": "All topics — functions, calculus, trigonometry",
    },
    # Pre-built presets (add hash once created and shared on Desmos)
    # "derivative": {
    #     "url": f"{DESMOS_BASE}/[hash]",
    #     "title": "Derivative Visualiser",
    #     "ibdp": "Calculus — Topic 5",
    # },
}

_KEYWORDS = ("math", "maths", "calculus", "algebra", "statistics", "ibdp math", "ap calc")


def inject_if_match(course_name: str, extra: str) -> str:
    """Standard interface — called by subject_prompts dispatcher."""
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## Interactive Mathematics Tools

You can embed a Desmos graphing calculator inline using:

[DESMOS: graphing]

Use it when:
- Graphing a function would help the student visualise it
- Checking roots, intercepts, turning points, or asymptotes
- Showing transformations f(x+a), af(x), f(ax), f(x)+a visually
- Integrating / finding area under a curve

When you embed Desmos, tell the student exactly what to type in the calculator,
for example: "Type `y = x^2 - 4x + 3` and observe where it crosses the x-axis."

IBDP Math exam technique:
- AA HL: show all working — a correct answer with no working scores 0 on Paper 2
- AI HL: technology is expected — show calculator method AND interpret the result
- Always state which GDC method you used (regression, solve, integral)
- Distinguish exact values (leave as fractions/surds) from decimal approximations
- For Paper 1 (no calculator): practice mental estimation and exact arithmetic
"""
