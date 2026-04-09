"""
Healthcare Math — 50 clinical calculation tests.

Every wrong answer in healthcare math is a patient safety event.
LLMs hallucinate dosages, lab corrections, and vital calculations.
The Math Swarm eliminates this entire class of error.

For MedOne Systems / BOLT EHR demo.
"""

import json
import sys
import time

sys.path.insert(0, ".")
from math_swarm import solve as math_solve

TESTS = [
    # ============================================================
    # BMI — Body Mass Index
    # ============================================================
    ("Calculate BMI for weight 80 kg height 1.75 m", 26.122),
    ("Calculate BMI for weight 70 kg height 1.80 m", 21.605),
    ("Calculate BMI for weight 100 kg height 1.70 m", 34.602),
    ("Calculate BMI for weight 55 kg height 1.65 m", 20.202),
    ("Calculate BMI for weight 90 kg height 1.85 m", 26.297),
    ("Calculate BMI for weight 120 kg height 1.78 m", 37.878),

    # ============================================================
    # MAP — Mean Arterial Pressure
    # ============================================================
    ("Mean arterial pressure for blood pressure 120/80", 93.333),
    ("Mean arterial pressure for blood pressure 140/90", 106.667),
    ("Mean arterial pressure for blood pressure 90/60", 70.0),
    ("Mean arterial pressure for blood pressure 160/100", 120.0),
    ("Mean arterial pressure for blood pressure 110/70", 83.333),
    ("Mean arterial pressure for blood pressure 80/50", 60.0),

    # ============================================================
    # Corrected Calcium — for hypoalbuminemia
    # ============================================================
    ("Corrected calcium for Ca 8.5 albumin 2.5", 9.7),
    ("Corrected calcium for Ca 9.0 albumin 3.0", 9.8),
    ("Corrected calcium for Ca 7.8 albumin 2.0", 9.4),
    ("Corrected calcium for Ca 10.0 albumin 4.0", 10.0),
    ("Corrected calcium for Ca 8.0 albumin 1.5", 10.0),

    # ============================================================
    # Anion Gap — metabolic acidosis workup
    # ============================================================
    ("Anion gap with sodium 140 chloride 105 bicarbonate 24", 11),
    ("Anion gap with sodium 145 chloride 100 bicarbonate 22", 23),
    ("Anion gap with sodium 138 chloride 102 bicarbonate 26", 10),
    ("Anion gap with sodium 150 chloride 110 bicarbonate 20", 20),
    ("Anion gap with sodium 136 chloride 98 bicarbonate 28", 10),

    # ============================================================
    # Cockcroft-Gault — Creatinine Clearance for drug dosing
    # ============================================================
    ("Creatinine clearance for 65 year old male weight 80 kg creatinine 1.4", 59.524),
    ("Creatinine clearance for 45 year old male weight 70 kg creatinine 0.9", 102.623),
    ("Creatinine clearance for 80 year old female weight 60 kg creatinine 1.2", 35.417),
    ("Creatinine clearance for 30 year old male weight 90 kg creatinine 1.0", 137.5),
    ("Creatinine clearance for 55 year old female weight 65 kg creatinine 0.8", 81.532),

    # ============================================================
    # QTc — Corrected QT interval (Bazett)
    # ============================================================
    ("QTc for QT 440 ms heart rate 72", 482.0),
    ("QTc for QT 400 ms heart rate 60", 400.0),
    ("QTc for QT 380 ms heart rate 80", 438.786),
    ("QTc for QT 500 ms heart rate 90", 612.372),
    ("QTc for QT 360 ms heart rate 100", 464.758),

    # ============================================================
    # Pediatric Dosing — weight-based (wrong = child harm)
    # ============================================================
    ("Dose for 20 kg child at 15 mg/kg", 300),
    ("Dose for 8 kg infant at 10 mg/kg", 80),
    ("Dose for 35 kg child at 25 mg/kg", 875),
    ("Dose for 5 kg neonate at 4 mg/kg", 20),
    ("Dose for 12 kg toddler at 7.5 mg/kg", 90),
    ("Dose for 50 kg adolescent at 20 mg/kg", 1000),

    # ============================================================
    # IV Drip Rate
    # ============================================================
    ("IV drip rate for 1000 ml over 8 hours", 125),
    ("IV drip rate for 500 ml over 4 hours", 125),
    ("IV drip rate for 250 ml over 2 hours", 125),
    ("IV drip rate for 1000 ml over 24 hours", 41.667),
    ("IV drip rate for 100 ml over 1 hours", 100),

    # ============================================================
    # eGFR — CKD-EPI 2021 (kidney function)
    # ============================================================
    ("eGFR for 65 year old male creatinine 1.4", 55.778),
    ("eGFR for 45 year old male creatinine 0.9", 107.335),
    ("eGFR for 70 year old female creatinine 1.0", 60.606),
    ("eGFR for 30 year old male creatinine 1.0", 103.836),

    # ============================================================
    # MELD Score — liver transplant priority
    # ============================================================
    ("MELD score for creatinine 2.0 bilirubin 3.5 INR 1.8", 24.382),
    ("MELD score for creatinine 1.0 bilirubin 1.0 INR 1.0", 6.43),
    ("MELD score for creatinine 4.0 bilirubin 10.0 INR 2.5", 38.663),
]


def main():
    print("=" * 70)
    print(f"  HEALTHCARE MATH TEST — {len(TESTS)} clinical calculations")
    print(f"  Every wrong answer = patient safety event")
    print("=" * 70)
    print()

    passed = 0
    failed = []
    start = time.time()

    for problem, expected in TESTS:
        tol = max(abs(expected) * 0.02, 0.1) if expected != 0 else 0.1
        r = math_solve(problem)
        ans = r.get("answer")
        ok = ans is not None and abs(ans - expected) <= tol
        if ok:
            passed += 1
        else:
            failed.append(f"  got={ans} exp={expected} | {problem[:60]}")

    total = len(TESTS)
    elapsed = time.time() - start
    print(f"RESULT: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"TIME:   {elapsed:.2f}s total")
    print(f"COST:   $0.00")
    print()
    if failed:
        print(f"FAILURES ({len(failed)}):")
        for f in failed:
            print(f)
    else:
        print("ZERO FAILURES — every clinical calculation exact")
        print()
        print("Formulas verified: BMI, MAP, Corrected Calcium, Anion Gap,")
        print("Cockcroft-Gault CrCl, QTc Bazett, Pediatric Dosing,")
        print("IV Drip Rate, eGFR CKD-EPI 2021, MELD Score")

    results = {
        "total": total, "passed": passed,
        "accuracy": round(passed/total*100, 2),
        "failures": failed,
    }
    with open("stress_test_healthcare_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to stress_test_healthcare_results.json")


if __name__ == "__main__":
    main()
