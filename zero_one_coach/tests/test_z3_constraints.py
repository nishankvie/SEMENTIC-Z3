"""
Z3 Constraint Tests — prove all 4 startup invariants.
These tests are the formal proof artifacts shown in the demo's Z3 Proofs tab.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from engine.z3_scope_prover import (
    prove_scope_invariant,
    prove_advisor_route_completeness,
    prove_coachable,
)
from engine.z3_hypothesis_engine import (
    prove_h3_cold_feet_mutual_exclusivity,
    prove_cold_feet_silence_guarantee,
    discriminate_at_tariff_selection,
    discriminate_at_final_price,
    discriminate_at_personal_data,
)
from engine.variant_generator import generate_variants, generate_population


class TestScopeProofs(unittest.TestCase):

    def test_scope_invariant(self):
        """No out-of-scope user can ever receive coaching."""
        proven, msg = prove_scope_invariant()
        self.assertTrue(proven, f"Scope invariant failed: {msg}")

    def test_advisor_completeness(self):
        """Every out-of-scope user is routed to advisor."""
        proven, msg = prove_advisor_route_completeness()
        self.assertTrue(proven, f"Advisor completeness failed: {msg}")

    def test_in_scope_paths_are_coachable(self):
        """Doctor visits + myself + online tariff → coachable."""
        in_scope_cases = [
            {"coverage_type": "doctor_visits", "beneficiary": "myself"},
            {"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "start"},
            {"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "optimal"},
        ]
        for case in in_scope_cases:
            ok, reason = prove_coachable(case)
            self.assertTrue(ok, f"Expected coachable, got False: {case} → {reason}")

    def test_out_of_scope_paths_are_not_coachable(self):
        """Hospital / other persons / premium tariffs → not coachable."""
        out_of_scope_cases = [
            {"coverage_type": "hospital", "beneficiary": "myself"},
            {"coverage_type": "doctor_visits", "beneficiary": "other"},
            {"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "opt_plus"},
            {"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "premium"},
        ]
        for case in out_of_scope_cases:
            ok, reason = prove_coachable(case)
            self.assertFalse(ok, f"Expected not coachable, got True: {case}")


class TestHypothesisProofs(unittest.TestCase):

    def test_h3_cold_feet_mutual_exclusivity(self):
        """H3 and Cold Feet at Step 7 are formally mutually exclusive."""
        proven, msg = prove_h3_cold_feet_mutual_exclusivity()
        self.assertTrue(proven, f"Mutual exclusivity failed: {msg}")

    def test_cold_feet_silence_guarantee(self):
        """Cold Feet classification always suppresses intervention."""
        proven, msg = prove_cold_feet_silence_guarantee()
        self.assertTrue(proven, f"Silence guarantee failed: {msg}")


class TestHypothesisDiscriminator(unittest.TestCase):

    def test_cold_feet_at_step4(self):
        """Fast traversal with no engagement → Cold Feet, no intervention."""
        signals = {
            "dwell_time_seconds": 8,
            "tariff_hovers": 0,
            "opt_plus_clicked": False,
            "back_nav_after_opt_plus": False,
            "tab_opened_external": False,
            "term_hover": False,
            "cancel_hover": False,
            "selected_tariff": "start",
        }
        result = discriminate_at_tariff_selection(signals)
        self.assertEqual(result.hypothesis, "COLD_FEET")
        self.assertFalse(result.intervention_warranted)

    def test_h2_advisory_frustration(self):
        """Opt.Plus clicked then back navigation → H2."""
        signals = {
            "dwell_time_seconds": 30,
            "tariff_hovers": 2,
            "opt_plus_clicked": True,
            "back_nav_after_opt_plus": True,
            "tab_opened_external": False,
            "term_hover": False,
            "cancel_hover": False,
            "selected_tariff": None,
        }
        result = discriminate_at_tariff_selection(signals)
        self.assertEqual(result.hypothesis, "H2")
        self.assertTrue(result.intervention_warranted)

    def test_h6_ropo_departure(self):
        """External tab opened → H6 ROPO."""
        signals = {
            "dwell_time_seconds": 25,
            "tariff_hovers": 1,
            "opt_plus_clicked": False,
            "back_nav_after_opt_plus": False,
            "tab_opened_external": True,
            "term_hover": False,
            "cancel_hover": False,
            "selected_tariff": None,
        }
        result = discriminate_at_tariff_selection(signals)
        self.assertEqual(result.hypothesis, "H6")
        self.assertTrue(result.intervention_warranted)

    def test_h4_cognitive_overload(self):
        """Long dwell + many hovers + no selection → H4."""
        signals = {
            "dwell_time_seconds": 65,
            "tariff_hovers": 7,
            "opt_plus_clicked": False,
            "back_nav_after_opt_plus": False,
            "tab_opened_external": False,
            "term_hover": False,
            "cancel_hover": False,
            "selected_tariff": None,
        }
        result = discriminate_at_tariff_selection(signals)
        self.assertEqual(result.hypothesis, "H4")
        self.assertTrue(result.intervention_warranted)

    def test_h3_trust_collapse(self):
        """Fast Step 4 + slow Step 7 + large delta + cancel hovers → H3."""
        step4 = {"dwell_time_seconds": 22}
        step7 = {
            "dwell_time_seconds": 48,
            "cancel_hovers": 4,
            "price_delta_shown": 15.0,
            "back_to_tariff_step": False,
        }
        result = discriminate_at_final_price(step4, step7)
        self.assertEqual(result.hypothesis, "H3")
        self.assertTrue(result.intervention_warranted)

    def test_cold_feet_at_step7(self):
        """Fast traversal everywhere → Cold Feet, suppressed."""
        step4 = {"dwell_time_seconds": 12}
        step7 = {
            "dwell_time_seconds": 10,
            "cancel_hovers": 0,
            "price_delta_shown": 3.0,
            "back_to_tariff_step": False,
        }
        result = discriminate_at_final_price(step4, step7)
        self.assertEqual(result.hypothesis, "COLD_FEET")
        self.assertFalse(result.intervention_warranted)

    def test_h7_ssn_trust_barrier(self):
        """Long dwell at personal data → H7."""
        signals = {"dwell_time_seconds": 75, "back_navigation": False, "completed": True}
        result = discriminate_at_personal_data(signals)
        self.assertEqual(result.hypothesis, "H7")
        self.assertTrue(result.intervention_warranted)


class TestVariantGenerator(unittest.TestCase):

    def test_all_subtypes_generate_valid_variants(self):
        """All 8 sub-types produce variants satisfying their Z3 constraints."""
        from engine.variant_generator import SUB_TYPE_REGISTRY, SUB_TYPE_SEGMENT
        for sub_type in SUB_TYPE_REGISTRY:
            variants = generate_variants(sub_type, n=3)
            self.assertGreater(len(variants), 0, f"No variants generated for {sub_type}")
            for v in variants:
                self.assertEqual(v.sub_type, sub_type)
                self.assertGreaterEqual(v.price_tolerance, 0.0)
                self.assertLessEqual(v.price_tolerance, 1.0)
                self.assertGreaterEqual(v.digital_confidence, 0.0)
                self.assertLessEqual(v.digital_confidence, 1.0)

    def test_franz_digital_confidence_floor(self):
        """Franz variants must have digital_confidence >= 0.5 (64% ever bought online)."""
        variants = generate_variants("franz_price", n=5)
        for v in variants:
            self.assertGreaterEqual(v.digital_confidence, 0.5,
                                    f"Franz digital_confidence below floor: {v.digital_confidence}")

    def test_franz_price_tolerance_cap(self):
        """franz_price sub-type must have price_tolerance < 0.30."""
        variants = generate_variants("franz_price", n=5)
        for v in variants:
            self.assertLess(v.price_tolerance, 0.30,
                            f"franz_price tolerance too high: {v.price_tolerance}")

    def test_peter_complexity_tolerance_cap(self):
        """All Peter variants must have complexity_tolerance <= 0.40."""
        for sub in ("peter_overwhelmed", "peter_urgent", "peter_browsing"):
            variants = generate_variants(sub, n=3)
            for v in variants:
                self.assertLessEqual(v.complexity_tolerance, 0.40,
                                     f"{sub} complexity_tolerance too high: {v.complexity_tolerance}")

    def test_judith_advisor_dependency_floor(self):
        """All Judith variants must have advisor_dependency >= 0.40 (78% purchase via advisor)."""
        for sub in ("judith_research", "judith_pressured"):
            variants = generate_variants(sub, n=3)
            for v in variants:
                self.assertGreaterEqual(v.advisor_dependency, 0.40,
                                        f"{sub} advisor_dependency below floor: {v.advisor_dependency}")

    def test_population_generation(self):
        """generate_population returns correct proportional mix."""
        variants = generate_population(total=30)
        segments = [v.segment for v in variants]
        franz_frac = segments.count("franz") / len(segments)
        judith_frac = segments.count("judith") / len(segments)
        # Allow ±15% tolerance due to rounding
        self.assertAlmostEqual(franz_frac, 0.50, delta=0.15)
        self.assertAlmostEqual(judith_frac, 0.30, delta=0.15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
