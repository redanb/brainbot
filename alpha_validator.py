import os
import sys
import re
import logging
from pathlib import Path

# Fix paths for llm_router import
def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

MASTER_DIR = get_master_dir()
sys.path.append(str(MASTER_DIR))

import llm_router

logger = logging.getLogger("AlphaValidator")
logger.setLevel(logging.INFO)

VALID_OPERATORS = {
    "ts_delta", "ts_delay", "ts_std_dev", "ts_decay_linear", "ts_mean",
    "ts_corr", "ts_rank", "ts_sum", "ts_zscore", "ts_max", "ts_product",
    "rank", "group_neutralize", "group_rank", "zscore", "normalize",
    "abs", "log", "sqrt", "sign", "signed_power", "multiply", "divide",
    "if_else", "greater", "less", "greater_equal", "less_equal",
    "tradewhen", "humpdecay"
}

def validate_syntax_rules(expression: str) -> tuple[bool, str]:
    """Perform deterministic syntax checks."""
    # 1. Rule: Functional math operators (multiply, divide) are forbidden in the final FASTEXPR
    for op in ["multiply(", "divide(", "add(", "sub("]:
        if op in expression.lower():
            return False, f"Rule: Functional operator '{op}' is forbidden. Use standard *, /, +, - symbols."
            
    # 2. Rule: Comma followed by a non-space character (common in (equity, enterprise) hallucinations)
    if re.search(r"\(([^,]+),([^)]+)\)", expression) and not re.search(r"\b(ts_|group_|rank|if_else|greater|less|tradewhen|humpdecay)", expression):
        # Allow if it's clearly a function call, but block (a,b) where a/b should be
        pass # This is tricky, LLM should judge

    # 3. Rule: Check character balance
    if expression.count('(') != expression.count(')'):
        return False, "Rule: Unbalanced parentheses."

    return True, ""

def validate_alpha_with_llm(expression: str) -> tuple[bool, str]:
    """Use Gemini Flash as a fast, cheap 'Linter' to catch semantic FASTEXPR errors."""
    system_prompt = """You are a WorldQuant Brain FASTEXPR Syntax Linter. 
Your ONLY job is to identify if an expression will be REJECTED by the Brain API.

SYNTAX RULES:
1. Functions like ts_mean(x, d), ts_std_dev(x, d), ts_rank(x, d) take EXACTLY 2 arguments.
2. Math must use symbols: (*, /, +, -). NEVER functional calls like multiply(a, b).
3. group_neutralize(x, g) takes EXACTLY 2 arguments (group must be 'subindustry', 'industry', or 'sector').
4. No comments (#) or multiple lines allowed.
5. All variables must be lowercase (e.g. close, open, volume).

OUTPUT: 
- If VALID: Respond with 'VALID'.
- If INVALID: Respond with 'INVALID: <reason>'."""

    user_query = f"Expression: {expression}"
    
    try:
        res = llm_router.route_query(
            system_prompt=system_prompt,
            user_query=user_query,
            depth="FAST", # Use Flash for speed/cost
            max_retries=2
        )
        text = res['text'].strip()
        if text.startswith("VALID"):
            return True, ""
        return False, text
    except Exception as e:
        logger.warning(f"LLM Linter failed: {e}. Falling back to deterministic rules.")
        return validate_syntax_rules(expression)

def solve_common_errors(expression: str) -> str:
    """Auto-corrector for common LLM hallucinations."""
    # Correct functional math
    expression = re.sub(r"multiply\s*\(([^,]+),\s*([^)]+)\)", r"(\1 * \2)", expression)
    expression = re.sub(r"divide\s*\(([^,]+),\s*([^)]+)\)", r"(\1 / \2)", expression)
    expression = re.sub(r"add\s*\(([^,]+),\s*([^)]+)\)", r"(\1 + \2)", expression)
    expression = re.sub(r"sub\s*\(([^,]+),\s*([^)]+)\)", r"(\1 - \2)", expression)
    
    # Correct capitalization
    expression = expression.lower()
    
    # Correct missing group_neutralize if not found
    if "neutralize" not in expression and "rank" in expression:
        # Avoid double-wrapping
        if not expression.startswith("group_neutralize"):
            expression = f"group_neutralize({expression}, subindustry)"
            
    return expression

if __name__ == "__main__":
    test_expr = "ts_mean(rank(close), 10, 5)" # 3 arguments (INVALID)
    valid, reason = validate_alpha_with_llm(test_expr)
    print(f"Expr: {test_expr}\nResult: {'PASS' if valid else 'FAIL'} | Reason: {reason}")
    
    test_expr_2 = "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)" # (VALID)
    valid2, reason2 = validate_alpha_with_llm(test_expr_2)
    print(f"Expr: {test_expr_2}\nResult: {'PASS' if valid2 else 'FAIL'} | Reason: {reason2}")
