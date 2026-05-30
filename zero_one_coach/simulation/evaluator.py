"""
Evaluator — computes all metrics from paired simulation results.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List, Dict, Any
from collections import defaultdict, Counter
from data.funnel_steps import JourneySession


def compute_metrics(
    sessions_baseline: List[JourneySession],
    sessions_coached: List[JourneySession],
) -> Dict[str, Any]:
    """Compute full metric set from paired simulation runs."""

    def _count_outcome(sessions, outcome):
        return sum(1 for s in sessions if s.outcome == outcome)

    def _rate(count, total):
        return count / total if total > 0 else 0.0

    n_base = len(sessions_baseline)
    n_coach = len(sessions_coached)

    # Conversion
    base_conv = _count_outcome(sessions_baseline, "converted")
    coach_conv = _count_outcome(sessions_coached, "converted")
    base_rate = _rate(base_conv, n_base)
    coach_rate = _rate(coach_conv, n_coach)
    uplift_abs = coach_rate - base_rate
    uplift_rel = (uplift_abs / base_rate) if base_rate > 0 else 0.0

    # Advisor route
    base_advisor = _count_outcome(sessions_baseline, "advisor_routed")
    coach_advisor = _count_outcome(sessions_coached, "advisor_routed")

    # Interventions
    all_fired = [i for s in sessions_coached for i in s.interventions_fired]
    all_suppressed = [i for s in sessions_coached for i in s.interventions_suppressed]
    total_interventions = len(all_fired) + len(all_suppressed)
    suppression_rate = _rate(len(all_suppressed), total_interventions)

    # Hypothesis distribution
    hypothesis_counts = Counter(
        hyp["hypothesis"]
        for s in sessions_coached
        for hyp in s.hypothesis_log
        if hyp["is_sat"]
    )

    # Per-sub-type breakdown
    all_sub_types = sorted(set(s.variant.sub_type for s in sessions_baseline))
    per_subtype = {}
    for sub_type in all_sub_types:
        base_sub = [s for s in sessions_baseline if s.variant.sub_type == sub_type]
        coach_sub = [s for s in sessions_coached if s.variant.sub_type == sub_type]
        if not base_sub:
            continue

        base_sub_conv = _count_outcome(base_sub, "converted")
        coach_sub_conv = _count_outcome(coach_sub, "converted") if coach_sub else 0
        base_sub_rate = _rate(base_sub_conv, len(base_sub))
        coach_sub_rate = _rate(coach_sub_conv, len(coach_sub)) if coach_sub else 0.0

        dom_hyp_counter = Counter(
            hyp["hypothesis"]
            for s in coach_sub
            for hyp in s.hypothesis_log
            if hyp["is_sat"]
        )
        dom_hyp = dom_hyp_counter.most_common(1)[0][0] if dom_hyp_counter else "NONE"

        sub_fired = sum(len(s.interventions_fired) for s in coach_sub)
        sub_suppressed = sum(len(s.interventions_suppressed) for s in coach_sub)

        per_subtype[sub_type] = {
            "segment": base_sub[0].variant.segment if base_sub else "?",
            "n_baseline": len(base_sub),
            "n_coached": len(coach_sub),
            "baseline_rate": round(base_sub_rate, 4),
            "coached_rate": round(coach_sub_rate, 4),
            "uplift_abs": round(coach_sub_rate - base_sub_rate, 4),
            "dominant_hypothesis": dom_hyp,
            "interventions_fired": sub_fired,
            "interventions_suppressed": sub_suppressed,
        }

    # Drop-off analysis
    drop_off = _compute_dropoff(sessions_baseline)

    return {
        "n_baseline": n_base,
        "n_coached": n_coach,
        "baseline_conversion_count": base_conv,
        "coached_conversion_count": coach_conv,
        "baseline_conversion_rate": round(base_rate, 4),
        "coached_conversion_rate": round(coach_rate, 4),
        "uplift_absolute": round(uplift_abs, 4),
        "uplift_relative": round(uplift_rel, 4),
        "baseline_advisor_routed": base_advisor,
        "coached_advisor_routed": coach_advisor,
        "interventions_fired": len(all_fired),
        "interventions_suppressed": len(all_suppressed),
        "total_intervention_opportunities": total_interventions,
        "suppression_rate": round(suppression_rate, 4),
        "hypothesis_distribution": dict(hypothesis_counts),
        "per_subtype": per_subtype,
        "drop_off": drop_off,
    }


def _compute_dropoff(sessions: List[JourneySession]) -> Dict[str, Any]:
    """Compute drop-off rates at each funnel step."""
    step_reached = defaultdict(int)
    step_exited = defaultdict(int)

    for s in sessions:
        for log_entry in s.step_log:
            step = log_entry["step"]
            step_reached[step] += 1
            next_state = log_entry.get("next_state", "")
            if next_state == "abandoned":
                step_exited[step] += 1

    result = {}
    for step, reached in step_reached.items():
        exited = step_exited.get(step, 0)
        result[step] = {
            "reached": reached,
            "exited": exited,
            "dropoff_rate": round(exited / reached, 4) if reached > 0 else 0.0,
        }
    return result


def format_summary(metrics: Dict[str, Any]) -> str:
    """Return a human-readable one-paragraph summary of key metrics."""
    b_rate = metrics["baseline_conversion_rate"]
    c_rate = metrics["coached_conversion_rate"]
    uplift = metrics["uplift_absolute"]
    rel = metrics["uplift_relative"]
    fired = metrics["interventions_fired"]
    suppressed = metrics["interventions_suppressed"]
    supp_rate = metrics["suppression_rate"]

    hyp_dist = metrics["hypothesis_distribution"]
    total_hyp = sum(hyp_dist.values()) or 1

    lines = [
        f"Baseline conversion: {b_rate:.1%} | Coached conversion: {c_rate:.1%} | "
        f"Uplift: +{uplift:.1%} absolute ({rel:.0%} relative)",
        f"Interventions: {fired} fired, {suppressed} suppressed ({supp_rate:.1%} suppression rate)",
        "Hypothesis distribution: " + ", ".join(
            f"{h}={v/total_hyp:.0%}" for h, v in sorted(hyp_dist.items(), key=lambda x: -x[1])
        ),
    ]
    return "\n".join(lines)
