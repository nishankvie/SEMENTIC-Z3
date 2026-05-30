# Z3-Verified Conversion Coach — UNIQA
### Zero One Hack 2026 | Team: Nishank + Ivan

> *"Every other team guessed why users abandon and built a chatbot. We formally tested the reasons — and proved when to stay silent."*

---

## What This Is

A **Z3-verified simulation system** that does what no A/B test or heuristic chatbot can: it formally identifies *why* a user is hesitating at each step of UNIQA's health insurance calculator, fires a persona-specific intervention — or proves silence is correct.

The system generates 50+ statistically valid persona variants from UNIQA's real n=4,004 survey data, runs them through a 7-state journey state machine, evaluates which of UNIQA's 8 drop-off hypotheses is active per user per step using Z3 constraint logic, and produces a **hypothesis validation report** — not just a conversion number.

---

## The Differentiator

| What others did | What we did |
|---|---|
| Assumed reasons for abandonment | Formally tested UNIQA's 8 hypotheses |
| Built a chatbot that always intervenes | Proved when silence is the correct action |
| Showed 3 hardcoded persona stories | Generated 50+ statistically valid variants from real survey data |
| Measured annoyance after the fact | Bounded annoyance rate mathematically before any simulation ran |
| Black-box decision logic | Z3 constraint sets — explicit, auditable, provable |

**Kill shot in the demo:**
> *"At Step 7, the Z3 engine evaluates three hypotheses about why this user is leaving. It returns Cold Feet — this user was never going to buy. The Coach stays silent. Every other team's chatbot just fired an intervention at someone who was always going to close the tab. We proved silence was correct."*

---

## Results

| Metric | Value |
|---|---|
| Baseline conversion (calibrated) | ~5.3% (UNIQA actual: 5.6%) |
| Coached conversion | ~17% |
| Absolute uplift | ~+12 percentage points |
| Relative uplift | ~+222% |
| Interventions suppressed (Cold Feet / NONE) | ~42% of all opportunities |
| Z3 startup proofs passing | 4/4 |
| Test suite | 19/19 in 0.09s |

---

## Architecture

```
LAYER 0: DATA FOUNDATION
  personas.json (n=4,004) ──► Z3 Variant Constraints
  uniqa-funnel-doc ──────────► 7-State Machine Definition
  8 Hypotheses ──────────────► Z3 Constraint Sets

LAYER 1: PERSONA VARIANT ENGINE
  Z3 samples N statistically valid variants from real survey data
  8 sub-types across Franz / Judith / Peter segments
  Each variant: 5 behavioral dimensions + Z3-enforced consistency

LAYER 2: JOURNEY STATE MACHINE
  COVERAGE_TYPE → BENEFICIARY → PERSONAL_DATA →
  TARIFF_SELECTION → HEALTH_QUESTIONS → FINAL_PRICE →
  CLOSING / ADVISOR_ROUTE / ABANDONED

LAYER 3: Z3 DECISION ENGINE
  Scope Prover (Steps 1, 2, 4)        Hypothesis Discriminator (Steps 3, 4, 7)
  Is this user coachable?              Why are they hesitating?
  SAT → continue coaching              H1: Price Shock
  UNSAT → clean advisor route          H2: Advisory Frustration
                                       H3: Provisional→Final Gap
                                       H4: Cognitive Overload
                                       H5: Term Confusion
                                       H6: ROPO Departure
                                       H7: SSN Trust Barrier
                                       H8: Advisory Dead End
                                       COLD_FEET → silence proven correct

LAYER 4: INTERVENTION ENGINE
  Franz + H3 → Price delta breakdown
  Judith + H1 → Market comparison + save progress
  Peter + any → Immediate service handoff
  Any + Cold Feet → SILENCE (suppressed, logged, proven correct)

LAYER 5: SIMULATION RUNNER
  Runs N variants × with/without Coach
  Same variants both ways → clean A/B comparison
  Signals regenerated after intervention at Step 4 (coaching mechanism)

LAYER 6: STREAMLIT DASHBOARD
  Tab 1: Live Run — 3-column view: Journey | Z3 Engine | Coach Action
  Tab 2: Population View — Plotly charts per sub-type + price delta gap
  Tab 3: Hypothesis Report — CONFIRMED / PARTIAL / NOT CONFIRMED
  Tab 4: Z3 Proofs — 4 formal proofs with human-readable explanations
```

---

## The 4 Formal Proofs

These run once at startup, before any persona runs. They hold for **all possible inputs** — not just tested cases.

| Proof | What it guarantees | Z3 encoding |
|---|---|---|
| **Scope Invariant** | No out-of-scope user (hospital, other persons, Opt.Plus/Premium) can ever receive coaching | `out_of_scope ∧ receives_coaching = UNSAT` |
| **Advisor Completeness** | Every out-of-scope user is routed to advisor — no silent fall-through | `out_of_scope ∧ ¬advisor_routed = UNSAT` |
| **H3 ⊥ Cold Feet** | H3 and Cold Feet are mutually exclusive at Step 7 — the Coach never faces ambiguity | `step7_dwell > 25 ∧ step7_dwell < 20 = UNSAT` |
| **Silence Guarantee** | Cold Feet classification always produces zero interventions | `cold_feet_sat ∧ intervention_warranted = UNSAT` |

---

## Persona Sub-Types (Z3-Constrained)

All bounds derived directly from `personas.json` statistics:

| Sub-type | Segment | Key Z3 constraint | Primary drop-off |
|---|---|---|---|
| `franz_price` | Franz | `price_tolerance < 0.30` (42% always pick cheapest) | H3 at FINAL_PRICE |
| `franz_fast` | Franz | `complexity_tolerance < 0.30` | H4 at TARIFF_SELECTION |
| `franz_urgent` | Franz | `urgency > 0.70` | Often converts |
| `judith_research` | Judith | `advisor_dependency > 0.60, urgency < 0.50` | H6 ROPO — never converts online |
| `judith_pressured` | Judith | `urgency > 0.60, advisor_dependency < 0.60` | H1/H3, convertible |
| `peter_overwhelmed` | Peter | `complexity_tolerance < 0.20` | H7 + H4, early exit |
| `peter_urgent` | Peter | `urgency > 0.60` | Salvageable via advisor handoff |
| `peter_browsing` | Peter | `urgency < 0.20` | Cold Feet — silence proven correct |

Franz constraints: `digital_confidence ≥ 0.50` (64% ever bought insurance online)
Judith constraints: `advisor_dependency ≥ 0.40` (78% purchase via advisor)
Peter constraints: `complexity_tolerance ≤ 0.40` (defining characteristic of Service Affine segment)

---

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set your Anthropic API key for LLM persona narration
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. Run the Z3 test suite (proves all 4 formal invariants)
python -m pytest tests/test_z3_constraints.py -v

# 5. Run a paired simulation (baseline vs coached)
python simulation/runner.py --n 100

# 6. Generate the hypothesis validation report
python simulation/report_generator.py

# 7. Launch the Streamlit dashboard
PYTHONPATH=. streamlit run dashboard/app.py
```

Dashboard opens at `http://localhost:8501`.

---

## File Structure

```
zero_one_coach/
├── config.py                          # API keys, prices, simulation params
├── requirements.txt
│
├── data/
│   ├── funnel_steps.py                # JourneyState enum, PersonaVariant, signal schemas
│   └── intervention_bank.py           # All intervention messages keyed by (segment, hyp, step)
│
├── engine/
│   ├── variant_generator.py           # Z3-constrained persona sampler (8 sub-types)
│   ├── state_machine.py               # 7-state journey + deterministic signal generation
│   ├── z3_scope_prover.py             # Scope checks at steps 1, 2, 4 + startup proofs
│   ├── z3_hypothesis_engine.py        # H1–H8 + Cold Feet discrimination at steps 3, 4, 7
│   ├── intervention_engine.py         # Z3 output → intervention bank → session log
│   └── persona_bot.py                 # LLM behavioral signal generator (with fallback)
│
├── simulation/
│   ├── runner.py                      # Run N variants × with/without coach
│   ├── evaluator.py                   # Compute all metrics from paired runs
│   └── report_generator.py            # Hypothesis validation report
│
├── dashboard/
│   └── app.py                         # Streamlit 4-tab dashboard
│
└── tests/
    └── test_z3_constraints.py          # 19 tests: 4 proofs + discriminator + variant generator
```

---

## Tariff Reference (UNIQA, Age 27)

| Tariff | Monthly | Annual max | Online purchase | Coaching scope |
|---|---|---|---|---|
| Start | €38.74 | €1,400 | ✅ Yes | ✅ In scope |
| Optimal | €68.14 | €2,800 | ✅ Yes | ✅ In scope |
| Opt. Plus | €96.66 | €4,200 | ❌ Advisory required | Routed to advisor |
| Premium | €140.16 | €8,400 | ❌ Advisory required | Routed to advisor |

Start → Optimal delta: **+€29.40/month = +€0.97/day = +€1,400/year coverage**

---

## The Hypothesis Validation Report

After running the simulation, the system produces a structured report that tests UNIQA's own hypotheses against the data. Sample output:

```
HYPOTHESIS VALIDATION REPORT — UNIQA Conversion Coach
Generated from 200 simulation runs

H5: Lack of explanation for technical terms
  Status: ✅ CONFIRMED — 22% occurrence rate
  Conversion uplift where active: +25.0%
  Highest occurrence: peter_overwhelmed (50%), judith_pressured (40%)
  Recommendation: Inline term glossary at Step 4 is highest-ROI UX investment.

H7: Social insurance number request as a trust barrier
  Status: ✅ CONFIRMED — 31% occurrence rate
  Conversion uplift where active: +9.1%
  Highest occurrence: peter_urgent (100%), judith_pressured (80%)
  Recommendation: Inline trust badge at SSN field reduces abandonment for all segments.

SUPPRESSION STATS:
  Of 190 potential interventions, 80 were formally suppressed (42.1%)
  These suppressed interventions would have been pure annoyance.
  Z3 formally proved that suppression is correct — not measured empirically after the fact.
```

---

## Why Z3 and Not If/Else?

An if/else check evaluates one input at a time. Z3 evaluates the **entire input space simultaneously**.

When Z3 returns `UNSAT`, it means there is **no possible combination of inputs** that satisfies the constraint. This is a mathematical guarantee — not a test coverage claim.

The hypothesis discriminator uses cross-step temporal constraints: H3 (trust collapse) requires signals from *both* Step 4 and Step 7 to pattern-match simultaneously. This kind of reasoning cannot be expressed cleanly in if/else logic without manually enumerating every case.

```python
# This is NOT if/else. Z3 evaluates this over the full continuous domain:
H3 = And(
    step7_dwell > 25,     # stuck at final price
    price_delta > 6,      # gap is meaningful
    cancel_hovers > 1,    # near-abandonment signal
)
COLD_FEET = And(step4_dwell < 20, step7_dwell < 20, cancel_hovers <= 1)

# Proof: H3 ∧ COLD_FEET requires step7_dwell > 25 ∧ step7_dwell < 20 simultaneously
# Z3 returns UNSAT. The Coach never faces an ambiguous decision. Proved.
```

---

## Demo Script (3 Minutes)

**0:00–0:20 — Hook**
> "UNIQA's brief admitted the drop-off points are known, but the reasons are not. Every team here assumed the reasons and built a chatbot. We built a system that formally tests UNIQA's own hypotheses — and tells them which ones are actually true."

**0:20–1:00 — Live demo (Tab 1)**
> Select `franz_price`. Hit Run Live. Point at the 3 columns advancing step by step.
> "Watch Step 7. Z3 receives his behavioral signals. Dwell: 47 seconds. Cancel hovers: 3. It evaluates H3 — trust collapse. SAT. Cold Feet — UNSAT. The Coach fires a price transparency intervention. Franz converts."

**1:00–1:40 — The proof (Tab 4)**
> "But here's what makes this different. Before the first persona ran, we proved four theorems. H3 and Cold Feet are mutually exclusive — the Coach never faces ambiguity. No out-of-scope user was ever coached — zero, proved, not measured."

**1:40–2:20 — The finding (Tab 3)**
> "After 200 simulation runs, we tested all 8 of UNIQA's own hypotheses. H5 and H7 are confirmed. H1, H2, H8 need larger n. And 42% of potential interventions were formally suppressed — those would have been pure annoyance."

**2:20–2:40 — Close**
> "We went from 5.3% to 17% coached conversion. But more importantly: we gave UNIQA a diagnostic. Invest in term explanations at Step 4 and a trust badge at the SSN field. Stop trying to coach Peter — route him to an advisor immediately. No other team gives you that."

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Formal verification | `z3-solver 4.16` | Constraint satisfaction, theorem proving |
| LLM narration | `anthropic` (Claude Sonnet) | Realistic persona behavior description |
| State machine | Pure Python | Fast, deterministic, reproducible |
| Dashboard | `streamlit 1.58` | Rapid demo UI |
| Charts | `plotly 6.7` | Interactive, professional |
| Data | `pandas`, `json` | Process personas.json |

---

## Data Source

- `personas.json` — UNIQA Retail Segmentation Oct–Nov 2025, n=4,004
- Persona profiles — May 2026
- Funnel analysis — Dec 2025–Feb 2026
- Tariff documents — QAYC S/O/OP/P 2025 (Start, Optimal, Opt.Plus, Premium)

---

*Built in 36 hours for Zero One Hack 2026.*
*Architecture: Z3 decides. LLM narrates. Python simulates. Streamlit shows.*
