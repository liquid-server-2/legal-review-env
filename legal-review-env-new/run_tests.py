#!/usr/bin/env python3
"""
run_tests.py — Self-contained test runner for LegalReviewEnv.
Does NOT require pytest or network access. Uses only stdlib + the env's own modules.
Run with: python run_tests.py
"""
from __future__ import annotations
import sys
import traceback
from typing import Callable, List, Tuple

# ── Minimal stubs for external deps ────────────────────────────────────────

import types, builtins

# Pydantic v2 stub
pydantic_mod = types.ModuleType("pydantic")

class _BaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"

def _field(*args, **kwargs):
    return None

pydantic_mod.BaseModel = _BaseModel
pydantic_mod.Field = _field
sys.modules["pydantic"] = pydantic_mod

# ── Import env modules ──────────────────────────────────────────────────────
from graders import (
    grade_clause_identification,
    grade_risk_flagging,
    grade_negotiation_strategy,
    _fuzzy_match,
    _normalise,
)
from models import Action, Observation, Reward, State, StepResult
from environment import LegalReviewEnv

# ── Test harness ────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
_tests: List[Tuple[str, Callable]] = []
_results: List[bool] = []


def test(name: str):
    def decorator(fn: Callable):
        _tests.append((name, fn))
        return fn
    return decorator


def approx(a: float, b: float, tol: float = 1e-4) -> bool:
    return abs(a - b) <= tol


def assert_true(cond: bool, msg: str = ""):
    if not cond:
        raise AssertionError(msg or "Assertion failed")


def assert_between(val: float, lo: float, hi: float, label: str = ""):
    if not (lo <= val <= hi):
        raise AssertionError(f"{label or 'value'} {val:.4f} not in [{lo}, {hi}]")


# ── Tests: fuzzy matching ───────────────────────────────────────────────────

@test("normalise removes underscores and lowercases")
def _():
    assert_true(_normalise("Limitation_Of_Liability") == "limitation of liability")

@test("fuzzy_match: exact match")
def _():
    assert_true(_fuzzy_match("indemnification", ["indemnification", "term"]))

@test("fuzzy_match: substring match")
def _():
    assert_true(_fuzzy_match("governing law clause", ["governing_law"]))

@test("fuzzy_match: no match")
def _():
    assert_true(not _fuzzy_match("xyz_unknown", ["indemnification", "term"]))

@test("fuzzy_match: token overlap ≥50%")
def _():
    assert_true(_fuzzy_match("limitation liability", ["limitation_of_liability"]))


# ── Tests: Task 1 grader ────────────────────────────────────────────────────

GT_CLAUSES = ["confidentiality", "term", "governing_law", "obligations",
              "exclusions", "purpose", "return_of_information"]

@test("T1: perfect submission → 1.0")
def _():
    r = grade_clause_identification(GT_CLAUSES, GT_CLAUSES)
    assert_true(approx(r.total, 1.0), f"Expected 1.0, got {r.total}")

@test("T1: empty submission → 0.0")
def _():
    r = grade_clause_identification([], GT_CLAUSES)
    assert_true(approx(r.total, 0.0))

@test("T1: partial submission → 0 < score < 1")
def _():
    r = grade_clause_identification(["confidentiality", "term"], GT_CLAUSES)
    assert_between(r.total, 0.01, 0.99, "partial T1 score")

@test("T1: precision = 1.0 when all submitted are correct")
def _():
    r = grade_clause_identification(["confidentiality", "term"], GT_CLAUSES)
    assert_true(approx(r.precision, 1.0))

@test("T1: reward always in [0, 1]")
def _():
    for submitted in [[], ["foo"], GT_CLAUSES, ["foo", "bar", "baz"]]:
        r = grade_clause_identification(submitted, GT_CLAUSES)
        assert_between(r.total, 0.0, 1.0, f"T1 reward for {submitted}")


# ── Tests: Task 2 grader ────────────────────────────────────────────────────

GT_RISKS = [
    {"clause_reference": "fees_and_payment", "severity": "medium",
     "rationale": "x", "keywords": ["non-refundable", "interest"]},
    {"clause_reference": "indemnification", "severity": "high",
     "rationale": "x", "keywords": ["asymmetric", "broad"]},
    {"clause_reference": "limitation_of_liability", "severity": "high",
     "rationale": "x", "keywords": ["limitation", "cap", "consequential"]},
]

@test("T2: empty submission → 0.0")
def _():
    r = grade_risk_flagging([], GT_RISKS)
    assert_true(approx(r.total, 0.0))

@test("T2: correct severity boosts score vs wrong severity")
def _():
    correct = [{"clause_reference": "indemnification", "severity": "high",
                "rationale": "Asymmetric indemnification exposes customer to very broad liability under the agreement and related regulations."}]
    wrong = [{"clause_reference": "indemnification", "severity": "low",
              "rationale": "Asymmetric indemnification exposes customer to very broad liability under the agreement and related regulations."}]
    r_c = grade_risk_flagging(correct, GT_RISKS)
    r_w = grade_risk_flagging(wrong, GT_RISKS)
    assert_true(r_c.total > r_w.total, f"correct={r_c.total:.3f} wrong={r_w.total:.3f}")

@test("T2: fuzzy clause reference matching")
def _():
    submitted = [{"clause_reference": "limitation of liability",
                  "severity": "high",
                  "rationale": "Cap is too low. The consequential damages exclusion is one-sided and reduces customer protection significantly."}]
    r = grade_risk_flagging(submitted, GT_RISKS)
    assert_true(r.recall > 0.0, "Should match 'limitation_of_liability' fuzzily")

@test("T2: reward always in [0, 1]")
def _():
    cases = [
        [],
        [{"clause_reference": "foo", "severity": "high", "rationale": "bad"}],
        [{"clause_reference": "indemnification", "severity": "high",
          "rationale": "Asymmetric indemnification exposes customer to very broad liability under agreement. Material risk."}],
    ]
    for c in cases:
        r = grade_risk_flagging(c, GT_RISKS)
        assert_between(r.total, 0.0, 1.0, f"T2 reward")

@test("T2: high recall + good rationale gives score > 0.6")
def _():
    submitted = [
        {"clause_reference": "fees_and_payment", "severity": "medium",
         "rationale": "All fees are non-refundable with no exceptions. The interest rate of 1.5% per month is excessive and compounds customer liability."},
        {"clause_reference": "indemnification", "severity": "high",
         "rationale": "Customer indemnity is overly broad. Asymmetric indemnification exposes customer to wide liability for any law violation."},
        {"clause_reference": "limitation_of_liability", "severity": "high",
         "rationale": "Liability cap limited to 12 months of fees. Consequential damages exclusion is one-sided and the overall limitation is inadequate."},
    ]
    r = grade_risk_flagging(submitted, GT_RISKS)
    assert_true(r.total > 0.6, f"Expected > 0.6, got {r.total:.3f}")


# ── Tests: Task 3 grader ────────────────────────────────────────────────────

GT_REDLINES = [
    {"clause_reference": "limitation_of_liability", "priority": 1,
     "issue": "cap low", "proposed_direction": "raise cap"},
    {"clause_reference": "indemnification", "priority": 2,
     "issue": "asymmetric", "proposed_direction": "narrow"},
    {"clause_reference": "termination", "priority": 3,
     "issue": "no cure", "proposed_direction": "add cure period"},
]

@test("T3: empty submission → 0.0")
def _():
    r = grade_negotiation_strategy([], GT_REDLINES)
    assert_true(approx(r.total, 0.0))

@test("T3: correct priority ordering scores higher")
def _():
    correct_order = [
        {"clause_reference": "limitation_of_liability", "priority": 1,
         "current_language": "twelve months of fees",
         "proposed_language": "Provider liability shall not exceed twenty-four months of fees paid. Data breach events shall not be subject to the cap limitation.",
         "justification": "Raise cap to provide adequate protection against material breach scenarios."},
        {"clause_reference": "indemnification", "priority": 2,
         "current_language": "any and all claims",
         "proposed_language": "Customer shall indemnify Provider only for losses arising from Customer's gross negligence or willful misconduct.",
         "justification": "Narrow indemnity to reduce asymmetric risk exposure."},
    ]
    wrong_order = [
        {"clause_reference": "indemnification", "priority": 1,
         "current_language": "any and all claims",
         "proposed_language": "Customer shall indemnify Provider only for losses arising from Customer's gross negligence or willful misconduct.",
         "justification": "Narrow indemnity to reduce asymmetric risk exposure."},
        {"clause_reference": "limitation_of_liability", "priority": 2,
         "current_language": "twelve months of fees",
         "proposed_language": "Provider liability shall not exceed twenty-four months of fees paid. Data breach events shall not be subject to the cap limitation.",
         "justification": "Raise cap to provide adequate protection."},
    ]
    r_correct = grade_negotiation_strategy(correct_order, GT_REDLINES)
    r_wrong = grade_negotiation_strategy(wrong_order, GT_REDLINES)
    assert_true(r_correct.total >= r_wrong.total,
                f"correct={r_correct.total:.3f} wrong={r_wrong.total:.3f}")

@test("T3: substantive proposed language scores higher than thin language")
def _():
    good_lang = [{"clause_reference": "limitation_of_liability", "priority": 1,
                   "current_language": "twelve months",
                   "proposed_language": "Provider liability shall not exceed twenty-four months of fees paid by Customer prior to the claim. This limitation shall not apply to breaches of confidentiality or gross negligence.",
                   "justification": "Raise cap and add carve-outs for material breaches."}]
    thin_lang = [{"clause_reference": "limitation_of_liability", "priority": 1,
                   "current_language": "twelve months",
                   "proposed_language": "change this",
                   "justification": "Fix it"}]
    r_good = grade_negotiation_strategy(good_lang, GT_REDLINES)
    r_thin = grade_negotiation_strategy(thin_lang, GT_REDLINES)
    assert_true(r_good.total > r_thin.total,
                f"good={r_good.total:.3f} thin={r_thin.total:.3f}")

@test("T3: reward always in [0, 1]")
def _():
    cases = [[], [{"clause_reference": "foo", "priority": 1,
                   "current_language": "x", "proposed_language": "y", "justification": "z"}]]
    for c in cases:
        r = grade_negotiation_strategy(c, GT_REDLINES)
        assert_between(r.total, 0.0, 1.0)


# ── Tests: Environment lifecycle ────────────────────────────────────────────

@test("Env: invalid task raises ValueError")
def _():
    try:
        LegalReviewEnv(task_id="make_coffee")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass

@test("Env: reset() returns Observation with step=0")
def _():
    env = LegalReviewEnv(task_id="clause_identification")
    obs = env.reset()
    assert_true(obs.step_number == 0, f"Expected 0, got {obs.step_number}")
    assert_true(len(obs.contract_text) > 50, "Contract text too short")

@test("Env: state() reflects reset")
def _():
    env = LegalReviewEnv(task_id="risk_flagging")
    env.reset()
    s = env.state()
    assert_true(s.step_number == 0)
    assert_true(not s.done)

@test("Env: step() increments step_number")
def _():
    env = LegalReviewEnv(task_id="clause_identification")
    env.reset()
    result = env.step(Action(action_type="submit_clauses", payload={"clauses": ["term"]}))
    assert_true(result.observation.step_number == 1)

@test("Env: done action ends episode")
def _():
    env = LegalReviewEnv(task_id="clause_identification")
    env.reset()
    result = env.step(Action(action_type="done", payload={}))
    assert_true(result.done)

@test("Env: step after done raises RuntimeError")
def _():
    env = LegalReviewEnv(task_id="clause_identification")
    env.reset()
    env.step(Action(action_type="done", payload={}))
    try:
        env.step(Action(action_type="done", payload={}))
        raise AssertionError("Should have raised RuntimeError")
    except RuntimeError:
        pass

@test("Env: all tasks complete without error")
def _():
    task_actions = {
        "clause_identification": Action(action_type="submit_clauses",
            payload={"clauses": ["confidentiality", "term", "governing_law"]}),
        "risk_flagging": Action(action_type="submit_risks", payload={"risks": [
            {"clause_reference": "indemnification", "severity": "high",
             "rationale": "Asymmetric indemnification exposes customer to very broad liability and significant legal risk under the agreement."}
        ]}),
        "negotiation_strategy": Action(action_type="submit_redlines", payload={"redlines": [
            {"clause_reference": "limitation_of_liability", "priority": 1,
             "current_language": "twelve months", "justification": "Raise cap for protection.",
             "proposed_language": "Provider liability shall not exceed twenty-four months of fees paid. Breach of confidentiality shall not be subject to this limitation."}
        ]})
    }
    for task_id, action in task_actions.items():
        env = LegalReviewEnv(task_id=task_id)
        env.reset()
        result = env.step(action)
        assert_between(result.reward.total, 0.0, 1.0, f"task={task_id}")

@test("Env: loop penalty applied after 3 identical noop actions")
def _():
    env = LegalReviewEnv(task_id="clause_identification")
    env.reset()
    results = []
    for _ in range(5):
        result = env.step(Action(action_type="submit_clauses", payload={"clauses": ["term"]}))
        results.append(result)
        if result.done:
            break
    # After 3 identical actions, at least one reward should show loop_penalty > 0
    penalties = [r.reward.loop_penalty for r in results]
    assert_true(any(p > 0 for p in penalties),
                f"Expected loop penalty > 0 in {penalties}")

@test("Env: negotiation_strategy context includes known_risks")
def _():
    env = LegalReviewEnv(task_id="negotiation_strategy")
    obs = env.reset()
    assert_true("known_risks" in obs.context, "known_risks missing from context")
    assert_true(len(obs.context["known_risks"]) > 0)

@test("Env: reset() clears prior episode state")
def _():
    env = LegalReviewEnv(task_id="clause_identification")
    env.reset()
    env.step(Action(action_type="done", payload={}))
    obs2 = env.reset()
    s = env.state()
    assert_true(s.step_number == 0)
    assert_true(not s.done)


# ── Run all tests ────────────────────────────────────────────────────────────

def run():
    passed = 0
    failed = 0
    print(f"\n{'='*60}")
    print(f"  LegalReviewEnv — Test Suite")
    print(f"{'='*60}\n")

    for name, fn in _tests:
        try:
            fn()
            print(f"  {PASS}  {name}")
            passed += 1
        except Exception as e:
            print(f"  {FAIL}  {name}")
            print(f"         → {e}")
            failed += 1

    total = passed + failed
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
    else:
        print("  ✓ All tests passed")
    print(f"{'='*60}\n")
    return failed == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
