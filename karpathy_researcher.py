import os
import sys
import json
import logging
import random
from pathlib import Path
from datetime import datetime

# Fix paths for llm_router and alpha_validator import
def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

MASTER_DIR = get_master_dir()
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(MASTER_DIR))
sys.path.append(str(BASE_DIR))

import llm_router
import alpha_validator

logger = logging.getLogger("KAR-Researcher")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s [KAR] %(message)s'))
    logger.addHandler(ch)

HYPOTHESIS_FILE = MASTER_DIR / "karpathy_hypotheses.json"

class KarpathyResearcher:
    def __init__(self):
        self.research_context = """
        LATEST 2026 QUANT TRENDS:
        1. High-Dimensional Screening (LASSO): Identify marginal predictive power.
        2. Denoising: Use ts_decay_linear, ts_mean, and wavelets (ts_std_dev) to extract signals.
        3. Alternative Data: Sentiment (volume/returns mismatch), Supply Chain (fundamental ratios).
        4. Cross-Market Validation: Statistical arbitrage between sectors.
        5. Quality + Value: fnd6_ebitda / enterprise_value mixed with low-volatility price signals.
        """

    def generate_hypotheses(self, count=5):
        """Perform 'Deep Research' and generate validated alpha expressions."""
        logger.info(f"Generating {count} Deep Research hypotheses...")
        
        system_prompt = f"""You are a World-Class Quantitative Researcher. 
Your goal is to propose NOVEL, high-Sharpe (>1.5) alpha factors for WorldQuant Brain.

CONTEXT:
{self.research_context}

FASTEXPR GUIDELINES:
- Operators: ts_mean, ts_delta, ts_rank, ts_corr, ts_std_dev, ts_decay_linear, group_neutralize, rank, etc.
- Data: close, open, volume, vwap, fnd6_ebitda, enterprise_value, fnd6_roa, debt_lt.
- Rule: Always neutralize against 'subindustry' or 'industry'.
- Rule: Maximize complexity (3-5 nested levels).

OUTPUT:
A JSON array of strings, where each string is a raw FASTEXPR expression."""

        user_query = f"Provide {count} unique, high-intelligence FASTEXPR alphas based on 2026 trends."
        
        try:
            # Use DEEP reasoning if available (cascades to Claude 3.7 or Gemini 1.5 Pro)
            res = llm_router.route_query(
                system_prompt=system_prompt,
                user_query=user_query,
                depth="DEEP"
            )
            
            # Extract JSON array
            raw_text = res['text'].strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
            hypotheses = json.loads(raw_text)
            validated = []
            
            for h in hypotheses:
                # 1. Self-Correction / Auto-Fix
                h = alpha_validator.solve_common_errors(h)
                
                # 2. Validation
                is_valid, reason = alpha_validator.validate_alpha_with_llm(h)
                if is_valid:
                    logger.info(f"Validated Alpha: {h[:60]}...")
                    validated.append({
                        "expression": h,
                        "timestamp": datetime.now().isoformat(),
                        "source": "KAR-Researcher",
                        "model": res.get('model', 'unknown')
                    })
                else:
                    logger.warning(f"Rejected Alpha: {h[:60]}... Reason: {reason}")
            
            self._save_hypotheses(validated)
            return validated
            
        except Exception as e:
            logger.error(f"Research loop failed: {e}")
            return []

    def _save_hypotheses(self, new_hyps):
        """Append new validated hypotheses to the persistent store."""
        current = []
        if HYPOTHESIS_FILE.exists():
            try:
                current = json.loads(HYPOTHESIS_FILE.read_text(encoding="utf-8"))
            except:
                current = []
        
        # Avoid exact duplicates
        existing_exprs = {h['expression'] for h in current}
        for h in new_hyps:
            if h['expression'] not in existing_exprs:
                current.append(h)
        
        HYPOTHESIS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
        logger.info(f"Saved {len(new_hyps)} new hypotheses to {HYPOTHESIS_FILE}")

    def refine_failed_alpha(self, expression: str, failure_reason: str, universe_context: str = "TOP3000") -> str:
        """Deep research to structurally refine an alpha that failed validation."""
        logger.info(f"Refining failed alpha: {expression[:40]}... due to {failure_reason}")
        
        system_prompt = f"""You are a World-Class Quantitative Researcher.
A previously generated FASTEXPR alpha failed simulation validation.
You must structurally mutate/refine it to fix the issue based on the failure reason.
Do NOT generate a random alpha. Address the specific failure reason.

CONTEXT:
{self.research_context}

REQUIREMENTS:
1. Wrap final expression in group_neutralize(..., subindustry) or industry. 
2. Use valid standard operators.
3. OUTPUT ONLY THE RAW STRING FASTEXPR. No markdown."""
        
        user_query = f"""
ORIGINAL EXPRESSION: {expression}
FAILURE REASON: {failure_reason}
UNIVERSE: {universe_context}

Provide ONE refined alpha expression that fixes this failure:
"""
        try:
            res = llm_router.route_query(
                system_prompt=system_prompt,
                user_query=user_query,
                depth="DEEP"
            )
            raw_text = res['text'].strip()
            
            # Clean up
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            hypothesis = lines[-1] if lines else raw_text
            hypothesis = hypothesis.replace("`", "").strip()
            
            hypothesis = alpha_validator.solve_common_errors(hypothesis)
            return hypothesis
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return expression # Fallback to original

    def audit_graduation_candidate(self, expression: str) -> bool:
        """Audit a candidate before grading it (prevents cluster-waste and duplicates).
        Uses simple heuristic for now, expandable to LLM-similarity analysis.
        """
        audit_file = MASTER_DIR / "submission_audit.json"
        
        if not audit_file.exists():
            return True
            
        try:
            with open(audit_file, "r") as f:
                audit_data = json.load(f)
            
            # Simple check against previous failures to avoid repeating known 403s on identical alpha
            for entry in audit_data.get("failed_submissions", []):
                if entry.get("expression") == expression:
                    logger.warning(f"Auditor Blocked: Exact duplicate of known failed submission found.")
                    return False
            
            for entry in audit_data.get("successful_submissions", []):
                if entry.get("expression") == expression:
                    logger.warning(f"Auditor Blocked: Already successfully submitted.")
                    return False
                    
            return True
        except Exception as e:
            logger.warning(f"Auditor failed: {e}")
            return True

    def update_global_skills(self):
        """Analyze last evolution_log entries and update SKILLS.md for factory context injection."""
        logger.info("Updating global SKILLS.md context from evolution_log...")
        evo_file = MASTER_DIR / "evolution_log.json"
        
        if not evo_file.exists():
            return
            
        try:
            with open(evo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            brain_entries = data.get("brain", [])
            successes = [e for e in brain_entries if e.get("status") in ["GRADUATED", "SUBMITTED"]]
            
            if not successes:
                return
                
            last_winners = successes[-10:] # last 10
            
            system_prompt = """You are leading Quantitative Knowledge Management.
Analyze the provided recent winning alpha expressions.
Generate a concise Markdown snippet mapping which operators/factors are currently working well.
Limit to 150 words. Do not list expressions exactly, but derive the conceptual 'skills'."""

            wins_text = "\n".join([f"- {e.get('expression')} (Sharpe: {e.get('sharpe')})" for e in last_winners])
            user_query = f"RECENT WINNING ALPHAS:\n{wins_text}\n\nUpdate the SKILLS context:"
            
            res = llm_router.route_query(system_prompt, user_query, depth="STANDARD")
            skill_content = res['text'].strip()
            
            scout_dir = BASE_DIR / "scouts"
            scout_dir.mkdir(exist_ok=True)
            skills_file = scout_dir / "SKILLS.md"
            
            skills_content = f"""# Factory SKILLS Knowledge Base
Last Updated: {datetime.now().isoformat()}

## Winning Factors & Operator Syntheses (Auto-Researched)
{skill_content}
"""
            skills_file.write_text(skills_content, encoding="utf-8")
            logger.info("Global SKILLS.md updated.")
            
        except Exception as e:
            logger.error(f"Failed to update SKILLS.md: {e}")

if __name__ == "__main__":
    kr = KarpathyResearcher()
    kr.generate_hypotheses(count=3)
