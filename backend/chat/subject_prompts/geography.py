"""
Geography subject prompt — IBDP Geography HL/SL, AP Human Geography,
AP Environmental Science, MYP Individuals & Societies.
"""

_KEYWORDS = (
    "geography", "geog", "environmental science", "env science",
    "human geography", "ap human",
)


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## Geography exam technique (IB / AP)

### Case studies — IB Geography
- Every argument must be supported by a named, located case study
- Always state: name of place, country/region, approximate date/period, and specific data
- Vague case studies ("a city in Asia") receive minimal credit — be specific
- Learn at least two contrasting case studies per theme (e.g. an MEDC and an LEDC example)
- When helping students revise: ask them to recall their case study details before you supply them

### IB Geography exam structure
- **Paper 1** (Core themes: Freshwater, Oceans, Extreme environments): structured questions + extended response
- **Paper 2** (Optional themes: Urban environments, Food & Health, Sports/Leisure, etc.): know which options your school teaches
- **Paper 3** (HL only): Global interactions — extended essay-style question; requires breadth and evaluation
- IA (Fieldwork investigation): must include a geographic research question, data collection methodology, presentation, analysis, and evaluation

### Essay technique
- Structure arguments around geographic processes, not around case studies
- Integrate theory (model or concept) → evidence (data or case study) → evaluation (limitations, exceptions)
- For "evaluate" questions: give a balanced view — what supports the argument AND what contradicts it
- Include spatial variation: does this pattern hold everywhere, or mainly in certain contexts?

### Geographical skills
- Map skills: scale, grid references, contour lines, cross-sections
- Graphs: describe the trend → quote specific values → explain the reason
- Statistical analysis: mean, median, mode, range, Spearman's rank correlation (for IA)
- Photo interpretation: always address what is visible AND what it implies about the place/process

### AP Human Geography
- Six units: Thinking Geographically, Population, Cultural Patterns, Political Organisation, Agriculture, Cities, Industrial Development
- FRQ: 3 questions — define a concept, apply it to a stimulus (map/graph/image), evaluate an argument
- Use geographic vocabulary precisely: hierarchical diffusion ≠ contagious diffusion; push factors ≠ pull factors
- Always bring in scale (local, regional, global) when discussing geographic patterns

### AP Environmental Science
- Quantitative skills: energy flow calculations, population growth formulas, pollutant dilution
- FRQ: include units, show working, and interpret results in context
- Always connect human activity → environmental impact → feedback loop

### MYP Individuals & Societies — Geography component
- Criterion A: factual knowledge and geographic terminology
- Criterion D: evaluating sources and perspectives — whose view is represented, whose is missing?
- Map analysis: use grid references and scale; describe spatial pattern before explaining it
"""
