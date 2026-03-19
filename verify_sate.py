"""
verify_sate.py
Verifies the Self-Improving Alpha Thinking Engine (SATE) loop.
Tests:
1. ThinkingEngine initialization and regime detection.
2. LLM hypothesis generation (via mock or real call).
3. AlphaFactory integration.
"""
import sys
import os
from pathlib import Path

# Add brainbot to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from thinking_engine import ThinkingEngine
from evolution_tracker import log_brain_submission

def test_thinking_engine():
    print("Testing ThinkingEngine...")
    engine = ThinkingEngine()
    
    regime = engine.get_current_regime()
    print(f"Detected Regime: {regime}")
    assert regime in ["TRENDING", "REVERTING", "STAGNANT", "TRANSITIONAL", "UNKNOWN"]
    
    history = engine.analyze_history()
    print(f"Analyzed History:\n{history}")
    assert isinstance(history, str)
    
    # Test hypothesis evolution (This calls the LLM, so we check formatting)
    print("Testing Hypothesis Evolution (calling Gemini)...")
    try:
        hypothesis = engine.evolve_hypothesis()
        print(f"Generated Hypothesis: {hypothesis}")
        assert "rank" in hypothesis.lower()
        print("[PASS] ThinkingEngine basic checks passed.")
    except Exception as e:
        print(f"[FAIL] ThinkingEngine hypothesis failed: {e}")
        sys.exit(1)

def test_integration():
    print("\nTesting AlphaFactory Integration...")
    try:
        from alpha_factory import generate_hypothesis
        hyp = generate_hypothesis()
        print(f"Factory Hypothesis: {hyp}")
        assert "rank" in hyp.lower()
        print("[PASS] AlphaFactory integration passed.")
    except Exception as e:
        print(f"[FAIL] AlphaFactory integration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_thinking_engine()
    test_integration()
    print("\nSATE VERIFICATION COMPLETE.")
