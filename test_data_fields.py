
import os
import sys
from pathlib import Path

# Load environment
sys.path.append(str(Path.cwd()))
import env_discovery
env_discovery.initialize_environment()

from alpha_factory import BrainAPI

def test_fields():
    # BrainAPI handles connection in __init__
    api = BrainAPI()
    
    # Check for sentiment fields specifically
    test_fields = ["sentiment", "news_count", "analyst_est_up", "fnd6_ebitda"]
    results = {}
    
    print("Verifying data fields...")
    for field in test_fields:
        # We try to simulate a trivial alpha with this field
        # neutralization must be 'subindustry' or 'industry'
        expr = f"group_neutralize(rank({field}), subindustry)"
        try:
            # We use a short simulation to just check if the field is recognized
            res = api.simulate(expr, universe="TOP3000")
            if res and "sharpe" in res:
                results[field] = "AVAILABLE"
            else:
                results[field] = f"UNAVAILABLE ({res.get('error', 'Unknown Error')})"
        except Exception as e:
            results[field] = f"ERROR: {e}"

    print("\nData Field Availability Results:")
    for f, status in results.items():
        print(f" - {f}: {status}")

if __name__ == "__main__":
    test_fields()
