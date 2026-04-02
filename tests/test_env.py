"""
Tests for LegalReviewEnv graders and environment lifecycle.
Run with: python -m pytest tests/test_env.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from models import Action, Observation, State, StepResult
from environment import LegalReviewEnv
from graders import (
    grade_clause_identification,
    grade_risk_flagging,
    grade_negotiation_strategy,
)


# ---------------------------------------------------------------------------
# Grader tests
# ---------------------------------------------------------------------------

class TestClauseIdentificationGrader:
    GT = ["confidentiality", "term", "governing_law", "obligations", "exclusions",
          "purpose", "return_of_information"]

    def test_perfect_score(self):
        r = grade_clause_identification(self.GT, self.GT)
        assert r.total == pytest.approx(1.0)
        assert r.precision == pytest.approx(1.0)
        assert r.recall == pytest.approx(1.0)

    def test_empty_submission_zero(self):
        r = grade_clause_identification([], self.GT)
        assert r.total == 0.0

    def test_partial_submission(self):
        partial = ["confidentiality", "term", "governing_law"]
        r = grade_clause_identification(partial, self.GT)
        assert 0.0 < r.total < 1.0
        assert r.precision == pytest.approx(1.0)
        assert r.recall < 1.0

    def test_fuzzy_matching(self):
        # Slight naming variation should still match
        r = grade_clause_identification(
            ["confidentiality clause", "governing law", "term and duration"],
            ["confidentiality", "governing_law", "term"]
        )
        assert r.recall > 0.9

    def test_reward_in_range(self):
        r = grade_clause_identification(["some clause"], self.GT)
        assert 0.0 <= r.total <= 1.0


class TestRiskFlaggingGrader:
    GT = [
        {"clause_reference": "fees_and_payment", "severity": "medium",
         "rationale": "Non-refundable fees with interest charges disadvantage customer.",
         "keywords": ["non-refundable", "interest"]},
        {"clause_reference": "indemnification", "severity": "high",
         "rationale": "Asymmetric indemnification exposes customer to broad liability.",
         "keywords": ["asymmetric", "broad"]},
        {"clause_reference": "limitation_of_liability", "severity": "high",
         "rationale": "Cap too low; consequential damages exclusion one-sided.",
         "keywords": ["limitation", "cap", "consequential"]},
    ]

    def test_perfect_match(self):
        submitted = [
            {"clause_reference": "fees_and_payment", "severity": "medium",
             "rationale": "All fees are non-refundable with no exceptions. Interest rate of 1.5% is punitive and asymmetric."},
            {"clause_reference": "indemnification", "severity": "high",
             "rationale": "Customer indemnity is broad covering any law violation. Asymmetric allocation hurts customer badly."},
            {"clause_reference": "limitation_of_liability", "severity": "high",
             "rationale": "Liability cap limited to 12 months. Consequential damages exclusion is one-sided and reduces protection significantly."},
        ]
        r = grade_risk_flagging(submitted, self.GT)
        assert r.total > 0.7

    def test_empty_submission(self):
        r = grade_risk_flagging([], self.GT)
        assert r.total == 0.0

    def test_severity_mismatch_penalty(self):
        submitted = [
            {"clause_reference": "indemnification", "severity": "low",
             "rationale": "Asymmetric indemnification exposes customer to broad liability claims under the law."},
        ]
        r = grade_risk_flagging(submitted, self.GT)
        assert r.severity_accuracy < 0.6

    def test_reward_bounds(self):
        r = grade_risk_flagging([{"clause_reference": "foo", "severity": "high", "rationale": "bad"}], self.GT)
        assert 0.0 <= r.total <= 1.0


class TestNegotiationGrader:
    GT = [
        {"clause_reference": "limitation_of_liability", "priority": 1,
         "issue": "Cap too low", "proposed_direction": "Raise cap to 24 months"},
        {"clause_reference": "indemnification", "priority": 2,
         "issue": "Asymmetric", "proposed_direction": "Narrow customer indemnity"},
        {"clause_reference": "termination", "priority": 3,
         "issue": "No cure period", "proposed_direction": "Add 10-day cure"},
    ]

    def test_good_submission(self):
        submitted = [
            {"clause_reference": "limitation_of_liability", "priority": 1,
             "current_language": "twelve months",
             "proposed_language": "Provider's total liability shall not exceed twenty-four (24) months of fees paid.",
             "justification": "Raise cap to provide adequate protection for material breach and data loss scenarios."},
            {"clause_reference": "indemnification", "priority": 2,
             "current_language": "any and all claims",
             "proposed_language": "Customer shall indemnify Provider only for losses arising from Customer's gross negligence or willful misconduct.",
             "justification": "Narrow indemnity to reduce asymmetric risk exposure for customer."},
            {"clause_reference": "termination", "priority": 3,
             "current_language": "Provider may immediately terminate",
             "proposed_language": "Provider shall provide ten (10) days written notice before terminating for non-payment.",
             "justification": "Add cure period and notice requirement to protect customer from sudden service loss."},
        ]
        r = grade_negotiation_strategy(submitted, self.GT)
        assert r.total > 0.5

    def test_wrong_priority_order(self):
        submitted = [
            {"clause_reference": "termination", "priority": 1,
             "current_language": "terminate immediately",
             "proposed_language": "Add written notice and cure period of thirty days before termination shall take effect.",
             "justification": "Ensure reasonable notice and cure period before service termination."},
            {"clause_reference": "limitation_of_liability", "priority": 2,
             "current_language": "twelve months",
             "proposed_language": "Raise cap to twenty-four months of fees paid prior to claim.",
             "justification": "Higher cap provides better coverage for data breach events."},
        ]
        r1 = grade_negotiation_strategy(submitted, self.GT)
        # Correct priority order should score higher
        submitted_correct = [
            {"clause_reference": "limitation_of_liability", "priority": 1,
             "current_language": "twelve months",
             "proposed_language": "Raise cap to twenty-four months of fees paid prior to claim.",
             "justification": "Higher cap provides better coverage for data breach events."},
            {"clause_reference": "termination", "priority": 2,
             "current_language": "terminate immediately",
             "proposed_language": "Add written notice and cure period of thirty days before termination shall take effect.",
             "justification": "Ensure reasonable notice and cure period before service termination."},
        ]
        r2 = grade_negotiation_strategy(submitted_correct, self.GT)
        assert r2.total >= r1.total

    def test_reward_bounds(self):
        r = grade_negotiation_strategy([], self.GT)
        assert 0.0 <= r.total <= 1.0


# ---------------------------------------------------------------------------
# Environment lifecycle tests
# ---------------------------------------------------------------------------

class TestEnvironmentLifecycle:
    def test_reset_returns_observation(self):
        env = LegalReviewEnv(task_id="clause_identification")
        obs = env.reset()
        assert obs.task_id == "clause_identification"
        assert obs.step_number == 0
        assert len(obs.contract_text) > 100

    def test_state_after_reset(self):
        env = LegalReviewEnv(task_id="risk_flagging")
        env.reset()
        s = env.state()
        assert isinstance(s, State)
        assert s.step_number == 0
        assert not s.done

    def test_step_increments_step_number(self):
        env = LegalReviewEnv(task_id="clause_identification")
        env.reset()
        action = Action(action_type="submit_clauses", payload={"clauses": ["confidentiality"]})
        result = env.step(action)
        assert result.observation.step_number == 1

    def test_done_on_done_action(self):
        env = LegalReviewEnv(task_id="clause_identification")
        env.reset()
        result = env.step(Action(action_type="done", payload={}))
        assert result.done

    def test_error_on_step_after_done(self):
        env = LegalReviewEnv(task_id="clause_identification")
        env.reset()
        env.step(Action(action_type="done", payload={}))
        with pytest.raises(RuntimeError):
            env.step(Action(action_type="done", payload={}))

    def test_reward_in_bounds(self):
        for task in ["clause_identification", "risk_flagging", "negotiation_strategy"]:
            env = LegalReviewEnv(task_id=task)
            env.reset()
            result = env.step(Action(action_type="done", payload={}))
            assert 0.0 <= result.reward.total <= 1.0

    def test_invalid_task_raises(self):
        with pytest.raises(ValueError):
            LegalReviewEnv(task_id="make_coffee")

    def test_all_three_tasks_completable(self):
        tasks_actions = {
            "clause_identification": Action(
                action_type="submit_clauses",
                payload={"clauses": ["confidentiality", "term", "governing_law"]}
            ),
            "risk_flagging": Action(
                action_type="submit_risks",
                payload={"risks": [
                    {"clause_reference": "indemnification", "severity": "high",
                     "rationale": "Asymmetric indemnification exposes customer to very broad liability under the agreement terms."}
                ]}
            ),
            "negotiation_strategy": Action(
                action_type="submit_redlines",
                payload={"redlines": [
                    {"clause_reference": "limitation_of_liability", "priority": 1,
                     "current_language": "twelve months",
                     "proposed_language": "Provider liability shall not exceed twenty-four months of fees paid by Customer.",
                     "justification": "Raise cap to provide adequate protection against material breach."}
                ]}
            )
        }
        for task_id, action in tasks_actions.items():
            env = LegalReviewEnv(task_id=task_id)
            env.reset()
            result = env.step(action)
            assert 0.0 <= result.reward.total <= 1.0, f"Out-of-bounds reward for {task_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
