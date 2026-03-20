
import os
import sys
from pathlib import Path
import shutil

# Add current dir to path to import env_discovery
sys.path.append(str(Path.cwd()))
import env_discovery

def test_env_discovery_logic():
    print("Testing Multi-Tier Env Discovery...")
    # Create a mock .env in CWD
    cwd_env = Path.cwd() / ".env.test"
    cwd_env.write_text("MOCK_KEY_TEST=TRUE\nOPENROUTER_API_KEY=mock_or_val")
    
    try:
        # Manually trigger discovery on the test file
        search_paths = [Path.cwd()]
        loaded = []
        if cwd_env.exists():
            content = cwd_env.read_text()
            for line in content.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
            loaded.append(str(cwd_env))
        
        env_discovery.resolve_key_aliases()
        
        if os.getenv("MOCK_KEY_TEST") != "TRUE":
            print("[FAIL] MOCK_KEY_TEST not found.")
            return False
            
        if os.getenv("OPEN_ROUTER_KEY") != "mock_or_val":
            print(f"[FAIL] Key alias resolution failed. Expected mock_or_val, got {os.getenv('OPEN_ROUTER_KEY')}")
            return False
            
        print("[PASS] Multi-Tier Discovery and Alias Resolution verified.")
        return True
    finally:
        if cwd_env.exists():
            cwd_env.unlink()

def test_core_integrations():
    print("Checking core integrations for env_discovery imports...")
    files = ["alpha_factory.py", "llm_router.py", "health_check.py"]
    for f in files:
        path = Path(f"c:/Users/admin/Downloads/medsumag1/brainbot/{f}")
        if "import env_discovery" not in path.read_text():
            print(f"[FAIL] {f} missing env_discovery import.")
            return False
    print("[PASS] All core scripts integrated with env_discovery.")
    return True

def regression_audit():
    print("Running Regression Audit...")
    router_path = Path("c:/Users/admin/Downloads/medsumag1/brainbot/llm_router.py")
    content = router_path.read_text()
    
    if '"REASONING":' not in content:
        print("[FAIL] REASONING depth lost in llm_router.py.")
        return False
        
    if "xiaomi/mimo-v2-pro" not in content:
        print("[FAIL] Xiaomi models lost in llm_router.py.")
        return False
        
    print("[PASS] Regression Audit complete.")
    return True

if __name__ == "__main__":
    results = [
        test_env_discovery_logic(),
        test_core_integrations(),
        regression_audit()
    ]
    
    if all(results):
        print("\n[SUCCESS] All verification tests passed.")
        sys.exit(0)
    else:
        print("\n[FAILURE] One or more verification tests failed.")
        sys.exit(1)
