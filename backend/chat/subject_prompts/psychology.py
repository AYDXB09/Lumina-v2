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

### IA (Internal Assessment) — IB
- Replication of a published study — must cite the original
- Must include: introduction, exploration, analysis, evaluation, references
- Sample: at least 10 participants per condition; describe sampling method
- Inferential statistics: Mann-Whitney U (non-parametric), or appropriate test — state the null and alternative hypothesis
- Ethical considerations: informed consent, right to withdraw, debrief — all must be addressed
"""
