import os
import sys
from pathlib import Path

PASS = "[PASS]"
FAIL = "[FAIL]"

def check(label, condition, msg=""):
    if condition:
        print(f"{PASS} {label}")
        return True
    else:
        print(f"{FAIL} {label} - {msg}")
        return False

def run_regression_audit():
    print("\n--- REGRESSION AUDIT ---")
    all_passed = True
    
    # 1. Existing functionality check: alpha_factory can be imported
    try:
        import alpha_factory
        all_passed &= check("alpha_factory.py imports successfully", True)
    except Exception as e:
        all_passed &= check("alpha_factory.py imports successfully", False, str(e))
        
    # 2. Existing functionality check: health_check can be imported
    try:
        import health_check
        all_passed &= check("health_check.py imports successfully", True)
    except Exception as e:
        all_passed &= check("health_check.py imports successfully", False, str(e))
        
    return all_passed

def run_feature_checks():
    print("\n--- NEW FEATURE CHECKS ---")
    all_passed = True
    
    # Node 24 Env check in YML
    yml_path = Path(".github/workflows/trinity_hyperscale.yml")
    if yml_path.exists():
        content = yml_path.read_text()
        has_env = "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: \"true\"" in content
        all_passed &= check("GHA Workflow has Node 24 override", has_env, "Missing FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 in env")
    else:
        all_passed &= check("GHA Workflow exists", False, "File not found")
        
    return all_passed

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except:
            pass
            
    r_pass = run_regression_audit()
    f_pass = run_feature_checks()
    
    if r_pass and f_pass:
        print("\n[ALL CHECKS PASSED] Readiness Verified")
        sys.exit(0)
    else:
        print("\n[CHECKS FAILED] See details above")
        sys.exit(1)
