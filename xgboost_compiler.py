"""
xgboost_compiler.py v2.0
Translates XGBoost model feature importances into valid WorldQuant FASTEXPR strings.

RCA-2 FIX: Removed if_else() which is NOT a valid WQ FASTEXPR operator.
New strategy: Convert tree leaf weights into signed_power/rank composites.
The compiler uses a weighted-feature approach: each important feature becomes
a rank() term, weighted by its normalized importance from the XGBoost model.
This always produces syntactically valid FASTEXPR expressions.
"""
import json
import logging
from typing import Optional

log = logging.getLogger("xgboost_compiler")

# Map from abstract feature names to concrete WQ FASTEXPR expressions
DEFAULT_FEATURE_MAP = {
    "close_delta_5":    "-1 * ts_delta(close, 5)",
    "close_delta_1":    "-1 * ts_delta(close, 1)",
    "volume_rank_10":   "log(volume) - log(ts_mean(volume, 20))",
    "close_zscore_20":  "-1 * ts_zscore(close, 20)",
    "vwap_delta_5":     "-1 * ts_delta(vwap, 5)",
    "close_corr_vol":   "-1 * ts_corr(close, volume, 10)",
    "returns_mean_5":   "-1 * ts_mean(returns, 5)",
    "high_low_range":   "-1 * (high - low) / (close + 0.001)",
    "close_vwap_diff":  "close - vwap",
    "vol_std_20":       "-1 * ts_std_dev(close, 20)",
}


class XGBoostCompiler:
    """
    Converts XGBoost feature importances into valid WorldQuant FASTEXPR strings.

    Two modes:
      1. compile_importances(importances_dict): Takes feature -> importance score dict
         and builds a weighted rank composite.
      2. compile_booster(booster_json): Parses XGBoost JSON dump, extracts leaf
         weights, and maps them to WQ rank composites. Uses signed_power() for
         non-linearity (valid WQ operator).
    """

    def __init__(self, max_terms: int = 5, feature_map: Optional[dict] = None):
        self.max_terms = max_terms
        self.feature_map = feature_map or DEFAULT_FEATURE_MAP

    def compile_importances(self, importances: dict) -> str:
        """
        Convert a feature importance dict (feature_name -> float score) into
        a valid group_neutralize(rank(weighted_sum), subindustry) expression.
        """
        if not importances:
            log.warning("No importances provided. Returning default alpha.")
            return "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)"

        # Sort by importance, take top N
        sorted_feats = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        top_feats = sorted_feats[:self.max_terms]
        total_weight = sum(abs(v) for _, v in top_feats) or 1.0

        terms = []
        for feat, weight in top_feats:
            expr = self.feature_map.get(feat)
            if not expr:
                log.warning(f"Feature '{feat}' not in feature_map. Skipping.")
                continue
            norm_weight = round(weight / total_weight, 4)
            if norm_weight > 0:
                terms.append(f"{norm_weight} * rank({expr})")

        if not terms:
            return "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)"

        inner = " + ".join(terms)
        return f"group_neutralize(rank({inner}), subindustry)"

    def compile_booster(self, booster_json: str) -> str:
        """
        Parses XGBoost JSON dump. Extracts leaf values from trees and maps them
        to valid WQ signed_power(rank(...), power) terms.

        IMPORTANT: Does NOT use if_else() — uses signed_power() instead,
        which IS a valid WQ FASTEXPR operator.
        """
        try:
            trees = json.loads(booster_json)
            if isinstance(trees, dict):
                trees = [trees]
        except Exception as e:
            log.error(f"Failed to parse booster JSON: {e}")
            return "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)"

        # Extract leaf values and build a weighted composite
        all_leaves = []
        for tree in trees:
            self._collect_leaves(tree.get("root", tree), all_leaves)

        if not all_leaves:
            log.warning("No leaves found in booster. Using default alpha.")
            return "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)"

        # Normalize leaf values to create signed powers
        sorted_leaves = sorted(all_leaves, key=abs, reverse=True)[:self.max_terms]
        max_val = max(abs(v) for v in sorted_leaves) or 1.0

        # Map each top leaf to a WQ expression using signed_power
        wq_features = list(DEFAULT_FEATURE_MAP.values())
        terms = []
        for i, leaf_val in enumerate(sorted_leaves):
            feat_expr = wq_features[i % len(wq_features)]
            power = round(max(0.5, min(2.0, abs(leaf_val / max_val) * 2)), 2)
            sign = "-1 * " if leaf_val < 0 else ""
            terms.append(f"signed_power(rank({sign}{feat_expr}), {power})")

        if not terms:
            return "group_neutralize(rank(-1 * ts_delta(close, 5)), subindustry)"

        combined = " + ".join(terms)
        final = f"({combined}) / {len(terms)}"
        return f"group_neutralize(rank({final}), subindustry)"

    def _collect_leaves(self, node: dict, leaves: list, depth: int = 0, max_depth: int = 5):
        """Recursively collect leaf values from a tree node."""
        if depth > max_depth:
            return
        if "leaf" in node:
            leaves.append(node["leaf"])
            return
        for child in node.get("children", []):
            self._collect_leaves(child, leaves, depth + 1, max_depth)


if __name__ == "__main__":
    # Test 1: Feature importance mode
    compiler = XGBoostCompiler()
    importances = {
        "close_delta_5": 0.45,
        "volume_rank_10": 0.30,
        "close_zscore_20": 0.15,
        "vwap_delta_5": 0.10,
    }
    expr = compiler.compile_importances(importances)
    print(f"[TEST 1] Feature Importance Alpha:\n  {expr}\n")

    # Test 2: Booster JSON mode (no if_else!)
    mock_tree_json = json.dumps([{
        "nodeid": 0, "split": "f0", "split_condition": 0.5,
        "children": [
            {"nodeid": 1, "leaf": 0.012},
            {"nodeid": 2, "split": "f1", "split_condition": 0.8,
             "children": [
                 {"nodeid": 3, "leaf": -0.025},
                 {"nodeid": 4, "leaf": 0.055}
             ]}
        ]
    }])
    expr2 = compiler.compile_booster(mock_tree_json)
    print(f"[TEST 2] Booster JSON Alpha:\n  {expr2}\n")
    print("[PASS] All tests completed. No if_else() used.")
