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
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [BRAIN_FACTORY] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- STEP 3: PRE-FLIGHT GUARDRAILS (RCA-DRIVEN) ---
MAX_API_CALLS = 15           # Economic Governor to prevent account throttling
CHAMPION_SHARPE = 1.50
CHAMPION_FITNESS = 1.00
MAX_TURNOVER = 0.70

# --- STEP 1 & 4: HYPOTHESIS-DRIVEN ORTHOGONAL FACTORS ---
# Value/Fundamental (Is it cheap?)
VALUE_FACTORS = [
    "operating_income / cap",
    "ebit / cap",
    "retained_earnings / total_assets",
    "sales / cap",
    "free_cash_flow / cap"
]

# Quality/Margin (Is it a good business?)
QUALITY_FACTORS = [
    "gross_margin",
    "return_on_equity",
    "return_on_assets",
    "operating_margin",
    "assets / liabilities"
]

# Momentum/Sentiment/Reversion (When do we enter?)
MOMENTUM_FACTORS = [
    "close / ts_mean(close, 20)",
    "ts_corr(close, volume, 20)",
    "returns",
    "ts_mean(returns, 10) / ts_std(returns, 10)",
    "ts_rank(volume, 10)"
]

# --- API INTEGRATION ---
class BrainAPI:
    def __init__(self, email, password):
        self.base_url = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        self._authenticate(email, password)

    def _authenticate(self, email, password):
        logger.info("Authenticating via Brain API...")
        response = self.session.post(
            f"{self.base_url}/authentication",
            auth=(email, password)
        )
        if response.status_code == 201:
            logger.info("Authentication Successful.")
        else:
            logger.error(f"Authentication Failed. Code: {response.status_code}")
            sys.exit(1)

    def simulate_hypothesis(self, expression: str) -> dict:
        """Runs the orthogonal hypothesis against Brain historical data."""
        payload = {
            "type": "REGULAR",
            "settings": {
                "instrumentType": "EQUITY",
                "region": "USA",
                "universe": "TOP3000",
                "delay": 1,
                "decay": 0, 
                "neutralization": "SUBINDUSTRY",
                "truncation": 0.08,
                "pasteurize": "ON",
                "target": "pv1a",
                "nanHandling": "ON",
                "language": "FASTEXPR",
                "visualization": False,
            },
            "regular": expression
        }

        # Submit simulation
        sim_response = self.session.post(f"{self.base_url}/simulations", json=payload)
        if sim_response.status_code != 201:
            logger.error("Simulation submission failed.")
            return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}

        sim_url = sim_response.headers.get("Location")
        
        # Poll for results (Wait for backtest)
        while True:
            status_response = self.session.get(sim_url)
            if status_response.status_code == 200:
                data = status_response.json()
                if data["status"] == "ERROR":
                    logger.warning("Alpha structural error.")
                    return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}
                elif data["status"] == "COMPLETE":
                    metrics = data["alpha"]
                    return {
                        "sharpe": metrics.get("sharpe", 0.0),
                        "fitness": metrics.get("fitness", 0.0),
                        "turnover": metrics.get("turnover", 1.0),
                        "id": metrics.get("id")
                    }
            time.sleep(4)

    def submit_alpha(self, alpha_id: str):
        response = self.session.post(f"{self.base_url}/alphas/{alpha_id}/submit")
        if response.status_code == 201:
            logger.info(f"Alpha {alpha_id} Successfully SUBMITTED to IQC 2026!")
        else:
            logger.error(f"Failed to submit: {response.text}")

def generate_hypothesis() -> str:
    """Combines Orthogonal Factors into a logical, neutralized strategy."""
    val = random.choice(VALUE_FACTORS)
    qual = random.choice(QUALITY_FACTORS)
    mom = random.choice(MOMENTUM_FACTORS)
    
    # Randomly weight the factors to find the best balance
    w_val = round(random.uniform(0.1, 0.5), 2)
    w_qual = round(random.uniform(0.1, 0.5), 2)
    w_mom = round(1.0 - w_val - w_qual, 2)
    
    # Build core composite score
    composite = f"{w_val} * rank({val}) + {w_qual} * rank({qual}) + {w_mom} * rank(-1 * {mom})"
    
    # Subindustry Neutralization to eliminate broad market betas
    expression = f"group_neutralize(rank(ts_decay_linear({composite}, 5)), subindustry)"
    return expression

def run_factory():
    # --- STEP 0: HYBRID AUTH (RULE-025) ---
    env_path = Path(r"C:\Users\admin\.antigravity\master\.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    
    if not email or not password:
        logger.error("[GUARDRAIL] Secrets missing. Aborting to prevent crash.")
        sys.exit(1)
        
    api = BrainAPI(email, password)
    logger.info("Starting Hypothesis-Driven Alpha Factory...")
    
    calls = 0
    best_alpha = None
    best_score = 0.0
    
    while calls < MAX_API_CALLS:
        calls += 1
        hypothesis = generate_hypothesis()
        logger.info(f"Testing Hypothesis {calls}/{MAX_API_CALLS}:\n{hypothesis}")
        
        metrics = api.simulate_hypothesis(hypothesis)
        score = metrics["sharpe"]
        
        logger.info(f"Result: Sharpe={score:.2f}, Fitness={metrics['fitness']:.2f}, Turnover={metrics['turnover']:.2f}")
        
        # VETO GUARDRAILS
        if score > CHAMPION_SHARPE and metrics["fitness"] > CHAMPION_FITNESS and metrics["turnover"] < MAX_TURNOVER:
            if score > best_score:
                best_score = score
                best_alpha = metrics["id"]
                
    if best_alpha:
        logger.info(f"!!! CHAMPION HYPOTHESIS VALIDATED !!! Sharpe: {best_score:.2f}")
        api.submit_alpha(best_alpha)
    else:
        logger.info("Cycle complete. No champion met the steep risk-adjusted requirements.")

if __name__ == "__main__":
    run_factory()
