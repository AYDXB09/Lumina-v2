"""
History subject prompt — IB History HL/SL, AP World History, AP US History,
AP European History, MYP Individuals & Societies.
"""

_KEYWORDS = ("history", "hist", "world history", "us history", "european history")


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## History exam technique

### Source analysis — IB Paper 1 (OPCVL → now OPVL in new syllabus)
For each source, guide students to address:
- **Origin**: who created it, when, in what form (speech, photograph, government document, etc.)
- **Purpose**: why was it created — to persuade, inform, commemorate, justify?
- **Value**: what does it tell us that is useful for the historian? (content + origin/purpose both add value)
- **Limitation**: what does it NOT tell us, or why might it be unreliable? (bias, incomplete picture, context missing)

Common mistake: students describe what the source says (content) instead of evaluating it (value/limitation). Push them to evaluate, not summarise.

### Essay technique — IB Papers 2 and 3
- Open with a clear, argumentative thesis — avoid "In this essay I will discuss..."
- Structure: thesis → body paragraphs with topic sentences → counter-argument → conclusion that reinforces thesis
- Each body paragraph: argument → specific evidence → link to question
- Named historians and their interpretations = bonus marks (historiography)
- Balance: "to what extent" questions require evaluation of both sides, not one-sided narrative

### HL Paper 3 (IB)
- Three essays in 2.5 hours — approximately 50 minutes per essay
- Depth over breadth: one well-argued essay beats three superficial ones
- Regional options: know which prescribed subjects and topics your school has selected

### Historical Investigation (IA) — IB History

**Format:** Written | **Weight:** 25% of final grade | **Word count:** 2,200 words | **Assessed by:** Teacher, moderated by IB

#### Structure and criteria (total 25 marks)

| Section | Criterion | Marks | What it tests |
|---|---|---|---|
| A | Identification and Evaluation of Sources | 6 | Two sources selected; full OPVL applied to each; sources must be relevant to the research question |
| B | Investigation | 15 | Structured argument using a range of evidence; not a narrative; must engage with different perspectives |
| C | Reflection | 4 | Genuine reflection on methods of the historian: how do the sources' origins and limitations affect historical understanding? |

#### Research question
- Must be specific, historical, and debatable — not a yes/no question
- Good format: "To what extent did X cause Y?" or "How significant was X in shaping Y?"
- Avoid questions about events too recent (less than ~20 years) — insufficient historiography
- Avoid questions answered by a single source — the investigation requires multiple perspectives

#### Section A — Identification and Evaluation of Sources
- Choose two sources that directly address the research question and come from different origins (e.g. one primary, one secondary; or two contrasting primaries)
- Apply OPVL rigorously to each: Origin, Purpose, Value, Limitation
- Common mistake: describing what the source says (content) instead of evaluating it — focus on VALUE and LIMITATION

#### Section B — Investigation
- Structured argument with a clear line of reasoning — not a chronological narrative
- Each paragraph: claim → evidence (specific, cited) → analysis → link to research question
- Engage with at least two historical perspectives or interpretations
- Use Section A sources plus additional evidence throughout

#### Section C — Reflection
- Reflect on the METHODS of historical investigation, not just the content of sources
- Address: What challenges did you face in assessing sources? How do limitations in available sources shape historical knowledge?
- This is a historiographical reflection — avoid summarising your findings again

#### Official resources
- IB History subject page: https://www.ibo.org/programmes/diploma-programme/curriculum/individuals-and-societies/history/

### AP History (US, World, European)
- **DBQ** (Document-Based Question): thesis + contextualization + HAPP analysis (Historical situation, Audience, Purpose, Point of view) for at least 3 documents + sourcing + complexity point
- **LEQ** (Long Essay): choose one prompt from three; thesis + contextualization + argument with evidence + complexity
- **SAQ** (Short Answer): part a/b/c structure — be concise and specific; no thesis needed
- For AP: complexity point = make a nuanced argument (turning point, continuity AND change, comparison across periods/regions)

### Historiography and historical thinking
- Causation: distinguish short-term triggers from long-term causes
- Continuity and change: help students identify what changed AND what stayed the same
- Significance: why does this event/person matter — in their own time and later?
- Perspective: whose history is being told? Whose is missing?

### MYP Individuals & Societies (Grades 6–10)
- Criterion A (Knowing and Understanding): factual accuracy, use of terminology
- Criterion B (Investigating): formulating and researching a focused question
- Criterion C (Communicating): clear structure, citations, bibliography
- Criterion D (Thinking Critically): identifying different perspectives, evaluating sources
- For source work: always ask "who wrote this and why?" before analysing content
"""
