"""
250+ tests for the 5 NEW math swarm categories.
Covers: trigonometry, combinatorics, number theory, logarithms, statistics.

Combined with stress_test_750.py (771 tests), total coverage: 1000+ tests.
"""

import json
import math
import sys
import time

sys.path.insert(0, ".")
from math_swarm import solve as math_solve

TESTS = [
    # ============================================================
    # TRIGONOMETRY — 60 problems
    #   LLMs confuse degrees/radians, truncate irrational results
    # ============================================================
    # Sine
    ("What is the sine of 0 degrees?", 0.0),
    ("What is the sine of 30 degrees?", 0.5),
    ("What is the sine of 45 degrees?", 0.707107),
    ("What is the sine of 60 degrees?", 0.866025),
    ("What is the sine of 90 degrees?", 1.0),
    ("What is the sine of 120 degrees?", 0.866025),
    ("What is the sine of 135 degrees?", 0.707107),
    ("What is the sine of 150 degrees?", 0.5),
    ("What is the sine of 180 degrees?", 0.0),
    ("What is the sine of 270 degrees?", -1.0),
    ("What is the sine of 360 degrees?", 0.0),
    ("What is the sine of 15 degrees?", 0.258819),
    ("What is the sine of 75 degrees?", 0.965926),
    ("What is the sine of 10 degrees?", 0.173648),
    ("What is the sine of 1 degrees?", 0.017452),
    # Cosine
    ("What is the cosine of 0 degrees?", 1.0),
    ("What is the cosine of 30 degrees?", 0.866025),
    ("What is the cosine of 45 degrees?", 0.707107),
    ("What is the cosine of 60 degrees?", 0.5),
    ("What is the cosine of 90 degrees?", 0.0),
    ("What is the cosine of 120 degrees?", -0.5),
    ("What is the cosine of 135 degrees?", -0.707107),
    ("What is the cosine of 150 degrees?", -0.866025),
    ("What is the cosine of 180 degrees?", -1.0),
    ("What is the cosine of 270 degrees?", 0.0),
    ("What is the cosine of 360 degrees?", 1.0),
    ("What is the cosine of 15 degrees?", 0.965926),
    ("What is the cosine of 75 degrees?", 0.258819),
    ("What is the cosine of 10 degrees?", 0.984808),
    # Tangent
    ("What is the tangent of 0 degrees?", 0.0),
    ("What is the tangent of 30 degrees?", 0.577350),
    ("What is the tangent of 45 degrees?", 1.0),
    ("What is the tangent of 60 degrees?", 1.732051),
    ("What is the tangent of 135 degrees?", -1.0),
    ("What is the tangent of 150 degrees?", -0.577350),
    ("What is the tangent of 180 degrees?", 0.0),
    ("What is the tangent of 15 degrees?", 0.267949),
    ("What is the tangent of 75 degrees?", 3.732051),
    ("What is the tangent of 10 degrees?", 0.176327),
    # Inverse trig
    ("What is the arcsin of 0?", 0.0),
    ("What is the arcsin of 0.5?", 30.0),
    ("What is the arcsin of 1?", 90.0),
    ("What is the arcsin of -1?", -90.0),
    ("What is the arccos of 1?", 0.0),
    ("What is the arccos of 0.5?", 60.0),
    ("What is the arccos of 0?", 90.0),
    ("What is the arccos of -1?", 180.0),
    ("What is the arctan of 0?", 0.0),
    ("What is the arctan of 1?", 45.0),
    ("What is the arctan of -1?", -45.0),
    # Edge cases LLMs get wrong
    ("What is the sine of 90 degrees?", 1.0),     # LLMs sometimes say 0
    ("What is the cosine of 90 degrees?", 0.0),    # LLMs sometimes say 1
    ("What is the sine of 180 degrees?", 0.0),     # LLMs sometimes say 1
    ("What is the cosine of 180 degrees?", -1.0),  # LLMs forget the negative
    ("What is the sine of 270 degrees?", -1.0),    # LLMs forget the negative
    ("What is the sine of 45 degrees?", 0.707107), # LLMs round to 0.71 or 0.7
    ("What is the tangent of 30 degrees?", 0.577350), # LLMs say 0.58 or 1/sqrt(3)
    ("What is the cosine of 45 degrees?", 0.707107),
    ("What is the tangent of 60 degrees?", 1.732051), # LLMs say sqrt(3) but round wrong
    ("What is the arccos of -0.5?", 120.0),

    # ============================================================
    # COMBINATORICS — 50 problems
    #   LLMs hallucinate factorial values above 7!
    # ============================================================
    # Factorials
    ("What is 0 factorial?", 1),
    ("What is 1 factorial?", 1),
    ("What is 2 factorial?", 2),
    ("What is 3 factorial?", 6),
    ("What is 4 factorial?", 24),
    ("What is 5 factorial?", 120),
    ("What is 6 factorial?", 720),
    ("What is 7 factorial?", 5040),
    ("What is 8 factorial?", 40320),
    ("What is 9 factorial?", 362880),
    ("What is 10 factorial?", 3628800),
    ("What is 11 factorial?", 39916800),
    ("What is 12 factorial?", 479001600),
    ("What is 13 factorial?", 6227020800),
    ("What is 15 factorial?", 1307674368000),
    ("What is 20 factorial?", 2432902008176640000),
    # Combinations C(n,r)
    ("How many combinations of 5 choose 2?", 10),
    ("How many combinations of 6 choose 3?", 20),
    ("How many combinations of 10 choose 3?", 120),
    ("How many combinations of 10 choose 5?", 252),
    ("How many combinations of 10 choose 7?", 120),  # C(10,7) = C(10,3) = 120
    ("How many combinations of 12 choose 4?", 495),
    ("How many combinations of 15 choose 5?", 3003),
    ("How many combinations of 20 choose 10?", 184756),
    ("How many combinations of 52 choose 5?", 2598960),  # Poker hands
    ("How many combinations of 6 choose 1?", 6),
    ("How many combinations of 6 choose 6?", 1),
    ("How many combinations of 100 choose 2?", 4950),
    ("How many combinations of 8 choose 4?", 70),
    ("How many combinations of 7 choose 3?", 35),
    ("How many combinations of 9 choose 4?", 126),
    ("How many combinations of 4 choose 2?", 6),
    # Permutations P(n,r)
    ("How many permutations of 3 from 5?", 60),
    ("How many permutations of 2 from 10?", 90),
    ("How many permutations of 3 from 10?", 720),
    ("How many permutations of 4 from 8?", 1680),
    ("How many permutations of 5 from 10?", 30240),
    ("How many permutations of 3 from 7?", 210),
    ("How many permutations of 2 from 6?", 30),
    ("How many permutations of 4 from 12?", 11880),
    ("How many permutations of 3 from 20?", 6840),
    ("How many permutations of 2 from 52?", 2652),
    # Edge cases
    ("How many combinations of 5 choose 0?", 1),
    ("How many combinations of 10 choose 10?", 1),
    ("How many combinations of 10 choose 1?", 10),
    ("What is 14 factorial?", 87178291200),
    ("How many permutations of 1 from 100?", 100),
    ("How many combinations of 3 choose 2?", 3),
    ("How many combinations of 4 choose 3?", 4),
    ("How many combinations of 50 choose 2?", 1225),
    ("How many combinations of 26 choose 2?", 325),
    ("How many permutations of 2 from 5?", 20),

    # ============================================================
    # NUMBER THEORY — 50 problems
    #   LLMs frequently miscalculate GCD/LCM for larger numbers
    # ============================================================
    # GCD
    ("What is the GCD of 12 and 8?", 4),
    ("What is the GCD of 48 and 36?", 12),
    ("What is the GCD of 100 and 75?", 25),
    ("What is the GCD of 24 and 18?", 6),
    ("What is the GCD of 15 and 25?", 5),
    ("What is the GCD of 56 and 42?", 14),
    ("What is the GCD of 90 and 60?", 30),
    ("What is the GCD of 144 and 108?", 36),
    ("What is the GCD of 1000 and 750?", 250),
    ("What is the GCD of 252 and 105?", 21),
    ("What is the GCD of 36 and 48?", 12),
    ("What is the GCD of 7 and 11?", 1),
    ("What is the GCD of 13 and 17?", 1),
    ("What is the GCD of 100 and 10?", 10),
    ("What is the GCD of 1024 and 512?", 512),
    ("What is the GCD of 360 and 240?", 120),
    ("What is the GCD of 84 and 126?", 42),
    ("What is the GCD of 210 and 330?", 30),
    ("What is the GCD of 99 and 66?", 33),
    ("What is the GCD of 150 and 225?", 75),
    ("What is the greatest common divisor of 18 and 24?", 6),
    ("What is the greatest common divisor of 45 and 30?", 15),
    ("What is the greatest common divisor of 72 and 48?", 24),
    ("What is the greatest common divisor of 120 and 84?", 12),
    ("What is the greatest common divisor of 36 and 54?", 18),
    # LCM
    ("What is the LCM of 4 and 6?", 12),
    ("What is the LCM of 12 and 15?", 60),
    ("What is the LCM of 8 and 12?", 24),
    ("What is the LCM of 3 and 5?", 15),
    ("What is the LCM of 6 and 10?", 30),
    ("What is the LCM of 7 and 11?", 77),
    ("What is the LCM of 12 and 18?", 36),
    ("What is the LCM of 15 and 20?", 60),
    ("What is the LCM of 24 and 36?", 72),
    ("What is the LCM of 100 and 150?", 300),
    ("What is the LCM of 9 and 12?", 36),
    ("What is the LCM of 14 and 21?", 42),
    ("What is the LCM of 25 and 30?", 150),
    ("What is the LCM of 8 and 14?", 56),
    ("What is the LCM of 16 and 24?", 48),
    ("What is the least common multiple of 6 and 8?", 24),
    ("What is the least common multiple of 10 and 15?", 30),
    ("What is the least common multiple of 12 and 16?", 48),
    ("What is the least common multiple of 20 and 30?", 60),
    ("What is the least common multiple of 5 and 7?", 35),

    # ============================================================
    # LOGARITHMS — 50 problems
    #   LLMs hallucinate log values, especially non-integer results
    # ============================================================
    # Natural log (ln)
    ("What is ln(1)?", 0.0),
    ("What is the natural log of 1?", 0.0),
    ("What is ln(10)?", 2.302585),
    ("What is ln(100)?", 4.605170),
    ("What is ln(1000)?", 6.907755),
    ("What is the natural log of 2?", 0.693147),
    ("What is the natural log of 3?", 1.098612),
    ("What is the natural log of 5?", 1.609438),
    ("What is the natural log of 7?", 1.945910),
    ("What is the natural log of 50?", 3.912023),
    # Log base 10
    ("What is log(10)?", 1.0),
    ("What is log(100)?", 2.0),
    ("What is log(1000)?", 3.0),
    ("What is log(10000)?", 4.0),
    ("What is log(1000000)?", 6.0),
    ("What is log(50)?", 1.698970),
    ("What is log(500)?", 2.698970),
    ("What is log(2)?", 0.301030),
    ("What is log(3)?", 0.477121),
    ("What is log(5)?", 0.698970),
    ("What is log(7)?", 0.845098),
    ("What is log(20)?", 1.301030),
    ("What is log(200)?", 2.301030),
    ("What is log(0.1)?", -1.0),
    ("What is log(0.01)?", -2.0),
    # Log base N
    ("What is log base 2 of 2?", 1.0),
    ("What is log base 2 of 4?", 2.0),
    ("What is log base 2 of 8?", 3.0),
    ("What is log base 2 of 16?", 4.0),
    ("What is log base 2 of 32?", 5.0),
    ("What is log base 2 of 64?", 6.0),
    ("What is log base 2 of 128?", 7.0),
    ("What is log base 2 of 256?", 8.0),
    ("What is log base 2 of 512?", 9.0),
    ("What is log base 2 of 1024?", 10.0),
    ("What is log base 3 of 9?", 2.0),
    ("What is log base 3 of 27?", 3.0),
    ("What is log base 3 of 81?", 4.0),
    ("What is log base 3 of 243?", 5.0),
    ("What is log base 5 of 25?", 2.0),
    ("What is log base 5 of 125?", 3.0),
    ("What is log base 5 of 625?", 4.0),
    ("What is log base 4 of 16?", 2.0),
    ("What is log base 4 of 64?", 3.0),
    ("What is log base 4 of 256?", 4.0),
    ("What is log base 8 of 64?", 2.0),
    ("What is log base 8 of 512?", 3.0),
    ("What is log base 10 of 1000?", 3.0),
    ("What is log base 16 of 256?", 2.0),
    ("What is log base 2 of 65536?", 16.0),

    # ============================================================
    # STATISTICS — 50 problems
    #   LLMs miscalculate with datasets, especially median/std dev
    # ============================================================
    # Mean
    ("What is the mean of 1, 2, 3, 4, 5?", 3.0),
    ("What is the mean of 10, 20, 30?", 20.0),
    ("What is the mean of 10, 20, 30, 40, 50?", 30.0),
    ("What is the mean of 100, 200, 300, 400?", 250.0),
    ("What is the mean of 5, 10, 15, 20, 25, 30?", 17.5),
    ("What is the mean of 1, 1, 1, 1, 1?", 1.0),
    ("What is the mean of 0, 0, 0, 10?", 2.5),
    ("What is the mean of 85, 90, 78, 92, 88?", 86.6),
    ("What is the mean of 3, 7, 11, 15, 19?", 11.0),
    ("What is the average of 50, 60, 70, 80, 90?", 70.0),
    ("What is the average of 2, 4, 6, 8?", 5.0),
    ("What is the average of 100, 0?", 50.0),
    # Median
    ("What is the median of 1, 2, 3, 4, 5?", 3.0),
    ("What is the median of 1, 3, 5, 7, 9?", 5.0),
    ("What is the median of 10, 20, 30, 40?", 25.0),
    ("What is the median of 1, 2, 3, 4?", 2.5),
    ("What is the median of 5, 1, 3, 2, 4?", 3.0),
    ("What is the median of 100, 200, 300?", 200.0),
    ("What is the median of 10, 10, 10?", 10.0),
    ("What is the median of 1, 100?", 50.5),
    ("What is the median of 3, 7, 2, 9, 5?", 5.0),
    ("What is the median of 15, 25, 35, 45, 55?", 35.0),
    # Standard deviation
    ("What is the standard deviation of 2, 4, 4, 4, 5, 5, 7, 9?", 2.0),
    ("What is the standard deviation of 10, 10, 10, 10?", 0.0),
    ("What is the standard deviation of 1, 2, 3, 4, 5?", 1.414214),
    ("What is the standard deviation of 0, 10?", 5.0),
    ("What is the standard deviation of 5, 5, 5, 5, 5?", 0.0),
    ("What is the standard deviation of 1, 3, 5, 7, 9?", 2.828427),
    # Variance
    ("What is the variance of 2, 4, 4, 4, 5, 5, 7, 9?", 4.0),
    ("What is the variance of 10, 10, 10?", 0.0),
    ("What is the variance of 1, 2, 3, 4, 5?", 2.0),
    ("What is the variance of 0, 10?", 25.0),
    ("What is the variance of 1, 3, 5, 7, 9?", 8.0),
    # Mode
    ("What is the mode of 1, 2, 2, 3, 4?", 2.0),
    ("What is the mode of 5, 5, 5, 1, 2?", 5.0),
    ("What is the mode of 1, 1, 2, 2, 3?", 1.0),
    ("What is the mode of 10, 20, 20, 30?", 20.0),
    ("What is the mode of 7, 7, 7, 7?", 7.0),
    # Range
    ("What is the range of 1, 5, 10, 15, 20?", 19.0),
    ("What is the range of 100, 200, 300?", 200.0),
    ("What is the range of 0, 0, 0?", 0.0),
    ("What is the range of 5, 10?", 5.0),
    ("What is the range of 3, 7, 2, 9, 1?", 8.0),
    # Mixed: mean with larger datasets
    ("What is the mean of 72, 85, 91, 68, 79?", 79.0),
    ("What is the mean of 1000, 2000, 3000, 4000, 5000?", 3000.0),
    ("What is the average of 33, 44, 55, 66, 77?", 55.0),
    ("What is the median of 22, 44, 66, 88?", 55.0),
    ("What is the mean of 12, 15, 18, 21, 24?", 18.0),
    ("What is the median of 7, 3, 1, 5, 9?", 5.0),
    ("What is the median of 2, 8, 4, 6?", 5.0),
    ("What is the average of 25, 50, 75?", 50.0),
]


def main():
    print("=" * 70)
    print(f"  NEW CATEGORIES TEST — {len(TESTS)} problems")
    print(f"  Trigonometry | Combinatorics | Number Theory | Logarithms | Statistics")
    print("=" * 70)
    print()

    passed = 0
    failed = []
    categories = {}
    times = []
    start = time.time()

    for i, (problem, expected) in enumerate(TESTS):
        tol = max(abs(expected) * 0.001, 0.01) if expected != 0 else 0.01

        r = math_solve(problem)
        ans = r.get("answer")
        elapsed = r.get("elapsed_ms", 0)
        times.append(elapsed)
        cat = r.get("problem_type", "unknown")
        categories.setdefault(cat, {"pass": 0, "fail": 0})

        ok = ans is not None and abs(ans - expected) <= tol
        if ok:
            passed += 1
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1
            failed.append({
                "index": i,
                "problem": problem[:60],
                "expected": expected,
                "got": ans,
                "category": cat,
                "formula": r.get("formula_used"),
            })

    total = len(TESTS)
    total_time = time.time() - start
    avg_ms = sum(times) / len(times) if times else 0

    print(f"RESULT: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"TIME:   {total_time:.1f}s total | {avg_ms:.1f}ms avg")
    print(f"COST:   $0.00")
    print()
    print("By category:")
    for cat in sorted(categories):
        c = categories[cat]
        t = c["pass"] + c["fail"]
        pct = c["pass"] / t * 100
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        status = "PASS" if pct == 100 else "FAIL"
        print(f"  {cat:>14}: {c['pass']:>3}/{t:<3} ({pct:>5.1f}%) [{bar}] {status}")

    print()
    if failed:
        print(f"FAILURES ({len(failed)}):")
        for f in failed:
            print(f"  #{f['index']:>3} [{f['category']:>14}] got={f['got']} exp={f['expected']} formula={f['formula']} | {f['problem']}")
    else:
        print("ZERO FAILURES — all 5 new categories proven")

    results = {
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total * 100, 4),
        "avg_ms": round(avg_ms, 1),
        "total_time_s": round(total_time, 1),
        "categories": categories,
        "failure_details": failed,
    }
    with open("stress_test_new_categories_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to stress_test_new_categories_results.json")


if __name__ == "__main__":
    main()
