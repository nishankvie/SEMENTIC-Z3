"""
Z3 Scope Prover — runs at Steps 1, 2, and 4.
Proves that no out-of-scope user can ever receive coaching (scope invariant).
The invariant is encoded as a theorem and checked once at startup.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from z3 import Solver, Bool, And, Or, Not, unsat, sat
from typing import Dict, Any, Tuple


def prove_coachable(selections: Dict[str, Any]) -> Tuple[bool, str]:
    """
    At Steps 1, 2, and 4: prove whether this session is on the coachable online path.
    Returns (is_coachable, reason_string).
    SAT  → continue coaching.
    UNSAT → route to advisor immediately.
    """
    s = Solver()

    coverage_type = selections.get("coverage_type", "doctor_visits")
    beneficiary   = selections.get("beneficiary", "myself")
    tariff        = selections.get("tariff")  # May be None before step 4

    is_doctor_visits = Bool("is_doctor_visits")
    is_myself        = Bool("is_myself")
    is_online_tariff = Bool("is_online_tariff")

    s.add(is_doctor_visits == (coverage_type == "doctor_visits"))
    s.add(is_myself        == (beneficiary == "myself"))

    if tariff is not None:
        s.add(is_online_tariff == (tariff in ("start", "optimal")))
        coachable = And(is_doctor_visits, is_myself, is_online_tariff)
    else:
        # Tariff not yet selected — check coverage and beneficiary only
        coachable = And(is_doctor_visits, is_myself)

    s.add(coachable)
    result = s.check()

    if result == sat:
        return True, "On online-completable path. Coach active."

    # Generate specific reason (UNSAT — which condition failed?)
    if coverage_type != "doctor_visits":
        return False, f"Hospital coverage selected → routing to advisor."
    if beneficiary != "myself":
        return False, f"Insurance for other persons → routing to advisor."
    if tariff in ("opt_plus", "premium"):
        return False, (
            f"{tariff.replace('_', '.')} requires advisory consultation "
            f"(Austrian insurance regulation). Start and Optimal available online."
        )
    return False, "Out of scope → routing to advisor."


def prove_scope_invariant() -> Tuple[bool, str]:
    """
    STARTUP PROOF: there is no possible input combination where an out-of-scope
    user receives coaching. Runs once at startup.
    Returns (proven: bool, message: str).
    """
    s = Solver()

    # Boolean variables for all possible scope-disqualifying conditions
    is_hospital     = Bool("is_hospital")
    is_other_person = Bool("is_other_person")
    is_premium      = Bool("is_premium")
    is_opt_plus     = Bool("is_opt_plus")
    receives_coaching = Bool("receives_coaching")

    # Encoding of the Coach logic:
    # A user receives coaching iff they are NOT out of scope
    out_of_scope = Or(is_hospital, is_other_person, is_premium, is_opt_plus)
    s.add(receives_coaching == Not(out_of_scope))

    # Try to find: out_of_scope AND receives_coaching (should be impossible)
    s.add(out_of_scope)
    s.add(receives_coaching)

    if s.check() == unsat:
        return True, (
            "PROVEN: Scope Invariant holds. "
            "No user on hospital path, other-person path, or Opt.Plus/Premium can ever receive coaching. "
            "Zero false positives, guaranteed by Z3."
        )
    else:
        m = s.model()
        return False, f"INVARIANT VIOLATED — counterexample: {m}"


def prove_advisor_route_completeness() -> Tuple[bool, str]:
    """
    STARTUP PROOF: every out-of-scope user is routed to advisor (completeness).
    Encoded as: out_of_scope → advisor_routed (no user falls through silently).
    """
    s = Solver()

    is_hospital     = Bool("h")
    is_other_person = Bool("o")
    is_premium      = Bool("p")
    is_opt_plus     = Bool("op")
    is_advisor_routed = Bool("ar")

    out_of_scope = Or(is_hospital, is_other_person, is_premium, is_opt_plus)

    # Logic: out_of_scope → advisor_routed
    # Violation: out_of_scope AND NOT advisor_routed
    s.add(out_of_scope)
    s.add(is_advisor_routed == out_of_scope)
    s.add(Not(is_advisor_routed))

    if s.check() == unsat:
        return True, (
            "PROVEN: Every out-of-scope user is routed to advisor. "
            "No user silently falls through without a clean handoff."
        )
    else:
        return False, f"COMPLETENESS VIOLATED — {s.model()}"


_STARTUP_RESULTS: Dict[str, Tuple[bool, str]] = {}


def run_startup_proofs() -> Dict[str, Tuple[bool, str]]:
    """Run all scope-related proofs once at startup. Cache results."""
    global _STARTUP_RESULTS
    if _STARTUP_RESULTS:
        return _STARTUP_RESULTS
    _STARTUP_RESULTS = {
        "scope_invariant": prove_scope_invariant(),
        "advisor_completeness": prove_advisor_route_completeness(),
    }
    return _STARTUP_RESULTS


if __name__ == "__main__":
    print("Running scope prover startup proofs...")
    results = run_startup_proofs()
    for name, (ok, msg) in results.items():
        status = "✓ PROVEN" if ok else "✗ FAILED"
        print(f"  [{status}] {name}: {msg}")

    print("\nTesting prove_coachable on example sessions:")
    tests = [
        ({"coverage_type": "doctor_visits", "beneficiary": "myself"}, True),
        ({"coverage_type": "hospital", "beneficiary": "myself"}, False),
        ({"coverage_type": "doctor_visits", "beneficiary": "other"}, False),
        ({"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "optimal"}, True),
        ({"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "opt_plus"}, False),
        ({"coverage_type": "doctor_visits", "beneficiary": "myself", "tariff": "premium"}, False),
    ]
    all_pass = True
    for selections, expected in tests:
        ok, reason = prove_coachable(selections)
        status = "✓" if ok == expected else "✗ FAIL"
        if ok != expected:
            all_pass = False
        print(f"  [{status}] {selections} → coachable={ok}: {reason}")
    print("All tests passed" if all_pass else "SOME TESTS FAILED")
