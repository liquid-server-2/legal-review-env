"""
LegalReviewEnv — core environment implementing the OpenEnv spec.
Manages episode state, dispatches to graders, computes shaped rewards.
"""
from __future__ import annotations
import copy
import uuid
from typing import Any, Dict, List, Optional

from models import Action, Observation, Reward, State, StepResult
from contracts import CONTRACTS, TASK_CONTRACTS
from graders import (
    grade_clause_identification,
    grade_risk_flagging,
    grade_negotiation_strategy,
)

MAX_STEPS = 10
LOOP_PENALTY_THRESHOLD = 3   # penalise after this many identical action types
LOOP_PENALTY_VALUE = 0.05    # subtracted per repeat above threshold


class LegalReviewEnv:
    """
    OpenEnv-compliant environment for legal contract review.

    Tasks:
        - clause_identification (easy)
        - risk_flagging (medium)
        - negotiation_strategy (hard)
    """

    VALID_TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]

    def __init__(self, task_id: str = "clause_identification") -> None:
        if task_id not in self.VALID_TASKS:
            raise ValueError(f"task_id must be one of {self.VALID_TASKS}")
        self._task_id = task_id
        self._state: Dict[str, Any] = {}
        self._episode_id: str = ""
        self.reset()

    # ------------------------------------------------------------------
    # OpenEnv API
    # ------------------------------------------------------------------

    def reset(self) -> Observation:
        """Start a new episode. Returns initial observation."""
        self._episode_id = str(uuid.uuid4())
        contract_id = TASK_CONTRACTS[self._task_id]
        contract = CONTRACTS[contract_id]

        self._state = {
            "task_id": self._task_id,
            "contract_id": contract_id,
            "contract": contract,
            "step_number": 0,
            "done": False,
            "cumulative_reward": 0.0,
            "last_action_type": None,
            "action_history": [],
            "best_reward": 0.0,
        }

        context: Dict[str, Any] = {}
        if self._task_id == "negotiation_strategy":
            # Pre-populate the risk context so the agent can focus on strategy
            gt = contract["ground_truth"]
            context["known_risks"] = [
                {"clause_reference": r["clause_reference"], "severity": r["severity"]}
                for r in gt["risks"]
            ]

        return Observation(
            contract_text=contract["text"],
            task_id=self._task_id,
            step_number=0,
            context=context,
            message=f"Episode started. Task: {self._task_id}. Max steps: {MAX_STEPS}."
        )

    def step(self, action: Action) -> StepResult:
        """Process an agent action and return the next observation + reward."""
        if self._state["done"]:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._state["step_number"] += 1
        step_num = self._state["step_number"]
        self._state["action_history"].append(action.action_type)
        self._state["last_action_type"] = action.action_type

        # Compute loop penalty
        recent = self._state["action_history"][-LOOP_PENALTY_THRESHOLD:]
        if len(recent) == LOOP_PENALTY_THRESHOLD and len(set(recent)) == 1:
            loop_penalty = LOOP_PENALTY_VALUE
        else:
            loop_penalty = 0.0

        # Dispatch to grader
        reward = self._compute_reward(action, loop_penalty)

        # Track best reward (for partial-progress signal)
        if reward.total > self._state["best_reward"]:
            self._state["best_reward"] = reward.total
        self._state["cumulative_reward"] += reward.total

        # Episode ends on 'done' action or max steps
        done = (
            action.action_type == "done"
            or step_num >= MAX_STEPS
            or reward.total >= 0.95  # early success
        )
        self._state["done"] = done

        # Build next observation
        context: Dict[str, Any] = {}
        if self._task_id == "negotiation_strategy":
            gt = self._state["contract"]["ground_truth"]
            context["known_risks"] = [
                {"clause_reference": r["clause_reference"], "severity": r["severity"]}
                for r in gt["risks"]
            ]
        context["best_reward_so_far"] = self._state["best_reward"]

        obs = Observation(
            contract_text=self._state["contract"]["text"],
            task_id=self._task_id,
            step_number=step_num,
            context=context,
            message=self._step_message(reward, done, loop_penalty)
        )

        return StepResult(
            observation=obs,
            reward=reward,
            done=done,
            info={
                "episode_id": self._episode_id,
                "step": step_num,
                "max_steps": MAX_STEPS,
                "best_reward": self._state["best_reward"],
            }
        )

    def state(self) -> State:
        """Return the current internal state (for inspection/debugging)."""
        return State(
            task_id=self._state["task_id"],
            step_number=self._state["step_number"],
            max_steps=MAX_STEPS,
            contract_id=self._state["contract_id"],
            done=self._state["done"],
            cumulative_reward=self._state["cumulative_reward"],
            last_action_type=self._state["last_action_type"],
            previous_actions=list(self._state["action_history"]),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_reward(self, action: Action, loop_penalty: float) -> Reward:
        gt = self._state["contract"]["ground_truth"]

        if action.action_type == "done":
            # No new submission — return last best reward (shaped)
            r = Reward(total=max(0.0, self._state["best_reward"] - loop_penalty))
            r.loop_penalty = loop_penalty
            return r

        if action.action_type == "request_section":
            # Provide a small reward for targeted information gathering
            r = Reward(total=0.05, loop_penalty=loop_penalty)
            r.total = max(0.0, r.total - loop_penalty)
            return r

        if self._task_id == "clause_identification":
            if action.action_type != "submit_clauses":
                return Reward(total=0.0, loop_penalty=loop_penalty)
            submitted = action.payload.get("clauses", [])
            r = grade_clause_identification(submitted, gt["clauses"])

        elif self._task_id == "risk_flagging":
            if action.action_type != "submit_risks":
                return Reward(total=0.0, loop_penalty=loop_penalty)
            submitted = action.payload.get("risks", [])
            r = grade_risk_flagging(submitted, gt["risks"])

        elif self._task_id == "negotiation_strategy":
            if action.action_type != "submit_redlines":
                return Reward(total=0.0, loop_penalty=loop_penalty)
            submitted = action.payload.get("redlines", [])
            r = grade_negotiation_strategy(submitted, gt["redlines"])

        else:
            return Reward(total=0.0)

        r.loop_penalty = loop_penalty
        r.total = max(0.0, round(r.total - loop_penalty, 4))
        return r

    def _step_message(self, reward: Reward, done: bool, loop_penalty: float) -> str:
        msgs = [f"Step reward: {reward.total:.3f}"]
        if loop_penalty > 0:
            msgs.append(f"Loop penalty applied: -{loop_penalty:.2f}")
        if done:
            msgs.append(f"Episode complete. Best reward: {self._state['best_reward']:.3f}.")
        return " | ".join(msgs)
