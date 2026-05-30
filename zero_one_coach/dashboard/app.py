"""
Z3-Verified Conversion Coach — Streamlit Dashboard
4 tabs: Live Run | Population View | Hypothesis Report | Z3 Proofs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Z3 Conversion Coach — UNIQA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
.metric-box { background: #1e1e2e; padding: 12px; border-radius: 8px; margin: 4px 0; }
.hypothesis-card { background: #2a2a3e; padding: 10px; border-radius: 6px; margin: 4px 0; border-left: 3px solid #7c6af7; }
.fired { border-left: 3px solid #22c55e; }
.suppressed { border-left: 3px solid #ef4444; }
.proven { color: #22c55e; font-weight: bold; }
.step-active { background: #7c6af7; color: white; padding: 4px 8px; border-radius: 4px; }
.step-done { background: #22c55e; color: white; padding: 4px 8px; border-radius: 4px; }
.step-pending { background: #374151; color: #9ca3af; padding: 4px 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Startup proofs (run once) ──────────────────────────────────────────────────
@st.cache_resource
def run_all_startup_proofs():
    from engine.z3_scope_prover import run_startup_proofs
    from engine.z3_hypothesis_engine import run_hypothesis_startup_proofs
    scope = run_startup_proofs()
    hyp = run_hypothesis_startup_proofs()
    return {**scope, **hyp}


# ── Simulation cache ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Running simulation...")
def run_cached_simulation(n_variants: int, seed: int):
    from simulation.runner import run_paired_simulation
    from simulation.evaluator import compute_metrics
    from simulation.report_generator import generate_report
    baseline, coached = run_paired_simulation(total_variants=n_variants)
    metrics = compute_metrics(baseline, coached)
    report = generate_report(baseline, coached, metrics)
    return baseline, coached, metrics, report


@st.cache_data(show_spinner="Generating variants...")
def get_population(n: int):
    from engine.variant_generator import generate_population
    return generate_population(total=n)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚡ Z3 Conversion Coach")
    st.caption("UNIQA Hackathon — Zero One Hack 2026")
    st.divider()

    n_variants = st.slider("Simulation variants", min_value=20, max_value=200, value=60, step=10)
    seed = st.number_input("Random seed", value=42, step=1)

    run_btn = st.button("▶ Run Simulation", type="primary", use_container_width=True)
    st.divider()

    # Quick stats (populated after run)
    st.markdown("**Key Metrics**")
    conv_placeholder = st.empty()
    supp_placeholder = st.empty()
    st.divider()
    st.markdown("**Startup Proofs**")
    proof_placeholder = st.empty()


# ── Load proofs ────────────────────────────────────────────────────────────────
proofs = run_all_startup_proofs()
all_proven = all(ok for ok, _ in proofs.values())

with proof_placeholder.container():
    for name, (ok, _) in proofs.items():
        icon = "✅" if ok else "❌"
        label = name.replace("_", " ").title()[:30]
        st.markdown(f"{icon} {label}")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_live, tab_pop, tab_report, tab_proofs = st.tabs([
    "🔴 Live Run", "📊 Population View", "📋 Hypothesis Report", "🔐 Z3 Proofs"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: LIVE RUN
# ══════════════════════════════════════════════════════════════════════════════
with tab_live:
    st.header("Live Session Walkthrough")
    st.caption("Watch Z3 evaluate a single persona in real time.")

    col_variant, col_run = st.columns([3, 1])
    with col_variant:
        sub_type = st.selectbox("Select persona sub-type", [
            "franz_price", "franz_fast", "franz_urgent",
            "judith_research", "judith_pressured",
            "peter_overwhelmed", "peter_urgent", "peter_browsing",
        ], index=0)
    with col_run:
        live_run = st.button("▶ Run Live", type="primary", use_container_width=True)

    if live_run:
        from engine.variant_generator import generate_variants
        from simulation.runner import run_single_session

        variants = generate_variants(sub_type, n=1)
        if not variants:
            st.error("Could not generate variant — Z3 constraints unsatisfiable for this sub-type.")
        else:
            variant = variants[0]
            st.divider()

            # Show variant profile
            prof_col1, prof_col2 = st.columns(2)
            with prof_col1:
                st.markdown(f"**Variant:** `{variant.sub_type}` | **Segment:** {variant.segment.title()}")
                st.markdown(f"**Seed:** {variant.seed}")
            with prof_col2:
                st.markdown(f"price_tolerance=`{variant.price_tolerance}` | digital_confidence=`{variant.digital_confidence}`")
                st.markdown(f"urgency=`{variant.urgency}` | advisor_dependency=`{variant.advisor_dependency}` | complexity_tolerance=`{variant.complexity_tolerance}`")

            st.divider()

            # 3-column layout
            col_journey, col_z3, col_coach = st.columns(3)

            with col_journey:
                st.markdown("### 🧭 User Journey")
            with col_z3:
                st.markdown("### 🔐 Z3 Engine")
            with col_coach:
                st.markdown("### 💬 Coach Action")

            # Run session with step-by-step display
            from data.funnel_steps import JourneyState, TERMINAL_STATES
            from engine.state_machine import (
                advance_state, generate_signals_for_state, make_default_selections
            )
            from engine.z3_scope_prover import prove_coachable
            from engine.intervention_engine import run_hypothesis_step
            from data.funnel_steps import JourneySession
            import time

            session = JourneySession(variant=variant)
            session.selections = make_default_selections(variant)
            step4_signals = None
            max_steps = 12

            journey_msgs = []
            z3_msgs = []
            coach_msgs = []

            journey_ph = col_journey.empty()
            z3_ph = col_z3.empty()
            coach_ph = col_coach.empty()

            steps_taken = 0
            while session.state not in TERMINAL_STATES and steps_taken < max_steps:
                steps_taken += 1
                current_state = session.state
                time.sleep(0.3)

                # Journey update
                journey_msgs.append(f"**Step:** `{current_state.value}`")

                # Scope check
                if current_state in (JourneyState.COVERAGE_TYPE, JourneyState.BENEFICIARY):
                    ok, reason = prove_coachable(session.selections)
                    if not ok:
                        session.state = JourneyState.ADVISOR_ROUTE
                        session.outcome = "advisor_routed"
                        journey_msgs.append(f"→ Advisor Route: {reason}")
                        z3_msgs.append(f"🔐 Scope: UNSAT\n{reason}")
                        break
                    session.state = advance_state(session, {})
                    z3_msgs.append(f"🔐 Scope: SAT ✓\nPath is coachable")
                    coach_msgs.append("—")
                    journey_msgs.append("→ passed scope check")

                    journey_ph.markdown("\n\n".join(journey_msgs[-5:]))
                    z3_ph.markdown("\n\n".join(z3_msgs[-5:]))
                    coach_ph.markdown("\n\n".join(coach_msgs[-5:]))
                    continue

                signals = generate_signals_for_state(session)

                # Signal summary for journey column
                sig_lines = []
                if "dwell_time_seconds" in signals:
                    sig_lines.append(f"⏱ dwell: `{signals['dwell_time_seconds']:.0f}s`")
                if "tariff_hovers" in signals:
                    sig_lines.append(f"🖱 hovers: `{signals['tariff_hovers']}`")
                if "cancel_hovers" in signals:
                    sig_lines.append(f"❌ cancel hovers: `{signals['cancel_hovers']}`")
                if "price_delta_shown" in signals:
                    sig_lines.append(f"💰 delta: `€{signals['price_delta_shown']:.2f}`")
                if "selected_tariff" in signals:
                    sig_lines.append(f"🎯 selected: `{signals.get('selected_tariff') or 'none'}`")
                journey_msgs.extend(sig_lines)

                # Z3 hypothesis (at active steps)
                intervention = None
                if current_state in (JourneyState.PERSONAL_DATA, JourneyState.TARIFF_SELECTION, JourneyState.FINAL_PRICE):
                    # Scope check at tariff selection for premium tariffs
                    if current_state == JourneyState.TARIFF_SELECTION:
                        sel = signals.get("selected_tariff", "start")
                        check_sel = dict(session.selections)
                        check_sel["tariff"] = sel or "start"
                        ok, reason = prove_coachable(check_sel)
                        if not ok and sel not in (None, "start", "optimal"):
                            session.state = JourneyState.ADVISOR_ROUTE
                            session.outcome = "advisor_routed"
                            journey_msgs.append(f"→ Advisor Route: {reason}")
                            z3_msgs.append(f"🔐 Scope: UNSAT\n{reason}")
                            break

                    intervention = run_hypothesis_step(
                        session=session,
                        state=current_state,
                        signals=signals,
                        step4_signals=step4_signals if current_state == JourneyState.FINAL_PRICE else None,
                        with_coach=True,
                    )

                    if session.hypothesis_log:
                        last_h = session.hypothesis_log[-1]
                        z3_msgs.append(
                            f"**{last_h['hypothesis']}** {'✅ SAT' if last_h['is_sat'] else '❌ UNSAT'}\n"
                            f"{last_h['reason'][:120]}"
                        )
                    else:
                        z3_msgs.append("—")

                    if intervention and not intervention.suppressed:
                        coach_msgs.append(
                            f"**{intervention.type}**\n_{intervention.message[:200]}_"
                        )
                    elif session.interventions_suppressed and session.interventions_suppressed[-1].step == current_state.value:
                        coach_msgs.append("🔇 **Suppressed** (Cold Feet — silence is correct)")
                    else:
                        coach_msgs.append("—")
                else:
                    z3_msgs.append("—")
                    coach_msgs.append("—")

                if current_state == JourneyState.TARIFF_SELECTION:
                    step4_signals = signals
                    tariff = signals.get("selected_tariff")
                    if tariff:
                        session.selections["tariff"] = tariff

                if current_state == JourneyState.FINAL_PRICE:
                    final_p = signals.get("final_price", 0)
                    if final_p:
                        session.final_price = final_p

                session.signals[current_state.value] = signals
                session.state = advance_state(session, signals, intervention)
                session.step_log.append({"step": current_state.value, "next_state": session.state.value})

                journey_ph.markdown("\n\n".join(journey_msgs[-8:]))
                z3_ph.markdown("\n\n".join(z3_msgs[-8:]))
                coach_ph.markdown("\n\n".join(coach_msgs[-8:]))
                time.sleep(0.2)

            if session.outcome is None:
                if session.state == JourneyState.CLOSING:
                    session.outcome = "converted"
                elif session.state == JourneyState.ADVISOR_ROUTE:
                    session.outcome = "advisor_routed"
                else:
                    session.outcome = "abandoned"

            # Outcome banner
            st.divider()
            outcome_colors = {
                "converted": "🟢",
                "advisor_routed": "🟡",
                "abandoned": "🔴",
            }
            icon = outcome_colors.get(session.outcome, "⚪")
            st.markdown(f"## {icon} Outcome: **{session.outcome.replace('_', ' ').upper()}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Interventions Fired", len(session.interventions_fired))
            c2.metric("Interventions Suppressed", len(session.interventions_suppressed))
            c3.metric("Steps Completed", len(session.step_log))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: POPULATION VIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_pop:
    st.header("Population Simulation Results")

    if run_btn or st.session_state.get("sim_done"):
        st.session_state["sim_done"] = True
        baseline, coached, metrics, report = run_cached_simulation(n_variants, seed)

        # Summary metrics
        b_rate = metrics["baseline_conversion_rate"]
        c_rate = metrics["coached_conversion_rate"]
        uplift = metrics["uplift_absolute"]
        rel = metrics["uplift_relative"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Baseline Conversion", f"{b_rate:.1%}")
        m2.metric("Coached Conversion", f"{c_rate:.1%}", f"+{uplift:.1%}")
        m3.metric("Relative Uplift", f"+{rel:.0%}")
        m4.metric("Suppression Rate", f"{metrics['suppression_rate']:.1%}")

        # Update sidebar
        conv_placeholder.metric("Conversion uplift", f"+{uplift:.1%}")
        supp_placeholder.metric("Suppression rate", f"{metrics['suppression_rate']:.1%}")

        st.divider()

        # Per sub-type conversion chart
        st.subheader("Conversion by Sub-Type")
        sub_data = metrics["per_subtype"]
        df_sub = pd.DataFrame([
            {
                "Sub-type": st,
                "Baseline": d["baseline_rate"] * 100,
                "Coached": d["coached_rate"] * 100,
                "Uplift (pp)": d["uplift_abs"] * 100,
                "Dominant Hypothesis": d["dominant_hypothesis"],
            }
            for st, d in sub_data.items()
        ])

        fig_conv = go.Figure()
        fig_conv.add_bar(
            x=df_sub["Sub-type"], y=df_sub["Baseline"],
            name="Without Coach", marker_color="#374151",
        )
        fig_conv.add_bar(
            x=df_sub["Sub-type"], y=df_sub["Coached"],
            name="With Coach", marker_color="#7c6af7",
        )
        fig_conv.update_layout(
            barmode="group", title="Conversion Rate by Sub-Type",
            yaxis_title="Conversion Rate (%)",
            plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
            font_color="white", legend=dict(x=0.8, y=0.95),
        )
        st.plotly_chart(fig_conv, use_container_width=True)

        # Price delta gap chart (The Demo Centerpiece)
        st.subheader("The Price Delta Gap — Steps 4 to 7")
        step7_sessions = [
            s for s in baseline
            if "final_price" in s.signals
        ]
        if step7_sessions:
            deltas = [
                s.signals.get("final_price", {}).get("price_delta_shown", 0)
                for s in step7_sessions
            ]
            provisional_prices = [s.provisional_price for s in step7_sessions]
            final_prices = [p + d for p, d in zip(provisional_prices, deltas)]

            fig_delta = go.Figure()
            fig_delta.add_scatter(
                x=list(range(len(provisional_prices))),
                y=provisional_prices,
                name="Step 4 Provisional Price",
                mode="markers", marker_color="#60a5fa", marker_size=6,
            )
            fig_delta.add_scatter(
                x=list(range(len(final_prices))),
                y=final_prices,
                name="Step 7 Final Price",
                mode="markers", marker_color="#f97316", marker_size=6,
            )
            # Add gap fill
            for i, (prov, final) in enumerate(zip(provisional_prices, final_prices)):
                if final > prov + 5:
                    fig_delta.add_shape(
                        type="line", x0=i, x1=i, y0=prov, y1=final,
                        line=dict(color="rgba(239,68,68,0.4)", width=2),
                    )
            fig_delta.update_layout(
                title="Provisional → Final Price Gap (red lines = H3 trust collapse risk)",
                yaxis_title="Monthly Premium (€)",
                plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                font_color="white",
            )
            st.plotly_chart(fig_delta, use_container_width=True)

        # Hypothesis distribution pie
        st.subheader("Hypothesis Distribution")
        hyp_dist = metrics["hypothesis_distribution"]
        if hyp_dist:
            fig_pie = px.pie(
                values=list(hyp_dist.values()),
                names=list(hyp_dist.keys()),
                title="Active Hypotheses Across All Sessions",
                color_discrete_sequence=["#7c6af7", "#22c55e", "#f97316", "#60a5fa",
                                          "#ef4444", "#a78bfa", "#34d399", "#fbbf24"],
            )
            fig_pie.update_layout(
                plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e", font_color="white"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Intervention breakdown table
        st.subheader("Sub-Type Detail Table")
        st.dataframe(
            df_sub.style.format({
                "Baseline": "{:.1f}%",
                "Coached": "{:.1f}%",
                "Uplift (pp)": "{:+.1f}",
            }),
            use_container_width=True,
        )

    else:
        st.info("Click **▶ Run Simulation** in the sidebar to generate population results.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: HYPOTHESIS REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_report:
    st.header("Hypothesis Validation Report")
    st.caption("UNIQA's 8 conversion-killer hypotheses — tested, not assumed.")

    if st.session_state.get("sim_done"):
        _, _, _, report = run_cached_simulation(n_variants, seed)
        st.markdown(report)
    else:
        st.info("Run the simulation first to generate the hypothesis validation report.")

        st.markdown("""
**What this report shows:**
- Which of UNIQA's 8 hypotheses are CONFIRMED vs NOT CONFIRMED in simulation
- Which sub-types drive each hypothesis (Franz vs Judith vs Peter)
- How many interventions were suppressed (Cold Feet — silence proven correct)
- Conversion uplift per hypothesis where intervention was active
""")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Z3 PROOFS
# ══════════════════════════════════════════════════════════════════════════════
with tab_proofs:
    st.header("Z3 Formal Proofs")
    st.caption("These proofs ran once at startup. They hold for ALL possible inputs — not just tested cases.")

    proof_names = {
        "scope_invariant": {
            "title": "Proof 1: Scope Invariant",
            "description": "No user on the hospital path, 'other persons' path, or Opt.Plus/Premium tariff can **ever** receive coaching.",
            "formal": "∀x. out_of_scope(x) → ¬receives_coaching(x)\nEquivalent to: out_of_scope ∧ receives_coaching = UNSAT",
        },
        "advisor_completeness": {
            "title": "Proof 2: Advisor Completeness",
            "description": "Every out-of-scope user is routed to an advisor. No user silently falls through.",
            "formal": "∀x. out_of_scope(x) → advisor_routed(x)\nEquivalent to: out_of_scope ∧ ¬advisor_routed = UNSAT",
        },
        "h3_cold_feet_mutual_exclusivity": {
            "title": "Proof 3: H3 ⊥ Cold Feet (Mutual Exclusivity)",
            "description": "H3 (trust collapse) and Cold Feet cannot both be SAT simultaneously at Step 7. The Coach never faces an ambiguous decision.",
            "formal": "H3 requires step7_dwell > 30\nCold Feet requires step7_dwell < 20\nConjunction: step7_dwell > 30 ∧ step7_dwell < 20 = UNSAT (by Z3 arithmetic)",
        },
        "cold_feet_silence_guarantee": {
            "title": "Proof 4: Annoyance Bound (Silence Guarantee)",
            "description": "Cold Feet classification always produces intervention_warranted = False. Zero interventions can be fired on Cold Feet sessions.",
            "formal": "∀x. cold_feet_sat(x) → ¬intervention_warranted(x)\nEquivalent to: cold_feet_sat ∧ intervention_warranted = UNSAT",
        },
    }

    for proof_key, proof_def in proof_names.items():
        ok, msg = proofs.get(proof_key, (False, "Not run"))
        status_color = "#22c55e" if ok else "#ef4444"
        status_text = "PROVEN" if ok else "FAILED"

        with st.expander(f"{'✅' if ok else '❌'} {proof_def['title']} — **{status_text}**", expanded=ok):
            st.markdown(f"**Status:** <span style='color:{status_color}'>**{status_text}**</span>", unsafe_allow_html=True)
            st.markdown(f"**What this means:** {proof_def['description']}")
            st.markdown("**Formal encoding:**")
            st.code(proof_def["formal"], language="text")
            st.markdown(f"**Z3 output:** _{msg}_")

    st.divider()
    st.markdown("""
### Why Z3 and not if/else?

These proofs check not just tested inputs, but **all possible inputs simultaneously**.

An if/else check runs on one input at a time. Z3 evaluates the entire input space.

When Z3 returns `UNSAT`, it means **there is no possible combination of inputs** that satisfies
the constraint. This is a mathematical guarantee — not a test coverage claim.

**For the demo:** "Before the first persona ran, we proved these 4 invariants hold for every
possible user input. No edge case can break them."
""")

    if not all_proven:
        st.error("One or more proofs FAILED. The simulation should not be run until invariants are restored.")
    else:
        st.success("All 4 proofs hold. The Coach is formally verified.")
