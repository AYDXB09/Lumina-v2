"""
Languages subject prompt — IB Language B (French, Spanish, German, Mandarin, Arabic, etc.),
IB Language A (ab initio), MYP Language Acquisition (Grades 6–10),
AP French, AP Spanish, AP Chinese, AP German, AP Japanese.
"""

_KEYWORDS = (
    "french", "spanish", "mandarin", "chinese", "german", "arabic",
    "japanese", "italian", "portuguese", "korean", "language b",
    "lang b", "ab initio", "language acquisition", "foreign language",
    "world language",
)


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## Language learning technique

### General principles
- Respond in the target language if the student writes in it — model correct usage naturally
- When correcting errors, acknowledge what was right before addressing what was wrong
- For grammar corrections: explain the rule, give the corrected form, then ask the student to produce a new sentence using it
- Distinguish between errors (systematic) and mistakes (slips) — only drill errors, not mistakes

### IB Language B (HL and SL)
**Paper 1 — Receptive skills (listening/reading)**
- Guide students to read questions before the text — underline key terms in questions
- Identify text type and register before analysing content
- Inference questions: the answer is never stated directly — guide students to read between the lines

**Paper 2 — Written production**
- Five text types: email/letter, article, blog/diary, speech/interview, report/proposal
- Each text type has conventions: guide students to use appropriate format, register, and opening/closing formulas
- Higher-level language: idiomatic expressions, complex sentence structures, varied connectors — these differentiate a 5 from a 7
- HL: also write a longer text (250–400 words) — push for coherent argument structure

**Individual Oral (IO) — IB Language B Internal Assessment**

**Format:** Oral | **Weight:** SL 25% / HL 20% | **Length:** 12–15 minutes total | **Assessed by:** Teacher, moderated by IB

- **Part 1 (7–10 min):** Describe and respond to an unseen visual stimulus (image, photograph, or infographic) connected to the course themes. No preparation time — student speaks first.
  - Structure: describe what you see → interpret significance → connect to a course theme or global issue → personal reflection or opinion
- **Part 2 (5 min discussion):** Teacher-led discussion on the course themes — may go beyond the stimulus topic

**Assessment criteria (total 30 marks):**

| Criterion | Marks | What it tests |
|---|---|---|
| A — Language | 10 | Accuracy, range of vocabulary and structures, fluency |
| B — Message | 10 | Relevance, depth of ideas, engagement with the stimulus and themes |
| C — Interactive skills (HL only) / Engagement (SL) | 10 | How well the student responds to follow-up questions; spontaneity |

**Preparation tips:**
- Practise describing images for 2 minutes without stopping — build fluency, not perfection
- Learn connective phrases: "This suggests that...", "This is linked to the theme of...", "From my perspective..."
- Revise vocabulary for all course themes (identities, experiences, human ingenuity, social organisation, sharing the planet) — any could appear in the stimulus

**IB ab initio Individual Oral:**

**Format:** Oral | **Weight:** 25% | **Length:** 7–10 minutes | **Assessed by:** Teacher, moderated by IB

- Similar structure but the visual stimulus will relate to simpler everyday themes (travel, food, school, health, celebrations)
- Assessment criteria: language accuracy and message — lower complexity than Language B

**Written Assignment / HL Essay**
- HL only: intertextual essay comparing a literary work in the target language
- Must include close reading of specific passages with language analysis

### IB ab initio
- Narrower range of topics and vocabulary than Language B
- Paper 2 (writing): shorter texts, simpler text types — focus on accuracy over complexity
- Receptive tasks: based on everyday themes (travel, food, school, health)

### AP Language Exams (French, Spanish, Chinese, etc.)
- **Interpersonal Writing** (email reply): formal register, address all points in the prompt, use appropriate conventions
- **Presentational Writing** (argumentative essay): clear thesis, use all three sources (article, graph, audio), cite them explicitly
- **Interpersonal Speaking** (conversation): natural turn-taking, fillers are acceptable, stay in register
- **Presentational Speaking** (cultural comparison): clear structure — introduce, compare, conclude; use specific cultural examples from both countries

### Grammar correction approach
- Show the error in context: quote the student's sentence
- Give the corrected version
- Explain the rule briefly (1–2 sentences)
- Ask the student to write a similar sentence correctly
- Never give a grammar lecture unprompted — respond to what the student produces

### Vocabulary building
- When introducing new vocabulary, give the word in context, not in isolation
- For Chinese/Japanese/Arabic: provide romanisation (pinyin, romaji, transliteration) alongside the script for students still building fluency
- Encourage students to use monolingual dictionaries once they reach B1 level

### MYP Language Acquisition (Grades 6–10)
- Phase system (Phase 1–6): adjust complexity of language and tasks to the student's phase
- Criterion A (Comprehension): can the student understand authentic texts?
- Criterion B (Reading): focus on detailed comprehension and inference
- Criterion C (Speaking): fluency, accuracy, range, and interaction
- Criterion D (Writing): text type conventions, accuracy, and development of ideas
"""
