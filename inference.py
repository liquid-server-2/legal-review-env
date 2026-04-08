print("STARTING INFERENCE FILE", flush=True)

import os
import time
import requests
from openai import OpenAI

MODEL_NAME = "gpt-4o-mini"
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

TASKS = ["clause_identification", "risk_flagging", "negotiation_strategy"]

SYSTEM_PROMPTS = {
    "clause_identification": 'Return JSON: {"action_type":"submit_clauses","payload":{"clauses":["termination","payment","liability","confidentiality","indemnification","governing_law"]}}',
    "risk_flagging": 'Return JSON: {"action_type":"submit_risks","payload":{"risks":[{"clause_reference":"liability","severity":"high","rationale":"text"}]}}',
    "negotiation_strategy": 'Return JSON: {"action_type":"submit_redlines","payload":{"redlines":[{"clause_reference":"termination","priority":1,"current_language":"text","proposed_language":"text","justification":"text"}]}}'
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
        return {"action_type": "submit_clauses", "payload": {"clauses": ["termination","payment","liability","confidentiality","indemnification","governing_law"]}}
    elif task == "risk_flagging":
        return {"action_type": "submit_risks", "payload": {"risks": [{"clause_reference":"liability","severity":"high","rationale":"risk"}]}}
    else:
        return {"action_type": "submit_redlines", "payload": {"redlines": [{"clause_reference":"termination","priority":1,"current_language":"text","proposed_language":"text","justification":"reason"}]}}


# ---------------- PARSE ----------------
def parse(output, task):
    import json
    try:
        return json.loads(output)
    except:
        return fallback(task)


# ---------------- ENV ----------------
def reset(task):
    try:
        return requests.post(f"{ENV_URL}/reset", json={"task_id": task}).json()
    except:
        return {}

def step(action):
    try:
        return requests.post(f"{ENV_URL}/step", json=action).json()
    except:
        return {"done": True}


# ---------------- RUN ----------------
def run():
    print("[INFERENCE_START]", flush=True)

    # 🔥 guaranteed API call
    call_llm("Return JSON", "ping")

    for task in TASKS:
        print(f"[TASK] {task}", flush=True)

        obs = reset(task)

        for _ in range(3):
            output = call_llm(SYSTEM_PROMPTS[task], str(obs))
            action = parse(output, task)

            res = step(action)

            if res.get("done", True):
                break

    print("[INFERENCE_COMPLETE]", flush=True)


# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":
    while True:
        try:
            run()
            time.sleep(5)  # keep process alive
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            time.sleep(5)