"""
alpha_mutator.py
Genetic mutation layer for WorldQuant alphas.
Takes a valid FASTEXPR string and generates mutated variations (changing parameters, operators).
"""
import re
import random

MUTATION_RATES = [
    (r"(5)", ["10", "20", "3"]),
    (r"(10)", ["5", "20", "60"]),
    (r"(20)", ["10", "60", "252"]),
    (r"(252)", ["120", "60", "20"]),
    (r"ts_rank", ["ts_zscore", "ts_mean", "ts_std_dev"]),
    (r"ts_mean", ["ts_decay_linear", "ts_sum"]),
    (r"close", ["vwap", "open", "high"]),
    (r"volume", ["vwap", "close"]),
    (r"fnd6_fopo", ["fnd6_ebitda", "fnd6_roa", "fnd6_equity", "fnd6_grossmargin"]),
]

def mutate_expression(expr: str, count: int = 3) -> list[str]:
    """Generates `count` mutated variations of the base expression."""
    mutants = set()
    attempts = 0
    max_attempts = count * 10
    
    while len(mutants) < count and attempts < max_attempts:
        attempts += 1
        new_expr = expr
        
        num_mutations = random.randint(1, 3)
        applied = 0
        
        rules = list(MUTATION_RATES)
        random.shuffle(rules)
        
        for pattern, replacements in rules:
            if re.search(pattern, new_expr) and applied < num_mutations:
                replacement = random.choice(replacements)
                new_expr = re.sub(pattern, replacement, new_expr, count=1)
                applied += 1
                
        if new_expr != expr and "group_neutralize" in new_expr:
            mutants.add(new_expr)
            
    return list(mutants)

if __name__ == "__main__":
    base = "group_neutralize(rank(ts_rank(close, 20) / fnd6_fopo), SUBINDUSTRY)"
    print(f"Base: {base}")
    for m in mutate_expression(base, 5):
        print(f"Mutant: {m}")
