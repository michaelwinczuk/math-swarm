# /compute

Compute an exact mathematical answer using SymPy symbolic math instead of token prediction.

## Usage
```
/compute What is the monthly payment on a $450,000 mortgage at 6.5% for 30 years?
/compute eGFR for 65 year old male creatinine 1.4
/compute 347 * 893 + 1729
/compute sine of 45 degrees
/compute mean of 85, 90, 78, 92, 88
```

## Instructions

Run the math swarm computation engine:

```bash
cd $PLUGIN_DIR && python -c "
from math_swarm import solve
import json
result = solve('$ARGUMENTS')
print(json.dumps(result, indent=2))
"
```

Present the result clearly:
- Show the exact answer
- Show verification status
- For healthcare formulas: run clinical decision support and show interpretation + actions + guideline source
