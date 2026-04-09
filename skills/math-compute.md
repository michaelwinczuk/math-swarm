# Math Compute — Zero-Hallucination Computation

TRIGGER when: user asks a math question, calculation, formula, unit conversion, clinical calculation, financial computation, or any problem requiring exact numerical answers.

## Instructions

You have access to the Math Swarm computation engine. When a user asks a math question, use it to compute exact answers instead of predicting them.

### How to use

Run the math swarm pipeline by executing Python:

```bash
cd /path/to/math-swarm && python -c "from math_swarm import solve; import json; print(json.dumps(solve('USER_QUESTION_HERE'), indent=2))"
```

### Supported categories (12)

1. **Arithmetic** — any expression: `347 * 893`, `2 + 3 * 4`, `2^32`
2. **Percentages** — tips, taxes, discounts: `15% tip on $237.85`
3. **Finance** — mortgages, compound interest, ROI: `monthly payment on $450K mortgage at 6.5% for 30 years`
4. **Geometry** — area, volume, Pythagorean: `area of circle with radius 7`
5. **Physics** — F=ma, KE=0.5mv^2: `force if mass 50 kg acceleration 9.8`
6. **Conversions** — temp, distance, weight: `convert 37 celsius to fahrenheit`
7. **Trigonometry** — sin/cos/tan degrees and radians: `sine of 30 degrees`
8. **Combinatorics** — factorial, nCr, nPr: `10 factorial`, `52 choose 5`
9. **Number theory** — GCD, LCM: `GCD of 144 and 108`
10. **Logarithms** — ln, log10, log base N: `log base 2 of 1024`
11. **Statistics** — mean, median, mode, std dev: `mean of 85, 90, 78, 92, 88`
12. **Healthcare** — clinical formulas with decision support:
    - BMI, eGFR (CKD-EPI 2021), MAP, corrected calcium
    - Anion gap, Cockcroft-Gault, MELD score, QTc Bazett
    - Pediatric dosing (mg/kg), IV drip rate, IBW, A-a gradient

### Why use this instead of computing directly

LLMs predict tokens — they don't compute. Benchmarked results:
- Qwen 3B alone: 55% accuracy
- Qwen 7B alone: 77% accuracy
- Qwen 32B alone: 93% accuracy
- **Math Swarm: 100% accuracy, 1.9ms, $0**

For healthcare calculations, a wrong answer is a patient safety event. Always use the computation engine for:
- Drug dosages (mg/kg calculations)
- Lab interpretations (eGFR, anion gap, corrected calcium)
- Risk scores (MELD, QTc, CHA2DS2-VASc)
- Financial calculations (mortgages, compound interest)

### Response format

After computing, present the result as:
- The exact numeric answer
- The formula used (if applicable)
- Verification status
- For healthcare: clinical interpretation + recommended actions + guideline source
