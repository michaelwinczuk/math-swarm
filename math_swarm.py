"""
Math Swarm — 6-agent pipeline for exact mathematical computation.

Agents: Parser → Classifier → Planner → Compute → Verify → Explainer

Zero hallucination: formulas from KG, computation from SymPy, verification deterministic.
LLM only used for natural language parsing when regex patterns fail.

Usage:
    # Stdin/stdout JSON mode (for Swarm Claw integration)
    echo '{"problem":"What is the monthly payment on a $450K mortgage at 6.5% for 30 years?"}' | python math_swarm.py

    # CLI mode
    python math_swarm.py --problem "Calculate 15% tip on $84.50"

    # Interactive mode
    python math_swarm.py --interactive
"""

import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import sympy

from compute import MathEngine, ComputeResult

# ── Problem Classification ───────────────────────────────────

PROBLEM_TYPES = {
    "arithmetic": {
        "keywords": ["calculate", "compute", "what is", "how much is", "add", "subtract", "multiply", "divide", "sum", "total", "difference", "product"],
        "patterns": [r"\d+\s*[+\-*/^%]\s*\d+", r"what is \d+", r"calculate \d+"],
    },
    "percentage": {
        "keywords": ["percent", "%", "percentage", "tip", "tax", "discount", "markup", "margin"],
        "patterns": [r"\d+\s*%", r"percent of", r"tip on", r"tax on", r"discount"],
    },
    "finance": {
        "keywords": ["mortgage", "loan", "interest", "compound", "investment", "roi", "break even", "annuity", "payment", "apr", "apy", "present value", "future value", "sharpe"],
        "patterns": [r"\$[\d,]+", r"at \d+\.?\d*%", r"for \d+ years"],
    },
    "statistics": {
        "keywords": ["mean", "average", "median", "standard deviation", "variance", "probability", "z-score", "bayes", "expected value", "correlation"],
        "patterns": [r"data:?\s*\[", r"sample of \d+"],
    },
    "geometry": {
        "keywords": ["area", "volume", "perimeter", "circumference", "radius", "diameter", "circle", "sphere", "triangle", "rectangle", "cylinder", "pythagorean", "hypotenuse", "sides"],
        "patterns": [r"radius of \d+", r"area of", r"volume of", r"sides are \d+", r"hypotenuse"],
    },
    "physics": {
        "keywords": ["velocity", "acceleration", "force", "energy", "power", "momentum", "kinetic", "potential", "ohm", "voltage", "current", "resistance"],
        "patterns": [r"\d+\s*m/s", r"\d+\s*kg", r"\d+\s*N"],
    },
    "conversion": {
        "keywords": ["convert", "to celsius", "to fahrenheit", "to miles", "to km", "to kg", "to lbs", "to gb", "to bytes"],
        "patterns": [r"convert \d+", r"\d+\s*(celsius|fahrenheit|km|miles|kg|lbs|gb|mb)"],
    },
    "equation": {
        "keywords": ["solve", "find x", "equation", "what value of", "solve for"],
        "patterns": [r"solve\s+", r"find\s+\w+\s+if", r"\w+\s*=\s*\d+"],
    },
    "trigonometry": {
        "keywords": ["sine", "cosine", "tangent", "sin", "cos", "tan", "arcsin", "arccos", "arctan", "trig"],
        "patterns": [r"sin\w*\s+of", r"cos\w*\s+of", r"tan\w*\s+of", r"sin\s*\(", r"cos\s*\(", r"tan\s*\(", r"sine of \d+", r"cosine of \d+"],
    },
    "combinatorics": {
        "keywords": ["factorial", "permutation", "combination", "choose", "arrange", "ways", "nCr", "nPr"],
        "patterns": [r"\d+\s*!", r"choose\s+\d+", r"from\s+\d+", r"P\(\s*\d+", r"C\(\s*\d+", r"how many ways", r"\d+\s+factorial"],
    },
    "number_theory": {
        "keywords": ["gcd", "lcm", "greatest common divisor", "least common multiple", "greatest common", "least common"],
        "patterns": [r"gcd\s*\(?\s*\d+", r"lcm\s*\(?\s*\d+", r"greatest common\s+\w+\s+of", r"least common\s+\w+\s+of"],
    },
    "logarithm": {
        "keywords": ["log", "logarithm", "ln", "natural log", "log base"],
        "patterns": [r"log\s*\(?\s*\d+", r"ln\s*\(?\s*\d+", r"log\s+base\s+\d+", r"natural\s+log"],
    },
    "statistics": {
        "keywords": ["mean", "average", "median", "mode", "standard deviation", "std dev", "variance", "range of"],
        "patterns": [r"mean of\s+[\d,.\s\[\]]+", r"median of\s+[\d,.\s\[\]]+", r"average of\s+[\d,.\s\[\]]+",
                     r"data:?\s*\[?[\d,.\s]+\]?", r"std\w* dev\w*\s+of"],
    },
    "healthcare": {
        "keywords": ["bmi", "body mass index", "egfr", "creatinine clearance", "cockcroft", "corrected calcium",
                     "anion gap", "mean arterial", "meld", "qtc", "ideal body weight", "drip rate",
                     "dose per kg", "mg/kg", "pediatric dose", "a-a gradient"],
        "patterns": [r"\d+\s*/\s*\d+\s*(?:mmhg|bp|blood pressure)", r"\d+\s*mg/kg", r"\d+\s*kg\s+.*\d+\s*m\b"],
    },
}

# ── Number Extraction Patterns ───────────────────────────────

NUMBER_PATTERNS = [
    (r"\$\s*([\d,]+\.?\d*)", "currency"),           # $450,000 or $84.50
    (r"([\d,]+\.?\d*)\s*%", "percentage"),           # 6.5% or 15%
    (r"([\d,]+\.?\d*)\s*years?", "duration_years"),  # 30 years
    (r"([\d,]+\.?\d*)\s*months?", "duration_months"),
    (r"([\d,]+\.?\d*)\s*(?:m/s|km/h|mph)", "velocity"),
    (r"([\d,]+\.?\d*)\s*(?:kg|lbs|g)", "mass"),
    (r"([\d,]+\.?\d*)\s*(?:km|miles|m|cm|ft)", "distance"),
    (r"(-?[\d,]+\.?\d*)", "number"),                # bare numbers (including negative)
]


# ── Chalkboard ───────────────────────────────────────────────

@dataclass
class Chalkboard:
    """Shared state passed between agents."""
    problem: str = ""
    # Parser output
    numbers: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    raw_expression: Optional[str] = None
    data_list: Optional[list] = None  # For statistics: extracted data array
    # Classifier output
    problem_type: str = "unknown"
    confidence: float = 0.0
    # Planner output
    formula_name: Optional[str] = None
    variables: dict = field(default_factory=dict)
    sub_steps: list = field(default_factory=list)
    # Compute output
    result: Optional[ComputeResult] = None
    # Verify output
    verified: bool = False
    verification: Optional[dict] = None
    # Explainer output
    explanation: str = ""
    # Metadata
    steps_trace: list = field(default_factory=list)
    total_time_ms: int = 0


# ── Agent 1: Parser ──────────────────────────────────────────

def parse(chalkboard: Chalkboard) -> Chalkboard:
    """Extract numbers, units, and mathematical entities from natural language."""
    text = chalkboard.problem
    lower = text.lower()

    # Extract numbers with context
    numbers = []
    for pattern, label in NUMBER_PATTERNS:
        for match in re.finditer(pattern, lower):
            val_str = match.group(1).replace(",", "")
            try:
                val = float(val_str)
                numbers.append({"value": val, "type": label, "raw": match.group(0)})
            except ValueError:
                pass

    # Deduplicate by value+type (keep first occurrence with best label)
    seen = set()
    unique_numbers = []
    for n in numbers:
        key = (n["value"], n["type"])
        if key not in seen:
            seen.add(key)
            unique_numbers.append(n)

    chalkboard.numbers = unique_numbers

    # SymPy-first expression extraction:
    # 1. Try to find and parse a math expression using sympify
    # 2. Fall back to regex only if sympify fails

    # Normalize text for sympify: strip words, keep math tokens
    math_candidate = re.sub(r'[a-zA-Z$,]+', ' ', text)  # strip letters and $
    math_candidate = math_candidate.replace('^', '**').strip()
    # Clean up whitespace
    math_candidate = re.sub(r'\s+', ' ', math_candidate).strip()

    # Try to sympify any substring that looks mathematical
    best_expr = None

    # Strategy 1: Extract expression after "is/equals/=" up to "?"
    is_match = re.search(r'(?:is|equals?|=)\s*(.+?)(?:\?|$)', text)
    if is_match:
        sub = is_match.group(1).replace('^', '**').replace('$', '').replace(',', '').strip()
        if re.search(r'\d.*[+\-*/()]', sub):
            try:
                parsed = sympy.sympify(sub, evaluate=False)
                if parsed is not None:
                    best_expr = sub
            except (sympy.SympifyError, TypeError, SyntaxError, ValueError):
                pass

    # Strategy 2: Try the full cleaned math candidate
    if not best_expr and re.search(r'\d.*[+\-*/()]', math_candidate):
        try:
            parsed = sympy.sympify(math_candidate, evaluate=False)
            if parsed is not None:
                best_expr = math_candidate
        except (sympy.SympifyError, TypeError, SyntaxError, ValueError):
            pass

    # Strategy 3: Longest substring search (fallback)
    if not best_expr:
        parts = math_candidate.split()
        for length in range(len(parts), 1, -1):
            for start in range(len(parts) - length + 1):
                sub = ' '.join(parts[start:start+length])
                if not re.search(r'\d', sub):
                    continue
                if not re.search(r'[+\-*/()]', sub):
                    continue
                try:
                    parsed = sympy.sympify(sub, evaluate=False)
                    if parsed is not None:
                        best_expr = sub
                        break
                except (sympy.SympifyError, TypeError, SyntaxError, ValueError):
                    continue
            if best_expr:
                break

    if best_expr:
        chalkboard.raw_expression = best_expr
    else:
        # Final regex fallback for simple patterns
        expr_match = re.search(r"-?[\d.]+\s*[+\-*/^]\s*[\d.(]+[\d.+\-*/^() ]*[\d.)]+", text)
        if expr_match:
            chalkboard.raw_expression = expr_match.group(0).replace('^', '**')
        else:
            expr_match = re.search(r"-?[\d.]+\s*[+\-*/^]\s*-?[\d.]+", text)
            if expr_match:
                chalkboard.raw_expression = expr_match.group(0).replace('^', '**')

    # Data list extraction for statistics problems
    # Matches: [1,2,3], "data: 1, 2, 3", "values 85, 90, 75", "of 10, 20, 30"
    data_match = re.search(r'\[([0-9,.\s\-]+)\]', text)
    if not data_match:
        # Match "of X, Y, Z" or "data: X, Y, Z" — at least 2 comma-separated numbers
        data_match = re.search(r'(?:data|values|scores|numbers|of)\s*:?\s*((?:-?\d+\.?\d*\s*,\s*)+-?\d+\.?\d*)', lower)
    if data_match:
        raw = data_match.group(1)
        try:
            chalkboard.data_list = [float(x.strip()) for x in raw.split(',') if x.strip()]
        except ValueError:
            pass

    chalkboard.steps_trace.append({
        "agent": "Parser",
        "numbers_found": len(unique_numbers),
        "has_expression": chalkboard.raw_expression is not None,
        "has_data_list": chalkboard.data_list is not None,
    })

    return chalkboard


# ── Agent 2: Classifier ─────────────────────────────────────

def classify(chalkboard: Chalkboard) -> Chalkboard:
    """Classify the problem type using keyword + pattern matching."""
    lower = chalkboard.problem.lower()

    # Priority overrides — domain-specific keywords that uniquely identify a type
    # These beat the generic scoring system to prevent "what is" arithmetic from winning
    _OVERRIDES = [
        (["factorial", "permutation", "combination", " choose ", " arrange ", "how many ways"], "combinatorics"),
        (["gcd", "greatest common", "lcm", "least common"], "number_theory"),
        (["sine", "cosine", "tangent", "arcsin", "arccos", "arctan"], "trigonometry"),
        (["logarithm", "natural log", "log base", " ln(", " ln "], "logarithm"),
        (["mean of", "median of", "mode of", "standard deviation of", "std dev of", "variance of", "average of", "range of"], "statistics"),
        (["bmi", "body mass index", "egfr", "creatinine clearance", "cockcroft", "corrected calcium",
          "anion gap", "mean arterial pressure", "meld score", "qtc", "ideal body weight",
          "drip rate", "dose per kg", "mg/kg", "pediatric dose", "a-a gradient", "aa gradient"], "healthcare"),
    ]
    for keywords, ptype in _OVERRIDES:
        for kw in keywords:
            if kw in lower:
                chalkboard.problem_type = ptype
                chalkboard.confidence = 0.95
                chalkboard.steps_trace.append({
                    "agent": "Classifier",
                    "type": ptype,
                    "confidence": 0.95,
                    "override": kw,
                })
                return chalkboard

    scores = {}

    for ptype, config in PROBLEM_TYPES.items():
        score = 0
        # Keyword scoring
        for kw in config["keywords"]:
            if kw in lower:
                score += 1
        # Pattern scoring (higher weight)
        for pat in config["patterns"]:
            if re.search(pat, lower):
                score += 2

        if score > 0:
            scores[ptype] = score

    if scores:
        best = max(scores, key=scores.get)
        # Tiebreaker: if "%" appears in text, percentage wins ties
        if "%" in lower and "percentage" in scores and scores.get("percentage", 0) >= scores.get(best, 0):
            best = "percentage"
        total = sum(scores.values())
        chalkboard.problem_type = best
        chalkboard.confidence = scores[best] / total if total > 0 else 0.0
    else:
        chalkboard.problem_type = "arithmetic"
        chalkboard.confidence = 0.3

    chalkboard.steps_trace.append({
        "agent": "Classifier",
        "type": chalkboard.problem_type,
        "confidence": round(chalkboard.confidence, 2),
        "scores": scores,
    })

    return chalkboard


# ── Agent 3: Planner ─────────────────────────────────────────

def plan(chalkboard: Chalkboard, engine: MathEngine) -> Chalkboard:
    """Map the classified problem to a formula and extract variables."""
    ptype = chalkboard.problem_type
    lower = chalkboard.problem.lower()
    numbers = chalkboard.numbers

    # If we have a raw arithmetic expression, use it directly
    if chalkboard.raw_expression and ptype == "arithmetic":
        chalkboard.formula_name = "__raw_expression__"
        chalkboard.variables = {}
        chalkboard.steps_trace.append({
            "agent": "Planner",
            "plan": "direct_expression",
            "expression": chalkboard.raw_expression,
        })
        return chalkboard

    # Map problem type + keywords to specific formula
    if ptype == "percentage":
        if "tip" in lower or "tax" in lower:
            chalkboard.formula_name = "percentage"
            base = next((n["value"] for n in numbers if n["type"] == "currency"), None)
            pct = next((n["value"] for n in numbers if n["type"] == "percentage"), None)
            if base and pct:
                chalkboard.variables = {"base": base, "percent": pct}
        elif "change" in lower or "increase" in lower or "decrease" in lower:
            chalkboard.formula_name = "percentage_change"
            vals = [n["value"] for n in numbers if n["type"] in ("number", "currency")]
            if len(vals) >= 2:
                chalkboard.variables = {"old_val": vals[0], "new_val": vals[1]}
        elif "of" in lower:
            # "X% of Y" pattern
            chalkboard.formula_name = "percentage"
            pct_val = next((n["value"] for n in numbers if n["type"] == "percentage"), None)
            # The base is the number after "of"
            of_match = re.search(r"of\s+\$?([\d,]+\.?\d*)", lower)
            base_val = float(of_match.group(1).replace(",", "")) if of_match else None
            if pct_val is None:
                # Percentage might be a bare number before "% of"
                pct_val = next((n["value"] for n in numbers if n["value"] != base_val), None)
            if base_val and pct_val:
                chalkboard.variables = {"base": base_val, "percent": pct_val}
        else:
            chalkboard.formula_name = "percentage"
            vals = [n["value"] for n in numbers]
            if len(vals) >= 2:
                pct_val = next((n["value"] for n in numbers if n["type"] == "percentage"), vals[0])
                base_val = next((n["value"] for n in numbers if n["type"] != "percentage"), vals[-1])
                chalkboard.variables = {"base": base_val, "percent": pct_val}

    elif ptype == "finance":
        if "mortgage" in lower or "monthly payment" in lower or "loan payment" in lower:
            chalkboard.formula_name = "mortgage_payment"
            principal = next((n["value"] for n in numbers if n["type"] == "currency"), None)
            rate = next((n["value"] for n in numbers if n["type"] == "percentage"), None)
            years = next((n["value"] for n in numbers if n["type"] == "duration_years"), None)
            if principal and rate and years:
                chalkboard.variables = {
                    "P": principal,
                    "r": rate / 100 / 12,  # annual → monthly decimal
                    "n": int(years * 12),
                }
        elif "compound interest" in lower or "compound" in lower:
            chalkboard.formula_name = "compound_interest"
            principal = next((n["value"] for n in numbers if n["type"] == "currency"), None)
            rate = next((n["value"] for n in numbers if n["type"] == "percentage"), None)
            years = next((n["value"] for n in numbers if n["type"] == "duration_years"), None)
            # Default to annual compounding unless "monthly" or "quarterly" specified
            if "monthly" in lower:
                n_compound = 12
            elif "quarterly" in lower:
                n_compound = 4
            elif "daily" in lower:
                n_compound = 365
            else:
                n_compound = 1  # annual (standard textbook default)
            if principal and rate:
                chalkboard.variables = {
                    "P": principal,
                    "r": rate / 100,
                    "n": n_compound,
                    "t": years or 1,
                }
        elif "roi" in lower or "return on investment" in lower:
            chalkboard.formula_name = "roi"
            vals = [n["value"] for n in numbers if n["type"] in ("currency", "number") and n["value"] > 0]
            if len(vals) >= 2:
                # "spent X got back Y" → cost=X, gain=Y
                # "gained X on Y investment" → gain=X+Y, cost=Y
                if "spent" in lower and "got back" in lower:
                    chalkboard.variables = {"gain": vals[1], "cost": vals[0]}
                elif "gained" in lower:
                    chalkboard.variables = {"gain": vals[0] + vals[1], "cost": vals[1]}
                else:
                    # Default: larger is gain, smaller is cost
                    chalkboard.variables = {"gain": max(vals), "cost": min(vals)}
        elif "break even" in lower or "breakeven" in lower:
            chalkboard.formula_name = "break_even"
            vals = [n["value"] for n in numbers if n["type"] in ("currency", "number")]
            if len(vals) >= 3:
                chalkboard.variables = {"fixed_costs": vals[0], "price": vals[1], "variable_cost": vals[2]}
        elif "sharpe" in lower:
            chalkboard.formula_name = "sharpe_ratio"
            vals = [n["value"] for n in numbers]
            if len(vals) >= 3:
                chalkboard.variables = {"Rp": vals[0] / 100, "Rf": vals[1] / 100, "sigma_p": vals[2] / 100}

    elif ptype == "geometry":
        if "circle" in lower and "area" in lower:
            chalkboard.formula_name = "circle_area"
            r = next((n["value"] for n in numbers), None)
            if r: chalkboard.variables = {"r": r}
        elif "sphere" in lower and "volume" in lower:
            chalkboard.formula_name = "sphere_volume"
            r = next((n["value"] for n in numbers), None)
            if r: chalkboard.variables = {"r": r}
        elif "triangle" in lower and "area" in lower:
            chalkboard.formula_name = "triangle_area"
            vals = [n["value"] for n in numbers]
            if len(vals) >= 2:
                chalkboard.variables = {"b": vals[0], "h": vals[1]}
        elif "pythagorean" in lower or "hypotenuse" in lower:
            chalkboard.formula_name = "pythagorean"
            # Extract sides — may be same value (e.g., "sides are 5 and 5")
            sides_match = re.findall(r"(\d+\.?\d*)\s*and\s*(\d+\.?\d*)", lower)
            if sides_match:
                chalkboard.variables = {"a": float(sides_match[0][0]), "b": float(sides_match[0][1])}
            else:
                vals = [n["value"] for n in numbers if n["value"] > 0]
                if len(vals) >= 2:
                    chalkboard.variables = {"a": vals[0], "b": vals[1]}

    elif ptype == "conversion":
        if "celsius" in lower and "fahrenheit" in lower:
            chalkboard.formula_name = "celsius_to_fahrenheit"
            val = next((n["value"] for n in numbers), None)
            if val is not None:  # explicit None check — 0 is a valid value
                chalkboard.variables = {"c": val}
        elif "km" in lower and "miles" in lower:
            chalkboard.formula_name = "km_to_miles"
            val = next((n["value"] for n in numbers), None)
            if val: chalkboard.variables = {"km": val}
        elif "kg" in lower and ("lbs" in lower or "pounds" in lower):
            chalkboard.formula_name = "kg_to_lbs"
            val = next((n["value"] for n in numbers), None)
            if val: chalkboard.variables = {"kg": val}

    elif ptype == "physics":
        if "velocity" in lower or "speed" in lower:
            chalkboard.formula_name = "velocity"
            vals = [n["value"] for n in numbers]
            if len(vals) >= 2:
                chalkboard.variables = {"d": vals[0], "t": vals[1]}
        elif "force" in lower:
            chalkboard.formula_name = "force"
            # Use unit labels when available
            mass = next((n["value"] for n in numbers if n["type"] == "mass"), None)
            if mass is None:
                mass_match = re.search(r"([\d.]+)\s*kg", lower)
                if mass_match: mass = float(mass_match.group(1))
            # Acceleration is typically the non-mass number
            accel = None
            accel_match = re.search(r"acceleration\s+(?:is\s+|of\s+)?([\d.]+)", lower)
            if accel_match:
                accel = float(accel_match.group(1))
            else:
                accel = next((n["value"] for n in numbers if n["value"] != mass), None)
            if mass and accel:
                chalkboard.variables = {"m": mass, "a": accel}
        elif "kinetic energy" in lower:
            chalkboard.formula_name = "kinetic_energy"
            mass = next((n["value"] for n in numbers if n["type"] == "mass"), None)
            vel = next((n["value"] for n in numbers if n["type"] == "velocity"), None)
            if mass is None or vel is None:
                # Fallback: look for "X kg" and "Y m/s" in text
                mass_match = re.search(r"([\d.]+)\s*kg", lower)
                vel_match = re.search(r"([\d.]+)\s*m/s", lower)
                if mass_match: mass = float(mass_match.group(1))
                if vel_match: vel = float(vel_match.group(1))
            if mass and vel:
                chalkboard.variables = {"m": mass, "v": vel}

    elif ptype == "equation":
        chalkboard.formula_name = "__solve_equation__"

    elif ptype == "trigonometry":
        # Determine function: sin, cos, tan, or inverse
        is_arc = any(w in lower for w in ["arc", "inverse", "asin", "acos", "atan"])
        use_radians = "radian" in lower or ("pi" in lower and "/" in lower)

        # IMPORTANT: check "cos" BEFORE "sin" — "cosine" contains "sin" as substring
        if "cos" in lower:
            if is_arc:
                chalkboard.formula_name = "arccos_degrees"
            elif use_radians:
                chalkboard.formula_name = "cos_radians"
            else:
                chalkboard.formula_name = "cos_degrees"
        elif "sin" in lower:
            if is_arc:
                chalkboard.formula_name = "arcsin_degrees"
            elif use_radians:
                chalkboard.formula_name = "sin_radians"
            else:
                chalkboard.formula_name = "sin_degrees"
        elif "tan" in lower:
            if is_arc:
                chalkboard.formula_name = "arctan_degrees"
            elif use_radians:
                chalkboard.formula_name = "tan_radians"
            else:
                chalkboard.formula_name = "tan_degrees"

        val = next((n["value"] for n in numbers), None)
        if val is not None:
            chalkboard.variables = {"x": val}

    elif ptype == "combinatorics":
        if "factorial" in lower or re.search(r'\d+\s*!', lower):
            chalkboard.formula_name = "factorial"
            val = next((n["value"] for n in numbers), None)
            if val is not None:
                chalkboard.variables = {"n": int(val)}
        elif any(w in lower for w in ["permut", "arrange", "npr"]):
            chalkboard.formula_name = "permutation"
            # Extract n and r in order from text
            all_nums = [int(n["value"]) for n in numbers]
            if len(all_nums) >= 2:
                # "permutations of R from N" — R is smaller, N is larger
                chalkboard.variables = {"n": max(all_nums), "r": min(all_nums)}
            elif len(all_nums) == 1:
                chalkboard.variables = {"n": all_nums[0], "r": all_nums[0]}
        elif any(w in lower for w in ["combin", "choose", "ncr"]):
            chalkboard.formula_name = "combination"
            # Extract all numbers including 0 — C(n,0) = 1
            all_nums = [int(n["value"]) for n in numbers]
            if len(all_nums) >= 2:
                # "C(N choose R)" — N is the larger value, R is smaller
                chalkboard.variables = {"n": max(all_nums), "r": min(all_nums)}
            elif len(all_nums) == 1:
                # "C(n, n)" case where both values are the same → only one extracted
                # e.g. "combinations of 6 choose 6" — only one 6 extracted
                chalkboard.variables = {"n": all_nums[0], "r": all_nums[0]}

    elif ptype == "number_theory":
        if "gcd" in lower or "greatest common" in lower:
            chalkboard.formula_name = "gcd"
            vals = [int(n["value"]) for n in numbers if n["value"] > 0]
            if len(vals) >= 2:
                chalkboard.variables = {"a": vals[0], "b": vals[1]}
        elif "lcm" in lower or "least common" in lower:
            chalkboard.formula_name = "lcm"
            vals = [int(n["value"]) for n in numbers if n["value"] > 0]
            if len(vals) >= 2:
                chalkboard.variables = {"a": vals[0], "b": vals[1]}

    elif ptype == "logarithm":
        if "ln" in lower or "natural log" in lower:
            chalkboard.formula_name = "natural_log"
            val = next((n["value"] for n in numbers), None)
            if val:
                chalkboard.variables = {"x": val}
        elif "log base" in lower or "log_" in lower:
            chalkboard.formula_name = "log_base_n"
            # Extract base and value via regex: "log base B of X"
            base_match = re.search(r'log\s+base\s+(\d+\.?\d*)', lower)
            of_match = re.search(r'of\s+(\d+\.?\d*)', lower)
            if base_match and of_match:
                chalkboard.variables = {"b": float(base_match.group(1)), "x": float(of_match.group(1))}
            else:
                vals = [n["value"] for n in numbers]
                if len(vals) >= 2:
                    chalkboard.variables = {"b": vals[0], "x": vals[1]}
                elif len(vals) == 1:
                    # Same value for base and argument (e.g. log base 2 of 2)
                    chalkboard.variables = {"b": vals[0], "x": vals[0]}
        else:
            # Default: log base 10
            chalkboard.formula_name = "log_base_10"
            val = next((n["value"] for n in numbers), None)
            if val:
                chalkboard.variables = {"x": val}

    elif ptype == "statistics":
        chalkboard.formula_name = "__statistics__"
        # Determine which statistic
        if any(w in lower for w in ["mean", "average"]):
            chalkboard.variables = {"stat": "mean"}
        elif "median" in lower:
            chalkboard.variables = {"stat": "median"}
        elif "mode" in lower:
            chalkboard.variables = {"stat": "mode"}
        elif "std" in lower or "standard deviation" in lower:
            chalkboard.variables = {"stat": "std"}
        elif "variance" in lower:
            chalkboard.variables = {"stat": "variance"}
        elif "range" in lower:
            chalkboard.variables = {"stat": "range"}
        else:
            chalkboard.variables = {"stat": "mean"}  # default

    elif ptype == "healthcare":
        # Helper: extract labeled value from text
        def _hc_val(patterns):
            for pat in patterns:
                m = re.search(pat, lower)
                if m:
                    return float(m.group(1).replace(",", ""))
            return None

        if "bmi" in lower or "body mass index" in lower:
            chalkboard.formula_name = "bmi"
            w = _hc_val([r"(\d+\.?\d*)\s*kg", r"weight\s*[:=]?\s*(\d+\.?\d*)"])
            h = _hc_val([r"(\d+\.?\d*)\s*(?:m|meters?)\b", r"height\s*[:=]?\s*(\d+\.?\d*)"])
            if w and h:
                chalkboard.variables = {"weight": w, "height": h}

        elif "mean arterial" in lower or ("map" in lower.split() and ("systolic" in lower or "/" in lower)):
            chalkboard.formula_name = "map"
            bp_match = re.search(r'(\d+)\s*/\s*(\d+)', lower)
            if bp_match:
                chalkboard.variables = {"SBP": float(bp_match.group(1)), "DBP": float(bp_match.group(2))}
            else:
                sbp = _hc_val([r"systolic\s*[:=]?\s*(\d+)", r"sbp\s*[:=]?\s*(\d+)"])
                dbp = _hc_val([r"diastolic\s*[:=]?\s*(\d+)", r"dbp\s*[:=]?\s*(\d+)"])
                if sbp and dbp:
                    chalkboard.variables = {"SBP": sbp, "DBP": dbp}

        elif "corrected calcium" in lower or "corrected ca" in lower:
            chalkboard.formula_name = "corrected_calcium"
            ca = _hc_val([r"(?:calcium|ca)\s*[:=]?\s*(\d+\.?\d*)", r"measured\s*[:=]?\s*(\d+\.?\d*)"])
            alb = _hc_val([r"albumin\s*[:=]?\s*(\d+\.?\d*)"])
            if ca and alb:
                chalkboard.variables = {"Ca": ca, "albumin": alb}

        elif "anion gap" in lower:
            chalkboard.formula_name = "anion_gap"
            na = _hc_val([r"(?:sodium|na)\s*[:=]?\s*(\d+\.?\d*)"])
            cl = _hc_val([r"(?:chloride|cl)\s*[:=]?\s*(\d+\.?\d*)"])
            hco3 = _hc_val([r"(?:bicarbonate|bicarb|hco3)\s*[:=]?\s*(\d+\.?\d*)"])
            if na and cl and hco3:
                chalkboard.variables = {"Na": na, "Cl": cl, "HCO3": hco3}

        elif "creatinine clearance" in lower or "cockcroft" in lower:
            is_female = "female" in lower or "woman" in lower
            chalkboard.formula_name = "cockcroft_gault_female" if is_female else "cockcroft_gault_male"
            age = _hc_val([r"(\d+)\s*(?:year|yr|y/?o)", r"age\s*[:=]?\s*(\d+)"])
            w = _hc_val([r"(\d+\.?\d*)\s*kg", r"weight\s*[:=]?\s*(\d+\.?\d*)"])
            cr = _hc_val([r"(?:creatinine|cr)\s*[:=]?\s*(\d+\.?\d*)"])
            if age and w and cr:
                chalkboard.variables = {"age": age, "weight": w, "Cr": cr}

        elif "egfr" in lower:
            is_female = "female" in lower or "woman" in lower
            chalkboard.formula_name = "egfr_female" if is_female else "egfr_male"
            age = _hc_val([r"(\d+)\s*(?:year|yr|y/?o)", r"age\s*[:=]?\s*(\d+)"])
            cr = _hc_val([r"(?:creatinine|cr)\s*[:=]?\s*(\d+\.?\d*)"])
            if age and cr:
                chalkboard.variables = {"age": age, "Cr": cr}

        elif "meld" in lower:
            chalkboard.formula_name = "meld_score"
            cr = _hc_val([r"(?:creatinine|cr)\s*[:=]?\s*(\d+\.?\d*)"])
            bili = _hc_val([r"(?:bilirubin|bili)\s*[:=]?\s*(\d+\.?\d*)"])
            inr = _hc_val([r"inr\s*[:=]?\s*(\d+\.?\d*)"])
            if cr and bili and inr:
                chalkboard.variables = {"Cr": cr, "Bili": bili, "INR": inr}

        elif "qtc" in lower:
            chalkboard.formula_name = "qtc_bazett"
            qt = _hc_val([r"qt\s*[:=]?\s*(\d+\.?\d*)", r"(\d+)\s*ms"])
            hr = _hc_val([r"(?:heart rate|hr|pulse)\s*[:=]?\s*(\d+)"])
            if qt and hr:
                chalkboard.variables = {"QT": qt, "HR": hr}

        elif "ideal body weight" in lower or "ibw" in lower:
            is_female = "female" in lower or "woman" in lower
            chalkboard.formula_name = "ibw_female" if is_female else "ibw_male"
            h = _hc_val([r"(\d+\.?\d*)\s*(?:inch|in\b|\")", r"height\s*[:=]?\s*(\d+\.?\d*)"])
            if h:
                chalkboard.variables = {"height_in": h}

        elif "drip rate" in lower or "iv rate" in lower:
            chalkboard.formula_name = "iv_drip_rate"
            vol = _hc_val([r"(\d+\.?\d*)\s*ml", r"volume\s*[:=]?\s*(\d+\.?\d*)"])
            t = _hc_val([r"(\d+\.?\d*)\s*(?:hour|hr|h\b)", r"time\s*[:=]?\s*(\d+\.?\d*)"])
            if vol and t:
                chalkboard.variables = {"volume": vol, "time": t}

        elif "dose" in lower and ("mg/kg" in lower or "per kg" in lower):
            chalkboard.formula_name = "pediatric_dose"
            w = _hc_val([r"(\d+\.?\d*)\s*kg"])
            d = _hc_val([r"(\d+\.?\d*)\s*mg/kg", r"(\d+\.?\d*)\s*mg\s*per\s*kg"])
            if w and d:
                chalkboard.variables = {"weight": w, "dose_per_kg": d}

        elif "a-a gradient" in lower or "aa gradient" in lower:
            chalkboard.formula_name = "aa_gradient"
            fio2 = _hc_val([r"fio2\s*[:=]?\s*(\d+\.?\d*)"])
            paco2 = _hc_val([r"paco2\s*[:=]?\s*(\d+\.?\d*)"])
            pao2 = _hc_val([r"pao2\s*[:=]?\s*(\d+\.?\d*)"])
            if fio2 and paco2 and pao2:
                # Convert percentage to fraction if > 1
                if fio2 > 1:
                    fio2 = fio2 / 100
                chalkboard.variables = {"FiO2": fio2, "PaCO2": paco2, "PaO2": pao2}

    # Fallback: try raw expression evaluation
    if not chalkboard.formula_name and chalkboard.raw_expression:
        chalkboard.formula_name = "__raw_expression__"

    chalkboard.steps_trace.append({
        "agent": "Planner",
        "formula": chalkboard.formula_name,
        "variables": chalkboard.variables,
    })

    return chalkboard


# ── Agent 4: Compute ─────────────────────────────────────────

def compute(chalkboard: Chalkboard, engine: MathEngine) -> Chalkboard:
    """Execute the computation via SymPy."""
    if chalkboard.formula_name in ("gcd", "lcm"):
        # GCD/LCM must be computed with concrete integers, not symbolic
        import sympy as _sp
        a = int(chalkboard.variables.get("a", 0))
        b = int(chalkboard.variables.get("b", 0))
        if chalkboard.formula_name == "gcd":
            val = int(_sp.gcd(a, b))
            steps = [f"GCD({a}, {b})", f"Result: {val}"]
        else:
            val = int(_sp.lcm(a, b))
            steps = [f"LCM({a}, {b})", f"Result: {val}"]
        result = ComputeResult(
            success=True, formula_name=chalkboard.formula_name,
            expression=f"{chalkboard.formula_name}({a}, {b})",
            exact=str(val), numeric=float(val), steps=steps,
        )
    elif chalkboard.formula_name == "__statistics__":
        data = chalkboard.data_list
        stat = chalkboard.variables.get("stat", "mean")
        if data:
            result = engine.evaluate_statistics(stat, data)
        else:
            result = ComputeResult(success=False, error="No data found for statistics. Use format: mean of 1, 2, 3, 4, 5")
    elif chalkboard.formula_name == "__raw_expression__":
        result = engine.evaluate_raw(chalkboard.raw_expression)
    elif chalkboard.formula_name == "__solve_equation__":
        # Extract equation from problem text
        eq_match = re.search(r"solve\s+(.+?)(?:\s+for\s+(\w+))?$", chalkboard.problem.lower())
        if eq_match:
            equation = eq_match.group(1)
            solve_for = eq_match.group(2) or "x"
            result = engine.solve_equation(equation, solve_for, chalkboard.variables)
        else:
            result = ComputeResult(success=False, error="Could not parse equation")
    elif chalkboard.formula_name:
        result = engine.evaluate(chalkboard.formula_name, chalkboard.variables)
    else:
        result = ComputeResult(success=False, error="No formula or expression identified")

    chalkboard.result = result
    chalkboard.steps_trace.append({
        "agent": "Compute",
        "success": result.success,
        "exact": result.exact,
        "numeric": result.numeric,
        "error": result.error,
    })

    return chalkboard


# ── Agent 5: Verify ──────────────────────────────────────────

def verify(chalkboard: Chalkboard, engine: MathEngine) -> Chalkboard:
    """Verify the result with sanity checks."""
    if not chalkboard.result or not chalkboard.result.success:
        chalkboard.verified = False
        chalkboard.verification = {"passed": False, "reason": "computation failed"}
        chalkboard.steps_trace.append({"agent": "Verify", "passed": False})
        return chalkboard

    # Build verification checks based on problem type
    checks = {}
    if chalkboard.problem_type == "finance":
        checks["positive"] = True  # financial results should be positive
        if chalkboard.formula_name == "mortgage_payment":
            p = chalkboard.variables.get("P", 0)
            checks["max"] = p  # monthly payment can't exceed principal
            checks["min"] = 0
        elif chalkboard.formula_name == "roi":
            checks["min"] = -100  # ROI can't be less than -100%
    elif chalkboard.problem_type == "geometry":
        checks["positive"] = True  # areas and volumes are positive
    elif chalkboard.problem_type == "percentage":
        if chalkboard.formula_name == "percentage":
            checks["min"] = 0  # tip/tax result should be positive

    verification = engine.verify(chalkboard.result, checks)

    # Cross-verify: compute a second way if possible
    if chalkboard.formula_name == "mortgage_payment" and chalkboard.result.numeric:
        n = chalkboard.variables.get("n", 360)
        total_paid = chalkboard.result.numeric * n
        p = chalkboard.variables.get("P", 0)
        if total_paid < p:
            verification["passed"] = False
            verification["checks"].append({
                "check": "total_paid_sanity",
                "passed": False,
                "reason": f"Total paid ({total_paid:.2f}) < principal ({p}) — impossible"
            })

    chalkboard.verified = verification["passed"]
    chalkboard.verification = verification
    chalkboard.steps_trace.append({"agent": "Verify", "passed": verification["passed"], "checks": verification["checks"]})

    return chalkboard


# ── Agent 6: Explainer ───────────────────────────────────────

def explain(chalkboard: Chalkboard, engine: MathEngine) -> Chalkboard:
    """Format the result with step-by-step explanation."""
    if not chalkboard.result or not chalkboard.result.success:
        chalkboard.explanation = f"Could not solve: {chalkboard.result.error if chalkboard.result else 'unknown error'}"
        return chalkboard

    lines = []
    lines.append(f"**Problem:** {chalkboard.problem}")
    lines.append(f"**Type:** {chalkboard.problem_type}")
    lines.append("")

    # Formula used
    if chalkboard.formula_name and chalkboard.formula_name not in ("__raw_expression__", "__solve_equation__"):
        formula = engine.formulas.get(chalkboard.formula_name, {})
        lines.append(f"**Formula:** {formula.get('formula', chalkboard.formula_name)}")
        lines.append("")

    # Steps
    if chalkboard.result.steps:
        lines.append("**Steps:**")
        for step in chalkboard.result.steps:
            lines.append(f"  {step}")
        lines.append("")

    # Result
    if chalkboard.result.numeric is not None:
        # Format based on problem type
        numeric = chalkboard.result.numeric
        if chalkboard.problem_type == "finance" or any(n["type"] == "currency" for n in chalkboard.numbers):
            formatted = f"${numeric:,.2f}"
        elif chalkboard.problem_type == "percentage":
            if chalkboard.formula_name == "percentage_change":
                formatted = f"{numeric:.2f}%"
            else:
                formatted = f"${numeric:,.2f}" if any(n["type"] == "currency" for n in chalkboard.numbers) else f"{numeric:,.4f}"
        else:
            formatted = f"{numeric:,.6g}"

        lines.append(f"**Answer: {formatted}**")

        if chalkboard.result.exact and str(chalkboard.result.exact) != str(numeric):
            lines.append(f"**Exact:** {chalkboard.result.exact}")

    # Verification
    if chalkboard.verified:
        lines.append(f"\n*Verified: all sanity checks passed*")
    else:
        lines.append(f"\n*Warning: verification issues — {chalkboard.verification}*")

    chalkboard.explanation = "\n".join(lines)
    chalkboard.steps_trace.append({"agent": "Explainer", "output_length": len(chalkboard.explanation)})

    return chalkboard


# ── Pipeline Orchestrator ────────────────────────────────────

def solve(problem: str) -> dict:
    """Run the full 6-agent math pipeline."""
    start = time.time()
    engine = MathEngine()

    chalkboard = Chalkboard(problem=problem)

    # Sequential chalkboard pipeline
    chalkboard = parse(chalkboard)
    chalkboard = classify(chalkboard)
    chalkboard = plan(chalkboard, engine)
    chalkboard = compute(chalkboard, engine)
    chalkboard = verify(chalkboard, engine)
    chalkboard = explain(chalkboard, engine)

    elapsed_ms = int((time.time() - start) * 1000)
    chalkboard.total_time_ms = elapsed_ms

    return {
        "success": chalkboard.result.success if chalkboard.result else False,
        "answer": chalkboard.result.numeric if chalkboard.result else None,
        "exact": chalkboard.result.exact if chalkboard.result else None,
        "explanation": chalkboard.explanation,
        "problem_type": chalkboard.problem_type,
        "formula_used": chalkboard.formula_name,
        "verified": chalkboard.verified,
        "verification": chalkboard.verification,
        "trace": chalkboard.steps_trace,
        "elapsed_ms": elapsed_ms,
        "cost_usd": 0.0,
    }


# ── CLI ──────────────────────────────────────────────────────

def main():
    if not sys.stdin.isatty():
        # Stdin JSON mode (Swarm Claw integration)
        data = json.loads(sys.stdin.read())
        problem = data.get("problem", data.get("message", ""))
        result = solve(problem)
        print(json.dumps(result, indent=2))
        return

    import argparse
    ap = argparse.ArgumentParser(description="Math Swarm — exact computation pipeline")
    ap.add_argument("--problem", help="Math problem to solve")
    ap.add_argument("--interactive", action="store_true", help="Interactive mode")
    args = ap.parse_args()

    if args.interactive:
        print("=" * 50)
        print("  MATH SWARM — Exact Computation")
        print("  6 agents | SymPy backend | $0/calc")
        print("  Type 'quit' to exit")
        print("=" * 50)
        while True:
            try:
                problem = input("\nmath> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not problem or problem.lower() in ("quit", "exit", "q"):
                break
            result = solve(problem)
            print(f"\n{result['explanation']}")
            print(f"\n[{result['problem_type']} | {result['formula_used']} | {result['elapsed_ms']}ms | verified={result['verified']}]")

    elif args.problem:
        result = solve(args.problem)
        print(result["explanation"])
        print(f"\n[{result['elapsed_ms']}ms | verified={result['verified']} | $0]")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
