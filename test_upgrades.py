
import sys
import os
from pathlib import Path

# Add directories to path
sys.path.insert(0, str(Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\brainbot")))
sys.path.insert(0, str(Path(r"c:\Users\admin\Downloads\medsumag1\comp bet")))

from alpha_factory import is_high_conviction
from thinking_engine import ThinkingEngine
import thinking_engine

def test_high_conviction():
    print("Testing High-Conviction Override Logic...")
    
    # Standard: Low Sharpe, High Fitness
    m1 = {"sharpe": 1.1, "fitness": 1.0, "turnover": 0.5}
    # Champion: High Sharpe, Low Fitness (The VkEEb31A case)
    m2 = {"sharpe": 1.9, "fitness": 0.75, "turnover": 0.4}
    # Fail: Low Sharpe, Low Fitness
    m3 = {"sharpe": 1.1, "fitness": 0.5, "turnover": 0.5}
    # Fail: High Sharpe, High Turnover
    m4 = {"sharpe": 2.0, "fitness": 1.0, "turnover": 0.9}

    assert is_high_conviction(m1) == False, "m1 should not be high conviction (Sharpe too low)"
    assert is_high_conviction(m2) == True, "m2 SHOULD be high conviction (Override case)"
    assert is_high_conviction(m3) == False, "m3 should fail"
    assert is_high_conviction(m4) == False, "m4 should fail due to turnover"
    
    print("[PASS] High-Conviction logic verified.")

def test_thinking_engine():
    print("Testing Thinking Engine Evolution...")
    engine = ThinkingEngine()
    
    print("Mocking route_query in thinking_engine module...")
    original_route = thinking_engine.route_query
    
    try:
        # Proper mocking of the imported function in the target module
        # Note: Must include 'provider' key to avoid fallbacks
        thinking_engine.route_query = lambda **kwargs: {"text": "group_neutralize(rank(fnd6_fopo / debt_lt), SUBINDUSTRY)", "provider": "mock"}
        expr = engine.evolve_hypothesis()
        print(f"Generated expression: {expr}")
        assert "group_neutralize" in expr
        assert "fnd6_fopo" in expr
        
        thinking_engine.route_query = lambda **kwargs: {"text": "Here is your alpha:\n```python\ngroup_neutralize(ts_rank(fnd6_ebitda, 252), SUBINDUSTRY)\n```", "provider": "mock"}
        expr = engine.evolve_hypothesis()
        print(f"Generated multi-line expression: {expr}")
        assert "ts_rank" in expr
        assert "252" in expr
        
    finally:
        thinking_engine.route_query = original_route

    print("[PASS] Thinking Engine extraction and prompt logic verified.")

if __name__ == "__main__":
    try:
        test_high_conviction()
        test_thinking_engine()
        print("\nALL UPGRADE TESTS PASSED.")
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
