"""
7-state journey simulator with deterministic signal generation.
The LLM persona bot (persona_bot.py) can override these signals when available,
but the deterministic fallback is used for fast bulk simulation.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
from typing import Optional, Dict, Any
from data.funnel_steps import (
    JourneyState, JourneySession, PersonaVariant, ADVISOR_TARIFFS,
)
from config import PRICE_START, PRICE_OPTIMAL


def _rng(seed: int, step_hash: int) -> random.Random:
    return random.Random(seed * 31337 + step_hash)


# ── Signal generation (deterministic, variant-driven) ─────────────────────────

def generate_step3_signals(variant: PersonaVariant) -> Dict[str, Any]:
    """PERSONAL_DATA: social insurance number trust barrier."""
    r = _rng(variant.seed, hash("personal_data"))
    # Low digital confidence → more anxious about giving personal data
    base_dwell = 15 + (1 - variant.digital_confidence) * 60
    dwell = max(5, r.gauss(base_dwell, 10))
    # Low digital confidence + high advisor dependency = more back-navigation
    back_prob = (1 - variant.digital_confidence) * 0.25 + variant.advisor_dependency * 0.1
    back_nav = r.random() < back_prob
    # SSN abandonment: very low digital confidence
    abandon_prob = max(0, (1 - variant.digital_confidence) - 0.5) * 0.3
    completed = r.random() > abandon_prob
    return {
        "dwell_time_seconds": round(dwell, 1),
        "back_navigation": back_nav,
        "completed": completed,
    }


def generate_step4_signals(variant: PersonaVariant, intervention=None) -> Dict[str, Any]:
    """TARIFF_SELECTION: first price display — high-stakes decision point."""
    r = _rng(variant.seed, hash("tariff_selection"))

    # Dwell: low price_tolerance = longer dwell (price anxiety)
    # Low complexity tolerance = longer dwell (confused by table)
    price_anxiety = (1 - variant.price_tolerance) * 30
    complexity_stress = (1 - variant.complexity_tolerance) * 20
    base_dwell = 20 + price_anxiety + complexity_stress
    dwell = max(5, r.gauss(base_dwell, 12))

    # Hovers: low complexity_tolerance = more confused hovering
    base_hovers = 1 + int((1 - variant.complexity_tolerance) * 6)
    tariff_hovers = max(0, int(r.gauss(base_hovers, 1.5)))

    # High advisor_dependency → curious about Opt.Plus/Premium (advisor tariffs)
    opt_plus_prob = variant.advisor_dependency * 0.45
    opt_plus_clicked = r.random() < opt_plus_prob

    # If they clicked Opt.Plus and see "advisory required" — frustration back_nav
    back_nav_after_opt_plus = opt_plus_clicked and (r.random() < 0.75)

    # ROPO: low digital_confidence → opens tab to compare elsewhere
    ropo_prob = (1 - variant.digital_confidence) * 0.35 + (1 - variant.urgency) * 0.15
    tab_opened_external = r.random() < min(0.6, ropo_prob)

    # Term hover: low complexity_tolerance → hovers on unfamiliar terms
    term_hover = r.random() < (1 - variant.complexity_tolerance) * 0.4

    # Cancel hover: high price sensitivity → hesitates to proceed
    cancel_hover = r.random() < (1 - variant.price_tolerance) * 0.5

    # Tariff selection decision
    selected_tariff = _decide_tariff(variant, r, intervention, opt_plus_clicked)

    return {
        "dwell_time_seconds": round(dwell, 1),
        "tariff_hovers": tariff_hovers,
        "opt_plus_clicked": opt_plus_clicked,
        "back_nav_after_opt_plus": back_nav_after_opt_plus,
        "tab_opened_external": tab_opened_external,
        "term_hover": term_hover,
        "selected_tariff": selected_tariff,
        "cancel_hover": cancel_hover,
    }


def _decide_tariff(variant: PersonaVariant, r: random.Random, intervention, opt_plus_clicked: bool) -> Optional[str]:
    """Determine which tariff the user selects, if any."""
    # Base probability — calibrated for ~34% survive this step (matching 66% drop-off).
    # Constant base 0.30 ensures variants have reasonable floor before components.
    base_select_prob = 0.30 + (
        variant.digital_confidence * 0.10 +
        variant.urgency * 0.10 +
        variant.price_tolerance * 0.05 +
        (1 - variant.complexity_tolerance) * (-0.05)
    )
    base_select_prob = min(0.60, max(0.15, base_select_prob))

    # Intervention meaningfully boosts selection (key for coached uplift)
    if intervention:
        base_select_prob = min(0.75, base_select_prob + 0.30)

    if r.random() > base_select_prob:
        return None  # Abandoned at tariff selection

    # Advisory tariff clicked without redirect intervention → often abandon
    if opt_plus_clicked and not intervention:
        if r.random() < 0.5:
            return None
        return "optimal" if variant.price_tolerance > 0.4 else "start"

    optimal_prob = variant.price_tolerance * 0.6 + variant.urgency * 0.2
    return "optimal" if r.random() < optimal_prob else "start"


def generate_step7_signals(variant: PersonaVariant, provisional_price: float) -> Dict[str, Any]:
    """FINAL_PRICE: finalized premium after health assessment — highest drop-off."""
    r = _rng(variant.seed, hash("final_price"))

    # Risk surcharge: varies by variant (low health awareness → higher actual risk)
    # Price-sensitive franz gets hit hardest psychologically even with small delta
    surcharge_base = r.gauss(8.5, 5.0)
    surcharge_base = max(0.0, surcharge_base)
    final_price = provisional_price + surcharge_base
    price_delta = final_price - provisional_price

    # Dwell: low price_tolerance + large delta = long dwell
    price_shock = (1 - variant.price_tolerance) * price_delta * 2.5
    base_dwell = 15 + price_shock
    dwell = max(5, r.gauss(base_dwell, 8))

    # Cancel hovers: high price sensitivity + large delta
    cancel_base = (1 - variant.price_tolerance) * 4 * (price_delta / 15)
    cancel_hovers = max(0, int(r.gauss(cancel_base, 1)))

    # Back navigation: reconsidering tariff
    back_to_tariff = r.random() < 0.12

    return {
        "dwell_time_seconds": round(dwell, 1),
        "cancel_hovers": cancel_hovers,
        "back_to_tariff_step": back_to_tariff,
        "price_delta_shown": round(price_delta, 2),
        "final_price": round(final_price, 2),
        "session_duration_total": round(r.gauss(180, 40), 1),
    }


# ── Abandonment decision ───────────────────────────────────────────────────────

def _abandons_at_final_price(variant: PersonaVariant, signals: Dict, intervention) -> bool:
    """Returns True if the user abandons at the final price step.
    Calibrated for ~78% raw drop-off at this step (matching personas.json baseline).
    """
    r = _rng(variant.seed, hash("final_price_abandon"))
    price_delta = signals.get("price_delta_shown", 0)
    cancel_hovers = signals.get("cancel_hovers", 0)

    # Base abandon probability — calibrated for ~78% raw drop-off at final price.
    # Components intentionally moderate so the cap (0.88) is only hit for worst cases.
    abandon_prob = (
        0.43 +                                      # calibrated base for ~78% drop-off
        (1 - variant.price_tolerance) * 0.18 +     # price sensitivity (max +0.18)
        min(price_delta / 22.0, 0.14) +             # delta shock (max +0.14)
        min(cancel_hovers / 4.0, 0.07) +            # cancel signal (max +0.07)
        (1 - variant.urgency) * 0.03               # low urgency nudge (max +0.03)
    )
    abandon_prob = min(0.92, max(0.30, abandon_prob))

    # Intervention reduces abandonment meaningfully for clear demo uplift
    if intervention:
        abandon_prob = max(0.10, abandon_prob - 0.38)

    return r.random() < abandon_prob


def _abandons_at_health_questions(variant: PersonaVariant) -> bool:
    """Health questions: minimal drop-off on in-scope path (2–5%)."""
    r = _rng(variant.seed, hash("health_abandon"))
    base_prob = (1 - variant.digital_confidence) * 0.08
    return r.random() < min(0.08, base_prob)


# ── State advancement ──────────────────────────────────────────────────────────

def advance_state(session: JourneySession, signals: Dict, intervention=None) -> JourneyState:
    """Given current state + signals, return the next state."""
    current = session.state
    variant = session.variant

    if current == JourneyState.COVERAGE_TYPE:
        coverage = session.selections.get("coverage_type", "doctor_visits")
        return JourneyState.ADVISOR_ROUTE if coverage == "hospital" else JourneyState.BENEFICIARY

    if current == JourneyState.BENEFICIARY:
        beneficiary = session.selections.get("beneficiary", "myself")
        return JourneyState.ADVISOR_ROUTE if beneficiary != "myself" else JourneyState.PERSONAL_DATA

    if current == JourneyState.PERSONAL_DATA:
        if not signals.get("completed", True):
            return JourneyState.ABANDONED
        return JourneyState.TARIFF_SELECTION

    if current == JourneyState.TARIFF_SELECTION:
        selected = signals.get("selected_tariff")
        if selected is None:
            return JourneyState.ABANDONED
        if selected in ADVISOR_TARIFFS:
            return JourneyState.ADVISOR_ROUTE
        session.selections["tariff"] = selected
        session.provisional_price = PRICE_OPTIMAL if selected == "optimal" else PRICE_START
        return JourneyState.HEALTH_QUESTIONS

    if current == JourneyState.HEALTH_QUESTIONS:
        if _abandons_at_health_questions(variant):
            return JourneyState.ABANDONED
        return JourneyState.FINAL_PRICE

    if current == JourneyState.FINAL_PRICE:
        if _abandons_at_final_price(variant, signals, intervention):
            return JourneyState.ABANDONED
        return JourneyState.CLOSING

    return JourneyState.ABANDONED  # Safety fallback


def generate_signals_for_state(
    session: JourneySession,
    intervention=None,
) -> Dict[str, Any]:
    """Generate behavioral signals for the current state.
    Pass intervention to regenerate signals after coaching is applied.
    """
    state = session.state
    variant = session.variant

    if state == JourneyState.PERSONAL_DATA:
        return generate_step3_signals(variant)

    if state == JourneyState.TARIFF_SELECTION:
        return generate_step4_signals(variant, intervention)

    if state == JourneyState.FINAL_PRICE:
        return generate_step7_signals(variant, session.provisional_price)

    # No signals needed for routing/terminal states
    return {}


def make_default_selections(variant: PersonaVariant) -> Dict[str, Any]:
    """Default selections for routing steps (most users follow in-scope path)."""
    r = _rng(variant.seed, hash("selections"))
    # Peter: higher chance of selecting hospital (genuinely needs that)
    if variant.segment == "peter":
        hospital_prob = 0.35
    elif variant.segment == "judith":
        hospital_prob = 0.15
    else:
        hospital_prob = 0.10

    coverage = "hospital" if r.random() < hospital_prob else "doctor_visits"

    # "Other persons" is rare for all segments
    beneficiary_prob = 0.08
    beneficiary = "other" if (r.random() < beneficiary_prob and coverage == "doctor_visits") else "myself"

    return {
        "coverage_type": coverage,
        "beneficiary": beneficiary,
    }
