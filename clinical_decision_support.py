"""
Clinical Decision Support — Deterministic interpretation layer.

Takes Math Swarm computed values and returns clinical interpretation
using guideline-based lookup tables. ZERO LLM involvement in interpretation.

Every threshold, staging, and recommendation is sourced from published
clinical guidelines — not predicted by token probability.

For MedOne Systems / BOLT EHR integration.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClinicalInterpretation:
    """Structured clinical output — deterministic, sourced, auditable."""
    value: float
    unit: str
    interpretation: str          # e.g., "Stage 3a CKD"
    severity: str                # normal, mild, moderate, severe, critical
    actions: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    source: str = ""             # Guideline citation


# ── BMI Interpretation (WHO/CDC) ────────────────────────────────

def interpret_bmi(bmi: float) -> ClinicalInterpretation:
    if bmi < 16:
        stage, sev = "Severe Thinness", "critical"
        actions = ["Urgent nutritional assessment", "Evaluate for underlying pathology"]
    elif bmi < 17:
        stage, sev = "Moderate Thinness", "severe"
        actions = ["Nutritional counseling", "Monitor weight monthly"]
    elif bmi < 18.5:
        stage, sev = "Underweight", "mild"
        actions = ["Nutritional counseling", "Evaluate dietary intake"]
    elif bmi < 25:
        stage, sev = "Normal weight", "normal"
        actions = ["Routine follow-up"]
    elif bmi < 30:
        stage, sev = "Overweight", "mild"
        actions = ["Lifestyle modification counseling", "Diet and exercise plan"]
    elif bmi < 35:
        stage, sev = "Obesity Class I", "moderate"
        actions = ["Weight management program", "Screen for metabolic syndrome", "Consider referral to dietitian"]
    elif bmi < 40:
        stage, sev = "Obesity Class II", "severe"
        actions = ["Intensive weight management", "Screen for comorbidities", "Consider pharmacotherapy"]
    else:
        stage, sev = "Obesity Class III (Morbid)", "critical"
        actions = ["Bariatric surgery evaluation", "Comprehensive metabolic workup", "Multidisciplinary team referral"]

    return ClinicalInterpretation(
        value=round(bmi, 1), unit="kg/m²",
        interpretation=stage, severity=sev,
        actions=actions, source="WHO BMI Classification"
    )


# ── eGFR / CKD Staging (KDIGO 2024) ────────────────────────────

def interpret_egfr(egfr: float) -> ClinicalInterpretation:
    if egfr >= 90:
        stage, sev = "G1 — Normal or high", "normal"
        actions = ["Routine monitoring annually"]
        flags = []
    elif egfr >= 60:
        stage, sev = "G2 — Mildly decreased", "mild"
        actions = ["Monitor annually", "Assess CVD risk factors"]
        flags = []
    elif egfr >= 45:
        stage, sev = "G3a — Mildly to moderately decreased", "moderate"
        actions = ["Monitor every 6 months", "Check renally-dosed medications",
                   "Assess for complications (anemia, bone disease)"]
        flags = ["Adjust drug doses for renal function", "Consider nephrology referral if declining"]
    elif egfr >= 30:
        stage, sev = "G3b — Moderately to severely decreased", "moderate"
        actions = ["Monitor every 3-6 months", "Nephrology referral",
                   "Adjust all renally-cleared medications"]
        flags = ["Avoid nephrotoxic agents", "Monitor potassium and phosphorus"]
    elif egfr >= 15:
        stage, sev = "G4 — Severely decreased", "severe"
        actions = ["Nephrology co-management", "Prepare for renal replacement therapy",
                   "Monitor monthly"]
        flags = ["Pre-dialysis education", "Vascular access planning", "Avoid NSAIDs, contrast dye"]
    else:
        stage, sev = "G5 — Kidney failure", "critical"
        actions = ["Urgent nephrology", "Initiate dialysis planning",
                   "Transplant evaluation if appropriate"]
        flags = ["Dialysis indicated", "Strict potassium and fluid restriction"]

    return ClinicalInterpretation(
        value=round(egfr, 1), unit="mL/min/1.73m²",
        interpretation=stage, severity=sev,
        actions=actions, flags=flags,
        source="KDIGO 2024 CKD Guidelines"
    )


# ── MAP Interpretation ──────────────────────────────────────────

def interpret_map(map_val: float) -> ClinicalInterpretation:
    if map_val < 60:
        stage, sev = "Hypotension — organ perfusion at risk", "critical"
        actions = ["Immediate fluid resuscitation", "Vasopressor evaluation", "Assess for shock"]
        flags = ["End-organ damage risk", "ICU-level monitoring"]
    elif map_val < 70:
        stage, sev = "Low-normal — monitor closely", "mild"
        actions = ["Assess volume status", "Monitor urine output"]
        flags = ["Borderline perfusion pressure"]
    elif map_val <= 100:
        stage, sev = "Normal", "normal"
        actions = ["Routine monitoring"]
        flags = []
    elif map_val <= 110:
        stage, sev = "Mildly elevated", "mild"
        actions = ["Recheck in 15 minutes", "Assess pain and anxiety"]
        flags = []
    else:
        stage, sev = "Hypertensive — end-organ damage risk", "severe"
        actions = ["Stat antihypertensive evaluation", "Check for end-organ symptoms",
                   "ECG, troponin, renal panel"]
        flags = ["Hypertensive urgency/emergency workup"]

    return ClinicalInterpretation(
        value=round(map_val, 1), unit="mmHg",
        interpretation=stage, severity=sev,
        actions=actions, flags=flags,
        source="AHA/ACC Blood Pressure Guidelines"
    )


# ── Corrected Calcium ───────────────────────────────────────────

def interpret_corrected_calcium(ca: float) -> ClinicalInterpretation:
    if ca < 8.5:
        stage, sev = "Hypocalcemia", "moderate"
        actions = ["Check ionized calcium", "Assess magnesium and vitamin D",
                   "ECG for QT prolongation"]
        flags = ["Risk of tetany, seizures if severe"]
    elif ca <= 10.5:
        stage, sev = "Normal", "normal"
        actions = ["Routine monitoring"]
        flags = []
    elif ca <= 12.0:
        stage, sev = "Mild hypercalcemia", "mild"
        actions = ["Check PTH, Vitamin D", "Hydration", "Recheck in 1-2 weeks"]
        flags = ["Evaluate for primary hyperparathyroidism"]
    elif ca <= 14.0:
        stage, sev = "Moderate hypercalcemia", "moderate"
        actions = ["IV normal saline hydration", "Check PTH, PTHrP", "Evaluate for malignancy"]
        flags = ["Cardiac monitoring", "Monitor renal function"]
    else:
        stage, sev = "Severe hypercalcemia — life-threatening", "critical"
        actions = ["Emergent IV hydration", "Calcitonin", "Consider bisphosphonate",
                   "ICU admission"]
        flags = ["Risk of cardiac arrest", "Immediate treatment required"]

    return ClinicalInterpretation(
        value=round(ca, 1), unit="mg/dL (corrected)",
        interpretation=stage, severity=sev,
        actions=actions, flags=flags,
        source="Endocrine Society Guidelines"
    )


# ── Anion Gap ───────────────────────────────────────────────────

def interpret_anion_gap(ag: float) -> ClinicalInterpretation:
    if ag < 3:
        stage, sev = "Low — consider lab error or hypoalbuminemia", "mild"
        actions = ["Recheck electrolytes", "Check albumin"]
        flags = ["Low AG can indicate lab error, hypoalbuminemia, or lithium toxicity"]
    elif ag <= 12:
        stage, sev = "Normal", "normal"
        actions = ["No action needed"]
        flags = []
    elif ag <= 20:
        stage, sev = "Elevated — anion gap metabolic acidosis", "moderate"
        actions = ["Check lactate, ketones, BUN/Cr", "Evaluate for MUDPILES causes",
                   "Check osmolar gap"]
        flags = ["MUDPILES: Methanol, Uremia, DKA, Propylene glycol, INH/Iron, Lactic acidosis, Ethylene glycol, Salicylates"]
    else:
        stage, sev = "Severely elevated — critical metabolic acidosis", "critical"
        actions = ["Urgent ABG", "Stat lactate and ketones", "Toxicology screen",
                   "Consider empiric treatment for toxic ingestion"]
        flags = ["Consider ICU admission", "Evaluate for DKA, lactic acidosis, toxic ingestion"]

    return ClinicalInterpretation(
        value=round(ag, 1), unit="mEq/L",
        interpretation=stage, severity=sev,
        actions=actions, flags=flags,
        source="UpToDate Anion Gap Acidosis"
    )


# ── MELD Score ──────────────────────────────────────────────────

def interpret_meld(meld: float) -> ClinicalInterpretation:
    meld_rounded = round(meld)
    if meld_rounded <= 9:
        stage, sev = "Low — 1.9% 3-month mortality", "normal"
        actions = ["Routine monitoring", "Reassess every 3 months"]
    elif meld_rounded <= 19:
        stage, sev = "Moderate — 6% 3-month mortality", "mild"
        actions = ["Monitor every 1-3 months", "Transplant evaluation if appropriate"]
    elif meld_rounded <= 29:
        stage, sev = "High — 19.6% 3-month mortality", "moderate"
        actions = ["Active transplant listing", "Monitor monthly", "Optimize nutrition"]
    elif meld_rounded <= 39:
        stage, sev = "Very high — 52.6% 3-month mortality", "severe"
        actions = ["Urgent transplant priority", "ICU monitoring if decompensated"]
    else:
        stage, sev = "Critical — 71.3% 3-month mortality", "critical"
        actions = ["Highest transplant priority (Status 1)", "Intensive care"]

    return ClinicalInterpretation(
        value=meld_rounded, unit="points",
        interpretation=stage, severity=sev,
        actions=actions,
        source="UNOS MELD Allocation Policy"
    )


# ── QTc Interpretation ──────────────────────────────────────────

def interpret_qtc(qtc: float) -> ClinicalInterpretation:
    if qtc < 350:
        stage, sev = "Short QT — evaluate for short QT syndrome", "mild"
        actions = ["Cardiology referral", "Genetic testing consideration"]
        flags = ["Risk of atrial/ventricular arrhythmias"]
    elif qtc <= 440:
        stage, sev = "Normal QTc", "normal"
        actions = ["No action needed"]
        flags = []
    elif qtc <= 470:
        stage, sev = "Borderline prolonged", "mild"
        actions = ["Review QT-prolonging medications", "Recheck with repeat ECG",
                   "Check K+, Mg2+, Ca2+"]
        flags = ["Avoid additional QT-prolonging drugs"]
    elif qtc <= 500:
        stage, sev = "Prolonged QTc", "moderate"
        actions = ["Discontinue QT-prolonging medications", "Correct electrolytes",
                   "Cardiology consultation", "Continuous telemetry"]
        flags = ["Risk of Torsades de Pointes", "Hold offending medications"]
    else:
        stage, sev = "Critically prolonged — high arrhythmia risk", "critical"
        actions = ["Immediate telemetry", "Discontinue ALL QT-prolonging drugs",
                   "Stat Mg2+ and K+ correction", "Cardiology stat consult"]
        flags = ["Imminent Torsades de Pointes risk", "Consider isoproterenol or temporary pacing"]

    return ClinicalInterpretation(
        value=round(qtc, 1), unit="ms",
        interpretation=stage, severity=sev,
        actions=actions, flags=flags,
        source="AHA/ACC ECG Interpretation Guidelines"
    )


# ── Creatinine Clearance (Drug Dosing) ──────────────────────────

def interpret_crcl(crcl: float) -> ClinicalInterpretation:
    if crcl >= 90:
        stage, sev = "Normal renal function", "normal"
        actions = ["Standard drug dosing"]
        flags = []
    elif crcl >= 60:
        stage, sev = "Mild impairment", "mild"
        actions = ["Check package inserts for dose adjustments", "Monitor renal function"]
        flags = ["Some drugs require adjustment (e.g., gabapentin, metformin)"]
    elif crcl >= 30:
        stage, sev = "Moderate impairment", "moderate"
        actions = ["Reduce doses of renally-cleared drugs", "Avoid nephrotoxins",
                   "Consult pharmacy for dosing"]
        flags = ["Dose-adjust: aminoglycosides, vancomycin, DOACs, metformin"]
    elif crcl >= 15:
        stage, sev = "Severe impairment", "severe"
        actions = ["Major dose reductions required", "Pharmacy consult mandatory",
                   "Avoid contrast dye if possible"]
        flags = ["Many drugs contraindicated", "Dialysis may affect drug clearance"]
    else:
        stage, sev = "End-stage renal disease", "critical"
        actions = ["Dialysis dosing protocols", "Nephrology + pharmacy co-management"]
        flags = ["Supplement doses post-dialysis for dialyzable drugs"]

    return ClinicalInterpretation(
        value=round(crcl, 1), unit="mL/min",
        interpretation=stage, severity=sev,
        actions=actions, flags=flags,
        source="FDA Renal Dosing Guidance"
    )


# ── Dispatcher ──────────────────────────────────────────────────

INTERPRETERS = {
    "bmi": interpret_bmi,
    "egfr_male": interpret_egfr,
    "egfr_female": interpret_egfr,
    "map": interpret_map,
    "corrected_calcium": interpret_corrected_calcium,
    "anion_gap": interpret_anion_gap,
    "meld_score": interpret_meld,
    "qtc_bazett": interpret_qtc,
    "cockcroft_gault_male": interpret_crcl,
    "cockcroft_gault_female": interpret_crcl,
}


def interpret(formula_name: str, value: float) -> Optional[ClinicalInterpretation]:
    """Get clinical interpretation for a computed value."""
    fn = INTERPRETERS.get(formula_name)
    if fn:
        return fn(value)
    return None


def format_clinical_output(problem: str, result: dict, interp: ClinicalInterpretation) -> str:
    """Format a complete clinical decision support output."""
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  CLINICAL DECISION SUPPORT")
    lines.append(f"{'='*60}")
    lines.append(f"  Query:   {problem}")
    lines.append(f"  Result:  {interp.value} {interp.unit}")
    lines.append(f"  Status:  {interp.interpretation}")
    lines.append(f"  Severity: {interp.severity.upper()}")
    lines.append(f"")
    if interp.actions:
        lines.append(f"  Recommended Actions:")
        for a in interp.actions:
            lines.append(f"    • {a}")
    if interp.flags:
        lines.append(f"")
        lines.append(f"  ** Clinical Flags:")
        for f in interp.flags:
            lines.append(f"    >> {f}")
    lines.append(f"")
    lines.append(f"  Source: {interp.source}")
    lines.append(f"  Computed by: Math Swarm (SymPy) — deterministic, verified")
    lines.append(f"  LLM involvement: NONE — zero hallucination risk")
    lines.append(f"{'='*60}")
    return "\n".join(lines)


# ── Demo ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from math_swarm import solve

    demos = [
        "eGFR for 65 year old male creatinine 1.4",
        "Calculate BMI for weight 110 kg height 1.70 m",
        "Mean arterial pressure for blood pressure 85/55",
        "QTc for QT 480 ms heart rate 65",
        "Anion gap with sodium 148 chloride 100 bicarbonate 18",
        "MELD score for creatinine 3.0 bilirubin 8.0 INR 2.2",
        "Creatinine clearance for 72 year old female weight 55 kg creatinine 1.8",
        "Corrected calcium for Ca 7.5 albumin 2.0",
    ]

    for problem in demos:
        r = solve(problem)
        formula = r.get("formula_used", "")
        answer = r.get("answer")

        if answer is not None and formula in INTERPRETERS:
            interp = interpret(formula, answer)
            if interp:
                print(format_clinical_output(problem, r, interp))
                print()
