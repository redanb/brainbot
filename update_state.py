import json
from pathlib import Path

# Update learning_state.json
state_file = Path(r"C:\Users\admin\.antigravity\master\learning_state.json")
if state_file.exists():
    data = json.loads(state_file.read_text(encoding="utf-8"))
    
    new_rule = {
        "PREVENT_REPEAT": True,
        "correction_path": "Fixed Node.js 20 deprecation by setting global env FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 and robustifying path resolution.",
        "rule": "Always specify required Node.js versions via global Action env vars to avoid runner deprecation failures. Ensure environment discovery occurs before checking specific keys in CI pipelines.",
        "category": "CI/CD Stability",
        "source_task": "Trinity Pulse GHA Fix"
    }
    
    if "permanent_rules" not in data:
        data["permanent_rules"] = []
    data["permanent_rules"].append(new_rule)
    
    state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Updated learning_state.json")

# Update RESUME_CONTEXT.md
resume_file = Path(r"C:\Users\admin\.antigravity\master\RESUME_CONTEXT.md")
if resume_file.exists():
    content = resume_file.read_text(encoding="utf-8")
    
    new_status = """
---
### Execution Status - Trinity Pulse Hyperscaling Fixes (2026-03-25)
- [x] **Resolved Node.js 20 Deprecation**: Set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` globally in GHA.
- [x] **Fixed Health Check Crash**: Initialized `env_discovery` before checking `ANTIGRAVITY_MASTER_DIR` to ensure correct OS path resolution.
- [x] **Verified**: Full regression audit via `verify_task.py` PASSED with 0 exit code.
"""
    if "Trinity Pulse Hyperscaling Fixes" not in content:
        with open(resume_file, "a", encoding="utf-8") as f:
            f.write(new_status)
        print("Updated RESUME_CONTEXT.md")

print("Reflect() Protocol Complete.")
