"""
Psychology subject prompt — IBDP Psychology HL/SL, AP Psychology.
"""

_KEYWORDS = ("psychology", "psych")


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## Psychology exam technique (IB / AP)

### IB Psychology — SAQ (Short Answer Question)
- 8 marks, ~22 minutes
- Structure: describe the study → link to the command term → evaluate briefly
- Always name the researcher(s), year if known, and outline methodology
- Do NOT evaluate in a "describe" SAQ — read the command term carefully
- Required: named study with sufficient detail (aim, participants, procedure, results, conclusion)

### IB Psychology — ERQ (Extended Response Question)
- 22 marks (SL) or higher with evaluation at HL; ~45 minutes
- Structure: introduction with clear argument → body paragraphs (theory/study + analysis + evaluation) → conclusion
- A strong ERQ cites at least 3–4 studies and discusses their strengths and limitations
- Address ethical considerations where relevant — examiners reward this
- HL: discuss cultural and gender considerations; show awareness of researcher bias

### Command terms (IB)
- **Describe**: state the features of a theory/study — no evaluation needed
- **Explain**: give reasons or mechanisms — "how" and "why"
- **Evaluate**: assess strengths AND limitations — must be balanced
- **Discuss**: present multiple perspectives, then reach a conclusion
- **Contrast**: identify differences only (not similarities)
- **To what extent**: weigh evidence for and against, then make a supported judgement

### Research methods
- Experimental: independent variable (IV), dependent variable (DV), extraneous variables — always define all three
- For studies: always state the aim, sample, procedure, and key finding
- Evaluate studies using: reliability (replication), validity (internal/external), ethical considerations, sample size and representativeness, cultural bias

### Key approaches (IB)
- Biological: brain structures, hormones, neurotransmitters, genetics, evolution
- Cognitive: schemas, memory models, cognitive biases, thinking errors
- Sociocultural: social identity, cultural norms, conformity, group behaviour
- Developmental (HL option): attachment, cognitive development, identity formation
- Abnormal (HL option): classification, explanations, treatments — know at least two disorders in depth

### AP Psychology
- Multiple choice: 100 questions, 70 minutes — know terminology precisely
- Free response: 2 questions — one concept application, one research design
- For research design FRQ: state hypothesis, identify IV/DV, design procedure, discuss ethical considerations
- High-yield topics: research methods, biological bases, sensation/perception, learning, memory, cognition, development, personality, abnormal, social, treatment

### IA (Internal Assessment) — IB Psychology

**Format:** Written report | **Weight:** 25% of final grade | **Word count:** 2,200 words (excluding references, appendices) | **Assessed by:** Teacher, moderated by IB

The IA is a replication (or partial replication) of a published psychological study using a simple experimental or quasi-experimental design.

#### Assessment criteria (total 22 marks)

| Criterion | Marks | What it tests |
|---|---|---|
| A — Introduction | 6 | Describes background theory and original study; clearly states aim and hypothesis (null + alternative) |
| B — Exploration | 4 | Identifies design (independent samples, repeated measures, matched pairs); states IV and DV precisely; describes sampling method; lists ethical procedures |
| C — Analysis | 6 | Correctly calculated descriptive statistics (mean, median, SD); appropriate graph; inferential test chosen and applied correctly; result interpreted (accept/reject null) |
| D — Evaluation | 6 | Discusses findings in relation to original study; identifies internal and external validity issues; suggests realistic modifications |

#### Key requirements
- **Participants:** minimum 10 per condition (independent samples) or 10 total (repeated measures)
- **Inferential test:** Mann-Whitney U (independent samples, ordinal data) is the most common — always state the null hypothesis, calculated U value, critical value, and conclusion
- **Ethics:** informed consent form, right to withdraw, debrief script, and anonymity — all must be included in appendices and addressed in Criterion B
- **Citation:** the original study being replicated must be fully cited; secondary sources must be cited too
- **Word count trap:** the 2,200-word limit is strict — appendices (raw data, consent forms, debriefs) do NOT count toward the limit

#### Official resources
- IB Psychology subject page: https://www.ibo.org/programmes/diploma-programme/curriculum/individuals-and-societies/psychology/
"""
