# Math Swarm — Zero-Hallucination Computation Engine for LLMs

**1,079 tests. 12 categories. 100% accuracy. $0 cost. <2ms per computation.**

LLMs predict tokens. They don't compute. When ChatGPT calculates your mortgage payment, it's guessing which digits come next — and it's wrong 7-45% of the time depending on model size. Math Swarm replaces token prediction with symbolic computation via SymPy. The result: mathematically perfect answers, every time, on any hardware.

## Benchmark: Math Swarm vs LLMs

Tested on 94 representative problems across all categories:

| System | Accuracy | Speed | Size | Cost |
|--------|----------|-------|------|------|
| **Math Swarm (SymPy)** | **94/94 (100%)** | **1.9ms** | **0 GPU** | **$0** |
| Qwen2.5-3B | 52/94 (55.3%) | 200ms | 1.8 GB | $0 |
| Qwen2.5-7B | 72/94 (76.6%) | 300ms | 4.4 GB | $0 |
| Qwen2.5-32B | 87/94 (92.6%) | 2,600ms | 18.5 GB | $0 |

**Key finding:** A 3B model + Math Swarm achieves 100% accuracy where a 32B model alone achieves 93%. Scaling parameters doesn't fix computation — architecture does.

### Where LLMs Fail (32B model, quantized, local)

| Category | 32B Accuracy | Failure Mode |
|----------|-------------|--------------|
| Mortgages | 5/5 (100%) | Gets lucky at this size — 3B and 7B get 0/5 |
| Compound Interest | 3/5 (60%) | Can't track exponential growth |
| Order of Operations | 7/8 (88%) | Flattens PEMDAS |
| Trigonometry | 6/8 (75%) | Confuses degree/radian, truncates irrationals |
| Negatives | 4/5 (80%) | Drops signs in chains |
| Statistics | 3/4 (75%) | Miscalculates std dev |

Math Swarm: 94/94 on all of the above.

## Full Test Coverage: 1,079 Problems

| Test Suite | Tests | Pass Rate | File |
|------------|-------|-----------|------|
| Core (arithmetic, finance, geometry, physics, conversion, percentage) | 771 | 100% | `stress_test_750.py` |
| New categories (trig, combinatorics, number theory, logarithms, statistics) | 258 | 100% | `stress_test_new_categories.py` |
| Healthcare (BMI, eGFR, MAP, MELD, QTc, CrCl, dosing) | 50 | 100% | `stress_test_healthcare.py` |

Run all tests:
```bash
python stress_test_750.py && python stress_test_new_categories.py && python stress_test_healthcare.py
```

## 12 Problem Categories

| Category | Examples | Engine |
|----------|----------|--------|
| Arithmetic | `347 * 893`, `2 + 3 * 4`, `2^32` | SymPy expression eval |
| Percentages | 15% tip on $237.85, 8.25% tax | Formula: base * pct/100 |
| Finance | Mortgage payments, compound interest, ROI, MELD | Named formulas + verification |
| Geometry | Circle area, sphere volume, Pythagorean theorem | Pi-precise computation |
| Physics | F=ma, KE=0.5mv^2 | Unit-aware extraction |
| Conversions | C-to-F, km-to-miles, kg-to-lbs | Exact conversion factors |
| Trigonometry | sin/cos/tan (degrees + radians), arcsin/arccos/arctan | SymPy symbolic trig |
| Combinatorics | n!, P(n,r), C(n,r) — up to 20! | SymPy factorial/binomial |
| Number Theory | GCD, LCM | Direct integer computation |
| Logarithms | ln, log10, log base N | SymPy symbolic log |
| Statistics | Mean, median, mode, std dev, variance, range | Data pipeline |
| Healthcare | BMI, eGFR, MAP, anion gap, MELD, QTc, CrCl, dosing | Clinical formulas + CDS |

## Healthcare: Clinical Decision Support

15 clinical formulas with guideline-based interpretation. Not just the number — the clinical meaning.

```
Query:   eGFR for 65 year old male creatinine 1.4
Result:  55.8 mL/min/1.73m2
Status:  G3a - Mildly to moderately decreased
Actions: Monitor every 6 months, check renally-dosed medications
Flags:   Adjust drug doses, consider nephrology referral if declining
Source:  KDIGO 2024 CKD Guidelines
LLM:     NONE - zero hallucination risk
```

### Clinical Formulas

| Formula | Use Case | Source |
|---------|----------|--------|
| BMI | Obesity screening | WHO Classification |
| eGFR (CKD-EPI 2021) | Kidney function staging | KDIGO 2024 |
| MAP | Organ perfusion assessment | AHA/ACC |
| Corrected Calcium | Hypoalbuminemia adjustment | Endocrine Society |
| Anion Gap | Metabolic acidosis workup | UpToDate |
| Cockcroft-Gault | Drug dosing (CrCl) | FDA Guidance |
| MELD Score | Liver transplant priority | UNOS Policy |
| QTc (Bazett) | Cardiac arrhythmia risk | AHA/ACC ECG |
| Pediatric Dosing | Weight-based (mg/kg) | Standard of care |
| IV Drip Rate | Infusion calculations | Standard of care |
| Ideal Body Weight | Dosing adjustment | Devine Formula |
| A-a Gradient | Pulmonary assessment | Pulmonology |

## Architecture

```
User prompt (natural language)
  |
  v
Parser ---- extract numbers, units, expressions (regex + SymPy)
  |
  v
Classifier - identify problem type (keyword + pattern scoring)
  |
  v
Planner ---- select formula, map variables
  |
  v
Compute ---- SymPy symbolic evaluation (EXACT, not approximate)
  |
  v
Verify ----- sanity checks (NaN, bounds, cross-verification)
  |
  v
Explain ---- formatted result with steps

Optional: Clinical Decision Support (deterministic lookup)
```

The LLM's only job: understand the question. All computation is SymPy. All interpretation is lookup tables. Zero hallucination surface.

## The Thesis

> Token prediction cannot guarantee mathematical correctness. It's architecturally impossible — you're sampling from a probability distribution, not computing. Separate perception (what's being asked?) from execution (compute the answer) and both work perfectly.

This is proven by the benchmark: 10x the parameters (3B to 32B) only moves accuracy from 55% to 93%. It never reaches 100% because the failure mode is architectural, not parametric. Math Swarm reaches 100% because computation is deterministic.

## Quick Start

```bash
pip install sympy
python math_swarm.py --interactive
```

```
math> What is the monthly payment on a $450,000 mortgage at 6.5% for 30 years?
Answer: $2,844.31 (verified, 2ms, $0)

math> eGFR for 65 year old male creatinine 1.4
Answer: 55.8 mL/min/1.73m2 (Stage 3a CKD — KDIGO 2024)
```

## Part of the Swarm Labs Ecosystem

- [Swarm Orchestrator](https://github.com/michaelwinczuk/swarm-orchestrator) — Multi-agent design patterns + chalkboard protocol
- [Knowledge Graph Reasoning](https://github.com/michaelwinczuk/knowledge-graph-reasoning) — 77+ KGs, adversarial validation, deterministic reasoning
- [PRISM](https://github.com/michaelwinczuk/prism) — Reliability primitives for multi-agent AI (VotingMesh, Sentinel, 95 tests)
- [Bastion](https://github.com/michaelwinczuk/bastion) — Safety kernel for agentic AI (consensus, verification, audit trails)

## License

Apache 2.0
