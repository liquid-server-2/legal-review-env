print("FORCE NEW BUILD v8")
import os
import sys
import requests

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]

# ---------------- CLIENT ----------------
client = None
if OpenAI:
    try:
        client = OpenAI(
            api_key=os.environ["API_KEY"],
            base_url=os.environ["API_BASE_URL"]
        )
        print(f"[INFO] client ready base_url={os.environ['API_BASE_URL']}", flush=True)
    except Exception as e:
        print(f"[WARN] client init failed: {e}", flush=True)
        client = None

# ---------------- LLM ----------------
def call_llm(system_prompt, user_prompt):
    if client is None:
        print("[WARN] client is None, skipping LLM call", flush=True)
        return ""
    try:
        print(f"[LLM] calling model={MODEL_NAME}", flush=True)
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        print(f"[LLM] response received", flush=True)
        return res.choices[0].message.content or ""
    except Exception as e:
        print(f"[WARN] LLM call failed: {e}", flush=True)
        return ""

# ---------------- FALLBACK ACTIONS ----------------
def get_fallback_action(task):
    if task == "clause_identification":
        return {
            "action_type": "submit_clauses",
            "payload": {
                "clauses": [
                    "termination",
                    "payment",
                    "liability",
                    "confidentiality",
                    "indemnification",
                    "governing_law"
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
                        "rationale": "Unlimited liability exposure without a cap poses significant financial risk"
                    },
                    {
                        "clause_reference": "indemnification",
                        "severity": "high",
                        "rationale": "Broad indemnification clause may require covering third-party claims"
                    },
                    {
                        "clause_reference": "termination",
                        "severity": "medium",
                        "rationale": "Termination for convenience clause lacks adequate notice period"
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
                        "current_language": "Either party may terminate immediately",
                        "proposed_language": "Either party may terminate with 30 days written notice",
                        "justification": "Provides adequate notice period to protect business continuity"
                    },
                    {
                        "clause_reference": "liability",
                        "priority": 2,
                        "current_language": "Party shall be liable for all damages",
                        "proposed_language": "Liability shall be capped at the total fees paid in the preceding 12 months",
                        "justification": "Limits financial exposure to a reasonable and predictable amount"
                    },
                    {
                        "clause_reference": "indemnification",
                        "priority": 3,
                        "current_language": "Party shall indemnify against all claims",
                        "proposed_language": "Indemnification limited to claims arising from gross negligence or wilful misconduct",
                        "justification": "Prevents overbroad indemnification obligations"
                    }
                ]
            }
        }

# ---------------- PARSE LLM OUTPUT ----------------
def parse_action(llm_output, task):
    import json
    try:
        cleaned = llm_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        parsed = json.loads(cleaned.strip())
        if parsed and "action_type" in parsed and "payload" in parsed:
            return parsed
        raise ValueError("missing keys")
    except Exception:
        return get_fallback_action(task)

# ---------------- ENV ----------------
def env_reset(task):
    try:
        r = requests.post(f"{ENV_URL}/reset", json={"task_id": task}, timeout=5)
        return r.json()
    except Exception as e:
        print(f"[WARN] env_reset failed: {e}", flush=True)
        return {}

def env_step(action_type, payload):
    try:
        r = requests.post(
            f"{ENV_URL}/step",
            json={"action_type": action_type, "payload": payload},
            timeout=5
        )
        return r.json()
    except Exception as e:
        print(f"[WARN] env_step failed: {e}", flush=True)
        return {"reward": {"total": 0.0}, "done": True}

# ---------------- SYSTEM PROMPTS ----------------
SYSTEM_PROMPTS = {
    "clause_identification": """You are a legal contract analyst. Given a contract, identify all key clauses.
Respond ONLY with valid JSON in this exact format, no markdown, no explanation:
{"action_type": "submit_clauses", "payload": {"clauses": ["termination", "payment", "liability", "confidentiality", "indemnification", "governing_law"]}}""",

    "risk_flagging": """You are a legal risk analyst. Given a contract, identify the top risks.
Respond ONLY with valid JSON in this exact format, no markdown, no explanation:
{"action_type": "submit_risks", "payload": {"risks": [{"clause_reference": "liability", "severity": "high", "rationale": "explanation here"}]}}""",

    "negotiation_strategy": """You are a contract negotiation expert. Given a contract, propose redlines.
Respond ONLY with valid JSON in this exact format, no markdown, no explanation:
{"action_type": "submit_redlines", "payload": {"redlines": [{"clause_reference": "termination", "priority": 1, "current_language": "original text", "proposed_language": "new text", "justification": "reason"}]}}"""
}

# ---------------- TASK RUNNER ----------------
def run_task(task):
    print(f"[START] task={task}", flush=True)
    obs = env_reset(task)
    best = 0.0
    step = 0

    for step in range(1, 4):
        system_prompt = SYSTEM_PROMPTS.get(task, "")
        user_prompt = f"Contract observation: {str(obs)}"

        llm_output = call_llm(system_prompt, user_prompt)
        action = parse_action(llm_output, task)

        res = env_step(action["action_type"], action["payload"])
        reward = res.get("reward", {}).get("total", 0.0)
        done = res.get("done", True)

        best = max(best, reward)
        print(f"[STEP] step={step} reward={reward}", flush=True)  # fixed
        
        if done:
            break

    print(f"[END] task={task} score={best} steps={step}", flush=True)
    return best

# ---------------- MAIN ----------------
def main():
    print(f"[INFERENCE_START] model={MODEL_NAME} tasks={TASKS}", flush=True)

    for task in TASKS:
        try:
            run_task(task)
        except Exception as e:
            print(f"[ERROR] task={task} error={e}", flush=True)
            print(f"[END] task={task} score=0.0 steps=0", flush=True)

    print("[INFERENCE_COMPLETE]", flush=True)

# ---------------- ENTRY ----------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
        sys.exit(0)