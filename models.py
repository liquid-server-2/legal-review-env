"""
Typed Pydantic models for the Legal Review OpenEnv environment.
Defines Observation, Action, Reward, and State models per the OpenEnv spec.
"""
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ClauseSubmission(BaseModel):
    """Used in Task 1: clause identification."""
    clauses: List[str] = Field(
        description="List of identified clause types, e.g. ['indemnification', 'termination']"
    )


class RiskItem(BaseModel):
    """One flagged risk item for Task 2."""
    clause_reference: str = Field(description="Short label of the clause containing the risk")
    severity: Literal["low", "medium", "high"]
    rationale: str = Field(description="One or two sentence explanation of why this is risky")


class RiskSubmission(BaseModel):
    """Used in Task 2: risk flagging."""
    risks: List[RiskItem]


class RedlineItem(BaseModel):
    """One proposed change for Task 3."""
    clause_reference: str
    priority: int = Field(description="1 = highest priority to negotiate", ge=1)
    current_language: str = Field(description="The problematic text (verbatim or paraphrase)")
    proposed_language: str = Field(description="The replacement text the agent proposes")
    justification: str = Field(description="Why this change protects the client")


class RedlineSubmission(BaseModel):
    """Used in Task 3: negotiation strategy."""
    redlines: List[RedlineItem]


# ---------------------------------------------------------------------------
# Core OpenEnv models
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """Returned by reset() and step()."""
    contract_text: str = Field(description="Full contract text the agent should review")
    task_id: Literal["clause_identification", "risk_flagging", "negotiation_strategy"]
    step_number: int = Field(ge=0)
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific context (e.g. prior clause list for Task 2)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable status message from the environment"
    )


class Action(BaseModel):
    """Sent by the agent to step()."""
    action_type: Literal["submit_clauses", "submit_risks", "submit_redlines", "request_section", "done"]
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-type-specific payload (see sub-models)"
    )


class Reward(BaseModel):
    """Returned by step() as part of the step result."""
    total: float = Field(ge=0.0, le=1.0, description="Composite reward [0.0, 1.0]")
    precision: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    severity_accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    loop_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    breakdown: Dict[str, float] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Full response from step()."""
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class State(BaseModel):
    """Returned by state() — full internal environment state."""
    task_id: str
    step_number: int
    max_steps: int
    contract_id: str
    done: bool
    cumulative_reward: float
    last_action_type: Optional[str] = None
    previous_actions: List[str] = Field(default_factory=list)
