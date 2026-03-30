import os
import sys
import json
from pathlib import Path

def test_phase_8_integrity():
    print("--- 🧠 PHASE 8 REGRESSION AUDIT 🧠 ---")
    
    # 1. Check Rank Fix
    with open('check_brain_rank.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'users/self/ranking' not in content:
             raise AssertionError("Rank endpoint singular not found.")
    print("[PASS] Rank API logic updated.")

    # 2. Check ThinkingEngine Diversity
    with open('thinking_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'sector' not in content or 'industry' not in content:
             raise AssertionError("Neutralization rotation not in TE.")
    print("[PASS] ThinkingEngine diversity prompt updated.")

    # 3. Check Alpha Factory Feedback
    with open('alpha_factory.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'submit(self, alpha_id: str) -> tuple[bool, str]' not in content:
             raise AssertionError("Submit signature not updated.")
    print("[PASS] AlphaFactory submission feedback updated.")

    # 4. Check GHA Scaling
    with open('.github/workflows/trinity_hyperscale.yml', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'batch: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]' not in content:
             raise AssertionError("GHA matrix not scaled to 25.")
    print("[PASS] GHA Hyperscaling matrix updated.")

    # 5. Check Submission Burst Deduplication
    with open('submission_burst.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'seen_exprs = set()' not in content:
             raise AssertionError("Deduplication missing in burst.")
    print("[PASS] SubmissionBurst deduplication updated.")

    print("\n--- 🏁 PHASE 8 ALL AUDITS PASSED 🏁 ---")

if __name__ == "__main__":
    try:
        test_phase_8_integrity()
        sys.exit(0)
    except AssertionError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
