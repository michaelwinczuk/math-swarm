"""
LLM vs Math Swarm Benchmark — Progressive Model Comparison

Tests the SAME problems across:
  1. qwen2.5:3b  (1.8GB, ~93 tok/s on Alienware)
  2. qwen2.5:7b  (4.4GB, ~40 tok/s on Alienware)
  3. qwen2.5:32b (18.5GB, ~4.2 tok/s on Desktop)

Then compares against Math Swarm (SymPy, 0ms, $0).

Thesis: 3B + Math Swarm > 32B alone.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from math_swarm import solve as math_solve

# ── Representative 100 problems across all 11 categories ────────
# Selected to target KNOWN LLM failure modes

BENCHMARK = [
    # MULTI-DIGIT MULTIPLICATION (LLMs lose carry digits)
    ("What is 347 * 893?", 309871, "multiplication"),
    ("What is 456 * 789?", 359784, "multiplication"),
    ("What is 999 * 999?", 998001, "multiplication"),
    ("What is 1234 * 5678?", 7006652, "multiplication"),
    ("What is 9999 * 9999?", 99980001, "multiplication"),
    ("What is 127 * 131?", 16637, "multiplication"),
    ("What is 5555 * 6666?", 37029630, "multiplication"),
    ("What is 7777 * 8888?", 69113976, "multiplication"),
    ("What is 123 * 456 * 789?", 44253432, "multiplication"),
    ("What is 256 * 256?", 65536, "multiplication"),

    # ORDER OF OPERATIONS (LLMs flatten PEMDAS)
    ("What is 2 + 3 * 4?", 14, "order_of_ops"),
    ("What is (2 + 3) * 4?", 20, "order_of_ops"),
    ("What is 6 / 2 * (1 + 2)?", 9, "order_of_ops"),
    ("What is 100 - 50 / 5?", 90, "order_of_ops"),
    ("What is 2 * 3 + 4 * 5?", 26, "order_of_ops"),
    ("What is ((3 + 4) * (5 - 2))?", 21, "order_of_ops"),
    ("What is 8 - 2 * 3 + 1?", 3, "order_of_ops"),
    ("What is 1 + 2 * 3 + 4 * 5 + 6?", 33, "order_of_ops"),

    # FLOATING POINT TRAPS
    ("What is 0.1 + 0.2?", 0.3, "float_trap"),
    ("What is 0.1 + 0.2 - 0.3?", 0.0, "float_trap"),
    ("What is 9.11 - 9.9?", -0.79, "float_trap"),
    ("What is 7.7 - 7.77?", -0.07, "float_trap"),
    ("What is 0.1 * 10?", 1.0, "float_trap"),

    # LARGE NUMBERS
    ("What is 2^32?", 4294967296, "large_numbers"),
    ("What is 2^20?", 1048576, "large_numbers"),
    ("What is 2^40?", 1099511627776, "large_numbers"),
    ("What is 123456789 + 987654321?", 1111111110, "large_numbers"),
    ("What is 999999999 + 1?", 1000000000, "large_numbers"),

    # NEGATIVE NUMBERS
    ("What is -3 * -4 * -5?", -60, "negatives"),
    ("What is -2 * -2 * -2 * -2?", 16, "negatives"),
    ("What is (-1)^99?", -1, "negatives"),
    ("What is -100 + 200 - 300 + 400?", 200, "negatives"),
    ("What is (-5 - 3) * (-2 + 1)?", 8, "negatives"),

    # MORTGAGE PAYMENTS (LLMs hallucinate by $10-100+)
    ("What is the monthly payment on a $450,000 mortgage at 6.5% for 30 years?", 2844.31, "mortgage"),
    ("What is the monthly payment on a $300,000 mortgage at 7.0% for 30 years?", 1995.91, "mortgage"),
    ("What is the monthly payment on a $200,000 mortgage at 4.5% for 30 years?", 1013.37, "mortgage"),
    ("What is the monthly payment on a $500,000 mortgage at 6.0% for 30 years?", 2997.75, "mortgage"),
    ("What is the monthly payment on a $100,000 mortgage at 5.0% for 15 years?", 790.79, "mortgage"),

    # COMPOUND INTEREST
    ("If I invest $10,000 at 7% compound interest for 20 years, how much do I have?", 38696.84, "compound"),
    ("If I invest $5,000 at 5% compound interest for 30 years, how much do I have?", 21609.71, "compound"),
    ("If I invest $75,000 at 9.5% compound interest for 15 years, how much do I have?", 292599.14, "compound"),
    ("If I invest $1,000 at 10% compound interest for 10 years, how much do I have?", 2593.74, "compound"),
    ("If I invest $50,000 at 8% compound interest for 10 years, how much do I have?", 107946.25, "compound"),

    # ROI
    ("What is the ROI if I spent $25,000 and got back $67,500?", 170.0, "roi"),
    ("What is the ROI if I spent $1,000 and got back $10,000?", 900.0, "roi"),
    ("What is the ROI if I gained $10,000 on a $50,000 investment?", 20.0, "roi"),

    # PERCENTAGES
    ("Calculate 15% tip on $237.85", 35.6775, "percentage"),
    ("Calculate 8.25% tax on $200", 16.5, "percentage"),
    ("What is 12.5% of 800?", 100, "percentage"),
    ("What is 37.5% of 400?", 150, "percentage"),
    ("What is 0.5% of 10000?", 50, "percentage"),

    # GEOMETRY
    ("What is the area of a circle with radius 7?", 153.938, "geometry"),
    ("What is the volume of a sphere with radius 5?", 523.599, "geometry"),
    ("What is the hypotenuse if sides are 7 and 24? Use pythagorean", 25, "geometry"),
    ("What is the area of a circle with radius 13?", 530.929, "geometry"),
    ("What is the volume of a sphere with radius 10?", 4188.79, "geometry"),

    # PHYSICS
    ("What is the force if mass is 75 kg and acceleration is 9.8?", 735, "physics"),
    ("What is the kinetic energy of a 10 kg object moving at 100 m/s?", 50000, "physics"),
    ("What is the kinetic energy of a 1500 kg object moving at 20 m/s?", 300000, "physics"),

    # CONVERSIONS
    ("Convert 37 celsius to fahrenheit", 98.6, "conversion"),
    ("Convert -40 celsius to fahrenheit", -40, "conversion"),
    ("Convert 42 km to miles", 26.098, "conversion"),
    ("Convert 75 kg to lbs", 165.347, "conversion"),

    # DIVISION PRECISION
    ("What is 1 / 7?", 0.142857, "division"),
    ("What is 355 / 113?", 3.141593, "division"),
    ("What is 100 / 7?", 14.285714, "division"),
    ("What is 1000 / 3?", 333.333333, "division"),

    # ─── NEW CATEGORIES ───────────────────────────────────────

    # TRIGONOMETRY
    ("What is the sine of 30 degrees?", 0.5, "trig"),
    ("What is the cosine of 60 degrees?", 0.5, "trig"),
    ("What is the tangent of 45 degrees?", 1.0, "trig"),
    ("What is the sine of 45 degrees?", 0.707107, "trig"),
    ("What is the cosine of 30 degrees?", 0.866025, "trig"),
    ("What is the tangent of 60 degrees?", 1.732051, "trig"),
    ("What is the arcsin of 0.5?", 30.0, "trig"),
    ("What is the arccos of 0.5?", 60.0, "trig"),

    # COMBINATORICS
    ("What is 10 factorial?", 3628800, "combinatorics"),
    ("What is 12 factorial?", 479001600, "combinatorics"),
    ("What is 15 factorial?", 1307674368000, "combinatorics"),
    ("How many combinations of 52 choose 5?", 2598960, "combinatorics"),
    ("How many combinations of 10 choose 5?", 252, "combinatorics"),
    ("How many permutations of 5 from 10?", 30240, "combinatorics"),

    # NUMBER THEORY
    ("What is the GCD of 144 and 108?", 36, "number_theory"),
    ("What is the GCD of 252 and 105?", 21, "number_theory"),
    ("What is the LCM of 12 and 15?", 60, "number_theory"),
    ("What is the LCM of 24 and 36?", 72, "number_theory"),

    # LOGARITHMS
    ("What is log base 2 of 1024?", 10.0, "logarithm"),
    ("What is log base 2 of 65536?", 16.0, "logarithm"),
    ("What is log base 3 of 243?", 5.0, "logarithm"),
    ("What is ln(100)?", 4.605170, "logarithm"),
    ("What is log(1000)?", 3.0, "logarithm"),

    # STATISTICS
    ("What is the mean of 85, 90, 78, 92, 88?", 86.6, "statistics"),
    ("What is the median of 3, 7, 2, 9, 5?", 5.0, "statistics"),
    ("What is the standard deviation of 2, 4, 4, 4, 5, 5, 7, 9?", 2.0, "statistics"),
    ("What is the variance of 1, 2, 3, 4, 5?", 2.0, "statistics"),
]


def query_ollama(model: str, host: str, problem: str, timeout: int = 60) -> dict:
    """Query Ollama and extract numeric answer."""
    url = f"http://{host}:11434/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": f"Solve this math problem. Give ONLY the numeric answer, nothing else. No words, no units, no explanation. Just the number.\n\n{problem}",
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 100},
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        elapsed = time.time() - start
        raw = data.get("response", "").strip()

        # Extract number from response
        # Try to find a number (possibly negative, with commas, decimals)
        raw_clean = raw.replace(",", "").replace("$", "").replace("%", "")
        # Find the first number-like pattern
        num_match = re.search(r'-?[\d]+\.?[\d]*(?:e[+-]?\d+)?', raw_clean)
        if num_match:
            answer = float(num_match.group(0))
        else:
            answer = None

        return {"answer": answer, "raw": raw, "elapsed": round(elapsed, 2)}
    except Exception as e:
        return {"answer": None, "raw": str(e), "elapsed": round(time.time() - start, 2)}


def run_benchmark(model: str, host: str, label: str):
    """Run all benchmark problems through a model."""
    print(f"\n{'='*70}")
    print(f"  BENCHMARK: {label} ({model} on {host})")
    print(f"  {len(BENCHMARK)} problems")
    print(f"{'='*70}\n")

    passed = 0
    failed = []
    categories = {}
    times = []

    for i, (problem, expected, cat) in enumerate(BENCHMARK):
        tol = max(abs(expected) * 0.02, 0.1) if expected != 0 else 0.1  # 2% tolerance for LLMs

        r = query_ollama(model, host, problem)
        ans = r["answer"]
        elapsed = r["elapsed"]
        times.append(elapsed)

        categories.setdefault(cat, {"pass": 0, "fail": 0})
        ok = ans is not None and abs(ans - expected) <= tol
        if ok:
            passed += 1
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1
            failed.append({
                "problem": problem[:55],
                "expected": expected,
                "got": ans,
                "raw": r["raw"][:60],
                "category": cat,
            })

        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(BENCHMARK)}] {passed} correct so far...")

    total = len(BENCHMARK)
    avg_s = sum(times) / len(times) if times else 0

    print(f"\n  RESULT: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"  TIME:   {avg_s:.1f}s avg per problem")
    print()
    print("  By category:")
    for cat in sorted(categories):
        c = categories[cat]
        t = c["pass"] + c["fail"]
        pct = c["pass"] / t * 100
        status = "OK" if pct == 100 else f"WRONG: {c['fail']}"
        print(f"    {cat:>16}: {c['pass']:>2}/{t:<2} ({pct:>5.1f}%) {status}")

    return {
        "model": model,
        "host": host,
        "label": label,
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total * 100, 2),
        "avg_seconds": round(avg_s, 2),
        "categories": categories,
        "failures": failed,
    }


def run_math_swarm():
    """Run all benchmark problems through Math Swarm."""
    print(f"\n{'='*70}")
    print(f"  BENCHMARK: Math Swarm (SymPy, local, $0)")
    print(f"  {len(BENCHMARK)} problems")
    print(f"{'='*70}\n")

    passed = 0
    categories = {}
    times = []

    for problem, expected, cat in BENCHMARK:
        tol = max(abs(expected) * 0.001, 0.01) if expected != 0 else 0.01

        r = math_solve(problem)
        ans = r.get("answer")
        elapsed = r.get("elapsed_ms", 0)
        times.append(elapsed)

        categories.setdefault(cat, {"pass": 0, "fail": 0})
        ok = ans is not None and abs(ans - expected) <= tol
        if ok:
            passed += 1
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1

    total = len(BENCHMARK)
    avg_ms = sum(times) / len(times) if times else 0

    print(f"  RESULT: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"  TIME:   {avg_ms:.1f}ms avg per problem")

    return {
        "model": "math_swarm",
        "label": "Math Swarm (SymPy)",
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total * 100, 2),
        "avg_ms": round(avg_ms, 1),
        "categories": categories,
    }


def main():
    import sys
    models = sys.argv[1:] if len(sys.argv) > 1 else ["3b"]

    results = []

    # Always run Math Swarm first as baseline
    swarm_result = run_math_swarm()
    results.append(swarm_result)

    if "3b" in models:
        r = run_benchmark("qwen2.5:3b", "192.168.1.215", "Qwen 3B (1.8GB)")
        results.append(r)

    if "7b" in models:
        r = run_benchmark("qwen2.5:7b", "192.168.1.215", "Qwen 7B (4.4GB)")
        results.append(r)

    if "32b" in models:
        r = run_benchmark("qwen2.5:32b", "127.0.0.1", "Qwen 32B (18.5GB)")
        results.append(r)

    # Summary
    print(f"\n{'='*70}")
    print(f"  FINAL COMPARISON")
    print(f"{'='*70}\n")
    for r in results:
        label = r["label"]
        acc = r["accuracy"]
        if "avg_ms" in r:
            speed = f"{r['avg_ms']:.1f}ms"
        else:
            speed = f"{r['avg_seconds']:.1f}s"
        print(f"  {label:>30}: {r['passed']:>3}/{r['total']} ({acc:>5.1f}%) | {speed}/problem")

    # Save
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to benchmark_results.json")


if __name__ == "__main__":
    main()
