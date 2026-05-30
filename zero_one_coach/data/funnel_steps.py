from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


class JourneyState(Enum):
    COVERAGE_TYPE    = "coverage_type"      # Step 1: Doctor visits vs Hospital
    BENEFICIARY      = "beneficiary"        # Step 2: Myself vs Others
    PERSONAL_DATA    = "personal_data"      # Step 3: DOB + social insurance number — H7 active
    TARIFF_SELECTION = "tariff_selection"   # Step 4: First price display — H1,H2,H4,H5,H6,H8
    HEALTH_QUESTIONS = "health_questions"   # Step 5: Health questionnaire
    FINAL_PRICE      = "final_price"        # Step 6: Finalized premium — H3 + Cold Feet
    CLOSING          = "closing"            # Purchase completion → converted
    ADVISOR_ROUTE    = "advisor_route"      # Clean advisor handoff → advisor_routed
    ABANDONED        = "abandoned"          # Left without completing


TERMINAL_STATES = {JourneyState.CLOSING, JourneyState.ADVISOR_ROUTE, JourneyState.ABANDONED}

ONLINE_TARIFFS = {"start", "optimal"}
ADVISOR_TARIFFS = {"opt_plus", "premium"}

# Signal schema documentation (runtime dicts match these shapes)
STEP3_SIGNALS = {
    "dwell_time_seconds": float,   # > 60 = H7 trust barrier
    "back_navigation": bool,
    "completed": bool,
}

STEP4_SIGNALS = {
    "dwell_time_seconds": float,   # > 45 = H1/H4; > 60 = H4 overload
    "tariff_hovers": int,          # > 3 = H1; > 5 without selection = H4
    "opt_plus_clicked": bool,      # H2/H8 trigger
    "back_nav_after_opt_plus": bool,
    "tab_opened_external": bool,   # H6 ROPO
    "term_hover": bool,            # H5 unfamiliar terms
    "selected_tariff": Optional[str],  # None = abandoned
    "cancel_hover": bool,
}

STEP7_SIGNALS = {
    "dwell_time_seconds": float,   # > 30 = H3
    "cancel_hovers": int,          # > 2 = near abandonment
    "back_to_tariff_step": bool,
    "price_delta_shown": float,    # provisional → final delta
    "session_duration_total": float,
}


@dataclass
class PersonaVariant:
    segment: str                     # "judith" | "franz" | "peter"
    sub_type: str                    # e.g. "franz_price"
    price_tolerance: float           # [0,1] 0=always cheapest, 1=price insensitive
    digital_confidence: float        # [0,1] 0=never online, 1=always online
    urgency: float                   # [0,1] 0=browsing, 1=real purchase intent
    advisor_dependency: float        # [0,1] 0=no advisor, 1=needs advisor
    complexity_tolerance: float      # [0,1] 0=overwhelmed, 1=reads everything
    seed: int


@dataclass
class HypothesisResult:
    hypothesis: str                  # "H1"–"H8", "COLD_FEET", "NONE"
    is_sat: bool
    reason: str
    signals_used: Dict[str, Any]
    intervention_warranted: bool


@dataclass
class InterventionRecord:
    step: str
    hypothesis: str
    segment: str
    sub_type: str
    type: str
    message: str
    action: str
    suppressed: bool = False
    suppression_reason: str = ""


@dataclass
class JourneySession:
    variant: PersonaVariant
    state: JourneyState = field(default=JourneyState.COVERAGE_TYPE)
    selections: Dict[str, Any] = field(default_factory=dict)
    signals: Dict[str, Dict] = field(default_factory=dict)
    interventions_fired: List[InterventionRecord] = field(default_factory=list)
    interventions_suppressed: List[InterventionRecord] = field(default_factory=list)
    outcome: Optional[str] = None    # "converted" | "abandoned" | "advisor_routed"
    step_log: List[Dict] = field(default_factory=list)
    hypothesis_log: List[Dict] = field(default_factory=list)
    provisional_price: float = 0.0
    final_price: float = 0.0
