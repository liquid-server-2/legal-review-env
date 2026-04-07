"""
FastAPI server for LegalReviewEnv.
Exposes: POST /reset, POST /step, GET /state, GET /tasks, GET /health
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import Action, Observation, State, StepResult
from environment import LegalReviewEnv

app = FastAPI(
    title="LegalReviewEnv",
    description="OpenEnv environment for AI-powered legal contract review.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One environment instance per process (stateful, single-threaded for simplicity)
_env: Optional[LegalReviewEnv] = None


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: str = "clause_identification"


class StepRequest(BaseModel):
    action_type: str
    payload: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "env": "LegalReviewEnv", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "id": "clause_identification",
                "difficulty": "easy",
                "description": "Identify clause types present in the contract."
            },
            {
                "id": "risk_flagging",
                "difficulty": "medium",
                "description": "Flag risky provisions with severity and rationale."
            },
            {
                "id": "negotiation_strategy",
                "difficulty": "hard",
                "description": "Propose prioritised redlines to protect the client."
            }
        ]
    }


from fastapi import Body

@app.post("/reset", response_model=Observation)
def reset(request: dict = Body(default={})):
    global _env
    valid = ["clause_identification", "risk_flagging", "negotiation_strategy"]

    task_id = request.get("task_id", "clause_identification")

    if task_id not in valid:
        raise HTTPException(status_code=400, detail=f"task_id must be one of {valid}")

    _env = LegalReviewEnv(task_id=task_id)
    obs = _env.reset()
    return obs


@app.post("/step", response_model=StepResult)
def step(request: StepRequest):
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first to start an episode.")
    try:
        action = Action(action_type=request.action_type, payload=request.payload)
        result = _env.step(action)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=State)
def state():
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    return _env.state()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
