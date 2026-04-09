"""
Math Compute Engine — Exact computation via SymPy.

Takes structured math problems (formula name + variables) and returns
exact symbolic results with numeric evaluation.

Usage:
    from compute import MathEngine
    engine = MathEngine()
    result = engine.evaluate("mortgage_payment", {"P": 450000, "r": 0.065/12, "n": 360})
    # result.exact = "P*r*(r + 1)**n/((r + 1)**n - 1)"
    # result.numeric = 2844.27
    # result.verified = True
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import sympy
from sympy import (
    Rational, Symbol, sqrt, pi, E, oo,
    simplify, nsimplify, N, solve, symbols,
    sin, cos, tan, asin, acos, atan, log, exp, factorial, binomial,
    gcd, lcm, Min, Max,
    Sum, Product, Integral, Derivative,
)

# Standard math functions available to all formula evaluations
_MATH_FUNCTIONS = {
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan,
    "log": log, "exp": exp, "sqrt": sqrt,
    "pi": pi, "E": E,
    "factorial": factorial, "binomial": binomial,
    "gcd": gcd, "lcm": lcm,
    "Min": Min, "Max": Max,
    "Rational": Rational,
}


@dataclass
class ComputeResult:
    """Result from a math computation."""
    success: bool
    formula_name: Optional[str] = None
    expression: Optional[str] = None     # Human-readable expression
    exact: Optional[str] = None          # Exact symbolic result
    numeric: Optional[float] = None      # Numeric evaluation
    steps: list = field(default_factory=list)  # Step-by-step computation
    verification: Optional[dict] = None  # Verification results
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "formula_name": self.formula_name,
            "expression": self.expression,
            "exact": self.exact,
            "numeric": self.numeric,
            "steps": self.steps,
            "verification": self.verification,
            "error": self.error,
        }


class MathEngine:
    """Exact computation engine backed by SymPy + formula KG."""

    def __init__(self, kg_dir: Optional[str] = None):
        self.kg_dir = Path(kg_dir or Path(__file__).parent / "kg")
        self.formulas = self._load_formulas()
        self.constants = self._load_constants()

    def _load_formulas(self) -> dict:
        """Load formula KG into a flat lookup."""
        path = self.kg_dir / "formulas.json"
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        flat = {}
        for category, formulas in data.items():
            for formula in formulas:
                flat[formula["name"]] = {**formula, "domain": category}
        return flat

    def _load_constants(self) -> dict:
        path = self.kg_dir / "constants.json"
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ── Core Compute ─────────────────────────────────────────

    def evaluate(self, formula_name: str, variables: dict) -> ComputeResult:
        """Evaluate a named formula with given variables."""
        if formula_name not in self.formulas:
            return ComputeResult(
                success=False,
                error=f"Unknown formula: {formula_name}. Available: {list(self.formulas.keys())[:20]}"
            )

        formula = self.formulas[formula_name]
        sympy_expr = formula["sympy"]

        try:
            # Create SymPy symbols for all variables
            sym_vars = {}
            for var_name in formula.get("variables", {}):
                sym_vars[var_name] = Symbol(var_name)

            # Parse the expression with math functions in scope
            local_ns = {**_MATH_FUNCTIONS, **sym_vars}
            expr = sympy.sympify(sympy_expr, locals=local_ns)

            # Substitute values
            subs = {}
            steps = [f"Formula: {formula['formula']}"]

            for var_name, value in variables.items():
                if var_name in sym_vars:
                    subs[sym_vars[var_name]] = value
                    steps.append(f"  {var_name} = {value}")

            # Evaluate
            result_expr = expr.subs(subs)
            steps.append(f"Substituted: {result_expr}")

            # Simplify
            simplified = simplify(result_expr)
            steps.append(f"Simplified: {simplified}")

            # Numeric evaluation
            numeric = float(N(simplified))
            steps.append(f"Numeric: {numeric}")

            return ComputeResult(
                success=True,
                formula_name=formula_name,
                expression=formula["formula"],
                exact=str(simplified),
                numeric=round(numeric, 10),
                steps=steps,
            )

        except Exception as e:
            return ComputeResult(
                success=False,
                formula_name=formula_name,
                error=f"Computation failed: {str(e)}"
            )

    def evaluate_raw(self, expression: str, variables: dict = None) -> ComputeResult:
        """Evaluate a raw mathematical expression."""
        try:
            # Create symbols from variable names
            sym_vars = {}
            if variables:
                for var_name in variables:
                    sym_vars[var_name] = Symbol(var_name)

            # Parse expression
            local_ns = {**sym_vars, "sqrt": sqrt, "pi": pi, "e": E,
                       "sin": sin, "cos": cos, "tan": tan,
                       "log": log, "exp": exp, "Rational": Rational}
            expr = sympy.sympify(expression, locals=local_ns)

            steps = [f"Expression: {expression}"]

            # Substitute
            if variables:
                subs = {sym_vars[k]: v for k, v in variables.items() if k in sym_vars}
                expr = expr.subs(subs)
                for k, v in variables.items():
                    steps.append(f"  {k} = {v}")
                steps.append(f"Substituted: {expr}")

            simplified = simplify(expr)
            numeric = float(N(simplified))

            return ComputeResult(
                success=True,
                expression=expression,
                exact=str(simplified),
                numeric=round(numeric, 10),
                steps=steps,
            )

        except Exception as e:
            return ComputeResult(success=False, error=f"Parse/compute failed: {str(e)}")

    def solve_equation(self, equation: str, solve_for: str, variables: dict = None) -> ComputeResult:
        """Solve an equation for a variable."""
        try:
            target = Symbol(solve_for)
            sym_vars = {solve_for: target}
            if variables:
                for k in variables:
                    sym_vars[k] = Symbol(k)

            local_ns = {**sym_vars, "sqrt": sqrt, "pi": pi, "Rational": Rational}

            # Parse equation (split on =)
            if "=" in equation:
                lhs, rhs = equation.split("=", 1)
                lhs_expr = sympy.sympify(lhs.strip(), locals=local_ns)
                rhs_expr = sympy.sympify(rhs.strip(), locals=local_ns)
                eq = lhs_expr - rhs_expr
            else:
                eq = sympy.sympify(equation, locals=local_ns)

            # Substitute known values
            if variables:
                subs = {sym_vars[k]: v for k, v in variables.items() if k in sym_vars}
                eq = eq.subs(subs)

            solutions = solve(eq, target)
            steps = [
                f"Equation: {equation}",
                f"Solving for: {solve_for}",
                f"Solutions: {solutions}",
            ]

            if solutions:
                numeric_sols = [float(N(s)) for s in solutions if s.is_real or s.is_number]
                return ComputeResult(
                    success=True,
                    expression=equation,
                    exact=str(solutions),
                    numeric=numeric_sols[0] if numeric_sols else None,
                    steps=steps,
                )
            else:
                return ComputeResult(success=False, error="No solutions found", steps=steps)

        except Exception as e:
            return ComputeResult(success=False, error=f"Solve failed: {str(e)}")

    # ── Statistics ────────────────────────────────────────────

    def evaluate_statistics(self, stat_type: str, data: list) -> ComputeResult:
        """Compute statistics on a dataset. No LLM needed."""
        if not data:
            return ComputeResult(success=False, error="Empty dataset")

        try:
            n = len(data)
            steps = [f"Data: {data}", f"N: {n}"]
            sorted_data = sorted(data)

            if stat_type == "mean":
                result = sum(data) / n
                steps.append(f"Sum: {sum(data)}")
                steps.append(f"Mean: {sum(data)} / {n} = {result}")
            elif stat_type == "median":
                if n % 2 == 1:
                    result = sorted_data[n // 2]
                else:
                    result = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
                steps.append(f"Sorted: {sorted_data}")
                steps.append(f"Median: {result}")
            elif stat_type == "mode":
                from collections import Counter
                counts = Counter(data)
                max_count = max(counts.values())
                modes = [k for k, v in counts.items() if v == max_count]
                result = modes[0] if len(modes) == 1 else min(modes)
                steps.append(f"Counts: {dict(counts)}")
                steps.append(f"Mode: {result}")
            elif stat_type in ("std", "stdev", "standard_deviation"):
                mean_val = sum(data) / n
                variance = sum((x - mean_val) ** 2 for x in data) / n
                result = math.sqrt(variance)
                steps.append(f"Mean: {mean_val}")
                steps.append(f"Variance: {variance}")
                steps.append(f"Std Dev: {result}")
            elif stat_type == "variance":
                mean_val = sum(data) / n
                result = sum((x - mean_val) ** 2 for x in data) / n
                steps.append(f"Mean: {mean_val}")
                steps.append(f"Variance: {result}")
            elif stat_type == "range":
                result = max(data) - min(data)
                steps.append(f"Range: {max(data)} - {min(data)} = {result}")
            elif stat_type == "sum":
                result = sum(data)
                steps.append(f"Sum: {result}")
            else:
                return ComputeResult(success=False, error=f"Unknown stat: {stat_type}")

            return ComputeResult(
                success=True,
                formula_name=f"statistics_{stat_type}",
                expression=f"{stat_type}({data})",
                exact=str(result),
                numeric=round(float(result), 10),
                steps=steps,
            )
        except Exception as e:
            return ComputeResult(success=False, error=f"Statistics failed: {str(e)}")

    # ── Verification ─────────────────────────────────────────

    def verify(self, result: ComputeResult, checks: dict = None) -> dict:
        """Verify a computation result with sanity checks."""
        verification = {"passed": True, "checks": []}

        if not result.success or result.numeric is None:
            verification["passed"] = False
            verification["checks"].append({"check": "computation", "passed": False, "reason": "computation failed"})
            return verification

        value = result.numeric

        # Standard sanity checks
        if math.isnan(value):
            verification["passed"] = False
            verification["checks"].append({"check": "nan", "passed": False, "reason": "result is NaN"})

        if math.isinf(value):
            verification["passed"] = False
            verification["checks"].append({"check": "infinity", "passed": False, "reason": "result is infinite"})

        # Custom bounds checks
        if checks:
            if "min" in checks and value < checks["min"]:
                verification["passed"] = False
                verification["checks"].append({
                    "check": "min_bound", "passed": False,
                    "reason": f"{value} < {checks['min']}"
                })
            if "max" in checks and value > checks["max"]:
                verification["passed"] = False
                verification["checks"].append({
                    "check": "max_bound", "passed": False,
                    "reason": f"{value} > {checks['max']}"
                })
            if "positive" in checks and checks["positive"] and value <= 0:
                verification["passed"] = False
                verification["checks"].append({
                    "check": "positive", "passed": False,
                    "reason": f"{value} is not positive"
                })
            if "integer" in checks and checks["integer"] and value != int(value):
                verification["checks"].append({
                    "check": "integer", "passed": False,
                    "reason": f"{value} is not an integer"
                })

        if verification["passed"]:
            verification["checks"].append({"check": "all_passed", "passed": True})

        return verification

    # ── Utility ──────────────────────────────────────────────

    def list_formulas(self, domain: Optional[str] = None) -> list:
        """List available formulas, optionally filtered by domain."""
        result = []
        for name, f in self.formulas.items():
            if domain and f.get("domain") != domain:
                continue
            result.append({
                "name": name,
                "formula": f["formula"],
                "domain": f.get("domain"),
                "variables": list(f.get("variables", {}).keys()),
            })
        return result

    def get_constant(self, name: str) -> Optional[dict]:
        """Look up a constant from the KG."""
        for category in self.constants.values():
            if name in category:
                return category[name]
        return None
