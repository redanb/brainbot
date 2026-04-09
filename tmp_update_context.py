import json
from pathlib import Path

# Update learning_state.json
learning_file = Path(r"C:\Users\admin\.antigravity\master\learning_state.json")
if learning_file.exists():
    data = json.loads(learning_file.read_text(encoding="utf-8"))
    
    new_rule = {
        "PREVENT_REPEAT": True,
        "correction_path": "Re-aligned brainbot thresholds and built a detailed 403 API Validation parser instead of infinite-looping 403 errors.",
        "rule": "Always explicitly map external API limits and structural validation requirements to internal defaults. Never mindlessly retry 4xx errors without first attempting to parse the JSON reason payload to abort deterministic validation rejections.",
        "category": "API Resilience",
        "source_task": "Alpha Submission Resolution"
    }
    
    # Add to permanent rules if 'permanent_rules' exists, else 'singularity_rules'
    if "permanent_rules" in data:
        data["permanent_rules"].append(new_rule)
    else:
        data["singularity_rules"].append(new_rule)
        
    learning_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Updated learning_state.json")

# Update RESUME_CONTEXT.md
resume_file = Path(r"C:\Users\admin\.antigravity\master\RESUME_CONTEXT.md")
if resume_file.exists():
    context = resume_file.read_text(encoding="utf-8")
    
    new_section = """
## Execution Status - Alpha Submission Constraints (Phase 13) DEPLOYED
- [x] Synchronized `alpha_factory.py` local boundaries to WQ Brain explicit limits (`Sharpe >= 1.25`, `Fitness >= 1.00`).
- [x] Implemented targeted JSON parser for `HTTP 403` validation paths in `BrainAPI.submit()` to abort instantly on fails.
- [x] Injected string hints directly into `ThinkingEngine.evolve_hypothesis()` on fitness failure.
- [x] Verified `verify_task.py` local rules alignment and zero-regression mock execution.
"""
    
    # insert at the top after "---"
    parts = context.split("---", 1)
    if len(parts) == 2:
        context = parts[0] + "---\n" + new_section + parts[1]
    else:
        context = new_section + "\n" + context
        
    resume_file.write_text(context, encoding="utf-8")
    print("Updated RESUME_CONTEXT.md")
