"""
Economics graph integration for Lumina — IBDP / AP Micro & Macro pilot.

Injected into the system prompt ONLY when an economics course is active.
Zero overhead for all other courses and students.

Interactive graphs by Christopher Makler, Stanford University.
Source: https://www.econgraphs.org  |  Engine: https://kineticgraphs.org
Attribution is displayed in the bottom-right corner of each embedded graph.
"""

# ------------------------------------------------------------------ #
# Pilot graph set — 6 most-examined IBDP / AP topics                 #
# Expand after confirming rendering works end-to-end.                #
# ------------------------------------------------------------------ #
ECONGRAPH_MAP: dict[str, dict] = {
    "supply_demand": {
        "url": "https://www.econgraphs.org/graphs/competition/equilibrium/supply_and_demand",
        "title": "Supply and Demand Equilibrium",
        "ibdp": "Unit 2.1–2.3",
    },
    "tax_incidence": {
        "url": "https://www.econgraphs.org/graphs/competition/taxes/tax_equilibrium",
        "title": "Tax Incidence",
        "ibdp": "Unit 2.6 — Indirect Taxes",
    },
    "negative_externality": {
        "url": "https://www.econgraphs.org/graphs/competition/externalities/pigovian_taxes",
        "title": "Negative Externality and Pigouvian Tax",
        "ibdp": "Unit 2.7 — Market Failure",
    },
    "cost_curves": {
        "url": "https://www.econgraphs.org/graphs/firm/costs/marginal_and_average",
        "title": "Marginal and Average Cost Curves",
        "ibdp": "Unit 2.8 HL — Costs of Production",
    },
    "monopoly": {
        "url": "https://www.econgraphs.org/graphs/market_power/profit_max/downward_sloping_demand",
        "title": "Monopoly Diagram",
        "ibdp": "Unit 2.8 HL — Monopoly",
    },
    "adas_phillips": {
        "url": "https://www.econgraphs.org/graphs/fluctuations/phillips/adas_phillips",
        "title": "AD-AS and Phillips Curve",
        "ibdp": "Unit 3.2 / 3.5 — Macroeconomics",
    },
}

_KEYWORDS = ("economics", "econ", "micro", "macro")


def inject_if_match(course_name: str, extra: str) -> str:
    """Standard interface — called by subject_prompts dispatcher."""
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


# Keep old name for any direct imports during transition
inject_if_economics = inject_if_match


def _build_prompt() -> str:
    graph_list = "\n".join(
        f"  [{gid}] — {meta['title']} ({meta['ibdp']})"
        for gid, meta in ECONGRAPH_MAP.items()
    )
    return f"""
## Interactive Economics Graphs

You can embed interactive diagrams inline using this exact syntax on its own line:

[ECONGRAPH: graph_id]

Rules:
- Use only when a diagram genuinely aids understanding — not on every response
- Place the marker on its own line, before or after the paragraph it supports
- After the marker, briefly say what the student should notice in the graph
- First time you use a graph in a conversation, add one line:
  *(Interactive graph — Christopher Makler, econgraphs.org)*

Available graphs (pilot set — use the exact ID):
{graph_list}

Additional interactive tools — embed using [KINETIC: graph_id]:
  [supply_demand_game] — Consumers, Producers & Market Equilibrium
  [prisoners_dilemma]  — Prisoner's Dilemma (Game Theory)
  [cobb_douglas]       — Cobb-Douglas Production Function (HL)
  [budget_constraint]  — Budget Constraint & Indifference Curves (HL)

Not yet available as interactive graphs (describe in words):
- Price ceiling / price floor
- Lorenz curve / Gini coefficient
- AD-AS standalone (use [adas_phillips] — it includes the Phillips curve)
- Exchange rate, trade, tariff diagrams

IBDP exam technique:
- Draw diagrams BEFORE written analysis — IB awards diagram marks separately
- Label all curves, axes, equilibrium points and any shifts explicitly
- HL students need MR=MC analysis; SL students need supply/demand
- Match response depth to the command term: Explain (mechanism + effect),
  Evaluate (strengths + limitations + judgement), Discuss (both sides + conclusion)

## IBDP Economics IA — Portfolio of Commentaries

**Format:** Written commentaries | **Weight:** 20% of final grade | **Assessed by:** Teacher, moderated by IB

### SL: 3 commentaries (2,400 words total)
### HL: 3 commentaries + research project (2,400 words + 2,200 words)

**Commentaries (SL + HL):**
- Each commentary: max 800 words (excluding diagrams, bibliography)
- Based on a real published article (newspaper, online news — must be recent, typically within 3 years)
- Each commentary must cover a different unit: Unit 1 (Intro), Unit 2 (Micro), Unit 3 (Macro), Unit 4 (Global) — choose 3 of 4
- Must include at least one correctly drawn and labelled diagram per commentary

### Assessment criteria — each commentary (12 marks each)

| Criterion | Marks | What it tests |
|---|---|---|
| A — Diagrams | 3 | Accurate, labelled, relevant to the article's economic issue |
| B — Terminology | 2 | Correct use of economic terms throughout |
| C — Concepts | 3 | Correct application of economic theory to the real-world article |
| D — Analysis | 2 | Logical chain of reasoning: cause → mechanism → effect |
| E — Evaluation | 2 | Strengths/limitations of the policy or economic event; balanced judgement |

### HL Research Project (2,200 words)
- An extended investigation of a real-world economic issue — not article-based
- Must demonstrate sustained analysis using HL concepts (e.g. price discrimination, game theory, IB-specific HL content)
- Assessed on a separate mark scheme: similar criteria A–E but expects deeper analysis and evaluation
- Official guidance: https://www.ibo.org/programmes/diploma-programme/curriculum/individuals-and-societies/economics/

### Article sourcing tips
Good sources: BBC News, The Economist, Financial Times, Reuters, Bloomberg, Al Jazeera Business.
Check article date — IB requires the article to be recent (within 3 years of submission).
Each commentary must cite a different article; articles cannot overlap significantly in topic.
"""
