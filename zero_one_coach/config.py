import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

# Simulation parameters
N_VARIANTS_DEFAULT = 50
SEED_BASE = 42

# Funnel prices (age-27 reference, from UNIQA tariff documents)
PRICE_START = 38.74
PRICE_OPTIMAL = 68.14
PRICE_OPT_PLUS = 96.66
PRICE_PREMIUM = 140.16

PRICE_START_OPTIMAL_DELTA_MONTHLY = PRICE_OPTIMAL - PRICE_START   # 29.40
PRICE_START_OPTIMAL_DELTA_DAILY = round(PRICE_START_OPTIMAL_DELTA_MONTHLY / 30, 2)  # 0.98
COVERAGE_START_ANNUAL = 1400
COVERAGE_OPTIMAL_ANNUAL = 2800

# Baseline conversion calibration (from personas.json shared_context)
BASELINE_CONVERSION_TARGET = 0.056
DROPOFF_TARIFF_SELECTION = 0.66
DROPOFF_HEALTH_QUESTIONS = 0.00   # minimal drop
DROPOFF_FINAL_PRICE = 0.78

# Funnel traffic share per segment (from personas.json)
SEGMENT_TRAFFIC_SHARE = {
    "judith": 0.30,
    "franz": 0.50,
    "peter": 0.20,
}

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "insurance-uniqa")
PERSONAS_JSON = os.path.join(DATA_DIR, "personas.json")
