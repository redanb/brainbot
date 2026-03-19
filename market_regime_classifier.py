"""
market_regime_classifier.py — BetScript Quant Port
Phase 2: Skill Monetization — NumerAI Alpha Track

Direct port of opponent_profiler.py to market regime classification.
Replaces ad-hoc z-score features with structured Bayesian signal profiles.

Poker -> Finance mapping:
  PlayerProfile (opponent stats)    ->  EraProfile (era/market stats)
  OpponentDatabase (session registry)  ->  MarketProfiler (era registry)

  VPIP  (voluntary entry %)         ->  participation_rate (features > era mean %)
  PFR   (preflop raise %)           ->  momentum_intensity (top-quartile return %)
  AF    (aggression factor)         ->  trend_strength (momentum / mean-reversion)
  FCB   (fold to cbet %)            ->  mean_reversion_prob (following-period pullback %)
  3Bet% (re-aggression)             ->  breakout_persistence (rank autocorrelation)
  Bluff%(hidden info)               ->  noise_ratio (vol / realized_move divergence)

  classify(): FISH/NIT/LAG/TAG      ->  classify_regime(): REVERTING/STAGNANT/TRENDING/TRANSITIONAL

RULE-023: No emojis in print statements (Windows cp1252 safety).
"""
from __future__ import annotations

import math
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("market_regime_classifier")

# ── Regime Labels ─────────────────────────────────────────────────────────────
REGIME_REVERTING    = "REVERTING"     # FISH analog: overextensions revert
REGIME_STAGNANT     = "STAGNANT"      # NIT analog:  low vol, minimal signal
REGIME_TRENDING     = "TRENDING"      # LAG analog:  momentum persists
REGIME_TRANSITIONAL = "TRANSITIONAL"  # TAG analog:  mixed signal, balanced


# ── Era Profile (PlayerProfile analog) ────────────────────────────────────────

@dataclass
class EraProfile:
    """
    Bayesian profile of a single NumerAI era.
    Mirrors PlayerProfile with rolling stat accumulators.
    """
    era_id: str

    # Participation Rate (VPIP analog)
    # % of features above era mean — high = broad market participation
    n_above_mean: int = 0
    n_total: int = 0

    # Momentum Intensity (PFR analog)
    # % of stocks in top-quartile feature rank
    n_top_quartile: int = 0
    n_ranked: int = 0

    # Trend Strength components (AF analog)
    # momentum signals (raises+bets) vs reversion signals (calls)
    n_momentum_signals: int = 0
    n_reversion_signals: int = 0

    # Mean Reversion Prob (FCB analog)
    # following-period feature pullback after spike
    n_spikes_followed_by_reversion: int = 0
    n_spikes_total: int = 0

    # Breakout Persistence (3-bet freq analog)
    # rank autocorrelation proxy: stocks staying in top rank across leading features
    rank_corr_sum: float = 0.0
    rank_corr_count: int = 0

    # Noise Ratio (bluff freq analog)
    # feature variance vs median cross-section signal
    feature_variances: List[float] = field(default_factory=list)
    cross_section_medians: List[float] = field(default_factory=list)

    # Sample size for confidence
    row_count: int = 0

    # ── Computed Properties (Property analogs of PlayerProfile) ──────────────

    @property
    def participation_rate(self) -> float:
        """VPIP analog: fraction of features above era mean. Prior=0.5."""
        if self.n_total == 0:
            return 0.5
        return self.n_above_mean / self.n_total

    @property
    def momentum_intensity(self) -> float:
        """PFR analog: fraction in top quartile. Prior=0.25."""
        if self.n_ranked == 0:
            return 0.25
        return self.n_top_quartile / self.n_ranked

    @property
    def trend_strength(self) -> float:
        """
        AF analog: momentum_signals / reversion_signals.
        > 2.0 = trending, < 1.0 = mean-reverting.
        Prior = 1.0 (balanced).
        """
        if self.n_reversion_signals == 0:
            return 1.0
        return (self.n_momentum_signals + 1) / (self.n_reversion_signals + 1)

    @property
    def mean_reversion_prob(self) -> float:
        """FCB analog: prob of pullback after spike. Prior=0.45."""
        if self.n_spikes_total == 0:
            return 0.45
        return self.n_spikes_followed_by_reversion / self.n_spikes_total

    @property
    def breakout_persistence(self) -> float:
        """3-bet freq analog: rank autocorrelation proxy. Prior=0.06."""
        if self.rank_corr_count == 0:
            return 0.06
        return max(0.0, min(1.0, self.rank_corr_sum / self.rank_corr_count))

    @property
    def noise_ratio(self) -> float:
        """Bluff freq analog: median feature variance / cross-section signal. Prior=0.3."""
        if not self.feature_variances or not self.cross_section_medians:
            return 0.3
        avg_var    = sum(self.feature_variances) / len(self.feature_variances)
        avg_signal = sum(abs(m) for m in self.cross_section_medians) / len(self.cross_section_medians)
        if avg_signal < 1e-8:
            return 0.3
        return min(1.0, avg_var / (avg_signal + 1e-8))

    def confidence(self) -> float:
        """Profile confidence [0-1] based on sample size. Approaches 1 after ~500 rows."""
        return 1 - math.exp(-self.row_count / 150)

    def classify_regime(self) -> str:
        """
        Classify market regime. Direct port of PlayerProfile.classify().

        Decision logic mirrors poker archetype detection:
          VPIP high  + AF high  -> LAG  -> TRENDING
          VPIP high  + AF low   -> FISH -> REVERTING
          VPIP low   + AF high  -> TAG  -> TRANSITIONAL
          VPIP low   + AF low   -> NIT  -> STAGNANT
        """
        pr = self.participation_rate   # VPIP
        mi = self.momentum_intensity   # PFR
        ts = self.trend_strength       # AF

        # High participation + strong trend = TRENDING (LAG)
        if pr >= 0.55 and ts >= 1.8:
            return REGIME_TRENDING

        # High participation + weak trend = REVERTING (FISH)
        if pr >= 0.55 and ts < 1.2:
            return REGIME_REVERTING

        # Low participation + any trend = STAGNANT (NIT)
        if pr < 0.45 and ts < 1.4:
            return REGIME_STAGNANT

        # Otherwise TRANSITIONAL (TAG) — mixed signals
        return REGIME_TRANSITIONAL

    def regime_features(self) -> Dict[str, float]:
        """
        Return numeric feature dict for downstream XGBoost input.
        These are the actionable alpha signals.
        """
        regime = self.classify_regime()
        return {
            "regime_participation_rate":  self.participation_rate,
            "regime_momentum_intensity":  self.momentum_intensity,
            "regime_trend_strength":      self.trend_strength,
            "regime_mean_reversion_prob": self.mean_reversion_prob,
            "regime_breakout_persist":    self.breakout_persistence,
            "regime_noise_ratio":         self.noise_ratio,
            "regime_confidence":          self.confidence(),
            # One-hot encode regime class
            "regime_is_trending":     float(regime == REGIME_TRENDING),
            "regime_is_reverting":    float(regime == REGIME_REVERTING),
            "regime_is_stagnant":     float(regime == REGIME_STAGNANT),
            "regime_is_transitional": float(regime == REGIME_TRANSITIONAL),
        }

    def __repr__(self) -> str:
        c = self.confidence()
        return (
            f"[Era {self.era_id}] {self.classify_regime()} "
            f"| PR={self.participation_rate:.0%} "
            f"MI={self.momentum_intensity:.0%} "
            f"TS={self.trend_strength:.2f} "
            f"MRP={self.mean_reversion_prob:.0%} "
            f"Conf={c:.0%}"
        )


# ── Market Profiler (OpponentDatabase analog) ─────────────────────────────────

class MarketProfiler:
    """
    Era-scoped registry of market regime profiles.
    Mirrors OpponentDatabase — one EraProfile per NumerAI era.
    """

    def __init__(self, feature_cols: Optional[List[str]] = None):
        self._profiles: Dict[str, EraProfile] = {}
        self.feature_cols = feature_cols or []

    def get(self, era_id: str) -> EraProfile:
        if era_id not in self._profiles:
            self._profiles[era_id] = EraProfile(era_id=era_id)
        return self._profiles[era_id]

    def all_eras(self) -> List[EraProfile]:
        return list(self._profiles.values())

    # ── Core Profiling Methods ─────────────────────────────────────────────────

    def _profile_single_era(self, era_df: pd.DataFrame, era_id: str, feat_cols: List[str]) -> EraProfile:
        """
        Compute a full EraProfile from a group of rows sharing the same era.
        The 'hand history' for a market era is the cross-section of feature values.
        """
        p = self.get(era_id)
        p.row_count = len(era_df)

        if era_df.empty or not feat_cols:
            return p

        X = era_df[feat_cols].values.astype(np.float32)   # shape: (rows, features)
        n_rows, n_feats = X.shape

        # ── VPIP: participation_rate ──────────────────────────────────────────
        # "Did this stock voluntarily participate above the era mean?"
        era_means = np.nanmean(X, axis=0)           # per-feature mean across era
        above_mean = (X > era_means).sum()
        p.n_above_mean = int(above_mean)
        p.n_total      = n_rows * n_feats

        # ── PFR: momentum_intensity ───────────────────────────────────────────
        # "What fraction of stocks raised (ranked in top 25%)?"
        col_ranks = np.argsort(np.argsort(X, axis=0), axis=0) / max(n_rows - 1, 1)
        top_q = (col_ranks >= 0.75).sum()
        p.n_top_quartile = int(top_q)
        p.n_ranked       = n_rows * n_feats

        # ── AF: trend_strength ───────────────────────────────────────────────
        # "Momentum signals (high and rising) vs reversion signals (high and falling)"
        # Proxy: compare first-half vs second-half feature column means
        if n_feats >= 2:
            half = n_feats // 2
            mean_first = np.nanmean(X[:, :half])
            mean_second = np.nanmean(X[:, half:])
            if mean_second > mean_first:
                p.n_momentum_signals  += int(n_rows * 0.6)
                p.n_reversion_signals += int(n_rows * 0.4)
            else:
                p.n_momentum_signals  += int(n_rows * 0.4)
                p.n_reversion_signals += int(n_rows * 0.6)

        # ── FCB: mean_reversion_prob ──────────────────────────────────────────
        # "Stocks in top decile this era — how many fall back next era?"
        # Since we don't have next-era data per row, approximate with intra-era pattern:
        # High-ranked rows within era that have below-median z-score = reversion tendency
        if n_rows > 4:
            row_means = np.nanmean(X, axis=1)
            top_decile_mask = row_means >= np.percentile(row_means, 75)
            n_spikes = int(top_decile_mask.sum())
            # Z-scored intra-era: "spike" rows closer to mean than outside suggest reversion
            era_col_std = np.nanstd(X, axis=0) + 1e-8
            X_z = (X - era_means) / era_col_std
            spike_rows_z = np.nanmean(np.abs(X_z[top_decile_mask]), axis=1) if n_spikes > 0 else np.array([])
            n_reverted = int((spike_rows_z < 1.5).sum()) if len(spike_rows_z) > 0 else 0
            p.n_spikes_total += n_spikes
            p.n_spikes_followed_by_reversion += n_reverted

        # ── 3-bet: breakout_persistence ──────────────────────────────────────
        # "Do stocks maintain their rank across features (correlated signals)?"
        if n_feats >= 4:
            # Compute Spearman rank correlation between first 2 and last 2 feature groups
            from scipy.stats import spearmanr
            group_a = np.nanmean(col_ranks[:, :n_feats//2], axis=1)
            group_b = np.nanmean(col_ranks[:, n_feats//2:], axis=1)
            try:
                corr, _ = spearmanr(group_a, group_b)
                if not math.isnan(corr):
                    p.rank_corr_sum += max(0.0, corr)
                    p.rank_corr_count += 1
            except Exception:
                pass

        # ── Bluff: noise_ratio ────────────────────────────────────────────────
        col_vars = np.nanvar(X, axis=0).tolist()
        col_medians = np.nanmedian(X, axis=0).tolist()
        p.feature_variances.extend(col_vars)
        p.cross_section_medians.extend(col_medians)

        return p

    def profile_all_eras(self, df: pd.DataFrame, era_col: str = "era") -> None:
        """
        Profile all eras in a DataFrame.
        Analogous to replaying all hands in a session.
        """
        feat_cols = self.feature_cols or [c for c in df.columns if c.startswith("feature_")]
        if not feat_cols:
            logger.warning("[MarketProfiler] No feature columns found.")
            return

        logger.info("[MarketProfiler] Profiling %d eras across %d features...",
                    df[era_col].nunique(), len(feat_cols))

        for era_id, era_df in df.groupby(era_col):
            self._profile_single_era(era_df, str(era_id), feat_cols)

        logger.info("[MarketProfiler] Done. %d era profiles built.", len(self._profiles))

    def get_regime_feature_matrix(self, df: pd.DataFrame, era_col: str = "era") -> pd.DataFrame:
        """
        Main integration method: add regime features to df.
        Each stock row gets regime features from its era's EraProfile.

        Returns df with ~11 new 'regime_*' feature columns added.
        This replaces the ad-hoc z-score loop in numerai_pipeline.engineer_features().
        """
        if not self._profiles:
            self.profile_all_eras(df, era_col)

        # Build era -> feature dict lookup
        era_feature_map: Dict[str, Dict] = {}
        for era_id, profile in self._profiles.items():
            era_feature_map[era_id] = profile.regime_features()

        # Map each row to its era's regime features
        regime_rows = df[era_col].astype(str).map(era_feature_map)

        # Convert list-of-dicts to DataFrame, fill missing with neutral priors
        regime_df = pd.DataFrame(regime_rows.tolist(), index=df.index)
        regime_df = regime_df.fillna({
            "regime_participation_rate":  0.5,
            "regime_momentum_intensity":  0.25,
            "regime_trend_strength":      1.0,
            "regime_mean_reversion_prob": 0.45,
            "regime_breakout_persist":    0.06,
            "regime_noise_ratio":         0.3,
            "regime_confidence":          0.0,
            "regime_is_trending":         0.0,
            "regime_is_reverting":        0.0,
            "regime_is_stagnant":         0.0,
            "regime_is_transitional":     1.0,
        })

        result = pd.concat([df, regime_df], axis=1)
        logger.info("[MarketProfiler] Added %d regime feature columns.", len(regime_df.columns))
        return result

    # ── Analytics (OpponentDatabase analytics analog) ─────────────────────────

    def dominant_regime(self) -> Optional[str]:
        """Return the regime that appeared most across eras."""
        if not self._profiles:
            return None
        regimes = [p.classify_regime() for p in self._profiles.values()]
        return max(set(regimes), key=regimes.count)

    def most_extreme_era(self) -> Optional[str]:
        """Return era_id with highest trend_strength (most LAG/TRENDING)."""
        if not self._profiles:
            return None
        return max(self._profiles.values(), key=lambda p: p.trend_strength).era_id

    def stagnant_eras(self, threshold: float = 0.48) -> List[str]:
        """Return list of era_ids with participation_rate below threshold (NIT/STAGNANT eras)."""
        return [era_id for era_id, p in self._profiles.items()
                if p.participation_rate < threshold]

    def print_summary(self) -> None:
        """Print regime summary for all eras."""
        counts: Dict[str, int] = {}
        for p in self._profiles.values():
            r = p.classify_regime()
            counts[r] = counts.get(r, 0) + 1

        print("\n=== Market Regime Summary ===")
        for regime, count in sorted(counts.items(), key=lambda x: -x[1]):
            pct = count / max(len(self._profiles), 1)
            print(f"  {regime:<15} {count:>4} eras  ({pct:.0%})")
        print(f"  Dominant: {self.dominant_regime()}")
        print(f"  Most extreme era: {self.most_extreme_era()}")
        print()

        for p in list(self._profiles.values())[:5]:
            print(f"  {p}")


# ── Quick Test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    print("=== Market Regime Classifier -- Self Test ===")

    # Simulate a small NumerAI-style DataFrame with 3 eras
    np.random.seed(42)
    n_rows = 300
    n_feats = 10
    feat_cols = [f"feature_{i:03d}" for i in range(n_feats)]

    # Era 0: trending (high features skewed upward)
    df_trend  = pd.DataFrame(np.random.normal(0.7, 0.15, (n_rows, n_feats)), columns=feat_cols)
    df_trend["era"] = "era_0001"

    # Era 1: reverting (high vol, broad cross-section)
    df_revert = pd.DataFrame(np.random.normal(0.5, 0.35, (n_rows, n_feats)), columns=feat_cols)
    df_revert["era"] = "era_0002"

    # Era 2: stagnant (low participation, narrow distribution)
    df_stag   = pd.DataFrame(np.random.normal(0.45, 0.05, (n_rows, n_feats)), columns=feat_cols)
    df_stag["era"] = "era_0003"

    df = pd.concat([df_trend, df_revert, df_stag], ignore_index=True)
    profiler = MarketProfiler(feature_cols=feat_cols)
    result = profiler.get_regime_feature_matrix(df, era_col="era")

    assert len([c for c in result.columns if c.startswith("regime_")]) >= 11, "Expected >= 11 regime_ columns"
    assert result["regime_confidence"].max() > 0, "Confidence should be non-zero"
    assert result["regime_trend_strength"].std() > 0, "Trend strength should vary across eras"

    profiler.print_summary()
    print(f"Regime columns: {[c for c in result.columns if c.startswith('regime_')]}")
    print("[PASS] All self-tests passed.")
