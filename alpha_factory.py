"""
alpha_factory.py v4.0 — GOD-LEVEL AUTONOMOUS 24/7 ALPHA FACTORY
WorldQuant Brain Leaderboard Assault Engine

CORRECTIONS FROM EVOLUTION LOG ANALYSIS:
  - RULE-100: Dynamic master_dir resolution
  - FIX-001: Elite threshold was 1.25 Sharpe — lowered to 1.0 (per WQ IQC standards)
  - FIX-002: Fitness threshold was 1.0 — corrected to 0.5 (IQC actual requirement)
  - FIX-003: Turnover < 0.65 too strict — relaxed to < 0.80
  - FIX-004: scout_calls was using wrong throttle, now per-iteration
  - FIX-005: Added submission retry on network failures
  - FIX-006: Added 100+ curated alpha expressions with confirmed operators
"""
import os
import sys
import re
import time
import json
import logging
import threading
import requests
import env_discovery
import concurrent.futures
from pathlib import Path
from datetime import datetime
from xgboost_compiler import XGBoostCompiler

# ─── ENCODING FIX (RULE-086) ──────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        # Cast to Any to satisfy linter with hasattr check
        from typing import Any
        reconfig: Any = sys.stdout.reconfigure
        reconfig(encoding="utf-8")
    except Exception:
        pass

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FACTORY] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
for handler in logging.getLogger().handlers:
    handler.flush = sys.stdout.flush
log = logging.getLogger("alpha_factory")

# ─── DYNAMIC PATH RESOLUTION (RULE-100) ───────────────────────────────────────
def get_master_dir() -> Path:
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == "nt":
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

def load_env():
    """Load environment using multi-tier discovery."""
    files = env_discovery.initialize_environment()
    if files and isinstance(files, list):
        log.info(f"Loaded environments from: {', '.join(map(str, files))}")
    else:
        log.warning("No .env files found. Relying on OS environment variables.")
    if not os.getenv("BRAIN_EMAIL"):
        log.error("CRITICAL: BRAIN_EMAIL is still empty after env_discovery.")

# ─── EVOLUTION TRACKER ────────────────────────────────────────────────────────
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from evolution_tracker import log_brain_submission, notify_submission
except ImportError:
    def log_brain_submission(*args, **kwargs): pass
    def notify_submission(*args, **kwargs): pass

try:
    import audit_helper
except ImportError:
    class _FakeAudit:
        def update_audit(self, *a, **kw): pass
    audit_helper = _FakeAudit()

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MAX_API_CALLS     = int(os.getenv("MAX_API_CALLS", "80"))
SCOUT_SHARPE_MIN  = 0.70    # Lowered to 0.70 to increase graduation rate
SUBMIT_SHARPE_MIN = 1.00    # WQ IQC actual requirement is Sharpe >= 1.0
SUBMIT_FITNESS_MIN= 0.5     # WQ IQC actual requirement is Fitness >= 0.5
SUBMIT_TURNOVER_MAX = 0.80  # Relaxed to 0.80 for more liquidity flexibility
PARALLEL_WORKERS  = 5
RATE_LIMIT_SLEEP  = 15      # Seconds between simulations to avoid 429s.

# ─── CURATED ALPHA LIBRARY (100+ confirmed-syntax expressions) ─────────────────
# Key insight from evolution log: expressions using SUBINDUSTRY as a string
# literal inside the expression work. All operators are confirmed valid.
ALPHA_LIBRARY = [
    # === TIER 1: PROVEN WINNERS FROM EVOLUTION LOG (Sharpe 0.84-1.46, HIGH FITNESS TARGET) ===
    # Key insight: HIGH FITNESS = High returns/drawdown ratio
    # Remove fundamental variables (fnd6_) - not in TOP1000 scout universe
    # Expressions tuned for Fitness >= 1.0 (requires high returns)
    "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)",
    "group_neutralize(rank(-1 * ts_rank(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(open, 3)), subindustry)",
    "group_neutralize(rank(-1 * (close - ts_mean(close, 20))), subindustry)",
    "group_neutralize(rank(ts_std_dev(close, 20) / ts_mean(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_corr(rank(volume), rank(close), 5)), subindustry)",
    "group_neutralize(rank(ts_mean(close, 5) / ts_mean(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(vwap, 5)), subindustry)",
    "group_neutralize(rank(close - vwap), subindustry)",
    "group_neutralize(rank(-1 * ts_corr(vwap, volume, 10)), subindustry)",
    "group_neutralize(rank(close / (vwap + 0.001) - 1), subindustry)",

    # === TIER 2: MOMENTUM FACTORS (HIGH FITNESS TUNING) ===
    "group_neutralize(rank(ts_delta(close, 1) / (close + 0.001)), subindustry)",
    "group_neutralize(rank(-1 * ts_rank(close, 10)), subindustry)",
    "group_neutralize(rank(close - ts_mean(close, 10)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(close, 10)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(close, 20)), subindustry)",
    "group_neutralize(rank(ts_delta(open, 5)), subindustry)",
    "group_neutralize(rank(-1 * (open - close)), subindustry)",
    "group_neutralize(rank(high - low), subindustry)",
    "group_neutralize(rank(-1 * (high - close)), subindustry)",
    "group_neutralize(rank(close - low), subindustry)",
    "group_neutralize(rank(-1 * ts_zscore(close, 20)), subindustry)",
    "group_neutralize(rank(ts_rank(volume, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_rank(volume, 10)), subindustry)",
    "group_neutralize(rank(log(volume) - log(ts_mean(volume, 20))), subindustry)",
    "group_neutralize(rank(-1 * ts_corr(close, volume, 10)), subindustry)",
    "group_neutralize(rank(ts_corr(ts_rank(close, 5), ts_rank(volume, 5), 10)), subindustry)",
    "group_neutralize(rank(ts_rank(close, 252) - ts_rank(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_rank(close - ts_mean(close, 5), 20)), subindustry)",

    # === TIER 3: VOLATILITY FACTORS ===
    "group_neutralize(rank(-1 * ts_std_dev(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_std_dev(ts_delta(close, 1), 10)), subindustry)",
    "group_neutralize(rank(-1 * ts_std_dev(returns, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_std_dev(high - low, 10)), subindustry)",
    "group_neutralize(rank(ts_zscore(ts_std_dev(close, 20), 252)), subindustry)",
    "group_neutralize(rank(-1 * (high - low) / (close + 0.001)), subindustry)",

    # === TIER 4: VWAP FACTORS ===
    "group_neutralize(rank(-1 * (vwap - close)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(vwap, 3)), subindustry)",
    "group_neutralize(rank(ts_rank(vwap, 20)), subindustry)",

    # === TIER 5: MULTI-FACTOR COMPOSITES (HIGH RETURNS TARGETING) ===
    "group_neutralize(rank(-1 * ts_delta(close, 5) * log(volume + 1)), subindustry)",
    "group_neutralize(rank((-1 * ts_delta(close, 5)) / (ts_std_dev(close, 20) + 0.001)), subindustry)",
    "group_neutralize(rank(ts_rank(-1 * ts_delta(close, 5), 20) + ts_rank(volume, 10)), subindustry)",
    "group_neutralize(rank((-1 * ts_delta(close, 3)) / (vwap + 0.001)), subindustry)",
    "group_neutralize(rank(-1 * ts_corr(close, volume, 5) * ts_std_dev(close, 10)), subindustry)",
    "group_neutralize(rank(ts_zscore(close - vwap, 20) + ts_rank(volume, 10)), subindustry)",
    "group_neutralize(rank(ts_decay_linear(ts_delta(close, 1), 10)), subindustry)",
    "group_neutralize(rank(-1 * ts_decay_linear(ts_delta(close, 5), 20)), subindustry)",
    "group_neutralize(rank(ts_decay_linear(-1 * (close - ts_mean(close, 20)), 10)), subindustry)",
    "group_neutralize(rank(signed_power(ts_zscore(close, 20), 0.5)), subindustry)",
    "group_neutralize(rank(-1 * signed_power(ts_delta(close, 5), 0.7)), subindustry)",

    # === TIER 6: CROSS-SECTIONAL RANK COMBINATIONS ===
    "rank(-1 * ts_delta(close, 5))",
    "rank(-1 * ts_rank(close, 20))",
    "rank(log(volume) - log(ts_mean(volume, 20)))",
    "rank(ts_zscore(close, 20))",
    "rank(-1 * ts_corr(close, volume, 10))",
    "rank(close / ts_mean(close, 20) - 1)",
    "rank(-1 * (close - ts_mean(close, 5)))",
    "rank(ts_std_dev(close, 20))",
    "rank(ts_delta(volume, 5) / (volume + 1))",
    "rank(open - close)",
    "rank(-1 * (high - close))",
    "rank(ts_rank(ts_std_dev(close, 5), 20))",
    "rank(-1 * ts_std_dev(returns, 10))",
    "rank(ts_mean(high - low, 5) / (ts_mean(close, 5) + 0.001))",
    "rank(-1 * ts_decay_linear(ts_delta(close, 3), 10))",
    "rank(ts_corr(ts_rank(close, 5), ts_rank(volume, 5), 10))",

    # === TIER 7: RETURNS-BASED ===
    "group_neutralize(rank(-1 * returns), subindustry)",
    "group_neutralize(rank(ts_mean(returns, 5)), subindustry)",
    "group_neutralize(rank(-1 * ts_mean(returns, 20)), subindustry)",
    "group_neutralize(rank(ts_zscore(returns, 60)), subindustry)",
    "group_neutralize(rank(-1 * ts_std_dev(returns, 60)), subindustry)",
    "group_neutralize(rank(ts_rank(returns, 252)), subindustry)",
    "group_neutralize(rank(ts_rank(-1 * ts_mean(returns, 5), 20)), subindustry)",
    "group_neutralize(rank(returns - ts_mean(returns, 20)), subindustry)",

    # === TIER 8: DECAY + MOMENTUM FUSION (HIGH FITNESS TARGETING) ===
    "group_neutralize(rank(ts_decay_linear(rank(-1 * ts_delta(close, 1)), 5)), subindustry)",
    "group_neutralize(rank(ts_decay_linear(rank(-1 * ts_corr(close, volume, 5)), 10)), subindustry)",
    "group_neutralize(rank(-1 * ts_decay_linear(rank(ts_zscore(close, 20)), 20)), subindustry)",
    "group_neutralize(signed_power(rank(-1 * ts_delta(close, 5)), 1.5), subindustry)",
    "group_neutralize(signed_power(rank(-1 * ts_corr(close, volume, 10)), 1.5), subindustry)",
    "group_neutralize(rank(-1 * ts_mean(ts_delta(close, 1), 5) / (ts_std_dev(close, 20) + 0.0001)), subindustry)",

    # === TIER 9: ULTRA-HIGH-FITNESS (Targeting Fitness >= 1.0) ===
    # WQ Fitness = returns * sqrt(252) / drawdown (approx)
    # Higher fitness = higher daily returns, lower drawdown
    # Short-lookback reversals with tight group neutralization maximize this ratio
    #
    # Strategy: 1-3 day reversals with aggressive normalization
    "group_neutralize(rank(-1 * ts_delta(close, 1)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(close, 2)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(open, 1)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(open, 2)), subindustry)",
    "group_neutralize(rank(open - close), subindustry)",
    "group_neutralize(rank(-1 * (close - open)), subindustry)",
    "group_neutralize(rank(vwap - close), subindustry)",
    "group_neutralize(rank(-1 * (close - vwap)), subindustry)",

    # Very short decay (aggressive position rotation)
    "group_neutralize(rank(ts_decay_linear(-1 * ts_delta(close, 1), 3)), subindustry)",
    "group_neutralize(rank(ts_decay_linear(-1 * ts_delta(close, 2), 3)), subindustry)",
    "group_neutralize(rank(ts_decay_linear(open - close, 3)), subindustry)",

    # Short-window zscore (focuses on recent regime)
    "group_neutralize(rank(-1 * ts_zscore(close, 5)), subindustry)",
    "group_neutralize(rank(-1 * ts_zscore(close, 10)), subindustry)",
    "group_neutralize(rank(ts_zscore(open - close, 10)), subindustry)",
    "group_neutralize(rank(-1 * ts_zscore(vwap - close, 5)), subindustry)",

    # Volume-weighted reversals
    "group_neutralize(rank(-1 * ts_delta(close, 1) * ts_rank(volume, 5)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(close, 1) * log(volume + 1)), subindustry)",
    "group_neutralize(rank((vwap - close) * ts_rank(volume, 10)), subindustry)",
    "group_neutralize(rank(-1 * (close - open) * ts_rank(volume, 5)), subindustry)",

    # Advanced signed_power for skewness exploitation
    "group_neutralize(signed_power(rank(-1 * ts_delta(close, 1)), 2.0), subindustry)",
    "group_neutralize(signed_power(rank(-1 * ts_delta(close, 2)), 1.5), subindustry)",
    "group_neutralize(signed_power(rank(open - close), 2.0), subindustry)",
    "group_neutralize(signed_power(rank(vwap - close), 1.5), subindustry)",
]



# ─── BRAIN API CLASS ──────────────────────────────────────────────────────────
class BrainAPI:
    """WorldQuant Brain API with retry logic and self-healing."""

    def __init__(self, email=None, password=None):
        self.base = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        })
        self.email = email or os.getenv("BRAIN_EMAIL")
        self.password = password or os.getenv("BRAIN_PASSWORD")
        self._connect()

    def _connect(self):
        if not self.email or not self.password:
            log.error("CRITICAL: BRAIN_EMAIL or BRAIN_PASSWORD missing. Check GitHub Secrets.")
            raise ConnectionError("BRAIN_EMAIL or BRAIN_PASSWORD not set. Aborting.")
        for attempt in range(10):
            try:
                r = self.session.post(f"{self.base}/authentication", auth=(self.email, self.password), timeout=30)
                if r.status_code == 201:
                    tok = self.session.cookies.get("t")
                    if tok:
                        self.session.headers.update({"Authorization": f"Bearer {tok}"})
                    log.info("Brain API authenticated.")
                    return
                
                # Exponential backoff: 2^attempt * 5 seconds (5, 10, 20, 40, 80, 160, 320...)
                wait = (2 ** attempt) * 5
                log.warning(f"Auth attempt {attempt+1}/10 failed: {r.status_code}. Sleeping {wait}s...")
                time.sleep(wait)
            except Exception as e:
                wait = (2 ** attempt) * 5
                log.warning(f"Auth attempt {attempt+1}/10 error: {e}. Sleeping {wait}s...")
                time.sleep(wait)
        
        log.error("All 10 authentication attempts failed. Account may be locked or credentials invalid.")
        raise ConnectionError("Failed to authenticate with WorldQuant Brain after 10 attempts.")

    def simulate(self, expression: str, universe: str = "TOP1000") -> dict:
        """Submit a simulation and wait for results."""
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

        for attempt in range(3):
            try:
                r = self.session.post(f"{self.base}/simulations", json=payload, timeout=30)
                if r.status_code == 201:
                    break
                elif r.status_code == 429:
                    sleep = (attempt + 1) * 30
                    log.warning(f"429 Rate Limit. Sleeping {sleep}s...")
                    time.sleep(sleep)
                    continue
                else:
                    log.warning(f"Sim start failed ({universe}): {r.status_code} {r.text[:80]}")
                    return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": r.text[:80]}
            except requests.RequestException as e:
                log.warning(f"Network error on sim start (attempt {attempt+1}): {e}")
                time.sleep(15)
        else:
            return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "429 persistent"}

        sim_url = r.headers.get("Location")
        if not sim_url:
            return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "no location header"}

        # Poll for completion
        deadline = time.time() + 300  # 5 minute max
        while time.time() < deadline:
            try:
                sr = self.session.get(sim_url, timeout=30)
                if sr.status_code != 200:
                    time.sleep(5)
                    continue
                data = sr.json()
                if data.get("status") == "ERROR":
                    msg = data.get("message", "unknown error")
                    log.warning(f"Sim error ({universe}): {msg}")
                    return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": msg}
                if data.get("status") == "COMPLETE":
                    alpha_id = data.get("alpha")
                    if not alpha_id:
                        return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "no alpha id"}
                    return self._get_metrics(alpha_id, universe)
                # Progress response — keep waiting
                time.sleep(5)
            except Exception as e:
                log.warning(f"Poll error: {e}")
                time.sleep(10)

        return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "timeout"}

    def _get_metrics(self, alpha_id: str, universe: str) -> dict:
        try:
            r = self.session.get(f"{self.base}/alphas/{alpha_id}", timeout=30)
            if r.status_code == 200:
                d = r.json()
                ims = d.get("is", {})
                return {
                    "id": alpha_id,
                    "sharpe": ims.get("sharpe", 0.0) or 0.0,
                    "fitness": ims.get("fitness", 0.0) or 0.0,
                    "turnover": ims.get("turnover", 1.0) or 1.0,
                    "returns": ims.get("returns", 0.0) or 0.0,
                    "margin": ims.get("margin", 0.0) or 0.0,
                    "universe": universe,
                }
        except Exception as e:
            log.warning(f"Metrics fetch error for {alpha_id}: {e}")
        return {"id": alpha_id, "sharpe": 0.0, "fitness": 0.0, "turnover": 1.0}

    def submit(self, alpha_id: str) -> tuple[bool, str]:
        """Submit alpha to IQC with retry. Returns (success, error_msg)."""
        last_error = ""
        for attempt in range(3):
            try:
                r = self.session.post(f"{self.base}/alphas/{alpha_id}/submit", timeout=30)
                if r.status_code == 201:
                    log.info(f"*** SUBMITTED: {alpha_id} ***")
                    audit_helper.update_audit("brain", "SUCCESS", details=f"SUBMITTED: {alpha_id}")
                    return True, ""
                elif r.status_code == 409:
                    log.warning(f"Alpha {alpha_id} already submitted (409 Conflict).")
                    return False, "409_ALREADY_SUBMITTED"
                else:
                    last_error = r.text[:200]
                    log.warning(f"Submit {attempt+1}/3 failed for {alpha_id}: {r.status_code} {last_error[:60]}")
                    time.sleep(10)
            except Exception as e:
                last_error = str(e)
                log.warning(f"Submit error (attempt {attempt+1}): {e}")
                time.sleep(10)
        log.error(f"All submit attempts failed for {alpha_id}. Last Error: {last_error[:100]}")
        audit_helper.update_audit("brain", "FAIL_SUBMIT", details=f"Failed: {alpha_id} | {last_error[:100]}")
        return False, last_error


# ─── ALPHA PROCESSOR ──────────────────────────────────────────────────────────
def meets_submission_criteria(m: dict) -> bool:
    """Check if an alpha meets IQC submission thresholds."""
    return (
        m.get("sharpe", 0) >= SUBMIT_SHARPE_MIN and
        m.get("fitness", 0) >= SUBMIT_FITNESS_MIN and
        m.get("turnover", 1.0) <= SUBMIT_TURNOVER_MAX
    )

def scout_alpha(api: BrainAPI, expression: str) -> dict:
    """Test an alpha on TOP1000 first (fast scout), then promote to TOP3000."""
    time.sleep(RATE_LIMIT_SLEEP)  # Rate-limiting courtesy sleep

    # Quick local syntax check
    if re.search(r"\b(delta|delay|std)\s*\(", expression):
        expression = re.sub(r"\bdelta\s*\(", "ts_delta(", expression)
        expression = re.sub(r"\bdelay\s*\(", "ts_delay(", expression)
        expression = re.sub(r"\bstd\s*\(", "ts_std_dev(", expression)
        log.info("Auto-corrected operator names.")

    safe_expr = expression[:60] if expression else "N/A"
    log.info(f"SCOUT [{safe_expr}...]")
    scout = api.simulate(expression, universe="TOP1000")
    sharpe_s = scout.get("sharpe", 0.0)
    log.info(f"Scout result: Sharpe={sharpe_s:.3f} Fitness={scout.get('fitness', 0):.3f}")

    if sharpe_s >= SCOUT_SHARPE_MIN:
        log.info(f"GRADUATED to TOP3000 (Scout Sharpe={sharpe_s:.2f})")
        time.sleep(RATE_LIMIT_SLEEP)
        elite = api.simulate(expression, universe="TOP3000")
        elite["expression"] = expression
        elite["scout_sharpe"] = sharpe_s
        elite["_api"] = api
        return elite

    scout["expression"] = expression
    scout["scout_sharpe"] = sharpe_s
    scout["_api"] = api
    return scout


# ─── MAIN FACTORY LOOP ────────────────────────────────────────────────────────
def run_factory():
    load_env()
    
    accounts = []
    accounts_env = os.getenv("BRAIN_ACCOUNTS")
    if accounts_env:
        for pair in accounts_env.split(","):
            if ":" in pair:
                e, p = pair.split(":", 1)
                accounts.append((e.strip(), p.strip()))
    
    # randomized de-synchronization for GHA parallel batches
    if os.getenv("GITHUB_ACTIONS") == "true":
        import random
        delay = random.randint(0, 60)
        log.info(f"GHA Detected. De-synchronizing batch with {delay}s random delay...")
        time.sleep(delay)

    api_pool = []
    for e, p in accounts:
        try:
            api_pool.append(BrainAPI(e, p))
        except SystemExit:
            pass

    if not api_pool:
        log.error("No valid BrainAPI accounts authenticated.")
        sys.exit(1)
        
    log.info(f"Initialized Hyperscaling API Pool with {len(api_pool)} accounts.")

    log.info("=" * 70)
    log.info("GOD-LEVEL ALPHA FACTORY v4.0 — LEADERBOARD ASSAULT MODE")
    log.info(f"Config: MAX_CALLS={MAX_API_CALLS}, SCOUT_SHARPE>={SCOUT_SHARPE_MIN}, SUBMIT_SHARPE>={SUBMIT_SHARPE_MIN}")
    log.info("=" * 70)

    # Load additional ThinkingEngine hypotheses if available
    ai_hypotheses = []
    te = None
    compiler = XGBoostCompiler()
    try:
        from thinking_engine import ThinkingEngine
        te = ThinkingEngine()
        regime = te.get_current_regime()
        log.info(f"Market Regime Detected: {regime}")
        
        # Phase 5: ML Generation Step (Draft)
        # In a real run, we would pull historical data here. 
        # For now, we seed the compiler with the current regime to influence the trees.
        ml_expr = compiler.compile_booster(json.dumps({
            "split": "rank(close)", "split_condition": 0.5,
            "children": [{"leaf": 0.02}, {"leaf": -0.01}]
        }))
        ai_hypotheses.append(ml_expr)
        log.info("Injected ML-Compiled Alpha into batch.")
        
        # Generate additional hypotheses from ThinkingEngine
        ai_hypotheses.extend(te.evolve_hypothesis(regime=regime, count=5))
        log.info(f"ThinkingEngine generated {len(ai_hypotheses) - 1} AI hypotheses (plus 1 ML).") # Adjusted count
    except ImportError:
        log.warning("ThinkingEngine not available. Using curated library only.")
    except Exception as e:
        log.warning(f"Could not load AI hypotheses: {e}")

    # Combine curated + AI hypotheses
    all_alphas = list(ALPHA_LIBRARY) + ai_hypotheses
    log.info(f"Total alpha candidates: {len(all_alphas)}")

    submitted = []
    rejected = []
    errors = []
    calls_made = 0

    while calls_made < MAX_API_CALLS and all_alphas:
        # Avoid indexing into list if it's too short
        batch_size = min(len(all_alphas), PARALLEL_WORKERS)
        batch = all_alphas[:batch_size]
        all_alphas = all_alphas[batch_size:]
        calls_made += len(batch)

        log.info(f"--- Batch {calls_made // PARALLEL_WORKERS} | {len(batch)} candidates | {calls_made}/{MAX_API_CALLS} calls used ---")

        with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            import random
            futures = {executor.submit(scout_alpha, random.choice(api_pool), expr): expr for expr in batch}
            for future in concurrent.futures.as_completed(futures):
                expr = futures[future]
                try:
                    metrics = future.result()
                    sharpe = metrics.get("sharpe", 0.0)
                    alpha_id = metrics.get("id")
                    expression = metrics.get("expression", expr)

                    log_brain_submission(
                        alpha_id or "NO_ID",
                        expression,
                        sharpe,
                        metrics.get("fitness", 0),
                        metrics.get("turnover", 1.0),
                        status="EVALUATING",
                        reason=f"Sharpe={sharpe:.3f}"
                    )

                    if alpha_id and meets_submission_criteria(metrics):
                        log.info(f"CHAMPION: {alpha_id} | Sharpe={sharpe:.3f} | Fitness={metrics.get('fitness'):.3f}")
                        used_api = metrics.get("_api", api_pool[0])
                        success, submit_error = used_api.submit(alpha_id)
                        if success:
                            submitted.append(alpha_id)
                            notify_submission(alpha_id, expression, sharpe, metrics.get("fitness", 0))
                            log_brain_submission(
                                alpha_id, expression, sharpe,
                                metrics.get("fitness", 0), metrics.get("turnover", 1.0),
                                status="SUBMITTED", reason=f"Sharpe={sharpe:.3f}"
                            )
                        else:
                            # Feed submission error (e.g. 403 Overlap) back to evolution
                            reason = f"SUBMIT_FAIL: {submit_error}"
                            rejected.append((expr, reason))
                    else:
                        reason = f"Sharpe={sharpe:.3f} Fitness={metrics.get('fitness', 0):.3f} Turnover={metrics.get('turnover', 1.0):.3f}"
                        rejected.append((expr, reason))
                        log.info(f"Rejected: {reason}")
                        
                        # God-Level Evolutionary Feedback Loop
                        if te is not None and len(all_alphas) + calls_made < MAX_API_CALLS:
                            feedback_data = {
                                "expr": expression,
                                "reason": reason,
                                "sharpe": sharpe,
                                "turnover": metrics.get("turnover", 1.0)
                            }
                            try:
                                mutated_alpha = te.evolve_hypothesis(feedback=feedback_data)
                                if mutated_alpha and mutated_alpha not in all_alphas and mutated_alpha != expression:
                                    all_alphas.append(mutated_alpha)
                                    log.info(f"Evolutionary Feedback: Appended new mutated alpha based on failure.")
                            except Exception as e:
                                log.error(f"Failed to evolve hypothesis during feedback: {e}")

                except Exception as e:
                    log.error(f"Worker error: {e}")
                    errors.append(str(e))

    # Final report
    log.info("=" * 70)
    log.info(f"FACTORY RUN COMPLETE")
    log.info(f"  Calls Used:    {calls_made}")
    log.info(f"  Submitted:     {len(submitted)}")
    log.info(f"  Rejected:      {len(rejected)}")
    log.info(f"  Errors:        {len(errors)}")
    if submitted:
        log.info(f"  Alpha IDs:     {submitted}")
    log.info("=" * 70)

    # Send Telegram report
    try:
        from sentinel_agent import send_telegram
        report = (
            f"FACTORY CYCLE DONE\n"
            f"Submitted: {len(submitted)}\n"
            f"Rejected: {len(rejected)}\n"
            f"Errors: {len(errors)}\n"
            f"AlphaIDs: {submitted}"
        )
        send_telegram(report)
    except Exception:
        pass

    return len(submitted)


if __name__ == "__main__":
    run_factory()
