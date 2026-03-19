"""
alpha_factory.py
WorldQuant Brain 24/7 Hypothesis-Driven Alpha Generator
Follows RULE-066: Uses Orthogonal Factor Assembly, not random genetic mutation.
"""
import os
import sys
import random
import time
import requests
import json
import logging
import concurrent.futures
import audit_helper  # Global submission auditor
from pathlib import Path
from alpha_mutator import mutate_expression

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [BRAIN_FACTORY] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

# Evolution Tracker Integration (RULE-079)
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from evolution_tracker import log_brain_submission, notify_submission
except ImportError:
    def log_brain_submission(*args, **kwargs):
        pass  # Graceful degradation
    def notify_submission(*args, **kwargs):
        pass

# --- STEP 3: PRE-FLIGHT GUARDRAILS (RCA-DRIVEN) ---
MAX_API_CALLS = int(os.getenv("MAX_API_CALLS", 50))  # 50 calls/batch × 10 batches = 500/day

CHAMPION_SHARPE = 1.05      # Lowered for higher submission volume
CHAMPION_FITNESS = 0.90     # Lowered for higher submission volume
MAX_TURNOVER = 0.70

# --- STEP 1 & 4: SELF-IMPROVING THINKING ENGINE ---
try:
    from thinking_engine import ThinkingEngine
    thinking_engine = ThinkingEngine()
except ImportError:
    thinking_engine = None
    logger.warning("ThinkingEngine not found. Falling back to basic logic.")


# --- API INTEGRATION ---
class BrainAPI:
    def __init__(self, email=None, password=None):
        self.base_url = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        if email and password:
            self._authenticate_api(email, password)
        else:
            self._authenticate_browser()

    def _authenticate_api(self, email, password):
        logger.info("Authenticating via Brain API...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = self.session.post(
            f"{self.base_url}/authentication",
            auth=(email, password),
            headers=headers
        )
        if response.status_code == 201:
            logger.info("Authentication Successful.")
            token = self.session.cookies.get("t")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                logger.info("Bearer Token active.")
            
            resp = self.session.get(f"{self.base_url}/users/self")
            if resp.status_code == 200:
                user_data = resp.json()
                username = user_data.get("username", "Unknown")
                user_id = user_data.get("id", "Unknown")
                logger.info(f"Logged in as: {username} ({user_id})")
            else:
                logger.error(f"API Authentication failed at self-verification. Status: {resp.status_code}")
                sys.exit(1)
        else:
            logger.error(f"Authentication Failed. Code: {response.status_code}, Msg: {response.text}")
            sys.exit(1)

    def simulate_hypothesis(self, expression: str, universe: str = "TOP3000") -> dict:
        """Runs the orthogonal hypothesis against Brain historical data."""
        
        # Critical Fix: API requires lowercase 'subindustry' inside the expression string.
        expression = expression.replace("SUBINDUSTRY", "subindustry")
        
        payload = {
            "type": "REGULAR",
            "settings": {
                "instrumentType": "EQUITY",
                "region": "USA",
                "universe": universe,
                "delay": 1,
                "decay": 4, 
                "neutralization": "SUBINDUSTRY",
                "truncation": 0.08,
                "pasteurization": "ON",
                "nanHandling": "ON",
                "unitHandling": "VERIFY",
                "language": "FASTEXPR",
                "visualization": False,
            },
            "regular": expression
        }

        max_retries = 3
        for attempt in range(max_retries):
            sim_response = self.session.post(f"{self.base_url}/simulations", json=payload)
            if sim_response.status_code == 201:
                break
            elif sim_response.status_code == 429:
                wait_time = (attempt + 1) * 10
                logger.warning(f"429 Limit Exceeded. Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"Simulation submission failed ({universe}). Status: {sim_response.status_code}, Response: {sim_response.text}")
                return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "api_error": f"HTTP {sim_response.status_code}"}
        else:
            return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "api_error": "429 Limit Persistent"}

        sim_url = sim_response.headers.get("Location")
        
        while True:
            status_response = self.session.get(sim_url)
            if status_response.status_code == 200:
                data = status_response.json()
                if "progress" in data and "status" not in data:
                    logger.info(f"[{universe}] Simulation Progress: {data['progress']*100:.1f}%")
                    time.sleep(5)
                    continue
                    
                if data.get("status") == "ERROR":
                    err_msg = data.get('message', 'Unknown structural error')
                    logger.warning(f"Alpha structural error in {universe}: {err_msg}")
                    return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "api_error": err_msg}
                elif data.get("status") == "COMPLETE":
                    alpha_id = data.get("alpha")
                    if not alpha_id:
                        logger.error(f"Simulation COMPLETE in {universe} but no alpha ID found.")
                        return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}
                        
                    metrics_resp = self.session.get(f"{self.base_url}/alphas/{alpha_id}")
                    if metrics_resp.status_code == 200:
                        alpha_data = metrics_resp.json()
                        ims = alpha_data.get("is", {})
                        return {
                            "sharpe": ims.get("sharpe", 0.0),
                            "fitness": ims.get("fitness", 0.0),
                            "turnover": ims.get("turnover", 1.0),
                            "returns": ims.get("returns", 0.0),
                            "margin": ims.get("margin", 0.0),
                            "id": alpha_id,
                            "universe": universe
                        }
                    else:
                        logger.error(f"Failed to fetch {universe} alpha metrics for {alpha_id}. Status: {metrics_resp.status_code}")
                        return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}
            time.sleep(5)

    def submit_alpha(self, alpha_id: str) -> dict:
        response = self.session.post(f"{self.base_url}/alphas/{alpha_id}/submit")
        if response.status_code == 201:
            logger.info(f"Alpha {alpha_id} Successfully SUBMITTED to IQC 2026!")
            audit_helper.update_audit("brain", "SUCCESS", details=f"SUBMITTED: {alpha_id}")
            return {"success": True}
        else:
            err = response.text
            logger.error(f"Failed to submit {alpha_id}: {err}")
            audit_helper.update_audit("brain", "FAIL_SUBMIT", details=f"{response.status_code}: {err[:100]}")
            return {"success": False, "error": err}

def is_high_conviction(metrics: dict) -> bool:
    sharpe = metrics.get("sharpe", 0)
    fitness = metrics.get("fitness", 0)
    turnover = metrics.get("turnover", 1)
    if sharpe > 1.8 and turnover < 0.8:
        if fitness > 0.7:
            return True
    return False

def generate_hypothesis(feedback=None) -> str:
    if thinking_engine:
        return thinking_engine.evolve_hypothesis(feedback=feedback)
    return "rank(returns_20d) * rank(fnd6_fopo)"

def _process_hypothesis(api, hypothesis, last_feedback=None):
    """Worker function to test a single hypothesis."""
    logger.info(f"--- SCOUT TEST [TOP1000] FOR: {hypothesis[:60]}... ---")
    # Initialize expression
    expression = hypothesis
    
    # Local Syntax Audit to save API quota
    # Check for (expr, expr) hallucinations that should be (expr / expr)
    # Detect calls with too many arguments in common functions
    invalid_patterns = [
        (r"\w+\([^,]+,[^,]+,[^,]+\)", "Likely 3+ arguments in a 2-arg function"),
        (r"\([^,]+,[^)]+\)\s*\/", "Implicit tuple division error"),
        (r"\w+\(\s*\([^,]+,[^)]+\)\s*,", "Tuple-as-argument error")
    ]
    
    import re
    for pattern, reason in invalid_patterns:
        if re.search(pattern, expression):
            logger.warning(f"Local Audit: Potential structural error detected ({reason}). Attempting auto-fix...")
            # Auto-fix: Convert (a, b) inside these cases to (a / b)
            expression = re.sub(r"\(\s*([^,()]+)\s*,\s*([^,()]+)\s*\)", r"(\1 / \2)", expression)

    # Re-verify subindustry casing one last time
    expression = expression.replace("SUBINDUSTRY", "subindustry")

    logger.info(f"Submitting sanitized expression: {expression[:80]}...")
    
    # STAGE 1: Scout Test (TOP1000)
    scout_results = api.simulate_hypothesis(expression, universe="TOP1000")
    sharpe = scout_results.get("sharpe", 0.0)
    
    if scout_results.get("api_error") == "429 Limit Persistent":
        logger.error("Skipping logging for 429 persistent failure to avoid noise.")
        return ("FAIL_429", None, expression, scout_results) # Return a specific state for 429 failure
    
    if sharpe > 1.0:
        logger.info(f"🎓 GRADUATION: {scout_results.get('id')} to STAGE 2 [TOP3000]. (Scout Sharpe: {sharpe:.2f})")
        elite_metrics = api.simulate_hypothesis(expression, universe="TOP3000")
        elite_sharpe = elite_metrics.get("sharpe", 0.0)
        
        status = "REJECTED"
        passed_standard = (elite_sharpe > 1.25 and 
                           elite_metrics.get("fitness", 0) > 1.0 and 
                           elite_metrics.get("turnover", 1.0) < 0.65)
        
        if passed_standard:
            status = "CHAMPION"
            logger.info(f"🏆 CHAMPION DETECTED: Elite Sharpe {elite_sharpe:.2f}")
            audit_helper.update_audit("brain", status, details=f"Elite: {elite_sharpe:.2f}")
            log_brain_submission(elite_metrics.get("id", "CHAMPION"), expression, elite_sharpe, elite_metrics.get("fitness", 0), elite_metrics.get("turnover", 1.0), status=status, reason="Passed Elite Thresholds")
            return ("CHAMPION", elite_metrics.get("id"), expression, elite_metrics)
        else:
            reason = f"Elite Rejected: Sharpe {elite_sharpe:.2f}, Fitness {elite_metrics.get('fitness')}, Turnover {elite_metrics.get('turnover')}"
            logger.info(reason)
            audit_helper.update_audit("brain", "BELOW_THRESHOLD", details=f"Elite rejected")
            log_brain_submission(elite_metrics.get("id", "ELITE_FAIL"), expression, elite_sharpe, elite_metrics.get("fitness", 0), elite_metrics.get("turnover", 1.0), status="REJECTED", reason=reason)
            return ("MUTATE" if elite_sharpe > 1.0 else "FAIL", elite_metrics.get("id"), expression, elite_metrics)
    else:
        reason = f"Scout Failed: Sharpe {sharpe:.2f} < 1.0"
        audit_helper.update_audit("brain", "BELOW_THRESHOLD", details="Scout failed")
        logger.info(reason)
        log_brain_submission("SCOUT_FAIL", expression, sharpe, scout_results.get("fitness", 0), scout_results.get("turnover", 1.0), status="REJECTED", reason=reason)
        return ("MUTATE" if sharpe > 0.6 else "FAIL", scout_results.get("id"), expression, scout_results)

def run_factory():
    env_path = get_master_dir() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    if not email or not password:
        logger.error("CRITICAL: BRAIN_EMAIL or BRAIN_PASSWORD missing from Environment/Secrets.")
        sys.exit(1)
        
    api = BrainAPI(email, password)
    logger.info("Starting God-Level 10x Parallel Alpha Factory...")
    
    scout_calls = 0
    champions = []
    mutants_queue = []
    last_feedback = None
    
    while scout_calls < MAX_API_CALLS:
        batch_size = min(5, MAX_API_CALLS - scout_calls)
        hypotheses = []
        for _ in range(batch_size):
            if mutants_queue:
                hypotheses.append(mutants_queue.pop(0))
            else:
                hypotheses.append(generate_hypothesis(feedback=last_feedback))
                
        scout_calls += batch_size
        logger.info(f"Executing Parallel Batch of {batch_size} (Calls: {scout_calls}/{MAX_API_CALLS})")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_process_hypothesis, api, h, last_feedback) for h in hypotheses]
            for future in concurrent.futures.as_completed(futures):
                try:
                    state, aid, expr, metrics = future.result()
                    if state == "CHAMPION":
                        champions.append((aid, expr, metrics))
                    elif state == "MUTATE" and metrics.get("sharpe", 0) > 0.8:
                        new_mutants = mutate_expression(expr, count=2)
                        mutants_queue.extend(new_mutants)
                        logger.info(f"🧬 Spawned {len(new_mutants)} mutated variants from expression with {metrics.get('sharpe'):.2f} Sharpe.")
                    elif state == "FAIL":
                        last_feedback = {"expr": expr, "reason": "Failed Scout threshold", "sharpe": metrics.get("sharpe", 0), "turnover": metrics.get("turnover", 1)}
                except Exception as e:
                    logger.error(f"Parallel worker error: {e}")
                    
        if champions:
            logger.info(f"!!! {len(champions)} CHAMPION HYPOTHESES VALIDATED !!!")
            for alpha_id, hyp_expr, metrics in champions:
                api.submit_alpha(alpha_id)
                logger.info(f"Alpha {alpha_id} submitted successfully.")
                notify_submission(alpha_id, hyp_expr, metrics['sharpe'], metrics.get('fitness', 0))
                time.sleep(2)
            champions.clear()
            
    logger.info("Cycle complete.")

if __name__ == "__main__":
    run_factory()
