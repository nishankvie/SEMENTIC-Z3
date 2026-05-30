"""
All intervention messages, keyed by (segment, hypothesis, step).
Lookup order: exact match → (segment, "any", step) → ("any", hypothesis, step) → default.
All prices are real values from UNIQA tariff documents (age-27 reference).
"""

from config import (
    PRICE_START, PRICE_OPTIMAL, PRICE_OPT_PLUS,
    PRICE_START_OPTIMAL_DELTA_MONTHLY, PRICE_START_OPTIMAL_DELTA_DAILY,
    COVERAGE_START_ANNUAL, COVERAGE_OPTIMAL_ANNUAL,
)

# Lookup key: (segment, hypothesis, step)
# segment: "judith" | "franz" | "peter" | "any"
# hypothesis: "H1"–"H8" | "COLD_FEET" | "any"
# step: "personal_data" | "tariff_selection" | "final_price"

INTERVENTIONS: dict = {

    # ── H7: SSN Trust Barrier (PERSONAL_DATA) ────────────────────────────────
    ("any", "H7", "personal_data"): {
        "type": "trust_signal",
        "message": (
            "Your social insurance number is used only to calculate your personal premium. "
            "It is not stored after your session ends and is never shared with third parties. "
            "This is required by Austrian insurance regulation."
        ),
        "action": "show_inline_trust_badge",
    },

    # ── H2: Advisory Requirement Frustration (TARIFF_SELECTION) ──────────────
    ("any", "H2", "tariff_selection"): {
        "type": "scope_redirect",
        "message": (
            f"Opt. Plus requires a short advisory call — this is required by Austrian "
            f"insurance regulation for this coverage level. "
            f"Start (€{PRICE_START:.2f}/month, €{COVERAGE_START_ANNUAL:,}/year) and "
            f"Optimal (€{PRICE_OPTIMAL:.2f}/month, €{COVERAGE_OPTIMAL_ANNUAL:,}/year) are "
            f"available completely online right now. "
            f"After 3 years you can upgrade to Opt. Plus without a new health assessment."
        ),
        "action": "highlight_start_optimal",
    },

    # ── H8: Advisory Dead End (TARIFF_SELECTION) ─────────────────────────────
    ("any", "H8", "tariff_selection"): {
        "type": "scope_redirect",
        "message": (
            f"Opt. Plus and Premium require an advisor consultation — this is mandatory under "
            f"Austrian insurance law for these coverage levels. "
            f"Start (€{PRICE_START:.2f}/mo) and Optimal (€{PRICE_OPTIMAL:.2f}/mo) give you "
            f"quality private doctor coverage you can complete online in minutes. "
            f"You can upgrade later without a new health check."
        ),
        "action": "highlight_start_optimal_and_book_callback",
    },

    # ── H1: Price Shock at TARIFF_SELECTION ──────────────────────────────────
    ("franz", "H1", "tariff_selection"): {
        "type": "value_justification",
        "message": (
            f"Start at €{PRICE_START:.2f}/month covers your doctor and specialist visits, "
            f"medications and vaccinations — up to €{COVERAGE_START_ANNUAL:,}/year. "
            f"That's €{PRICE_START/30:.2f}/day. "
            f"For €{PRICE_START_OPTIMAL_DELTA_DAILY:.2f}/day more, Optimal doubles your annual "
            f"coverage to €{COVERAGE_OPTIMAL_ANNUAL:,} and adds therapies, medical aids, "
            f"and glasses. You can complete either online right now."
        ),
        "action": "show_per_day_breakdown",
    },

    ("judith", "H1", "tariff_selection"): {
        "type": "market_comparison",
        "message": (
            f"Optimal at €{PRICE_OPTIMAL:.2f}/month is €{PRICE_OPTIMAL/30:.2f}/day — "
            f"comparable private doctor tariffs in Austria range considerably higher. "
            f"Your progress is saved if you'd like to return later or speak with an advisor first. "
            f"After 3 years on Optimal you can upgrade without a new health assessment."
        ),
        "action": "show_save_progress_and_advisor_cta",
    },

    ("peter", "H1", "tariff_selection"): {
        "type": "service_handoff",
        "message": (
            f"Based on your situation, Start (€{PRICE_START:.2f}/month) is the most popular "
            f"choice for people in your position. "
            f"A UNIQA advisor can confirm this is right for you in under 10 minutes — "
            f"no obligation. Book a free callback now."
        ),
        "action": "show_callback_booking",
    },

    # ── H4: Cognitive Overload (TARIFF_SELECTION) ─────────────────────────────
    ("any", "H4", "tariff_selection"): {
        "type": "simplification",
        "message": (
            f"Here's the short version: Start (€{PRICE_START:.2f}/mo) covers doctor visits, "
            f"medications, and vaccinations. Optimal (€{PRICE_OPTIMAL:.2f}/mo) adds therapies "
            f"and glasses. Both are available online with no advisor needed. "
            f"Most people in your situation start with Optimal. "
            f"You can always upgrade later without a new health check."
        ),
        "action": "show_simplified_comparison_two_tariffs_only",
    },

    # ── H5: Technical Term Confusion (TARIFF_SELECTION) ──────────────────────
    ("any", "H5", "tariff_selection"): {
        "type": "term_explanation",
        "message": (
            "'Refractive eye surgery' means laser eye correction (e.g. LASIK). "
            "Optimal covers this up to €280 per 2 calendar years. "
            "'Deductible' means the portion you pay yourself before insurance kicks in — "
            "UNIQA's online tariffs have no deductible. "
            "Any questions? Our advisor can explain in 10 minutes."
        ),
        "action": "show_glossary_modal",
    },

    # ── H6: ROPO Departure (TARIFF_SELECTION) ────────────────────────────────
    ("any", "H6", "tariff_selection"): {
        "type": "save_progress",
        "message": (
            "Your progress is saved. Come back any time to continue from where you left off. "
            "If you're comparing options elsewhere, note that Start (€38.74/mo) and Optimal "
            "(€68.14/mo) are UNIQA's online-only tariffs — no advisor required to complete."
        ),
        "action": "show_save_and_return_cta",
    },

    # ── H3: Provisional→Final Gap (FINAL_PRICE) ───────────────────────────────
    ("franz", "H3", "final_price"): {
        "type": "price_decomposition",
        "message": (
            "Your final price reflects your personal health profile from the questionnaire. "
            "The difference from the initial estimate is your individual risk assessment — "
            "standard across all Austrian health insurers. "
            f"Start at your final price is the minimum achievable online. "
            f"Optimal gives you double the annual coverage cap (€{COVERAGE_OPTIMAL_ANNUAL:,} "
            f"vs €{COVERAGE_START_ANNUAL:,}) for €{PRICE_START_OPTIMAL_DELTA_MONTHLY:.2f} more/month."
        ),
        "action": "show_price_breakdown_modal",
    },

    ("judith", "H3", "final_price"): {
        "type": "trust_and_save",
        "message": (
            "The price difference from your initial estimate reflects your health profile — "
            "this is required by Austrian insurance law and applies equally at all providers. "
            "Your progress is saved. Would you like to speak with an advisor to confirm "
            "this is the right coverage for you before completing online?"
        ),
        "action": "show_save_progress_and_advisor_cta",
    },

    ("peter", "H3", "final_price"): {
        "type": "service_handoff",
        "message": (
            "I see the final price differs from the initial estimate. "
            "A UNIQA advisor can walk you through exactly why and confirm the right coverage "
            "for you — free of charge, under 10 minutes. "
            "Book a callback now or complete online if you're happy with the price."
        ),
        "action": "show_callback_booking",
    },

    # ── Peter catch-all (any hypothesis) at any step ─────────────────────────
    ("peter", "any", "tariff_selection"): {
        "type": "service_handoff",
        "message": (
            f"You don't need to figure this out alone. Start (€{PRICE_START:.2f}/month) is "
            f"the most popular choice for people in similar situations. "
            f"A free UNIQA callback takes under 10 minutes and there's no obligation."
        ),
        "action": "show_callback_booking",
    },

    ("peter", "any", "final_price"): {
        "type": "service_handoff",
        "message": (
            "A UNIQA advisor can confirm your coverage choice and explain your final price "
            "in under 10 minutes — free, no obligation. "
            "Or complete online now if you're comfortable with the details."
        ),
        "action": "show_callback_booking",
    },
}


def get_intervention(segment: str, hypothesis: str, step: str) -> dict | None:
    """Return the best-matching intervention or None if not found."""
    keys_to_try = [
        (segment, hypothesis, step),
        (segment, "any", step),
        ("any", hypothesis, step),
        ("any", "any", step),
    ]
    for key in keys_to_try:
        if key in INTERVENTIONS:
            return INTERVENTIONS[key]
    return None
