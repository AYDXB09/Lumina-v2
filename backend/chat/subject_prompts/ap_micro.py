"""
AP Microeconomics — College Board exam technique + unit framework.

Distinct from IB Economics (chat.subject_prompts.economics): different exam
format (MCQ + FRQ, not commentaries), different unit structure, no IA.
Dispatched from economics.py when the course name indicates AP Micro.

Shares the interactive graph registry (ECONGRAPH_MAP) with the IB module —
the diagrams themselves are the same economics, only the exam framing differs.
"""

from chat.subject_prompts.economics import ECONGRAPH_MAP

AP_MICRO_UNITS = {
    1: "Basic Economic Concepts (scarcity, PPC, comparative advantage) — 8–14%",
    2: "Supply and Demand — 13–19%",
    3: "Production, Cost, and the Perfect Competition Model — 20–26%",
    4: "Imperfect Competition (monopoly, oligopoly, monopolistic competition) — 15–22%",
    5: "Factor Markets — 10–13%",
    6: "Market Failure and the Role of Government — 8–14%",
}


def _build_prompt() -> str:
    graph_list = "\n".join(
        f"  [{gid}] — {meta['title']}" for gid, meta in ECONGRAPH_MAP.items()
    )
    unit_list = "\n".join(f"  Unit {n}: {desc}" for n, desc in AP_MICRO_UNITS.items())
    return f"""
## AP Microeconomics

This is AP Microeconomics — College Board format, distinct from IB Economics.
Do not use IB command terms (Explain/Evaluate/Discuss) or reference IB IA
commentaries; AP has no equivalent internal assessment.

### AP Exam Structure
- **Section I — Multiple Choice:** 60 questions, 70 minutes, 66% of score
- **Section II — Free Response:** 3 questions, 60 minutes (1 long, 2 short), 33% of score
  - FRQs always require a fully labeled graph where relevant — no graph, no credit for that part
  - Grading is point-based (not holistic) — each FRQ has a published point allocation; be precise about what earns each point

### Course Framework (College Board Units)
{unit_list}

### Interactive Graphs
Embed using: [ECONGRAPH: graph_id]
{graph_list}

### Additional Static Diagrams
Embed using: [ECONSVG: diagram_id]
  [price_ceiling_floor] — Price Ceiling & Price Floor
  [lorenz_curve]         — Lorenz Curve & Gini Coefficient
  [adas_standalone]      — AD-AS Diagram (standalone)
  [tariff]                — Tariff Diagram

### AP-specific exam technique
- **Show ALL work** — AP FRQ grading awards points for correct labeled graphs and stated reasoning, not just final answers
- Label every graph: axes, curves, equilibrium point(s), and any shift with a clear before/after
- Use precise AP terminology: "marginal cost," "allocative efficiency," "deadweight loss" — graders pattern-match against the official rubric language
- For monopoly/oligopoly FRQs: always show MR=MC first, then derive price/quantity from the demand curve
- Free-response practice should mimic real released FRQs (College Board publishes past FRQs + scoring guidelines publicly — reference this format when creating practice questions)
"""


def inject_if_match(course_name: str, extra: str) -> str:
    """Called directly by economics.py's AP dispatch — not registered separately."""
    return extra + _build_prompt()
