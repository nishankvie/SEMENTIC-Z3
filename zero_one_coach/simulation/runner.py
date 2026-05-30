"""
Simulation Runner — runs N variants through the full 7-state journey.
Supports with_coach and without_coach modes for before/after comparison.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
from typing import List, Optional
from data.funnel_steps import JourneySession, JourneyState, PersonaVariant, TERMINAL_STATES
from engine.state_machine import (
    advance_state, generate_signals_for_state, make_default_selections,
)
from engine.z3_scope_prover import prove_coachable, run_startup_proofs
from engine.z3_hypothesis_engine import run_hypothesis_startup_proofs
from engine.intervention_engine import run_hypothesis_step
from engine.variant_generator import generate_population

logger = logging.getLogger(__name__)


def run_single_session(
    variant: PersonaVariant,
    with_coach: bool = True,
    verbose: bool = False,
    use_llm: bool = False,
) -> JourneySession:
    """
    Run one variant through the full journey.
    Returns a completed JourneySession with full logs.
    """
    session = JourneySession(variant=variant)
    session.selections = make_default_selections(variant)

    step4_signals: Optional[dict] = None  # Carried forward for H3 cross-step reasoning

    max_steps = 15  # Safety guard against infinite loops
    steps_taken = 0

    while session.state not in TERMINAL_STATES and steps_taken < max_steps:
        steps_taken += 1
        current_state = session.state
        if verbose:
            print(f"  [{variant.sub_type}] State: {current_state.value}")

        # ── Scope check at Steps 1 and 2 ──────────────────────────────────────
        if current_state in (JourneyState.COVERAGE_TYPE, JourneyState.BENEFICIARY):
            is_coachable, reason = prove_coachable(session.selections)
            if not is_coachable:
                session.state = JourneyState.ADVISOR_ROUTE
                session.outcome = "advisor_routed"
                session.step_log.append({
                    "step": current_state.value,
                    "event": "advisor_routed",
                    "reason": reason,
                })
                if verbose:
                    print(f"  [SCOPE] {reason}")
                break
            # Advance to next state (no signals needed for routing steps)
            session.state = advance_state(session, {})
            session.step_log.append({"step": current_state.value, "event": "passed_scope_check"})
            continue

        # ── Generate behavioral signals ────────────────────────────────────────
        signals = generate_signals_for_state(session)

        # ── Z3 hypothesis discrimination + intervention (at active steps) ─────
        intervention = None
        if current_state in (JourneyState.PERSONAL_DATA, JourneyState.TARIFF_SELECTION, JourneyState.FINAL_PRICE):
            # Scope check at TARIFF_SELECTION (Opt.Plus/Premium selected)
            if current_state == JourneyState.TARIFF_SELECTION:
                tariff_check_selections = dict(session.selections)
                tariff_check_selections["tariff"] = signals.get("selected_tariff", "start")
                is_coachable, reason = prove_coachable(tariff_check_selections)
                if not is_coachable and signals.get("selected_tariff") not in (None, "start", "optimal"):
                    session.state = JourneyState.ADVISOR_ROUTE
                    session.outcome = "advisor_routed"
                    session.step_log.append({
                        "step": current_state.value,
                        "event": "advisor_routed",
                        "reason": reason,
                    })
                    if verbose:
                        print(f"  [SCOPE] {reason}")
                    break

            # Run Z3 hypothesis discrimination
            intervention = run_hypothesis_step(
                session=session,
                state=current_state,
                signals=signals,
                step4_signals=step4_signals if current_state == JourneyState.FINAL_PRICE else None,
                with_coach=with_coach,
            )

            if verbose and session.hypothesis_log:
                last_hyp = session.hypothesis_log[-1]
                print(f"  [Z3]    {last_hyp['hypothesis']} — {last_hyp['reason'][:60]}")
                if intervention:
                    print(f"  [COACH] Fired: {intervention.type} → {intervention.action}")
                elif last_hyp['hypothesis'] in ('COLD_FEET', 'NONE'):
                    print(f"  [COACH] Silent (suppressed)")

            # Regenerate TARIFF_SELECTION signals with intervention applied.
            # This is the core coaching uplift mechanism at step 4: an H2/H1/H4
            # intervention changes the user's tariff selection decision.
            if intervention and current_state == JourneyState.TARIFF_SELECTION:
                signals = generate_signals_for_state(session, intervention=intervention)
                if verbose:
                    print(f"  [REGEN] Signals with intervention → "
                          f"tariff={signals.get('selected_tariff')}")

        # Carry step4 signals forward for H3 cross-step reasoning
        if current_state == JourneyState.TARIFF_SELECTION:
            step4_signals = signals
            # Also update final_price in session from step7 signals if available
            tariff = signals.get("selected_tariff")
            if tariff:
                session.selections["tariff"] = tariff

        if current_state == JourneyState.FINAL_PRICE:
            final_p = signals.get("final_price", 0)
            if final_p:
                session.final_price = final_p

        # Store signals
        session.signals[current_state.value] = signals

        # Advance state based on signals + intervention effect
        session.state = advance_state(session, signals, intervention)

        session.step_log.append({
            "step": current_state.value,
            "next_state": session.state.value,
            "signals_summary": {k: v for k, v in signals.items() if not isinstance(v, dict)},
        })

    # Set outcome
    if session.outcome is None:
        if session.state == JourneyState.CLOSING:
            session.outcome = "converted"
        elif session.state == JourneyState.ADVISOR_ROUTE:
            session.outcome = "advisor_routed"
        else:
            session.outcome = "abandoned"

    if verbose:
        print(f"  OUTCOME: {session.outcome}")

    return session


def run_simulation(
    variants: List[PersonaVariant],
    with_coach: bool = True,
    verbose: bool = False,
    use_llm: bool = False,
) -> List[JourneySession]:
    """Run all variants and return completed sessions."""
    sessions = []
    for i, variant in enumerate(variants):
        if verbose:
            print(f"\n[{i+1}/{len(variants)}] {variant.sub_type} (seed={variant.seed})")
        try:
            session = run_single_session(variant, with_coach=with_coach, verbose=verbose, use_llm=use_llm)
            sessions.append(session)
        except Exception as e:
            logger.error(f"Session failed for {variant.sub_type} seed={variant.seed}: {e}")
    return sessions


def run_paired_simulation(
    total_variants: int = 100,
    verbose: bool = False,
) -> tuple[List[JourneySession], List[JourneySession]]:
    """
    Run matched pairs: same variants with and without coach.
    Returns (sessions_without_coach, sessions_with_coach).
    """
    # Run startup proofs
    scope_proofs = run_startup_proofs()
    hyp_proofs = run_hypothesis_startup_proofs()
    all_proven = all(ok for ok, _ in scope_proofs.values()) and \
                 all(ok for ok, _ in hyp_proofs.values())
    if not all_proven:
        raise RuntimeError("Startup proofs failed — cannot run simulation with unproven invariants")

    variants = generate_population(total=total_variants)

    print(f"Running {len(variants)} variants WITHOUT coach...")
    sessions_baseline = run_simulation(variants, with_coach=False, verbose=verbose)

    print(f"Running {len(variants)} variants WITH coach...")
    sessions_coached = run_simulation(variants, with_coach=True, verbose=verbose)

    return sessions_baseline, sessions_coached


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="UNIQA Conversion Coach Simulation")
    parser.add_argument("--n", type=int, default=50, help="Number of variants to simulate")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--coach-only", action="store_true")
    args = parser.parse_args()

    print(f"Simulating {args.n} variants...")
    baseline, coached = run_paired_simulation(total_variants=args.n, verbose=args.verbose)

    b_conv = sum(1 for s in baseline if s.outcome == "converted")
    c_conv = sum(1 for s in coached if s.outcome == "converted")
    b_rate = b_conv / len(baseline) if baseline else 0
    c_rate = c_conv / len(coached) if coached else 0

    print(f"\nResults:")
    print(f"  Baseline conversion: {b_conv}/{len(baseline)} = {b_rate:.1%}")
    print(f"  Coached conversion:  {c_conv}/{len(coached)} = {c_rate:.1%}")
    print(f"  Uplift:              +{c_rate - b_rate:.1%} absolute ({(c_rate/b_rate - 1):.0%} relative)" if b_rate > 0 else "")

    fired = sum(len(s.interventions_fired) for s in coached)
    suppressed = sum(len(s.interventions_suppressed) for s in coached)
    total = fired + suppressed
    print(f"\n  Interventions fired:      {fired}")
    print(f"  Interventions suppressed: {suppressed}")
    print(f"  Suppression rate:         {suppressed/total:.1%}" if total > 0 else "")
