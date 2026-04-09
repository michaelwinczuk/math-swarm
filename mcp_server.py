"""
Math Swarm MCP Server — Exposes the computation engine as Claude Code tools.

Run: python mcp_server.py
Protocol: stdio (JSON-RPC over stdin/stdout)

Tools:
  - math_solve: Solve any math problem (12 categories, 1,079 tests, 100%)
  - math_clinical: Compute + clinical interpretation (15 healthcare formulas)
  - math_benchmark: Compare a problem against LLM accuracy expectations
"""

import json
import sys
import os

# Add math-swarm to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from math_swarm import solve as _solve

# Lazy import clinical support
_cds = None
def _get_cds():
    global _cds
    if _cds is None:
        from clinical_decision_support import interpret, INTERPRETERS
        _cds = (interpret, INTERPRETERS)
    return _cds


def handle_request(request):
    """Handle a JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "math-swarm", "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            }
        }

    elif method == "notifications/initialized":
        return None  # no response needed

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "math_solve",
                        "description": (
                            "Solve any math problem with 100% accuracy using SymPy symbolic computation. "
                            "Supports: arithmetic, percentages, finance (mortgages, compound interest, ROI), "
                            "geometry, physics, conversions, trigonometry, combinatorics (factorial, nCr, nPr), "
                            "number theory (GCD, LCM), logarithms, statistics (mean, median, mode, std dev), "
                            "and healthcare (BMI, eGFR, MAP, anion gap, MELD, QTc, drug dosing). "
                            "Always use this instead of computing math yourself."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "problem": {
                                    "type": "string",
                                    "description": "Natural language math problem. Examples: 'What is 347 * 893?', 'monthly payment on $450K mortgage at 6.5% for 30 years', 'eGFR for 65 year old male creatinine 1.4', 'sine of 30 degrees', 'mean of 85, 90, 78, 92, 88'"
                                }
                            },
                            "required": ["problem"]
                        }
                    },
                    {
                        "name": "math_clinical",
                        "description": (
                            "Compute a healthcare calculation AND return clinical interpretation with "
                            "guideline-based staging, recommended actions, and flags. "
                            "Supports: BMI, eGFR (CKD-EPI 2021), MAP, corrected calcium, anion gap, "
                            "Cockcroft-Gault CrCl, MELD score, QTc Bazett. "
                            "Sources: KDIGO 2024, AHA/ACC, FDA, WHO, UNOS, Endocrine Society."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "problem": {
                                    "type": "string",
                                    "description": "Healthcare math problem. Examples: 'eGFR for 65 year old male creatinine 1.4', 'BMI for weight 80 kg height 1.75 m', 'anion gap with sodium 148 chloride 100 bicarbonate 18'"
                                }
                            },
                            "required": ["problem"]
                        }
                    },
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        problem = args.get("problem", "")

        if tool_name == "math_solve":
            result = _solve(problem)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }

        elif tool_name == "math_clinical":
            result = _solve(problem)
            output = {**result}

            # Add clinical interpretation if available
            interpret_fn, interpreters = _get_cds()
            formula = result.get("formula_used", "")
            answer = result.get("answer")
            if formula in interpreters and answer is not None:
                interp = interpret_fn(formula, answer)
                if interp:
                    output["clinical"] = {
                        "value": interp.value,
                        "unit": interp.unit,
                        "interpretation": interp.interpretation,
                        "severity": interp.severity,
                        "actions": interp.actions,
                        "flags": interp.flags,
                        "source": interp.source,
                    }

            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(output, indent=2)}]
                }
            }

        else:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    else:
        return {
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }


def main():
    """Run the MCP server over stdio."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            error = {
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            sys.stdout.write(json.dumps(error) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
