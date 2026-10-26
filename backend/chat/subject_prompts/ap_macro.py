"""
AP Macroeconomics — College Board exam technique + unit framework.

Distinct from IB Economics (chat.subject_prompts.economics): different exam
format (MCQ + FRQ, not commentaries), different unit structure, no IA.
Dispatched from economics.py when the course name indicates AP Macro.

Shares the interactive graph registry (ECONGRAPH_MAP) with the IB module —
the diagrams themselves are the same economics, only the exam framing differs.
"""

from chat.subject_prompts.economics import ECONGRAPH_MAP

AP_MACRO_UNITS = {
    1: "Basic Economic Concepts (scarcity, PPC, comparative advantage) — 5–10%",
    2: "Economic Indicators and the Business Cycle (GDP, unemployment, CPI/inflation) — 12–17%",
    3: "National Income and Price Determination (AD-AS model) — 17–27%",
    4: "Financial Sector (money market, banking, the Fed) — 18–23%",
    5: "Long-Run Consequences of Stabilization Policies — 20–30%",
    6: "Open Economy — International Trade and Finance — 10–13%",
}


def _build_prompt() -> str:
    graph_list = "\n".join(
        f"  [{gid}] — {meta['title']}" for gid, meta in ECONGRAPH_MAP.items()
    )
    unit_list = "\n".join(f"  Unit {n}: {desc}" for n, desc in AP_MACRO_UNITS.items())
    return f"""
## AP Macroeconomics

This is AP Macroeconomics — College Board format, distinct from IB Economics.
Do not use IB command terms (Explain/Evaluate/Discuss) or reference IB IA
commentaries; AP has no equivalent internal assessment.

### AP Exam Structure
- **Section I — Multiple Choice:** 60 questions, 70 minutes, 66% of score
- **Section II — Free Response:** 3 questions, 60 minutes (1 long, 2 short), 33% of score
  - FRQs frequently require an AD-AS or money market graph — no graph, no credit for that part
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
- Use precise AP terminology: "expansionary/contractionary," "crowding out," "money multiplier" — graders pattern-match against the official rubric language
- Money market + loanable funds + AD-AS are frequently combined in one FRQ — practice moving between all three
- Fiscal vs. monetary policy questions expect the student to state BOTH the tool used AND the transmission mechanism (e.g. "the Fed sells bonds → reserves fall → interest rates rise → investment falls → AD shifts left")
- Free-response practice should mimic real released FRQs (College Board publishes past FRQs + scoring guidelines publicly — reference this format when creating practice questions)
"""


def inject_if_match(course_name: str, extra: str) -> str:
    """Called directly by economics.py's AP dispatch — not registered separately."""
    return extra + _build_prompt()
