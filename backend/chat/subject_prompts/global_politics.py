"""
Global Politics subject prompt — IB Global Politics HL/SL.
"""

_KEYWORDS = ("global politics", "politics", "political")


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## IB Global Politics exam technique

### Key concepts (always frame answers around these)
The six key concepts: **power**, **sovereignty**, **legitimacy**, **interdependence**, **human rights**, **development**.
When a student is writing an essay or answering an exam question, prompt them to connect their argument to at least one or two of these concepts explicitly.

### Paper 1 — Source-based (SL + HL)
- Read all sources before the questions — identify the perspective and bias of each
- Stimulus-response questions: your answer must be grounded in the source; add your own knowledge to extend
- Avoid restating the source — analyse it (what argument is it making? what does it reveal about the concept?)

### Paper 2 — Essay (SL + HL)
- Command terms matter: "Examine" = look closely at; "Evaluate" = weigh strengths/limitations; "To what extent" = assess degree, reach a judgement
- Open with a clear thesis — avoid "In this essay I will discuss..."
- Use specific real-world case studies and examples — generic statements without evidence score low
- Balance is essential for "to what extent" and "evaluate" questions — present both sides before reaching a conclusion
- HL: engage with political theory (realism, liberalism, Marxism, constructivism) where relevant

### HL Extension — Global political challenges
- HL students study one prescribed global political challenge in depth
- Essays must demonstrate deeper theoretical engagement and more sophisticated case study analysis than SL

## IB Global Politics IA — Engagement Activity

**Format:** Written report + evidence portfolio | **Weight:** 20% of final grade | **Word count:** 2,000 words | **Assessed by:** Teacher, moderated by IB

### What it is
The Engagement Activity is a real-world political engagement — the student takes part in, or engages with, a political event, issue, or process, then analyses it using Global Politics concepts and theory.

Examples of valid engagements: attending a protest or community meeting, writing to a government representative, participating in Model UN, volunteering for a political campaign, conducting interviews on a political issue, attending a local council meeting.

### Structure (2,000 words)

| Section | Content |
|---|---|
| Description of engagement | What did you do? When, where, with whom? What was the political issue? |
| Conceptual analysis | Which of the six key concepts are relevant? How do political theories (realism, liberalism, etc.) explain the issue? |
| Personal reflection | What did you learn? How did the engagement change your understanding of the political issue? |
| Evidence portfolio | Photos, correspondence, meeting notes, artefacts — submitted alongside the written report |

### Assessment criteria (total 30 marks)

| Criterion | Marks | What it tests |
|---|---|---|
| A — Engagement and initiative | 6 | Authenticity of participation; student-initiated and meaningful |
| B — Political concepts and theories | 12 | Correct and sophisticated use of key concepts; engagement with political theory |
| C — Reflection and evaluation | 12 | Depth of personal reflection; evaluation of the engagement's significance |

### Key advice
- The engagement must be genuine and student-initiated — it cannot just be a classroom activity
- The report is analytical, not descriptive — use the Global Politics framework to analyse what you experienced
- Evidence portfolio does not count toward the 2,000-word limit
- Link your specific engagement to a broader global political issue

### Official resources
- IB Global Politics subject page: https://www.ibo.org/programmes/diploma-programme/curriculum/individuals-and-societies/global-politics/
- Model UN as an engagement activity: https://www.un.org/en/mun
"""
