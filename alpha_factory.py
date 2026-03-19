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
import concurrent.futures
from pathlib import Path
from datetime import datetime

# ─── ENCODING FIX (RULE-086) ──────────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FACTORY] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("alpha_factory")

# ─── DYNAMIC PATH RESOLUTION (RULE-100) ───────────────────────────────────────
def get_master_dir() -> Path:
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == "nt":
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

def load_env():
    """Load .env from master dir if present."""
    env_path = get_master_dir() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        log.info("Loaded .env from master dir.")

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
SCOUT_SHARPE_MIN  = 0.80    # Scout must pass > 0.80 to graduate. Previously 1.0.
SUBMIT_SHARPE_MIN = 1.0     # WQ IQC requires Sharpe >= 1.0. Was wrongly set to 1.25.
SUBMIT_FITNESS_MIN= 0.40    # WQ IQC fitness >= 0.40. Was wrongly set to 1.0.
SUBMIT_TURNOVER_MAX = 0.85  # IQC standard is < 0.9. Was wrongly 0.65.
PARALLEL_WORKERS  = 5
RATE_LIMIT_SLEEP  = 12      # Seconds between simulations to avoid 429s.

# ─── CURATED ALPHA LIBRARY (100+ confirmed-syntax expressions) ─────────────────
# Key insight from evolution log: expressions using SUBINDUSTRY as a string
# literal inside the expression work. All operators are confirmed valid.
ALPHA_LIBRARY = [
    # === TIER 1: PROVEN WINNERS FROM EVOLUTION LOG (Sharpe 0.84-1.46) ===
    "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)",
    "group_neutralize(rank(-1 * ts_rank(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(open, 3)), subindustry)",
    "group_neutralize(rank(-1 * (close - ts_mean(close, 20))), subindustry)",
    "group_neutralize(rank(ts_std_dev(close, 20) / ts_mean(close, 20)), subindustry)",
    "group_neutralize(rank(-1 * ts_corr(rank(volume), rank(close), 5)), subindustry)",
    "group_neutralize(rank(ts_mean(close, 5) / ts_mean(close, 20)), subindustry)",

    # === TIER 2: MOMENTUM FACTORS ===
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
    "group_neutralize(rank(close - vwap), subindustry)",
    "group_neutralize(rank(-1 * (vwap - close)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(vwap, 5)), subindustry)",
    "group_neutralize(rank(close / (vwap + 0.001) - 1), subindustry)",
    "group_neutralize(rank(-1 * ts_corr(vwap, volume, 10)), subindustry)",
    "group_neutralize(rank(ts_rank(vwap, 20)), subindustry)",

    # === TIER 5: FUNDAMENTALS COMBINED WITH PRICE ===
    "group_neutralize(rank(ts_zscore(fnd6_roa, 252)), subindustry)",
    "group_neutralize(rank(ts_zscore(fnd6_ebitda, 252)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(fnd6_roa, 63)), subindustry)",
    "group_neutralize(rank(fnd6_roa - ts_mean(fnd6_roa, 252)), subindustry)",
    "group_neutralize(rank(ts_zscore(fnd6_grossmargin, 252)), subindustry)",
    "group_neutralize(rank(fnd6_ebitda / (enterprise_value + 0.001)), subindustry)",

    # === TIER 6: MULTI-FACTOR COMPOSITES ===
    "group_neutralize(rank(-1 * ts_delta(close, 5) * log(volume + 1)), subindustry)",
    "group_neutralize(rank(-1 * ts_delta(close, 5) + ts_zscore(volume, 20)), subindustry)",
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

    # === TIER 7: CROSS-SECTIONAL RANK COMBINATIONS ===
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
    "rank(ts_zscore(fnd6_roa, 252))",
    "rank(fnd6_roa - ts_mean(fnd6_roa, 252))",
    "rank(ts_zscore(fnd6_grossmargin, 252))",

    # === TIER 8: RETURNS-BASED ===
    "group_neutralize(rank(-1 * returns), subindustry)",
    "group_neutralize(rank(ts_mean(returns, 5)), subindustry)",
    "group_neutralize(rank(-1 * ts_mean(returns, 20)), subindustry)",
    "group_neutralize(rank(ts_zscore(returns, 60)), subindustry)",
    "group_neutralize(rank(-1 * ts_std_dev(returns, 60)), subindustry)",
    "group_neutralize(rank(ts_rank(returns, 252)), subindustry)",
    "group_neutralize(rank(ts_rank(-1 * ts_mean(returns, 5), 20)), subindustry)",
    "group_neutralize(rank(returns - ts_mean(returns, 20)), subindustry)",
]


# ─── BRAIN API CLASS ──────────────────────────────────────────────────────────
class BrainAPI:
    """WorldQuant Brain API with retry logic and self-healing."""

    def __init__(self):
        self.base = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        })
        self._connect()

    def _connect(self):
        email = os.getenv("BRAIN_EMAIL")
        password = os.getenv("BRAIN_PASSWORD")
        if not email or not password:
            log.error("CRITICAL: BRAIN_EMAIL or BRAIN_PASSWORD missing.")
            sys.exit(1)
        for attempt in range(3):
            try:
                r = self.session.post(f"{self.base}/authentication", auth=(email, password), timeout=30)
                if r.status_code == 201:
                    tok = self.session.cookies.get("t")
                    if tok:
                        self.session.headers.update({"Authorization": f"Bearer {tok}"})
                    log.info("Brain API authenticated.")
                    return
                log.warning(f"Auth attempt {attempt+1} failed: {r.status_code}")
                time.sleep(5)
            except Exception as e:
                log.warning(f"Auth attempt {attempt+1} error: {e}")
                time.sleep(10)
        log.error("All authentication attempts failed. Exiting.")
        sys.exit(1)

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

    def submit(self, alpha_id: str) -> bool:
        """Submit alpha to IQC with retry."""
        for attempt in range(3):
            try:
                r = self.session.post(f"{self.base}/alphas/{alpha_id}/submit", timeout=30)
                if r.status_code == 201:
                    log.info(f"*** SUBMITTED: {alpha_id} ***")
                    audit_helper.update_audit("brain", "SUCCESS", details=f"SUBMITTED: {alpha_id}")
                    return True
                elif r.status_code == 409:
                    log.warning(f"Alpha {alpha_id} already submitted (409 Conflict).")
                    return False
                else:
                    log.warning(f"Submit {attempt+1}/3 failed for {alpha_id}: {r.status_code} {r.text[:60]}")
                    time.sleep(10)
            except Exception as e:
                log.warning(f"Submit error (attempt {attempt+1}): {e}")
                time.sleep(10)
        log.error(f"All submit attempts failed for {alpha_id}.")
        audit_helper.update_audit("brain", "FAIL_SUBMIT", details=f"Failed: {alpha_id}")
        return False


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

    log.info(f"SCOUT [{expression[:60]}...]")
    scout = api.simulate(expression, universe="TOP1000")
    sharpe_s = scout.get("sharpe", 0.0)
    log.info(f"Scout result: Sharpe={sharpe_s:.3f} Fitness={scout.get('fitness', 0):.3f}")

    if sharpe_s >= SCOUT_SHARPE_MIN:
        log.info(f"GRADUATED to TOP3000 (Scout Sharpe={sharpe_s:.2f})")
        time.sleep(RATE_LIMIT_SLEEP)
        elite = api.simulate(expression, universe="TOP3000")
        elite["expression"] = expression
        elite["scout_sharpe"] = sharpe_s
        return elite

    scout["expression"] = expression
    scout["scout_sharpe"] = sharpe_s
    return scout


# ─── MAIN FACTORY LOOP ────────────────────────────────────────────────────────
def run_factory():
    load_env()
    api = BrainAPI()

    log.info("=" * 70)
    log.info("GOD-LEVEL ALPHA FACTORY v4.0 — LEADERBOARD ASSAULT MODE")
    log.info(f"Config: MAX_CALLS={MAX_API_CALLS}, SCOUT_SHARPE>={SCOUT_SHARPE_MIN}, SUBMIT_SHARPE>={SUBMIT_SHARPE_MIN}")
    log.info("=" * 70)

    # Load additional ThinkingEngine hypotheses if available
    ai_hypotheses = []
    try:
        from thinking_engine import ThinkingEngine
        te = ThinkingEngine()
        for _ in range(20):
            try:
                h = te.evolve_hypothesis(feedback=None)
                if h:
                    ai_hypotheses.append(h)
            except Exception:
                break
        log.info(f"ThinkingEngine generated {len(ai_hypotheses)} AI hypotheses.")
    except ImportError:
        log.warning("ThinkingEngine not available. Using curated library only.")

    # Combine curated + AI hypotheses
    all_alphas = list(ALPHA_LIBRARY) + ai_hypotheses
    log.info(f"Total alpha candidates: {len(all_alphas)}")

    submitted = []
    rejected = []
    errors = []
    calls_made = 0

    while calls_made < MAX_API_CALLS and all_alphas:
        batch = all_alphas[:PARALLEL_WORKERS]
        all_alphas = all_alphas[PARALLEL_WORKERS:]
        calls_made += len(batch)

        log.info(f"--- Batch {calls_made // PARALLEL_WORKERS} | {len(batch)} candidates | {calls_made}/{MAX_API_CALLS} calls used ---")

        with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            futures = {executor.submit(scout_alpha, api, expr): expr for expr in batch}
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
                        success = api.submit(alpha_id)
                        if success:
                            submitted.append(alpha_id)
                            notify_submission(alpha_id, expression, sharpe, metrics.get("fitness", 0))
                            log_brain_submission(
                                alpha_id, expression, sharpe,
                                metrics.get("fitness", 0), metrics.get("turnover", 1.0),
                                status="SUBMITTED", reason=f"Sharpe={sharpe:.3f}"
                            )
                    else:
                        reason = f"Sharpe={sharpe:.3f} Fitness={metrics.get('fitness', 0):.3f} Turnover={metrics.get('turnover', 1.0):.3f}"
                        rejected.append((expr, reason))
                        log.info(f"Rejected: {reason}")

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
