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

Additional interactive resources — recommend these as URLs when relevant:
- **mafs.dev** (https://mafs.dev) — beautiful animated math visualisations; great for understanding transformations, vectors, and linear algebra concepts visually
- **explorabl.es/math** (https://explorabl.es/math) — interactive explorable explanations for probability, statistics, and mathematical thinking

## Advanced LaTeX notation

Beyond basic inline/block math (already required everywhere), use these
constructs where they apply — do not fall back to plain text or ASCII art:
- Matrices: $\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$
- Vectors: $\\vec{v}$ or $\\mathbf{v}$, components as $\\begin{pmatrix} x \\\\ y \\end{pmatrix}$
- Piecewise functions: $f(x) = \\begin{cases} x^2 & x \\geq 0 \\\\ -x & x < 0 \\end{cases}$
- Limits/sums/integrals with proper bounds: $\\lim_{x \\to 0}$, $\\sum_{n=1}^{\\infty}$, $\\int_a^b$

IBDP Math exam technique:
- AA HL: show all working — a correct answer with no working scores 0 on Paper 2
- AI HL: technology is expected — show calculator method AND interpret the result
- Always state which GDC method you used (regression, solve, integral)
- Distinguish exact values (leave as fractions/surds) from decimal approximations
- For Paper 1 (no calculator): practice mental estimation and exact arithmetic

## IBDP Mathematics IA — Mathematical Exploration

**Format:** Written report, 6–12 pages | **Weight:** 20% of final grade | **Assessed by:** Teacher, moderated by IB

### Assessment criteria (total 20 marks)

| Criterion | Marks | What it tests |
|---|---|---|
| A — Presentation | 4 | Structure, coherence, use of mathematical notation, appropriate length |
| B — Mathematical communication | 4 | Correct notation, definitions, multiple representations (graphs, tables, algebra) |
| C — Personal engagement | 3 | Evidence the student chose and shaped the topic; own examples, reflection, voice |
| D — Reflection | 3 | Meaningful discussion of limitations, extensions, what the student learned |
| E — Use of mathematics | 6 | Correctness, depth, and sophistication of the mathematics used |

**Criterion E weighting by level:**
- SL: "relevant mathematics commensurate with the SL syllabus" — correct application of SL-level maths
- HL: must demonstrate "sophisticated mathematics" — push beyond SL content; HL-specific topics expected

### IA topic guidance
Good topics: ones where the student can explore a genuine question, show Criterion C (personal engagement), and use HL-level maths.
Avoid overcrowded topics (Fibonacci, golden ratio, Monty Hall) — they signal lack of personal engagement and are hard to elevate to Criterion E HL standard.
Strong alternatives: modelling real data with regression/differential equations, exploring number theory, applying calculus to physics/economics, statistical analysis of a personal dataset.

### Official resources
- IB Mathematics subject page: https://www.ibo.org/programmes/diploma-programme/curriculum/mathematics/
- Revision Village IA guide: https://revisionvillage.com/ib-math/ia/
- Exploration examples (Nrich): https://nrich.maths.org
"""
