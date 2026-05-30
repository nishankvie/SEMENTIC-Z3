"""
Intervention Engine — bridges Z3 hypothesis output to the intervention bank.
Z3 decides. This engine executes the decision.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.funnel_steps import (
    JourneySession, JourneyState, HypothesisResult, InterventionRecord,
)
from data.intervention_bank import get_intervention


def decide_and_record(
    session: JourneySession,
    hypothesis_result: HypothesisResult,
    step: JourneyState,
    with_coach: bool = True,
) -> InterventionRecord | None:
    """
    Given Z3 hypothesis output, fire or suppress an intervention.
    Returns the InterventionRecord if fired, None if suppressed or no coach.
    """
    step_str = step.value
    segment = session.variant.segment
    hypothesis = hypothesis_result.hypothesis

    # Log the hypothesis evaluation
    session.hypothesis_log.append({
        "step": step_str,
        "hypothesis": hypothesis,
        "is_sat": hypothesis_result.is_sat,
        "reason": hypothesis_result.reason,
        "signals_used": hypothesis_result.signals_used,
        "intervention_warranted": hypothesis_result.intervention_warranted,
    })

    # No coach mode → never intervene
    if not with_coach:
        return None

    # Cold Feet or NONE → suppress (formally proven correct)
    if hypothesis in ("COLD_FEET", "NONE") or not hypothesis_result.intervention_warranted:
        record = InterventionRecord(
            step=step_str,
            hypothesis=hypothesis,
            segment=segment,
            sub_type=session.variant.sub_type,
            type="suppressed",
            message="",
            action="",
            suppressed=True,
            suppression_reason=hypothesis_result.reason,
        )
        session.interventions_suppressed.append(record)
        return None

    # Fetch intervention from bank
    intervention = get_intervention(segment, hypothesis, step_str)
    if intervention is None:
        # No matching intervention in bank for this combination
        record = InterventionRecord(
            step=step_str,
            hypothesis=hypothesis,
            segment=segment,
            sub_type=session.variant.sub_type,
            type="no_match",
            message="",
            action="",
            suppressed=True,
            suppression_reason=f"No intervention in bank for ({segment}, {hypothesis}, {step_str})",
        )
        session.interventions_suppressed.append(record)
        return None

    # Fire the intervention
    # Format message with session-specific values
    message = _format_message(intervention["message"], session, hypothesis_result)

    record = InterventionRecord(
        step=step_str,
        hypothesis=hypothesis,
        segment=segment,
        sub_type=session.variant.sub_type,
        type=intervention["type"],
        message=message,
        action=intervention["action"],
        suppressed=False,
    )
    session.interventions_fired.append(record)
    return record


def _format_message(template: str, session: JourneySession, hyp: HypothesisResult) -> str:
    """Fill in template placeholders with real session values."""
    price_delta = hyp.signals_used.get("price_delta", 0) or hyp.signals_used.get("price_delta_shown", 0)
    provisional = session.provisional_price
    final = session.final_price if session.final_price > 0 else provisional + price_delta

    try:
        return template.format(
            provisional=f"{provisional:.2f}",
            final=f"{final:.2f}",
            delta=f"{price_delta:.2f}",
            optimal_delta="29.40",
        )
    except (KeyError, ValueError):
        return template


def run_hypothesis_step(
    session: JourneySession,
    state: JourneyState,
    signals: dict,
    step4_signals: dict | None,
    with_coach: bool,
) -> InterventionRecord | None:
    """
    Orchestrate Z3 hypothesis discrimination for a given step.
    Returns an intervention record if an intervention was fired, else None.
    """
    from engine.z3_hypothesis_engine import (
        discriminate_at_personal_data,
        discriminate_at_tariff_selection,
        discriminate_at_final_price,
    )

    if state == JourneyState.PERSONAL_DATA:
        hyp_result = discriminate_at_personal_data(signals)
    elif state == JourneyState.TARIFF_SELECTION:
        hyp_result = discriminate_at_tariff_selection(signals)
    elif state == JourneyState.FINAL_PRICE:
        prior_step4 = step4_signals or {}
        hyp_result = discriminate_at_final_price(prior_step4, signals)
    else:
        return None

    return decide_and_record(session, hyp_result, state, with_coach=with_coach)
