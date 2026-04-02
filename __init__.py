"""
LegalReviewEnv — OpenEnv environment for legal contract review.

Quick start:
    from environment import LegalReviewEnv

    env = LegalReviewEnv(task_id="clause_identification")
    obs = env.reset()
    result = env.step(action)
"""
from environment import LegalReviewEnv
from models import Action, Observation, Reward, State, StepResult

__all__ = ["LegalReviewEnv", "Action", "Observation", "Reward", "State", "StepResult"]
__version__ = "1.0.0"
