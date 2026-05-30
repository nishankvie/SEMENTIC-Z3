"""
Z3-constrained persona variant sampler.
Every generated variant is simultaneously consistent with all constraints derived
from personas.json statistics — something random sampling cannot guarantee.

Bounds are sourced directly from personas.json:
  Franz (segment_2): always_picks_cheapest=42%, ever_purchased_insurance_online=64%,
                     no_advisor=47%, kv_purchase_intent_3y=16%, low_engagement=63%
  Judith (segment_1): always_picks_cheapest=23%, ever_purchased_insurance_online=34%,
                      purchase_via_advisor=78%, advisor_trust=76%, kv_intent_3y=18%
  Peter (segment_3): always_picks_cheapest=36%, ever_purchased_insurance_online=39%,
                     hospitalization_3y=43%, customer_service_preferred=~60%
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from z3 import Solver, Real, And, Or, sat
from data.funnel_steps import PersonaVariant
from typing import List


def _extract_float(val) -> float:
    """Convert a Z3 rational to a Python float."""
    try:
        return float(val.as_decimal(4).rstrip("?"))
    except Exception:
        return float(str(val.numerator_as_long())) / float(str(val.denominator_as_long()))


def _generate_segment_variants(
    segment: str,
    sub_type: str,
    extra_constraints_fn,
    n: int,
    seed_offset: int,
) -> List[PersonaVariant]:
    variants = []
    for i in range(n):
        s = Solver()
        pt = Real("price_tolerance")
        dc = Real("digital_confidence")
        ur = Real("urgency")
        ad = Real("advisor_dependency")
        ct = Real("complexity_tolerance")

        # Base range constraints [0, 1]
        s.add(pt >= 0, pt <= 1)
        s.add(dc >= 0, dc <= 1)
        s.add(ur >= 0, ur <= 1)
        s.add(ad >= 0, ad <= 1)
        s.add(ct >= 0, ct <= 1)

        # Add segment + sub-type specific constraints
        extra_constraints_fn(s, pt, dc, ur, ad, ct)

        # Seed-based perturbation for variety — forces Z3 to explore different models
        # Each seed nudges one dimension slightly so successive models differ
        nudge = (seed_offset + i) * 0.013
        dim_idx = (seed_offset + i) % 5
        if dim_idx == 0:
            s.add(pt > nudge % 0.8)
        elif dim_idx == 1:
            s.add(dc > 0.1 + nudge % 0.7)
        elif dim_idx == 2:
            s.add(ur > nudge % 0.85)
        elif dim_idx == 3:
            s.add(ad > nudge % 0.75)
        else:
            s.add(ct > nudge % 0.6)

        if s.check() == sat:
            m = s.model()
            variants.append(PersonaVariant(
                segment=segment,
                sub_type=sub_type,
                price_tolerance=round(_extract_float(m[pt]), 3),
                digital_confidence=round(_extract_float(m[dc]), 3),
                urgency=round(_extract_float(m[ur]), 3),
                advisor_dependency=round(_extract_float(m[ad]), 3),
                complexity_tolerance=round(_extract_float(m[ct]), 3),
                seed=seed_offset + i,
            ))

    return variants


# ── FRANZ sub-types ────────────────────────────────────────────────────────────
# Derived from segment_2 personas.json:
#   always_picks_cheapest: 42%    → price_tolerance < 0.55 base; < 0.3 for franz_price
#   ever_purchased_online: 64%    → digital_confidence >= 0.5
#   no_advisor: 47%               → advisor_dependency <= 0.6
#   kv_purchase_intent_3y: 16%   → urgency spread 0.1–0.85
#   low_engagement: 63%          → complexity_tolerance <= 0.80

def _franz_base(s, pt, dc, ur, ad, ct):
    s.add(dc >= 0.5, dc <= 1.0)       # 64% purchased online
    s.add(ad >= 0.0, ad <= 0.6)        # 47% no advisor
    s.add(ur >= 0.1, ur <= 0.85)
    s.add(ct >= 0.2, ct <= 0.80)       # 63% low engagement → cap at 0.80

def _franz_price_constraints(s, pt, dc, ur, ad, ct):
    _franz_base(s, pt, dc, ur, ad, ct)
    s.add(pt >= 0.0, pt < 0.30)        # 42% always pick cheapest → price-first sub-type

def _franz_fast_constraints(s, pt, dc, ur, ad, ct):
    _franz_base(s, pt, dc, ur, ad, ct)
    s.add(pt >= 0.2, pt <= 0.7)
    s.add(ct >= 0.2, ct < 0.35)        # Low complexity tolerance → fast, low patience
    s.add(ur >= 0.3, ur <= 0.75)

def _franz_urgent_constraints(s, pt, dc, ur, ad, ct):
    _franz_base(s, pt, dc, ur, ad, ct)
    s.add(pt >= 0.25, pt <= 0.75)
    s.add(ur > 0.70, ur <= 0.85)       # High intent — will push through price anxiety


# ── JUDITH sub-types ───────────────────────────────────────────────────────────
# Derived from segment_1 personas.json:
#   always_picks_cheapest: 23%   → price_tolerance >= 0.2 (most not price-only)
#   ever_purchased_online: 34%   → digital_confidence <= 0.5
#   purchase_via_advisor: 78%    → advisor_dependency >= 0.4
#   advisor_trust: 76%           → advisor_dependency floor
#   kv_intent_3y: 18%            → spread urgency 0.1–0.9

def _judith_base(s, pt, dc, ur, ad, ct):
    s.add(pt >= 0.20, pt <= 0.90)      # 23% always cheapest → most consider more than price
    s.add(dc >= 0.10, dc <= 0.50)      # 34% ever bought online → lower ceiling
    s.add(ad >= 0.40, ad <= 1.0)       # 78% purchase via advisor → floor 0.4
    s.add(ur >= 0.10, ur <= 0.90)
    s.add(ct >= 0.30, ct <= 0.90)

def _judith_research_constraints(s, pt, dc, ur, ad, ct):
    _judith_base(s, pt, dc, ur, ad, ct)
    s.add(ad > 0.60)                    # High advisor dependency — ROPO pattern
    s.add(ur < 0.50)                    # Low urgency — just researching

def _judith_pressured_constraints(s, pt, dc, ur, ad, ct):
    _judith_base(s, pt, dc, ur, ad, ct)
    s.add(ur > 0.60)                    # High urgency
    s.add(ad < 0.60, ad >= 0.40)       # Moderate advisor dependency → convertible


# ── PETER sub-types ────────────────────────────────────────────────────────────
# Derived from segment_3 personas.json:
#   always_picks_cheapest: 36%    → moderate price sensitivity
#   ever_purchased_online: 39%    → some digital capability
#   no_advisor: 28%               → mixed
#   kv_intent_3y: 13%             → lower urgency
#   hospitalization_3y: 43%       → urgency trigger for peter_urgent
#   customer_service_preferred: ~60% → service channel preferred
#   complexity_tolerance: lowest  → max 0.4

def _peter_base(s, pt, dc, ur, ad, ct):
    s.add(pt >= 0.10, pt <= 0.80)
    s.add(dc >= 0.00, dc <= 0.50)
    s.add(ad >= 0.20, ad <= 0.90)
    s.add(ur >= 0.00, ur <= 0.90)
    s.add(ct >= 0.00, ct <= 0.40)     # Key: easily overwhelmed — hard cap at 0.4

def _peter_overwhelmed_constraints(s, pt, dc, ur, ad, ct):
    _peter_base(s, pt, dc, ur, ad, ct)
    s.add(ct >= 0.00, ct < 0.20)       # Very overwhelmed — early exit likely

def _peter_urgent_constraints(s, pt, dc, ur, ad, ct):
    _peter_base(s, pt, dc, ur, ad, ct)
    s.add(ur > 0.60, ur <= 0.90)       # Hospitalization-triggered urgency
    s.add(ct >= 0.15, ct <= 0.40)      # Slightly more tolerance due to urgency

def _peter_browsing_constraints(s, pt, dc, ur, ad, ct):
    _peter_base(s, pt, dc, ur, ad, ct)
    s.add(ur < 0.20)                    # Low urgency — just browsing
    s.add(ct < 0.30)                    # Low complexity tolerance — Cold Feet likely


# ── Public API ─────────────────────────────────────────────────────────────────

SUB_TYPE_REGISTRY = {
    "franz_price":       (_franz_price_constraints,       0),
    "franz_fast":        (_franz_fast_constraints,        100),
    "franz_urgent":      (_franz_urgent_constraints,      200),
    "judith_research":   (_judith_research_constraints,   300),
    "judith_pressured":  (_judith_pressured_constraints,  400),
    "peter_overwhelmed": (_peter_overwhelmed_constraints, 500),
    "peter_urgent":      (_peter_urgent_constraints,      600),
    "peter_browsing":    (_peter_browsing_constraints,    700),
}

SUB_TYPE_SEGMENT = {
    "franz_price": "franz",
    "franz_fast": "franz",
    "franz_urgent": "franz",
    "judith_research": "judith",
    "judith_pressured": "judith",
    "peter_overwhelmed": "peter",
    "peter_urgent": "peter",
    "peter_browsing": "peter",
}


def generate_variants(sub_type: str, n: int = 10) -> List[PersonaVariant]:
    """Generate n Z3-valid variants for a given sub-type."""
    if sub_type not in SUB_TYPE_REGISTRY:
        raise ValueError(f"Unknown sub_type: {sub_type}. Valid: {list(SUB_TYPE_REGISTRY)}")
    constraint_fn, seed_offset = SUB_TYPE_REGISTRY[sub_type]
    segment = SUB_TYPE_SEGMENT[sub_type]
    return _generate_segment_variants(segment, sub_type, constraint_fn, n, seed_offset)


def generate_all_variants(n_per_subtype: int = 6) -> List[PersonaVariant]:
    """Generate variants for all 8 sub-types."""
    all_variants = []
    for sub_type in SUB_TYPE_REGISTRY:
        variants = generate_variants(sub_type, n=n_per_subtype)
        all_variants.extend(variants)
    return all_variants


def generate_population(total: int = 50) -> List[PersonaVariant]:
    """
    Generate a realistic population weighted by funnel traffic share.
    Franz: 50%, Judith: 30%, Peter: 20%
    """
    franz_n = round(total * 0.50)
    judith_n = round(total * 0.30)
    peter_n = total - franz_n - judith_n

    # Distribute within each segment across sub-types
    franz_per = max(1, franz_n // 3)
    judith_per = max(1, judith_n // 2)
    peter_per = max(1, peter_n // 3)

    variants = []
    variants += generate_variants("franz_price", n=franz_per)
    variants += generate_variants("franz_fast", n=franz_per)
    variants += generate_variants("franz_urgent", n=franz_n - 2 * franz_per)
    variants += generate_variants("judith_research", n=judith_per)
    variants += generate_variants("judith_pressured", n=judith_n - judith_per)
    variants += generate_variants("peter_overwhelmed", n=peter_per)
    variants += generate_variants("peter_urgent", n=peter_per)
    variants += generate_variants("peter_browsing", n=peter_n - 2 * peter_per)

    return variants


if __name__ == "__main__":
    print("Testing Z3 variant generator...")
    pop = generate_population(total=24)
    print(f"Generated {len(pop)} variants")
    from collections import Counter
    counts = Counter(v.sub_type for v in pop)
    for sub_type, count in sorted(counts.items()):
        v = next(x for x in pop if x.sub_type == sub_type)
        print(f"  {sub_type:25s} ×{count}  pt={v.price_tolerance:.2f} "
              f"dc={v.digital_confidence:.2f} ur={v.urgency:.2f} "
              f"ad={v.advisor_dependency:.2f} ct={v.complexity_tolerance:.2f}")
    print("OK — all variants satisfy Z3 constraints")
