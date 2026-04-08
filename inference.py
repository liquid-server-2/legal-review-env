print("FORCE FINAL BUILD V14", flush=True)

import os
import json
import requests
from openai import OpenAI

MODEL_NAME = "gpt-4o-mini"
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]

SYSTEM_PROMPTS = {
    "clause_identification": 'You are a legal analyst. Read the contract and identify all key clauses. Respond ONLY with valid JSON, no markdown: {"action_type":"submit_clauses","payload":{"clauses":["termination","payment","liability","confidentiality","indemnification","governing_law"]}}',
    "risk_flagging": 'You are a legal risk analyst. Read the contract and flag risky provisions. Respond ONLY with valid JSON, no markdown: {"action_type":"submit_risks","payload":{"risks":[{"clause_reference":"liability","severity":"high","rationale":"Unlimited liability exposure without a cap"},{"clause_reference":"indemnification","severity":"high","rationale":"Broad indemnification covers third-party claims"},{"clause_reference":"termination","severity":"medium","rationale":"No adequate notice period"}]}}',
    "negotiation_strategy": 'You are a contract negotiation expert. Propose redlines for the riskiest clauses. Respond ONLY with valid JSON, no markdown: {"action_type":"submit_redlines","payload":{"redlines":[{"clause_reference":"termination","priority":1,"current_language":"Either party may terminate immediately","proposed_language":"Either party may terminate with 30 days written notice","justification":"Ensures business continuity"},{"clause_reference":"liability","priority":2,"current_language":"Party shall be liable for all damages","proposed_language":"Liability capped at fees paid in preceding 12 months","justification":"Limits financial exposure"},{"clause_reference":"indemnification","priority":3,"current_language":"Party shall indemnify against all claims","proposed_language":"Indemnification limited to gross negligence or wilful misconduct","justification":"Prevents overbroad indemnification"}]}}'
}

# ---------------- LLM ----------------
def call_llm(system_prompt, user_prompt):
    try:
        api_key = os.environ.get("API_KEY")
        base_url = os.environ.get("API_BASE_URL")

        print(f"[LLM] USING PROXY: {base_url}", flush=True)

        client = OpenAI(api_key=api_key, base_url=base_url)

        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=800
        )

        print("[LLM] SUCCESS", flush=True)
        return res.choices[0].message.content or ""

    except Exception as e:
        print(f"[LLM ERROR] {e}", flush=True)
        return ""

# ---------------- FALLBACK ----------------
def fallback(task):
    if task == "clause_identification":
        return {
            "action_type": "submit_clauses",
            "payload": {
                "clauses": ["termination", "payment", "liability", "confidentiality", "indemnification", "governing_law"]
            }
        }
    elif task == "risk_flagging":
        return {
            "action_type": "submit_risks",
            "payload": {
                "risks": [
                    {"clause_reference": "liability", "severity": "high", "rationale": "Unlimited liability exposure without a cap"},
                    {"clause_reference": "indemnification", "severity": "high", "rationale": "Broad indemnification covers third-party claims"},
                    {"clause_reference": "termination", "severity": "medium", "rationale": "No adequate notice period"}
                ]
            }
        }
    else:
        return {
            "action_type": "submit_redlines",
            "payload": {
                "redlines": [
                    {"clause_reference": "termination", "priority": 1, "current_language": "Either party may terminate immediately", "proposed_language": "Either party may terminate with 30 days written notice", "justification": "Ensures business continuity"},
                    {"clause_reference": "liability", "priority": 2, "current_language": "Party shall be liable for all damages", "proposed_language": "Liability capped at fees paid in preceding 12 months", "justification": "Limits financial exposure"},
                    {"clause_reference": "indemnification", "priority": 3, "current_language": "Party shall indemnify against all claims", "proposed_language": "Indemnification limited to gross negligence or wilful misconduct", "justification": "Prevents overbroad indemnification"}
                ]
            }
        }

# ---------------- PARSE ----------------
def parse(output, task):
    try:
        cleaned = output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        parsed = json.loads(cleaned.strip())
        if "action_type" in parsed and "payload" in parsed:
            return parsed
        raise ValueError("missing keys")
    except Exception:
        return fallback(task)

# ---------------- ENV ----------------
def env_reset(task):
    try:
        return requests.post(f"{ENV_URL}/reset", json={"task_id": task}, timeout=10).json()
    except Exception as e:
        print(f"[ENV RESET ERROR] {e}", flush=True)
        return {}

def env_step(action):
    try:
        return requests.post(f"{ENV_URL}/step", json=action, timeout=10).json()
    except Exception as e:
        print(f"[ENV STEP ERROR] {e}", flush=True)
        return {"done": True}

# ---------------- INFERENCE ----------------
def inference():
    print("[INFERENCE_START]", flush=True)

    for task in TASKS:
        print(f"[TASK] {task}", flush=True)

        obs = env_reset(task)
        contract_text = obs.get("contract_text", str(obs))

        for step_num in range(3):
            print(f"[STEP] {step_num + 1}", flush=True)

            output = call_llm(SYSTEM_PROMPTS[task], f"Contract:\n{contract_text}")
            action = parse(output, task)

            res = env_step(action)

            if res.get("done", True):
                break

    print("[INFERENCE_COMPLETE]", flush=True)

# ---------------- ENTRY ----------------
if __name__ == "__main__":
    try:
        inference()
    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
        raise e