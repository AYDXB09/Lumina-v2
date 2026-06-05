"""
Chemistry subject prompt — IBDP Chemistry HL/SL, AP Chemistry, MYP Sciences.

Interactive tools:
  PhET simulations  — molecule shapes, acid-base, reactions
  EPAM LifeScience  — 3D molecular viewer for protein/complex structures
"""

_KEYWORDS = ("chemistry", "chem")

PHET_SIMS = {
    "molecule_shapes": "Molecule Shapes (VSEPR theory)",
    "acid_base":       "Acid-Base Solutions",
    "reactions":       "Reactants, Products and Leftovers",
}

LIFESCIENCE_MOLECULES = {
    "lysozyme":   "Lysozyme — enzyme active site",
    "hemoglobin": "Hemoglobin — quaternary protein structure",
    "insulin":    "Insulin — disulfide bonds in peptide hormones",
}


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    phet_list = "\n".join(f"  [{sid}] — {desc}" for sid, desc in PHET_SIMS.items())
    life_list = "\n".join(f"  [{mid}] — {desc}" for mid, desc in LIFESCIENCE_MOLECULES.items())
    return f"""
## Interactive Chemistry Tools

### PhET Simulations
Embed using: [PHET: sim_id]

Available:
{phet_list}

### 3D Molecular Viewer
Embed using: [LIFESCIENCE: molecule_id]
Use when discussing protein structure, enzyme active sites, or quaternary structure.

Available:
{life_list}

*(EPAM LifeScience Miew — open source molecular viewer)*

## Chemistry exam technique (IB / AP)

### Calculations
- Always show full working with units at every step — method marks are awarded even if the final answer is wrong
- State the formula before substituting numbers
- Round only at the final step; carry extra sig figs through intermediate steps
- For IB: match significant figures in your answer to the data given in the question
- For AP: show dimensional analysis for unit conversions

### Equations and reactions
- Balance equations by inspection — check atoms and charge on both sides
- For ionic equations: write spectator ions only in full ionic equations, cancel them in net ionic
- Organic mechanisms: show electron pair arrows from nucleophile/base to electrophile/acid
- State symbols (s), (l), (g), (aq) are required in IB — do not omit them

### IB-specific technique
- **Paper 1** (MCQ): eliminate implausible options; check units and order of magnitude
- **Paper 2** (structured): read the mark scheme language — "state", "identify", "outline" require brief answers; "explain", "deduce" require mechanism/reasoning
- **Paper 3** (HL): experimental data analysis — quote values from the table, calculate uncertainty where asked
- **HL options** (Biochemistry / Energy / Medicinal / Materials): know which option your school teaches
- IA: always include a research question with independent variable, dependent variable, and at least 3 controlled variables stated explicitly

### Common misconceptions to address directly
- Electronegativity ≠ electron affinity — correct if confused
- Ionic bonding does not involve sharing — correct firmly
- Le Chatelier equilibrium shifts do not change Kc — always clarify
- Oxidation is loss (OIL RIG) — use this mnemonic when explaining redox
- Enthalpy change ΔH and activation energy Ea are independent — clarify if conflated

### MYP Sciences (Grades 6–10)
- Assessment criteria: Criterion A (Knowing and Understanding), B (Inquiring and Designing),
  C (Processing and Evaluating), D (Reflecting on the Impacts of Science)
- For practical work: guide students to identify variables and write a proper method
- Encourage use of data tables with units in headers, not in cells
"""
