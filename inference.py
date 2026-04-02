#!/usr/bin/env python3
"""
inference.py — Baseline inference script for LegalReviewEnv.

Runs an LLM agent (via OpenAI-compatible client) against all 3 tasks.
Reads credentials from environment variables:
    API_BASE_URL  — API endpoint (default: https://api.openai.com/v1)
    MODEL_NAME    — Model identifier (default: gpt-4o-mini)
    HF_TOKEN      — Hugging Face / API key (used as the API key)

Emits structured stdout logs in [START] / [STEP] / [END] format.
"""
from __future__ import annotations
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE_URL: str = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")
ENV_URL: str = os.environ.get("ENV_URL", "http://localhost:7860")

TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]
MAX_STEPS = 8

# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------
client = OpenAI(
    api_key=HF_TOKEN or "sk-placeholder",
    base_url=API_BASE_URL,
)

# ---------------------------------------------------------------------------
# Logging helpers (required format)
# ---------------------------------------------------------------------------

def log_start(task_id: str, model: str) -> None:
    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "model": model,
        "env_url": ENV_URL,
    }))
    sys.stdout.flush()


def log_step(task_id: str, step: int, action_type: str, reward: float, done: bool) -> None:
    print(json.dumps({
        "event": "STEP",
        "task_id": task_id,
        "step": step,
        "action_type": action_type,
        "reward": reward,
        "done": done,
    }))
    sys.stdout.flush()


def log_end(task_id: str, total_steps: int, final_reward: float, best_reward: float) -> None:
    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "total_steps": total_steps,
        "final_reward": final_reward,
        "best_reward": best_reward,
    }))
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Environment client helpers
# ---------------------------------------------------------------------------

def env_reset(task_id: str) -> Dict[str, Any]:
    r = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(
        f"{ENV_URL}/step",
        json={"action_type": action_type, "payload": payload},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# System prompts per task
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "clause_identification": """You are a paralegal reviewing contracts. Your task is to identify all standard clause types present in the given contract text.

Respond with ONLY a JSON object in exactly this format:
{
  "action_type": "submit_clauses",
  "payload": {
    "clauses": ["clause_type_1", "clause_type_2", ...]
  }
}

Common clause types include: definitions, services_grant, fees_and_payment, confidentiality, intellectual_property, indemnification, limitation_of_liability, termination, data_security, governing_law, auto_renewal, entire_agreement, purpose, obligations, exclusions, term, return_of_information.

Be thorough — include every clause type you can identify.""",

    "risk_flagging": """You are a contract lawyer reviewing a SaaS agreement for a customer client. Identify all risky provisions.

For each risk, assess severity (low/medium/high) and provide a clear rationale.

Respond with ONLY a JSON object in exactly this format:
{
  "action_type": "submit_risks",
  "payload": {
    "risks": [
      {
        "clause_reference": "clause_name",
        "severity": "high|medium|low",
        "rationale": "Explanation of why this is risky for the customer."
      }
    ]
  }
}

Focus on: asymmetric indemnification, inadequate liability caps, unfair termination provisions, non-refundable fees, auto-renewal traps, data security obligations.""",

    "negotiation_strategy": """You are a senior contract lawyer advising a customer on negotiation strategy. Based on the known risks in the context, propose specific redline changes.

Respond with ONLY a JSON object in exactly this format:
{
  "action_type": "submit_redlines",
  "payload": {
    "redlines": [
      {
        "clause_reference": "clause_name",
        "priority": 1,
        "current_language": "The problematic text from the contract",
        "proposed_language": "The replacement text you propose",
        "justification": "Why this change protects the client"
      }
    ]
  }
}

Priority 1 = most important to negotiate. Order by severity and business impact.
Focus on: liability cap, indemnification balance, termination cure periods, refund rights, auto-renewal notice."""
}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def build_user_prompt(obs: Dict[str, Any]) -> str:
    contract = obs.get("contract_text", "")
    context = obs.get("context", {})
    parts = [f"CONTRACT TEXT:\n{contract}"]
    if context:
        parts.append(f"\nCONTEXT:\n{json.dumps(context, indent=2)}")
    if obs.get("message"):
        parts.append(f"\nENV MESSAGE: {obs['message']}")
    return "\n".join(parts)


def call_llm(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    return response.choices[0].message.content or ""


def parse_action(llm_output: str) -> Dict[str, Any]:
    """Extract JSON action from LLM output, with fallback."""
    try:
        # Try direct parse
        return json.loads(llm_output.strip())
    except json.JSONDecodeError:
        pass
    # Try to extract JSON block
    import re
    match = re.search(r'\{.*\}', llm_output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Fallback
    return {"action_type": "done", "payload": {}}


def run_task(task_id: str) -> float:
    """Run one full episode for the given task. Returns best reward achieved."""
    log_start(task_id, MODEL_NAME)

    obs = env_reset(task_id)
    system_prompt = SYSTEM_PROMPTS[task_id]
    best_reward = 0.0
    final_reward = 0.0

    for step_num in range(1, MAX_STEPS + 1):
        user_prompt = build_user_prompt(obs)

        try:
            llm_output = call_llm(system_prompt, user_prompt)
            parsed = parse_action(llm_output)
        except Exception as e:
            print(json.dumps({"event": "ERROR", "task_id": task_id, "step": step_num, "error": str(e)}))
            parsed = {"action_type": "done", "payload": {}}

        action_type = parsed.get("action_type", "done")
        payload = parsed.get("payload", {})

        try:
            result = env_step(action_type, payload)
        except Exception as e:
            print(json.dumps({"event": "ERROR", "task_id": task_id, "step": step_num, "error": str(e)}))
            break

        reward_val = result.get("reward", {}).get("total", 0.0)
        done = result.get("done", False)
        final_reward = reward_val
        best_reward = max(best_reward, reward_val)

        log_step(task_id, step_num, action_type, reward_val, done)

        if done:
            obs = result.get("observation", obs)
            break

        obs = result.get("observation", obs)
        time.sleep(0.5)  # Rate-limiting courtesy

    log_end(task_id, step_num, final_reward, best_reward)
    return best_reward


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(json.dumps({"event": "INFERENCE_START", "model": MODEL_NAME, "tasks": TASKS}))
    sys.stdout.flush()

    scores: Dict[str, float] = {}
    for task_id in TASKS:
        score = run_task(task_id)
        scores[task_id] = score
        time.sleep(1.0)

    print(json.dumps({
        "event": "INFERENCE_COMPLETE",
        "model": MODEL_NAME,
        "scores": scores,
        "mean_score": round(sum(scores.values()) / len(scores), 4),
    }))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
