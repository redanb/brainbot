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
    "fnd1_capx / total_assets"
]

# Quality/Margin (Is it a good business?)
QUALITY_FACTORS = [
    "rank(operating_income / sales)",
    "return_on_equity",
    "return_on_assets",
    "rank(operating_income / total_assets)",
    "total_assets / total_liabilities"
]

# Momentum/Sentiment/Reversion (When do we enter?)
MOMENTUM_FACTORS = [
    "close / ts_mean(close, 20)",
    "ts_corr(close, volume, 20)",
    "returns",
    "ts_mean(returns, 10) / ts_std(returns, 10)",
    "ts_rank(volume, 10)"
]

# Advanced Mathematical/Volatility (Orthogonal Edge)
ADVANCED_FACTORS = [
    "ts_corr(close, ts_step(volume, 1), 10)",
    "ts_rank(ts_delta(close, 5), 10)",
    "ts_std(returns, 20) / ts_mean(returns, 20)",
    "ts_delta(close, 20)",
    "ts_rank(returns, 20)"
]

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
        response = self.session.post(
            f"{self.base_url}/authentication",
            auth=(email, password)
        )
        if response.status_code == 201:
            logger.info("Authentication Successful.")
        else:
            logger.error(f"Authentication Failed. Code: {response.status_code}")
            logger.warning("Falling back to Browser-based login...")
            self._authenticate_browser()

    def _authenticate_browser(self):
        """
        Launches a browser for manual login and captures the session cookie.
        This follows the 'browser_login_resume' protocol.
        """
        logger.info("ACTION REQUIRED: Please log in via the browser pop-up.")
        # This is a marker for the AGENT to use the browser_subagent tool.
        # In actual execution, the agent (Antigravity) will handle this.
        print("\n[BROWSER_AUTH_REQUIRED] https://platform.worldquantbrain.com/authentication\n")
        
        # For the script to continue, it needs the 'WQB_SESSION_ID' or similar cookie.
        # We will assume the session is captured and provided via an environment variable 
        # or a temporary file by the agent after the user says 'done'.
        session_file = Path(r"C:\Users\admin\.antigravity\master\browser_sessions\wqb_session.json")
        
        # Wait for the agent/user to complete the login
        while not session_file.exists():
            time.sleep(5)
            
        try:
            cookies = json.loads(session_file.read_text())
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            logger.info("Session captured from browser. Continuing...")
            # Verify session
            resp = self.session.get(f"{self.base_url}/users/self")
            if resp.status_code != 200:
                logger.error("Captured session is invalid or expired.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load captured session: {e}")
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

        # Submit simulation
        sim_response = self.session.post(f"{self.base_url}/simulations", json=payload)
        if sim_response.status_code != 201:
            logger.error(f"Simulation submission failed. Status: {sim_response.status_code}, Response: {sim_response.text}")
            return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}

        sim_url = sim_response.headers.get("Location")
        
        # Poll for results (Wait for backtest)
        while True:
            status_response = self.session.get(sim_url)
            if status_response.status_code == 200:
                data = status_response.json()
                # Check for progress payload
                if "progress" in data and "status" not in data:
                    logger.info(f"Simulation Progress: {data['progress']*100:.1f}%")
                    time.sleep(5)
                    continue
                    
                if data.get("status") == "ERROR":
                    logger.warning(f"Alpha structural error: {data.get('message')}")
                    return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}
                elif data.get("status") == "COMPLETE":
                    alpha_id = data.get("alpha")
                    if not alpha_id:
                        logger.error("Simulation COMPLETE but no alpha ID found.")
                        return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}
                        
                    # Step 2: Fetch detailed metrics from /alphas/{alpha_id}
                    metrics_resp = self.session.get(f"{self.base_url}/alphas/{alpha_id}")
                    if metrics_resp.status_code == 200:
                        alpha_data = metrics_resp.json()
                        ims = alpha_data.get("is", {})
                        return {
                            "sharpe": ims.get("sharpe", 0.0),
                            "fitness": ims.get("fitness", 0.0),
                            "turnover": ims.get("turnover", 1.0),
                            "id": alpha_id
                        }
                    else:
                        logger.error(f"Failed to fetch alpha metrics for {alpha_id}. Status: {metrics_resp.status_code}")
                        return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}
            time.sleep(5)

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
    adv = random.choice(ADVANCED_FACTORS)
    
    # Randomly weight the factors to find the best balance
    w_val = round(random.uniform(0.1, 0.4), 2)
    w_qual = round(random.uniform(0.1, 0.4), 2)
    w_mom = round(random.uniform(0.1, 0.4), 2)
    w_adv = round(1.0 - w_val - w_qual - w_mom, 2)
    
    # Dynamic decay tuning (The Edge)
    decay = random.choice([3, 5, 8, 10, 15])
    
    # Research-Driven Hypotheses (User Advice)
    # FFO / Long-term Debt: Cash flow visibility vs obligations
    ffo_debt = "fnd6_fopo / debt_lt"
    
    # Adding time-series delta to capture improving financial health
    ffo_debt_delta = f"ts_delta({ffo_debt}, 252)" # 1-year improvement
    
    # Selection pool including the new "God-Level" metrics
    metrics = [ffo_debt, ffo_debt_delta, val, qual, mom, adv]
    
    # Weights
    w1, w2, w3 = 0.4, 0.4, 0.2
    m1, m2, m3 = random.sample(metrics, 3)
    
    expression = f"{w1} * rank({m1}) + {w2} * rank({m2}) + {w3} * rank({m3})"
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
    
    # If credentials are missing, we don't abort anymore; we trigger browser-based auth
    if not email or not password:
        logger.info("Credentials missing in .env. Initiating pop-up login...")
        api = BrainAPI()
    else:
        api = BrainAPI(email, password)
        
    logger.info("Starting Multi-Submission Alpha Factory...")
    
    calls = 0
    champions = []
    
    while calls < MAX_API_CALLS:
        calls += 1
        hypothesis = generate_hypothesis()
        logger.info(f"Testing Hypothesis {calls}/{MAX_API_CALLS}:\n{hypothesis}")
        
        metrics = api.simulate_hypothesis(hypothesis)
        score = metrics["sharpe"]
        
        logger.info(f"Result: Sharpe={score:.2f}, Fitness={metrics['fitness']:.2f}, Turnover={metrics['turnover']:.2f}")
        
        # VETO GUARDRAILS (ALL CHAMPIONS MODE)
        if score > CHAMPION_SHARPE and metrics["fitness"] > CHAMPION_FITNESS and metrics["turnover"] < MAX_TURNOVER:
            logger.info(f"CHAMPION DETECTED: Sharpe {score:.2f}")
            champions.append(metrics["id"])
                
    if champions:
        logger.info(f"!!! {len(champions)} CHAMPION HYPOTHESES VALIDATED !!!")
        for alpha_id in champions:
            api.submit_alpha(alpha_id)
            time.sleep(3) # Respect submission rate limits
    else:
        logger.info("Cycle complete. No champion met the steep risk-adjusted requirements.")

if __name__ == "__main__":
    run_factory()
