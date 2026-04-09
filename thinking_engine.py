"""
thinking_engine.py
Self-Improving Alpha Thinking Engine (SATE)
Eliminates stochastic (random) sampling in favor of LLM-driven hypothesis evolution.
Follows WorldQuant Leaderboard strategies (Hybrid LLM+GP).
"""
import os
import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

MASTER_DIR = get_master_dir()
BASE_DIR = Path(__file__).resolve().parent
EVOLUTION_LOG = MASTER_DIR / "evolution_log.json"
PCDRAFT_DIR = BASE_DIR / "pcdraft"  # Assume relative to repo root or parent

sys.path.insert(0, str(BASE_DIR))
if str(MASTER_DIR) not in sys.path:
    sys.path.append(str(MASTER_DIR))

logger = logging.getLogger(__name__)

# ─── OPERATOR WHITELIST (Alpha-GPT inspired — verified from live API) ─────────
VALID_OPERATORS = {
    "ts_delta", "ts_delay", "ts_std_dev", "ts_decay_linear", "ts_mean",
    "ts_corr", "ts_rank", "ts_sum", "ts_zscore", "ts_max", "ts_product",
    "rank", "group_neutralize", "group_rank", "zscore", "normalize",
    "abs", "log", "sqrt", "sign", "signed_power", "multiply", "divide",
    "if_else", "greater", "less", "greater_equal", "less_equal",
    "tradewhen", "humpdecay"
}

# ─── SEED LIBRARY (Alpha-GPT: Seed alpha factory bootstraps from validated alphas)
# Confirmed valid from alpha_burst.py operator verification
SEED_LIBRARY = [
    "group_neutralize(rank(-1 * ts_delta(close, 5)), SUBINDUSTRY)",
    "group_neutralize(rank(ts_mean(close, 5) / ts_mean(close, 20)), SUBINDUSTRY)",
    "group_neutralize(rank(-1 * (close - ts_mean(close, 20))), SUBINDUSTRY)",
    "group_neutralize(rank(ts_std_dev(close, 20) / ts_mean(close, 20)), SUBINDUSTRY)",
    "group_neutralize(rank(volume / ts_mean(volume, 20)), SUBINDUSTRY)",
    "group_neutralize(rank(ts_corr(close, volume, 20)), SUBINDUSTRY)",
    "group_neutralize(rank(-1 * ts_rank(close, 20)), SUBINDUSTRY)",
    "group_neutralize(rank(log(volume) - log(ts_mean(volume, 20))), SUBINDUSTRY)",
]

try:
    from market_regime_classifier import MarketProfiler
except ImportError:
    MarketProfiler = None
    logger.warning("market_regime_classifier not available — regime sensing disabled.")

try:
    from llm_router import route_query
except ImportError:
    route_query = None
    logger.error("llm_router not available — SATE offline!")

try:
    import alpha_validator
except ImportError:
    alpha_validator = None
    logger.warning("alpha_validator not available — syntax linting disabled.")

KARPATHY_HYPOTHESES = MASTER_DIR / "karpathy_hypotheses.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SATE] - %(levelname)s - %(message)s')

class ThinkingEngine:
    def __init__(self):
        self.blacklist = set()

    def _get_seed_alpha(self) -> str:
        """Alpha-GPT inspired: Start mutations from a validated high-quality seed/research."""
        # 1. Prefer Karpathy Research Hypotheses
        if KARPATHY_HYPOTHESES.exists():
            try:
                data = json.loads(KARPATHY_HYPOTHESES.read_text(encoding="utf-8"))
                if data:
                    # Prefer fresh research (last 10)
                    choice = random.choice(data[-10:])
                    logger.info(f"Using KAR hypothesis as seed: {choice['expression'][:40]}...")
                    return choice['expression']
            except:
                pass
                
        # 2. Fallback to hardcoded factory seeds
        return random.choice(SEED_LIBRARY)

    def _validate_expression(self, expr: str) -> bool:
        """Pre-flight check using deterministic rules and LLM-linting."""
        # Baseline deterministic checks
        junk_phrases = ["sorry", "cannot", "sure", "here is", "response", "as an ai", "interface", "healed"]
        if any(j in expr.lower() for j in junk_phrases):
            return False
        if len(expr) < 5 or len(expr) > 2000:
            return False
        
        # Use a more capable validator if available
        if alpha_validator:
            is_valid, reason = alpha_validator.validate_syntax_rules(expr)
            if not is_valid:
                logger.warning(f"Deterministic validation failed: {reason}")
                return False
        
        return True

    def get_current_regime(self) -> str:
        """Determines market regime for context using SPX and VIX."""
        try:
            import yfinance as yf
            import logging
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            
            vix = yf.Ticker("^VIX").history(period="1mo")
            spy = yf.Ticker("^GSPC").history(period="1mo")
            
            if vix.empty or spy.empty:
                return "UNKNOWN"
            
            current_vix = float(vix['Close'].iloc[-1])
            spy_px = spy['Close'].values
            spy_returns = float((spy_px[-1] - spy_px[0]) / spy_px[0])
            
            if current_vix > 25:
                regime = "HIGH_VOLATILITY_REVERSION (Favor mean reversion, stat-arb)"
            elif current_vix < 20 and spy_returns > 0.02:
                regime = "BULL_MOMENTUM (Favor trend following, price momentum)"
            elif current_vix < 25 and spy_returns < -0.02:
                regime = "BEAR_MOMENTUM (Favor short signals, structural factor tilts)"
            else:
                regime = "RANGE_BOUND_STAGNANT (Favor low volatility, beta-neutral factors)"
                
            logger.info(f"Detected Market Regime: VIX={current_vix:.2f}, SPX_Return={spy_returns:.2%}, State={regime}")
            return regime
        except Exception as e:
            logger.warning(f"Failed to fetch market regime: {e}")
            return "UNKNOWN"


    def analyze_history(self) -> str:
        """Summarizes recent successful alphas and failures for LLM context."""
        if not EVOLUTION_LOG.exists():
            return "No historical data yet."
        
        try:
            data = json.loads(EVOLUTION_LOG.read_text(encoding="utf-8"))
            brain_entries = data.get("brain", [])
            
            # 1. SUCCESS LEARNING (Champions)
            champions = [e for e in brain_entries if e.get("status") == "SUBMITTED" or (e.get("sharpe") and e.get("sharpe") > 1.0)]
            champions.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
            
            # 2. FAILURE LEARNING (Anti-Patterns)
            failures = [e for e in brain_entries if e.get("status") == "REJECTED" or (e.get("sharpe") and e.get("sharpe") < 0.2)]
            failures.sort(key=lambda x: x.get("sharpe", 0)) # Most negative first
            
            summary = ["## CHAMPION PATTERNS (REVERSE ENGINEER THESE):"]
            for c in champions[:5]:
                summary.append(f"- Expr: {c.get('expression', 'N/A')} | Sharpe: {c.get('sharpe', 0)}")
            
            summary.append("\n## FAILURE ANTI-PATTERNS (AVOID THESE):")
            for f in failures[:5]:
                reason = f.get('reason', 'N/A')
                summary.append(f"- Rejected: {f.get('expression', 'N/A')} | Sharpe: {f.get('sharpe', 0)} | Reason: {reason}")
                
            return "\n".join(summary) if len(summary) > 2 else "Insufficient history data."
        except:
            return "History error."

    def get_latest_research(self) -> str:
        """Pulls the latest synthesis from LangGraph autonomous research."""
        try:
            reports = list(PCDRAFT_DIR.glob("langgraph_report_*.json"))
            if not reports:
                return "No recent deep research available."
            reports.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            latest = reports[0]
            data = json.loads(latest.read_text(encoding="utf-8"))
            return data.get("synthesis", "No synthesis in report.")[:2000] # Limit context size
        except Exception as e:
            logger.error(f"Failed to load research: {e}")
            return "Research engine offline."

    def evolve_hypothesis(self, mode="TRINITY", depth="DEEP", feedback=None) -> str:
        """Calls LLM to generate a high-intelligence alpha expression (Alpha-GPT style)."""
        if route_query is None:
            logger.error("LLM Router offline. Using seed alpha fallback.")
            return self._get_seed_alpha()

        regime = self.get_current_regime()
        history = self.analyze_history()
        seed = self._get_seed_alpha()
        
        feedback_prompt = ""
        if feedback:
            feedback_prompt = f"""
!! CRITICAL FEEDBACK ON PREVIOUS ITERATION !!
- Previous Expression: {feedback.get('expr')}
- Status/Reason: {feedback.get('reason')}
- Sharpe: {feedback.get('sharpe')} | Turnover: {feedback.get('turnover')}
- API Error (if any): {feedback.get('api_error', 'None')}

ACTION REQUIRED: MUTATE the previous expression to fix the failure. Do NOT just generate a random new idea.
- If Sharpe was 0.0: the expression likely has a structural error. Rewrite from scratch using validated operators.
- If Turnover was too high: add `ts_decay_linear(X, 10)` or `tradewhen(condition, exit, signal)` to reduce.
- If Fitness was too low: increase fundamental component weight, reduce price-momentum exposure.
"""

        prompt = f"""TASK: Generate a UNIQUE, HIGH-COMPLEXITY WorldQuant Brain FASTEXPR alpha expression.
ACT AS: Composite team of 3 experts — Senior Quant Strategist + Risk Manager + Data Scientist.

CONTEXT:
- Market Regime: {regime}
- PERFORMANCE HISTORY:
{history}
{feedback_prompt}

SEED ALPHA (MUTATE OR IMPROVE THIS — DO NOT COPY IT VERBATIM):
{seed}

CONFIRMED VALID OPERATORS (ONLY USE THESE):
ts_delta, ts_delay, ts_std_dev, ts_decay_linear, ts_mean, ts_corr, ts_rank, ts_sum,
ts_zscore, ts_max, ts_product, rank, group_neutralize, group_rank, zscore, normalize,
abs, log, sqrt, sign, signed_power, multiply, divide, if_else, greater, less,
greater_equal, less_equal, tradewhen, humpdecay

CONFIRMED VALID DATA FIELDS: close, open, high, low, volume, vwap, returns, returns_20d
FUNDAMENTAL FIELDS: fnd6_fopo, fnd6_ebitda, fnd6_roa, debt_lt, fnd6_equity, fnd6_revenue, enterprise_value, fnd6_grossmargin, mdl_cvol_252d

STRATEGIC GUIDELINES (2026 Season):
1. TARGET: Sharpe > 1.2, Fitness > 0.9, Turnover < 0.7
2. MUST: Wrap the final expression in group_neutralize(..., neutralization)
   - Default: subindustry
   - If previous attempt was REJECTED for Overlap: ROTATE to 'industry' or 'sector'.
3. PREFER: Long-window fundamentals (e.g., ts_zscore(fnd6_ebitda, 252)) mixed with short-term price signals.
4. AVOID: Simple `ts_delta(close, N)` or `rank(close)` — these are 100% saturated.
5. COMBINE: Orthogonal factors. Mix Quality (ROA), Value (EBITDA/EV), and Sentiment (Volume/Returns).
6. DIVERSITY: If repeating a theme, change the lookback period (e.g., use 60d instead of 20d).
6. COMPLEXITY: Use nested operators (at least 3-4 levels deep).

6. SYNTAX RULES (NON-NEGOTIABLE):
   - ALWAYS use standard operators (`*`, `/`, `+`, `-`) for math.
   - NEVER use functional math like `multiply(a, b)`, `divide(a, b)`, or `add(a, b)`.
   - NEVER use `(a, b)` syntax for division. WorldQuant requires `(a / b)`.
   - Functions like `ts_mean(x, d)`, `ts_std_dev(x, d)`, `ts_rank(x, d)`, `humpdecay(x, d)` take EXACTLY 2 arguments.
   - Functions like `group_neutralize(x, g)` take EXACTLY 2 arguments.
   - CROSS-CHECK: If you see three arguments in a `ts_` function (e.g. `ts_mean(a, b, c)`), it is a CRITICAL ERROR.

7. NEGATIVE EXAMPLES (DO NOT DO THIS):
   - Bad: `ts_mean(rank(close), 10, 5)` -> EXAM: Too many arguments.
   - Bad: `divide(close, open)` -> EXAM: Use `(close / open)`.
   - Bad: `humpdecay((equity, enterprise), 8)` -> EXAM: The comma inside parentheses is invalid. Use `humpdecay((equity / enterprise), 8)`.

OUTPUT: ONLY the raw FASTEXPR string. No markdown. No explanation. No comments."""

        logger.info(f"Evolving {mode} hypothesis for regime: {regime} using Expert Panel Reasoning (seed: {seed[:40]}...)")
        try:
            # EXPERT PANEL: Require Chain-of-Thought (CoT)
            system_prompt = (
                "You are a world-class Quantitative Research AI. "
                "Step 1: Analyze the market regime and performance history. "
                "Step 2: Propose a high-intelligence alpha concept. "
                "Step 3: Transform concept into raw WorldQuant FASTEXPR code. "
                "Your final line MUST be ONLY the FASTEXPR. No markdown, no comments."
            )
            
            result = route_query(
                system_prompt=system_prompt,
                user_query=prompt,
                depth="DEEP"
            )
            raw_text = result['text'].strip()
            
            # Extract the LAST line as the expression (CoT result)
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            hypothesis = lines[-1] if lines else raw_text
            
            # Sanitize via AlphaValidator if available
            if alpha_validator:
                hypothesis = alpha_validator.solve_common_errors(hypothesis)
            # Extract if wrapped in backticks
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("python") or raw_text.startswith("expression"):
                    raw_text = "\n".join(raw_text.splitlines()[1:])
            
            # Sanitize and unify syntax
            # Phase 8: Support neutralization rotation (subindustry, industry, sector)
            hypothesis = raw_text.replace("SUBINDUSTRY", "subindustry")
            hypothesis = hypothesis.replace("INDUSTRY", "industry")
            hypothesis = hypothesis.replace("SECTOR", "sector")
            # Force standard operators via regex for common LLM hallucinations
            import re
            hypothesis = re.sub(r"multiply\s*\(([^,]+),\s*([^)]+)\)", r"(\1 * \2)", hypothesis)
            hypothesis = re.sub(r"divide\s*\(([^,]+),\s*([^)]+)\)", r"(\1 / \2)", hypothesis)
            hypothesis = re.sub(r"add\s*\(([^,]+),\s*([^)]+)\)", r"(\1 + \2)", hypothesis)
            hypothesis = re.sub(r"sub\s*\(([^,]+),\s*([^)]+)\)", r"(\1 - \2)", hypothesis)
            # Note: The above is a bit risky if nested, but LLM should use operators.
            # Let's do a safer replacement for basic hallucination.
            
            # Better approach: Just warn the LLM more strictly and let the factory handle the 'subindustry' replacement.
            # But the factory should also log the sanitized version.
            
            # Extract if wrapped in backticks
            if "```" in raw_text:
                parts = raw_text.split("```")
                hypothesis = parts[1].strip() if len(parts) > 1 else raw_text
                for prefix in ["python", "fastexpr", "alpha"]:
                    if hypothesis.lower().startswith(prefix):
                        hypothesis = hypothesis[len(prefix):].strip()
            else:
                hypothesis = raw_text.strip()
            
            # Ensure it's a single line and clean up
            hypothesis = hypothesis.replace("\n", " ").replace("  ", " ").strip()
            
            # Take first valid-looking line (after ensuring it's one line, this will just be the hypothesis itself)
            lines = [l.strip() for l in hypothesis.split('\n') if l.strip() and not l.strip().startswith('#')]
            for line in lines:
                if "group_neutralize" in line or "rank(" in line or "ts_" in line:
                    hypothesis = line
                    break
            else:
                hypothesis = lines[0] if lines else hypothesis
            
            # Clean up
            hypothesis = hypothesis.replace("`", "").strip()
            
            # Validate — fallback to seed if junk
            if not self._validate_expression(hypothesis):
                logger.warning(f"LLM returned invalid expression: '{hypothesis[:60]}'. Using seed fallback.")
                return seed

            # Enforce mandatory group_neutralize wrapper
            if "neutralize" not in hypothesis.lower():
                hypothesis = f"group_neutralize(rank({hypothesis}), subindustry)"

            logger.info(f"Evolved Alpha: {hypothesis} (Provider: {result['provider']})")
            return hypothesis

        except Exception as e:
            logger.error(f"LLM Evolution failed: {e}. Using validated seed alpha fallback.")
            return seed  # Use validated seed — NOT rank(close)



if __name__ == "__main__":
    te = ThinkingEngine()
    print(te.evolve_hypothesis())
