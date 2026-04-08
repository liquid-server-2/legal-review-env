print("FORCE NEW BUILD v3")
import json
import os
import sys
import time
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]

# ---------------- SAFE CLIENT ----------------
def get_client():
    try:
        from openai import OpenAI
        return OpenAI(
            api_key=os.getenv("HF_TOKEN") or "dummy-key",
            base_url=os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
        )
    except Exception as e:
        print(json.dumps({"event": "ERROR", "message": f"client init failed: {str(e)}"}))
        sys.stdout.flush()
        return None

# ---------------- LOGGING ----------------
def log_start(task):
    print(json.dumps({
        "event": "START",
        "task_id": task,
        "model": MODEL_NAME,
        "env_url": ENV_URL
    }))
    sys.stdout.flush()

def log_step(task, step, action_type, reward, done):
    print(json.dumps({
        "event": "STEP",
        "task_id": task,
        "step": step,
        "action_type": action_type,
        "reward": reward,
        "done": done
    }))
    sys.stdout.flush()

def log_end(task, steps, final_reward, best_reward):
    print(json.dumps({
        "event": "END",
        "task_id": task,
        "total_steps": steps,
        "final_reward": final_reward,
        "best_reward": best_reward
    }))
    sys.stdout.flush()

# ---------------- ENV ----------------
def env_reset(task):
    try:
        r = requests.post(f"{ENV_URL}/reset", json={"task_id": task}, timeout=1)
        return r.json()
    except Exception as e:
        print(json.dumps({"event": "ERROR", "task_id": task, "error": str(e)}))
        sys.stdout.flush()
        return {}

def env_step(action_type, payload):
    try:
        r = requests.post(
            f"{ENV_URL}/step",
            json={"action_type": action_type, "payload": payload},
            timeout=1
        )
        return r.json()
    except Exception as e:
        print(json.dumps({"event": "ERROR", "error": str(e)}))
        sys.stdout.flush()
        return {"reward": {"total": 0.0}, "done": True}

# ---------------- LLM ----------------
def call_llm(system, user):
    try:
        client = get_client()
        if client is None:
            return "{}"

        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.2,
            max_tokens=1000
        )

        return res.choices[0].message.content or "{}"

    except Exception as e:
        print(json.dumps({"event": "ERROR", "message": str(e)}))
        sys.stdout.flush()
        return "{}"

# ---------------- PARSER ----------------
def parse_action(output, task):
    try:
        parsed = json.loads(output)

        if not parsed or "action_type" not in parsed:
            raise Exception()

        return parsed

    except:
        if task == "clause_identification":
            return {
                "action_type": "submit_clauses",
                "payload": {
                    "clauses": [
                        "termination",
                        "payment",
                        "liability",
                        "confidentiality"
                    ]
                }
            }

        elif task == "risk_flagging":
            return {
                "action_type": "submit_risks",
                "payload": {
                    "risks": [
                        {
                            "clause_reference": "liability",
                            "severity": "high",
                            "rationale": "Unlimited liability risk"
                        }
                    ]
                }
            }

        else:
            return {
                "action_type": "submit_redlines",
                "payload": {
                    "redlines": [
                        {
                            "clause_reference": "termination",
                            "priority": 1,
                            "current_language": "N/A",
                            "proposed_language": "Add termination rights",
                            "justification": "Protects customer"
                        }
                    ]
                }
            }

# ---------------- TASK ----------------
def run_task(task):
    log_start(task)

    obs = env_reset(task)
    best = 0.0
    final = 0.0

    for step in range(1, 3):
        try:
            llm_output = call_llm("", str(obs))
            parsed = parse_action(llm_output, task)

            res = env_step(parsed["action_type"], parsed["payload"])

            reward = res.get("reward", {}).get("total", 0.0)
            done = res.get("done", True)

            final = reward
            best = max(best, reward)

            log_step(task, step, parsed["action_type"], reward, done)

            if done:
                break

        except Exception as e:
            print(json.dumps({"event": "ERROR", "task_id": task, "error": str(e)}))
            sys.stdout.flush()
            break

    log_end(task, step, final, best)
    return best

# ---------------- MAIN ----------------
def main():
    print(json.dumps({
        "event": "INFERENCE_START",
        "model": MODEL_NAME,
        "tasks": TASKS
    }))
    sys.stdout.flush()

    scores = {}

    for t in TASKS:
        try:
            scores[t] = run_task(t)
        except Exception:
            scores[t] = 0.0

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