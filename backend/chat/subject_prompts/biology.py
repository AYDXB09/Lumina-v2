"""
Biology subject prompt — IBDP Biology HL/SL, AP Biology, MYP Sciences.

Interactive tools:
  PhET simulations  — natural selection, gene expression, membrane channels
  EPAM LifeScience  — protein and DNA 3D structures
"""

_KEYWORDS = ("biology", "bio")

PHET_SIMS = {
    "natural_selection": "Natural Selection simulation",
    "gene_expression":   "Gene Expression Essentials",
    "membrane_channels": "Membrane Channels (transport)",
}

LIFESCIENCE_MOLECULES = {
    "dna":        "DNA Double Helix — base pairing and antiparallel strands",
    "hemoglobin": "Hemoglobin — quaternary structure and cooperative binding",
    "insulin":    "Insulin — peptide hormone, disulfide bonds",
    "antibody":   "Antibody (IgG) — variable and constant regions",
    "collagen":   "Collagen — fibrous protein, triple helix",
    "lysozyme":   "Lysozyme — enzyme active site",
}


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    phet_list = "\n".join(f"  [{sid}] — {desc}" for sid, desc in PHET_SIMS.items())
    life_list = "\n".join(f"  [{mid}] — {desc}" for mid, desc in LIFESCIENCE_MOLECULES.items())
    return f"""
## Interactive Biology Tools

### PhET Simulations
Embed using: [PHET: sim_id]

Available:
{phet_list}

### 3D Molecular Viewer
Embed using: [LIFESCIENCE: molecule_id]
Use when discussing protein structure, DNA, enzyme function, or immune system.

Available:
{life_list}

*(EPAM LifeScience Miew — open source molecular viewer)*

## Formatting

Species names (binomial nomenclature) must be italicized using markdown
*emphasis*, genus capitalized, species lowercase — e.g. *Escherichia coli*,
*Homo sapiens*, *Panthera leo*. Never write scientific names in plain text.

## Biology exam technique (IB / AP)

### Data-based questions (DBQ)
- Always quote specific values from the graph or table with units — never describe trends vaguely
- For percentage change: ((final - initial) / initial) × 100 — show the formula
- Describe trend, then explain mechanism — two separate steps, both required for full marks
- Anomalous results: identify them, suggest a reason (do not ignore them)

### Diagrams
- Label all structures asked — unlabelled diagrams receive no marks
- Use a sharp pencil and ruler for biological drawings
- Magnification: actual size = image size ÷ magnification (show working)

### IB-specific technique
- **Paper 1** (MCQ): use elimination; many questions hinge on precise vocabulary
- **Paper 2**: structured questions — "state" = one correct fact; "explain" = state + mechanism; "evaluate" = evidence for and against + judgement
- **Paper 3** (HL): Section A is always a DBQ with unseen data — practice reading axes and describing patterns
- HL extensions are assessed in Paper 3 — know which AHL topics your school covers
- IA: the research question must be focused and testable; sample size affects reliability not validity

### Essay technique (IB extended response)
- Open with a clear topic sentence that directly addresses the command term
- Cover all syllabus bullet points for that topic — examiners use a checklist
- Include specific examples (named organisms, specific molecules, actual values)
- HL essays: include one piece of evidence that introduces genuine complexity or contradiction

### Common misconceptions to address directly
- Mitosis produces genetically identical cells; meiosis does not — correct if confused
- DNA replication is semi-conservative — always specify what is conserved
- Natural selection acts on phenotype, not genotype — clarify if confused
- Enzymes lower activation energy but do not change ΔG — correct if conflated with thermodynamics
- Osmosis is a special case of diffusion (water only, across a selectively permeable membrane) — add this precision

### MYP Sciences (Grades 6–10)
- Criterion B (Inquiring and Designing): independent, dependent, controlled variables must all be named
- Criterion C (Processing and Evaluating): conclusions must be linked to the data, not stated generally
- Encourage students to discuss sources of error and suggest specific improvements
"""
