
import json
from pathlib import Path
from datetime import datetime

master = Path(r"C:\Users\admin\.antigravity\master")
ls_path = master / "learning_state.json"

data = {}
try:
    data = json.loads(ls_path.read_text(encoding='utf-8'))
except:
    pass

if 'learnings' not in data:
    data['learnings'] = []

new_rules = [
    {
        "PREVENT_REPEAT": True,
        "rule": "ALWAYS log simulation failures as FAILED not EVALUATING: if sharpe=0.0 and fitness=0.0 in simulate() response, log status=FAILED, not EVALUATING. Use centralized _log_alpha_result() helper.",
        "correction_path": "Added _log_alpha_result() helper in alpha_factory.py that auto-detects zero-metric failures. Replaced all inline log_brain_submission(status='EVALUATING') calls.",
        "category": "brain_api",
        "timestamp": datetime.now().isoformat()
    },
    {
        "PREVENT_REPEAT": True,
        "rule": "Cerebras correct model is 'llama3.1-8b' not 'gpt-oss-120b'. The gpt-oss-120b model returns 404 Not Found. Always verify Cerebras model strings against confirmed telemetry.",
        "correction_path": "Updated _call_cerebras() default model in llm_router.py from gpt-oss-120b to llama3.1-8b. Telemetry confirmed 1 success with llama3.1-8b.",
        "category": "llm_router",
        "timestamp": datetime.now().isoformat()
    },
    {
        "PREVENT_REPEAT": True,
        "rule": "DeepSeek is PERMANENTLY DISABLED as of 2026-04-05 due to 402 Insufficient Balance. Never add it back to PROVIDER_CHAIN without TopUp confirmation. Fast-fail with raise at start of _call_deepseek().",
        "correction_path": "Added raise EnvironmentError at top of _call_deepseek() to immediately skip it without any API calls.",
        "category": "llm_router",
        "timestamp": datetime.now().isoformat()
    },
    {
        "PREVENT_REPEAT": True,
        "rule": "WQ IQC submission gate requires ALL of: Sharpe>=1.25, Fitness>=1.0, Turnover<=0.70, Returns>0, sub_universe_sharpe>=-0.52. Missing gates cause submit+fail cycles wasting simulation budget.",
        "correction_path": "Updated meets_submission_criteria() in alpha_factory.py to include returns and sub_universe_sharpe gates.",
        "category": "brain_api",
        "timestamp": datetime.now().isoformat()
    },
    {
        "PREVENT_REPEAT": True,
        "rule": "Evolution log cap must be at least 500 entries, not 60. A 60-entry cap destroys historical data within a single factory run and makes post-run analysis impossible.",
        "correction_path": "Changed data['brain'] = data['brain'][-60:] to [-500:] in evolution_tracker.py.",
        "category": "system",
        "timestamp": datetime.now().isoformat()
    }
]

data['learnings'].extend(new_rules)
ls_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(f"Saved {len(new_rules)} new rules to learning_state.json. Total: {len(data['learnings'])} learnings.")
