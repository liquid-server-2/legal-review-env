#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sys
import time
from typing import Any, Dict

import requests

# ---------------- CONFIG ----------------
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]
MAX_STEPS = 8

# ---------------- SAFE OPENAI CLIENT ----------------
client = None

def init_client():
    global client
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("HF_TOKEN") or "dummy-key",
            base_url=os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
        )
    except Exception as e:
        print(json.dumps({
            "event": "ERROR",
            "message": f"Client init failed: {str(e)}"
        }))
        sys.stdout.flush()
        client = None

init_client()

# ---------------- LOGGING ----------------
def log_start(task_id):
    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "model": MODEL_NAME,
        "env_url": ENV_URL
    }))
    sys.stdout.flush()

def log_step(task_id, step, action_type, reward, done):
    print(json.dumps({
        "event": "STEP",
        "task_id": task_id,
        "step": step,
        "action_type": action_type,
        "reward": reward,
        "done": done
    }))
    sys.stdout.flush()

def log_end(task_id, steps, final_reward, best_reward):
    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "total_steps": steps,
        "final_reward": final_reward,
        "best_reward": best_reward
    }))
    sys.stdout.flush()

# ---------------- SAFE ENV ----------------
def env_reset(task_id):
    try:
        r = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=10)
        return r.json()
    except Exception as e:
        print(json.dumps({
            "event": "ERROR",
            "task_id": task_id,
            "error": f"env_reset failed: {str(e)}"
        }))
        sys.stdout.flush()
        return {}

def env_step(action_type, payload):
    try:
        r = requests.post(
            f"{ENV_URL}/step",
            json={"action_type": action_type, "payload": payload},
            timeout=10
        )
        return r.json()
    except Exception as e:
        print(json.dumps({
            "event": "ERROR",
            "error": f"env_step failed: {str(e)}"
        }))
        sys.stdout.flush()
        return {"reward": {"total": 0.0}, "done": True, "observation": {}}

# ---------------- LLM ----------------
def call_llm(system, user):
    try:
        if client is None:
            return "{}"

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.2,
            max_tokens=2000
        )

        return response.choices[0].message.content or "{}"

    except Exception as e:
        print(json.dumps({
            "event": "ERROR",
            "message": f"LLM call failed: {str(e)}"
        }))
        sys.stdout.flush()
        return "{}"

def parse_action(output):
    try:
        return json.loads(output)
    except:
        return {"action_type": "done", "payload": {}}

# ---------------- TASK ----------------
def run_task(task_id):
    log_start(task_id)

    try:
        obs = env_reset(task_id)
    except Exception as e:
        print(json.dumps({
            "event": "ERROR",
            "task_id": task_id,
            "error": str(e)
        }))
        sys.stdout.flush()
        log_end(task_id, 0, 0.0, 0.0)
        return 0.0

    best_reward = 0.0
    final_reward = 0.0

    for step in range(1, MAX_STEPS + 1):
        try:
            user_prompt = str(obs)

            llm_output = call_llm("", user_prompt)
            parsed = parse_action(llm_output)

            action_type = parsed.get("action_type", "done")
            payload = parsed.get("payload", {})

            result = env_step(action_type, payload)

            reward = result.get("reward", {}).get("total", 0.0)
            done = result.get("done", True)

            final_reward = reward
            best_reward = max(best_reward, reward)

            log_step(task_id, step, action_type, reward, done)

            if done:
                break

            obs = result.get("observation", {})

        except Exception as e:
            print(json.dumps({
                "event": "ERROR",
                "task_id": task_id,
                "step": step,
                "error": str(e)
            }))
            sys.stdout.flush()
            break

    log_end(task_id, step, final_reward, best_reward)
    return best_reward

# ---------------- MAIN ----------------
def main():
    print(json.dumps({
        "event": "INFERENCE_START",
        "model": MODEL_NAME,
        "tasks": TASKS
    }))
    sys.stdout.flush()

    scores = {}

    for task in TASKS:
        try:
            scores[task] = run_task(task)
        except Exception as e:
            print(json.dumps({
                "event": "ERROR",
                "task_id": task,
                "error": str(e)
            }))
            sys.stdout.flush()
            scores[task] = 0.0

    print(json.dumps({
        "event": "INFERENCE_COMPLETE",
        "scores": scores
    }))
    sys.stdout.flush()

# ---------------- ENTRY ----------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({
            "event": "FATAL",
            "message": str(e)
        }))
        sys.stdout.flush()
        sys.exit(0)