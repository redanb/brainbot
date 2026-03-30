import sys
from thinking_engine import ThinkingEngine

te = ThinkingEngine()
regime = te.get_current_regime()
print(f"TEST REGIME: {regime}")
if regime == "UNKNOWN":
    print("Failed to get live regime")
    sys.exit(1)
sys.exit(0)
