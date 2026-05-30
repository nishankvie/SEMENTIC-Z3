"""
LLM Persona Bot — generates realistic behavioral signals and narratives.
The LLM narrates and reacts; Z3 decides. This module is the LLM layer only.

Falls back to deterministic signals from state_machine.py when:
- No API key configured
- LLM call fails
- use_llm=False (fast bulk simulation mode)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from typing import Any, Dict, Optional
from data.funnel_steps import PersonaVariant, JourneyState, InterventionRecord
from engine.state_machine import (
    generate_step3_signals,
    generate_step4_signals,
    generate_step7_signals,
)
from config import ANTHROPIC_API_KEY, MODEL

logger = logging.getLogger(__name__)

_SEGMENT_PROFILES = {
    "franz": {
        "name": "Franz Huber",
        "archetype": "Online-first, handles everything digitally. Price-performance is everything. Hates friction and advisor suggestions.",
        "quote": "I want to handle everything online — fast, simple, and transparent.",
    },
    "judith": {
        "name": "Judith Berger",
        "archetype": "Researches online, commits with advisor trust. Mid-management, Vienna. Comfortable with digital but wants human confirmation for important decisions.",
        "quote": "I prefer to research things myself online — but for important decisions I want someone I can trust.",
    },
    "peter": {
        "name": "Peter Wagner",
        "archetype": "Service-oriented, doesn't want to manage things alone. Prefers simple guidance over self-service. Overwhelmed by too many choices.",
        "quote": "I don't want to deal with this — just tell me what I need.",
    },
}


def _build_system_prompt(variant: PersonaVariant) -> str:
    profile = _SEGMENT_PROFILES[variant.segment]
    return f"""You are {profile['name']}, going through UNIQA's health insurance online calculator.

Your archetype: {profile['archetype']}
Your typical quote: "{profile['quote']}"

Your behavioral profile (all [0.0–1.0]):
- price_tolerance: {variant.price_tolerance:.2f}  (0=always picks cheapest, 1=price insensitive)
- digital_confidence: {variant.digital_confidence:.2f}  (0=never online, 1=always online)
- urgency: {variant.urgency:.2f}  (0=browsing, 1=real purchase intent)
- advisor_dependency: {variant.advisor_dependency:.2f}  (0=no advisor needed, 1=needs advisor for everything)
- complexity_tolerance: {variant.complexity_tolerance:.2f}  (0=overwhelmed by choices, 1=reads everything)

IMPORTANT: Behave consistently with your numbers. Be realistic — do not convert just because someone showed you a message.
A price_tolerance < 0.3 means you genuinely hesitate at prices and look for cheaper options.
An urgency < 0.2 means you're just browsing — no real purchase intent today.
An advisor_dependency > 0.7 means you feel uncomfortable completing this without talking to someone first."""


def _build_step_prompt(
    state: JourneyState,
    session_context: Dict,
    intervention: Optional[InterventionRecord],
) -> str:
    step_descriptions = {
        JourneyState.PERSONAL_DATA: "Step 3: You are asked for your date of birth and social insurance number to calculate your personal premium.",
        JourneyState.TARIFF_SELECTION: "Step 4: You see a comparison table with 4 tariffs: Start (€38.74/mo), Optimal (€68.14/mo), Opt.Plus (€96.66/mo, advisory required), Premium (€140.16/mo, advisory required).",
        JourneyState.FINAL_PRICE: f"Step 7: Your finalized premium is shown. The initial estimate was €{session_context.get('provisional_price', 0):.2f}/month. Your final personalized price is shown based on your health questionnaire answers.",
    }

    step_desc = step_descriptions.get(state, f"Step: {state.value}")
    intervention_text = ""
    if intervention and not intervention.suppressed:
        intervention_text = f'\nThe Coach just showed you this message: "{intervention.message}"\n'

    return f"""{step_desc}
{intervention_text}
Your session so far: {json.dumps(session_context, indent=2)}

Respond ONLY with valid JSON in this exact format:
{{
  "dwell_time_seconds": <number>,
  "action": "<continue|abandon|click_opt_plus|click_back|open_external_tab>",
  "internal_thought": "<what you are thinking right now, 1 sentence, honest>",
  "signal_details": {{
    "tariff_selected": "<start|optimal|opt_plus|premium|null>",
    "cancel_hovers": <integer 0-5>,
    "back_navigation": <true|false>,
    "tab_opened_external": <true|false>,
    "term_hover": <true|false>
  }}
}}"""


def _call_llm(system: str, user: str) -> Optional[Dict]:
    """Call the Anthropic API. Returns parsed JSON or None on failure."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text.strip()
        # Extract JSON from potential markdown code blocks
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        logger.debug(f"LLM call failed: {e}")
        return None


def _llm_to_signals(llm_output: Dict, state: JourneyState) -> Dict[str, Any]:
    """Convert LLM persona response to signal dict matching our schema."""
    details = llm_output.get("signal_details", {})
    action = llm_output.get("action", "continue")
    dwell = float(llm_output.get("dwell_time_seconds", 20))

    if state == JourneyState.PERSONAL_DATA:
        return {
            "dwell_time_seconds": dwell,
            "back_navigation": action == "click_back" or details.get("back_navigation", False),
            "completed": action not in ("abandon", "click_back"),
        }

    if state == JourneyState.TARIFF_SELECTION:
        tariff = details.get("tariff_selected")
        if action == "abandon":
            tariff = None
        return {
            "dwell_time_seconds": dwell,
            "tariff_hovers": int(details.get("cancel_hovers", 1)),
            "opt_plus_clicked": action == "click_opt_plus" or tariff in ("opt_plus", "premium"),
            "back_nav_after_opt_plus": action == "click_back",
            "tab_opened_external": action == "open_external_tab" or details.get("tab_opened_external", False),
            "term_hover": details.get("term_hover", False),
            "selected_tariff": tariff if tariff in ("start", "optimal", None) else None,
            "cancel_hover": int(details.get("cancel_hovers", 0)) > 2,
        }

    if state == JourneyState.FINAL_PRICE:
        return {
            "dwell_time_seconds": dwell,
            "cancel_hovers": int(details.get("cancel_hovers", 0)),
            "back_to_tariff_step": details.get("back_navigation", False),
            "price_delta_shown": 0,   # Filled in by state machine
            "session_duration_total": dwell + 120,
        }

    return {}


def generate_signals_llm(
    variant: PersonaVariant,
    state: JourneyState,
    session_context: Dict,
    intervention: Optional[InterventionRecord] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Generate behavioral signals for the given state.
    Tries LLM first; falls back to deterministic generation.
    """
    if use_llm and ANTHROPIC_API_KEY:
        system = _build_system_prompt(variant)
        user = _build_step_prompt(state, session_context, intervention)
        llm_output = _call_llm(system, user)
        if llm_output:
            return _llm_to_signals(llm_output, state)

    # Deterministic fallback
    if state == JourneyState.PERSONAL_DATA:
        return generate_step3_signals(variant, intervention)
    if state == JourneyState.TARIFF_SELECTION:
        return generate_step4_signals(variant, intervention)
    if state == JourneyState.FINAL_PRICE:
        provisional = session_context.get("provisional_price", 38.74)
        return generate_step7_signals(variant, provisional, intervention)
    return {}


def get_persona_narrative(variant: PersonaVariant, outcome: str, hypothesis: str) -> str:
    """Generate a short narrative explaining why this persona had this outcome."""
    narratives = {
        ("franz", "converted", "H3"): (
            "Franz was anchored to the initial price. The Coach's transparent price-delta "
            "breakdown restored trust — he understood the surcharge and completed online."
        ),
        ("franz", "abandoned", "H3"): (
            "The price jump at Step 7 broke Franz's trust. He felt misled by the initial "
            "estimate and closed the tab. No intervention reached him in time."
        ),
        ("franz", "converted", "COLD_FEET"): (
            "Franz moved through the funnel quickly and converted — no hesitation detected. "
            "Coach correctly stayed silent."
        ),
        ("judith", "advisor_routed", "NONE"): (
            "Judith was researching and never intended to complete online. "
            "She requested an advisor consultation — the ideal outcome for her segment."
        ),
        ("judith", "converted", "H1"): (
            "The market comparison and save-progress feature gave Judith the confidence "
            "to complete Optimal online without advisor validation."
        ),
        ("peter", "advisor_routed", "NONE"): (
            "Peter was overwhelmed by the tariff table. The Coach detected early complexity "
            "signals and offered a callback — Peter scheduled one immediately."
        ),
        ("peter", "converted", "H3"): (
            "Despite initial hesitation at the final price, the callback offer was declined "
            "and Peter completed Start online — driven by hospitalization urgency."
        ),
    }
    key = (variant.segment, outcome, hypothesis)
    if key in narratives:
        return narratives[key]
    return (
        f"{variant.sub_type.replace('_', ' ').title()} ({outcome.replace('_', ' ')}) — "
        f"hypothesis {hypothesis} was {'active' if hypothesis != 'NONE' else 'not detected'}."
    )
