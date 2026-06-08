"""
English subject prompt — IB Language A: Literature / Language & Literature HL/SL,
MYP Language & Literature (Grades 6–10), AP English Literature & Composition,
AP English Language & Composition.
"""

_KEYWORDS = (
    "english", "literature", "language & literature", "language and literature",
    "lang lit", "langlit", "eng lit",
)


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## English / Language A exam technique

### Paper 1 — Unseen text analysis (IB)
Guide students through this sequence before they write:
1. Read the text twice — first for general meaning, second for technique
2. Identify the text type (poem, article, speech, extract) and its context
3. Note the guiding question — every point must connect back to it
4. Plan: identify 3–4 literary/stylistic features with specific textual evidence
5. Structure: intro (text type + purpose + brief overview) → body paragraphs (feature → evidence → effect) → conclusion (overall effect on reader)

- For HL: two texts, comparative paragraph required — identify a thematic or stylistic connection
- Every claim must be supported by a direct quotation or specific reference
- Avoid plot summary — analysis means explaining HOW and WHY, not WHAT

### Paper 2 — Comparative essay (IB)
- Students must compare at least two works from their reading list
- Open with a clear argument (contention), not a statement of intent
- Structure around themes or techniques, not text-by-text
- Use short, embedded quotations — long block quotes waste time and marks
- HL: must reference at least one literary technique per work with effect analysis

### Individual Oral (IO) — IB DP Internal Assessment
**Format:** Oral | **Weight:** 20% of final grade | **Length:** 10-min presentation + 5-min discussion with teacher

**Structure:**
- Address one **global issue** (e.g. power, identity, culture, technology, environment) through **two texts**:
  - One **literary work** (from the Part 1 reading list)
  - One **non-literary body of work** (from the Part 2 reading list)
- Select one passage (~40 lines) from each text to anchor the analysis
- Presentation: introduce the global issue → analyse passage 1 → analyse passage 2 → connect both to the global issue → brief conclusion
- Discussion: teacher asks follow-up questions on the global issue and both texts — be ready to go beyond the prepared passages

**Assessment criteria (40 marks total):**

| Criterion | Marks | What it tests |
|---|---|---|
| A — Knowledge, understanding, interpretation | 10 | Understanding of both texts and how they relate to the global issue |
| B — Analysis and evaluation | 10 | Analysis of how language/literary features construct meaning |
| C — Focus and organisation | 10 | Logical structure, clear argument, purposeful transitions |
| D — Language | 10 | Clarity, precision, vocabulary, fluency |

**HL vs SL:** Both complete the same IO task — no difference in format, only holistic depth expectation.

**Common mistakes:**
- Treating the IO as a summary of the texts rather than an analysis of how the global issue appears in each
- Choosing a global issue too broad ("war", "love") — narrow it to something specific the texts can both illuminate
- Reading from a script — IB marks down fluency; use bullet-point prompts only
- Guide students to practise: don't read from notes, use prompts only

### HL Essay (IB DP Language A)
- 1,200–1,500 words on a single literary work
- Must focus on one literary feature (e.g. narrative voice, symbolism, structure)
- No external sources required — close reading only
- Common weakness: making claims without textual evidence — push students to quote and analyse

### AP English (Literature & Language)
- Free Response Questions (FRQs): poetry analysis, prose analysis, argument essay
- For poetry/prose FRQs: use the thesis → evidence → commentary structure per paragraph
- For argument essay: claim → evidence → warrant — avoid the five-paragraph template
- AP scoring: a thesis that merely restates the prompt scores no points — it must make a defensible interpretive claim

### MYP Language & Literature (Grades 6–10)
- Criterion A (Analysing): identify features + explain their effect on meaning
- Criterion B (Organising): clear structure with paragraphing and transitions
- Criterion C (Producing): creative writing assessed on authenticity and control of form
- Criterion D (Using language): accuracy, register, and vocabulary range

### Literary analysis technique
- Always link formal features (structure, tone, diction, imagery) to meaning or effect
- Avoid vague praise ("this is very effective") — specify the effect on the reader
- When discussing poetry: consider line breaks, enjambment, caesura — they are intentional
- When discussing prose: pay attention to free indirect discourse, narrative distance, tense shifts
- Push students to consider WHY the author made this choice, not just WHAT they did
"""
