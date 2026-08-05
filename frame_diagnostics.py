"""
Per-frame diagnostic: for a given frame, show all six TPR component scores
(pressure, compactness, POS, LPC, anticipation, synchronization) side by
side, not just the composite TPR number -- so it's visible at a glance
which specific dimension(s) drove a low or high moment. See
docs/HSV_INSIGHT_ROADMAP.md for why this matters on its own and as a
building block for per-dimension mistake attribution.

The checkpoint already has all six raw component columns per frame --
this is a query/presentation layer, not new computation. Checkpoints
sample every 25 frames (1Hz, confirmed against a real file), while
breakdown-event frames are full 25Hz precision, so each breakdown frame
is matched to its nearest checkpoint sample, not an exact hit.

Usage:
    python frame_diagnostics.py --dfl_match_id DFL-MAT-J041UB --frame 55596 --team 0
    python frame_diagnostics.py --breakdown_events  # diagnose every saved breakdown event
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

DIMENSIONS = ["pressure", "compactness", "lpc", "pos", "anticipation", "synchronization"]


def nearest_checkpoint_row(checkpoint: pd.DataFrame, team: int, frame: int) -> pd.Series:
    """The checkpoint row (this team, nearest sampled frame) to a given
    full-resolution frame number."""
    team_rows = checkpoint[checkpoint["team_id"] == team]
    idx = (team_rows["frame"] - frame).abs().idxmin()
    return team_rows.loc[idx]


def build_baseline_percentile_lookup() -> dict:
    """Sorted baseline values per dimension, from every is_defending==1
    frame across all 34 matches -- lets a raw value be converted to a
    percentile within its OWN distribution instead of compared directly
    against other dimensions' raw values.

    Comparing raw values across dimensions (plain argmin) is invalid:
    Pressure and Anticipation are near-zero for most of ordinary play
    (median 0.0 across all defending frames) while Synchronization has a
    mathematical floor around 0.27 by construction (max(n_fwd,n_bwd)/N
    can't go below 0.5). A raw-value argmin picks whichever dimension has
    the lowest natural floor almost regardless of context -- confirmed
    empirically: Pressure/Anticipation "weakest" 71%/18% of the time on
    real breakdown frames vs. 69.5%/24.2% on random non-breakdown frames,
    i.e. no real signal, just scale artifacts. Percentile rank fixes this
    by asking "how unusual is this value for THIS dimension," which is
    comparable across dimensions."""
    frames = []
    for path in sorted(CHECKPOINT_DIR.glob("match_*.csv")):
        cp = pd.read_csv(path, usecols=["is_defending", *DIMENSIONS])
        frames.append(cp[cp["is_defending"] == 1][DIMENSIONS].dropna())
    baseline = pd.concat(frames, ignore_index=True)
    return {dim: np.sort(baseline[dim].to_numpy()) for dim in DIMENSIONS}


def percentile_rank(sorted_baseline: np.ndarray, value: float) -> float:
    return float(np.searchsorted(sorted_baseline, value, side="left")) / len(sorted_baseline)


def _tie_aware_weakest(percentiles: dict) -> dict:
    """Percentile rank alone isn't enough to pick a single weakest
    dimension: Pressure, Anticipation, and POS all genuinely hit an exact
    floor of 0.0 often enough (a real, not approximate, tie), and
    `sorted(...)[0]` on tied keys silently returns whichever dimension
    happens to come first in DIMENSIONS -- confirmed this was happening
    on real data: 175 of 504 events initially labeled "pressure" were
    ALSO exactly tied with anticipation at percentile 0.0 (19 were a
    3-way tie with POS too), and every single one was resolved in
    Pressure's favor purely because it's listed first, not because it
    was actually weaker. Ties are real (e.g. "zero defenders within 15m
    AND zero within 5m" is one genuine total-breakdown moment expressed
    identically by two formulas), so this returns every tied dimension
    rather than picking one arbitrarily."""
    min_pct = min(percentiles.values())
    tied = sorted(dim for dim, pct in percentiles.items() if pct == min_pct)
    return {"tied_dimensions": tied, "n_tied": len(tied), "weakest_dimension": tied[0], "weakest_percentile": min_pct}


def diagnose_frame(dfl_match_id: str, team: int, frame: int, baseline: dict = None) -> dict:
    checkpoint = pd.read_csv(CHECKPOINT_DIR / f"match_{dfl_match_id}.csv")
    row = nearest_checkpoint_row(checkpoint, team, frame)
    scores = {dim: row[dim] for dim in DIMENSIONS}
    if baseline is None:
        baseline = build_baseline_percentile_lookup()
    percentiles = {dim: percentile_rank(baseline[dim], scores[dim]) for dim in DIMENSIONS}
    weakest = _tie_aware_weakest(percentiles)
    strongest_dim = max(percentiles.items(), key=lambda kv: kv[1])
    return {
        "match_id": dfl_match_id,
        "team": team,
        "requested_frame": frame,
        "checkpoint_frame": int(row["frame"]),
        "TPR": row["TPR"],
        **scores,
        **{f"{dim}_percentile": percentiles[dim] for dim in DIMENSIONS},
        "weakest_dimension": weakest["weakest_dimension"],
        "tied_dimensions": ",".join(weakest["tied_dimensions"]),
        "n_tied": weakest["n_tied"],
        "weakest_percentile": weakest["weakest_percentile"],
        "strongest_dimension": strongest_dim[0],
        "strongest_value": strongest_dim[1],
    }


def diagnose_all_breakdown_events() -> pd.DataFrame:
    """Attaches a 6-dimension diagnosis to every saved breakdown event
    across all 34 matches -- one checkpoint load per match, not per
    event, since re-reading the same file per row would be wasteful.

    Weakest dimension is determined by percentile rank against the full
    baseline distribution of that dimension (see
    build_baseline_percentile_lookup), not raw value -- see its
    docstring for why raw-value comparison is wrong. Ties at the exact
    floor are recorded explicitly in `tied_dimensions` rather than
    silently broken by list order -- see _tie_aware_weakest."""
    baseline = build_baseline_percentile_lookup()
    events = pd.read_csv(RESULTS_DIR / "pressing_breakdown_events.csv")
    rows = []
    for match_id, match_events in events.groupby("match_id"):
        checkpoint = pd.read_csv(CHECKPOINT_DIR / f"match_{match_id}.csv")
        for _, e in match_events.iterrows():
            row = nearest_checkpoint_row(checkpoint, e["team"], e["frame"])
            scores = {dim: row[dim] for dim in DIMENSIONS}
            percentiles = {dim: percentile_rank(baseline[dim], scores[dim]) for dim in DIMENSIONS}
            weakest = _tie_aware_weakest(percentiles)
            rows.append(
                {
                    "match_id": match_id,
                    "team": e["team"],
                    "frame": e["frame"],
                    "object_id": e["object_id"],
                    "player_name": e["player_name"],
                    "TPR": row["TPR"],
                    **scores,
                    **{f"{dim}_percentile": percentiles[dim] for dim in DIMENSIONS},
                    "weakest_dimension": weakest["weakest_dimension"],
                    "tied_dimensions": ",".join(weakest["tied_dimensions"]),
                    "n_tied": weakest["n_tied"],
                }
            )
    return pd.DataFrame(rows)


def fractional_weakest_share(diagnosed: pd.DataFrame) -> pd.Series:
    """The honest version of `weakest_dimension.value_counts()`: an event
    with a K-way tie contributes 1/K credit to each tied dimension
    instead of all 1 credit to whichever is first alphabetically, so
    ties don't silently inflate one dimension's share.

    NOTE: even this fractional-credit version turned out to still be
    confounded (see dimension_breakdown_signal's docstring below) --
    kept only as a documented, superseded step in the debugging history,
    not the method to draw conclusions from. Use
    dimension_breakdown_signal for the real answer."""
    credit = {dim: 0.0 for dim in DIMENSIONS}
    for tied_str, n_tied in zip(diagnosed["tied_dimensions"], diagnosed["n_tied"]):
        for dim in tied_str.split(","):
            credit[dim] += 1.0 / n_tied
    return pd.Series(credit).sort_values(ascending=False)


RANDOM_SAMPLE_SEED = 42
RANDOM_SAMPLE_SIZE = 20000


def sample_random_defending_frames(n: int = RANDOM_SAMPLE_SIZE, seed: int = RANDOM_SAMPLE_SEED) -> pd.DataFrame:
    """A large, reproducible random sample of ordinary is_defending==1
    frames across all 34 matches -- the control group for checking
    whether a dimension is genuinely elevated at real breakdown moments,
    or just reflects its own base rate in completely ordinary defending
    (fixed seed so this doesn't silently drift between runs)."""
    frames = []
    for path in sorted(CHECKPOINT_DIR.glob("match_*.csv")):
        cp = pd.read_csv(path)
        frames.append(cp[cp["is_defending"] == 1])
    all_defending = pd.concat(frames, ignore_index=True)
    return all_defending.sample(n=n, random_state=seed)


def dimension_breakdown_signal(diagnosed: pd.DataFrame = None, baseline: dict = None) -> pd.DataFrame:
    """The real test of "does dimension X drive breakdowns": is X's value
    at real breakdown moments significantly more extreme (lower
    percentile) than at a large random sample of ordinary defending
    moments -- controlling for X's own base-rate behavior, not just
    whether X wins an argmin comparison against the other five.

    Replaces fractional_weakest_share as the authoritative method. That
    approach (and the raw-value version before it) both turned out to
    still be confounded, checked directly against real data:
      1. Base-rate: a dimension that floors at its minimum in most of
         ORDINARY play (Pressure: 58.7% of all defending frames exactly
         0.0; Anticipation: 63.5%) wins the argmin comparison often
         regardless of context, not because it's specifically implicated
         in breakdowns.
      2. Relative-competition: argmin is a competition between the six
         dimensions in that one frame, not a measure of whether X itself
         got worse. Breakdown moments (shot/dribble-past situations)
         mechanically draw more defenders toward the danger area, so
         Pressure/Anticipation/POS/Compactness all measure LESS extreme
         (better) at real breakdowns than in random play -- confirmed
         directly. A dimension can "win" the argmin more often at
         breakdowns purely because its competitors improved, not because
         it got worse itself -- confirmed this is exactly what happened
         to LPC (2.57x argmin lift, but its own percentile distribution
         barely moved between breakdown and random, 0.485 vs 0.490).

    The deconfounded test: compare each dimension's OWN percentile
    distribution at breakdown moments against its OWN distribution at a
    large random sample of ordinary defending moments (one-sided
    Mann-Whitney U: is breakdown stochastically lower/worse). Run on
    real data, only Synchronization showed a real, statistically
    significant, negative effect; every other dimension was either not
    significant or moved in the opposite (better-at-breakdown) direction."""
    if diagnosed is None:
        diagnosed = pd.read_csv(RESULTS_DIR / "breakdown_events_dimension_diagnosis.csv")
    if baseline is None:
        baseline = build_baseline_percentile_lookup()

    random_sample = sample_random_defending_frames()
    random_pct = {dim: np.array([percentile_rank(baseline[dim], v) for v in random_sample[dim]]) for dim in DIMENSIONS}

    rows = []
    for dim in DIMENSIONS:
        bd_pct = diagnosed[f"{dim}_percentile"].to_numpy()
        rand_pct = random_pct[dim]
        stat, p_value = mannwhitneyu(bd_pct, rand_pct, alternative="less")
        rows.append(
            {
                "dimension": dim,
                "mean_percentile_random": rand_pct.mean(),
                "mean_percentile_breakdown": bd_pct.mean(),
                "shift": bd_pct.mean() - rand_pct.mean(),
                "p_value_worse_at_breakdown": p_value,
                "significant_and_worse": bool(p_value < 0.01 and bd_pct.mean() < rand_pct.mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("shift")


def main():
    parser = argparse.ArgumentParser(description="Per-frame TPR dimension diagnostic")
    parser.add_argument("--dfl_match_id", type=str)
    parser.add_argument("--frame", type=int)
    parser.add_argument("--team", type=int, choices=[0, 1])
    parser.add_argument("--breakdown_events", action="store_true", help="Diagnose every saved breakdown event instead of one frame")
    parser.add_argument("--dimension_signal", action="store_true", help="Statistically test which dimensions are really elevated at breakdown moments vs. a random baseline")
    args = parser.parse_args()

    if args.dimension_signal:
        signal = dimension_breakdown_signal()
        out_path = RESULTS_DIR / "dimension_breakdown_signal.csv"
        signal.to_csv(out_path, index=False)
        print(f"Saved -> {out_path}\n")
        print(signal.to_string(index=False))
    elif args.breakdown_events:
        diagnosed = diagnose_all_breakdown_events()
        out_path = RESULTS_DIR / "breakdown_events_dimension_diagnosis.csv"
        diagnosed.to_csv(out_path, index=False)
        print(f"Saved {len(diagnosed)} diagnosed breakdown events -> {out_path}\n")
        print(f"Events with an exact tie at the floor: {(diagnosed['n_tied'] > 1).sum()} of {len(diagnosed)}")
        print("\nNaive count (first-alphabetically wins every tie -- biased, kept for comparison only):")
        print(diagnosed["weakest_dimension"].value_counts())
        print("\nFractional-credit count (ties split evenly -- superseded, kept for comparison only):")
        print(fractional_weakest_share(diagnosed).round(1))
    else:
        result = diagnose_frame(args.dfl_match_id, args.team, args.frame)
        for k, v in result.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
