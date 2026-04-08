---
title: LegalReviewEnv
emoji: ⚖️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# LegalReviewEnv

An OpenEnv environment for training and evaluating AI agents on legal contract review.

## Motivation

Legal contract review is one of the highest-value professional tasks performed daily by lawyers, paralegals, and compliance officers. A skilled reviewer must: (1) identify what provisions are present, (2) assess which carry risk and how severe, and (3) propose concrete changes that protect the client. This environment models that full workflow with graded tasks, partial-progress rewards, and realistic contract texts — making it useful for evaluating LLM agents on practical legal reasoning.

---

## Environment description

The agent reviews synthetic but realistic contracts (SaaS agreements, NDAs) and must perform one of three tasks per episode. Contracts are modelled on real-world document structures; all parties and figures are fictional.

### Observation space

| Field | Type | Description |
|---|---|---|
| `contract_text` | `string` | Full contract text to review |
| `task_id` | `enum` | Which of the 3 tasks is active |
| `step_number` | `int` | Current step within the episode |
| `context` | `dict` | Task-specific hints (e.g. known risks for Task 3) |
| `message` | `string` | Human-readable env feedback |

### Action space

| `action_type` | Payload keys | When to use |
|---|---|---|
| `submit_clauses` | `clauses: list[str]` | Task 1: submit identified clause list |
| `submit_risks` | `risks: list[RiskItem]` | Task 2: submit flagged risks |
| `submit_redlines` | `redlines: list[RedlineItem]` | Task 3: submit negotiation strategy |
| `request_section` | `section: str` | Any: ask env for a specific contract section |
| `done` | — | Signal episode completion |

### Reward function

Reward is always in **[0.0, 1.0]**. It is **not sparse** — partial submissions receive partial credit.

- **Task 1** (clause identification): F1 score over identified vs. ground-truth clauses. Precision × recall balance ensures breadth and accuracy.
- **Task 2** (risk flagging): `0.4 × recall + 0.3 × severity_accuracy + 0.3 × rationale_quality`. Partial credit for correct clause reference even if severity is off.
- **Task 3** (negotiation strategy): `0.35 × coverage + 0.35 × priority_ordering + 0.30 × language_quality`. Rewards substantive proposed language and correct prioritisation.
- **Loop penalty**: repeated identical actions without progress are penalised by −0.05 per extra repeat beyond 3.

---

## Task descriptions

### Task 1 — Clause Identification (easy)
**Contract**: Simple 7-clause mutual NDA  
**Objective**: Output the list of clause types present.  
**Expected agent score**: 0.75–0.90 (GPT-4 class models)  
**Grader**: F1 between submitted clause list and ground truth, using fuzzy matching for naming variations.

### Task 2 — Risk Flagging (medium)
**Contract**: 12-clause SaaS subscription agreement  
**Objective**: Flag risky provisions with severity (low/medium/high) and rationale.  
**Expected agent score**: 0.50–0.70  
**Grader**: Recall of ground-truth risks, severity distance score, keyword-based rationale quality.

### Task 3 — Negotiation Strategy (hard)
**Contract**: Same SaaS agreement (Task 2 risks pre-populated in context)  
**Objective**: Propose prioritised redlines with specific proposed replacement language.  
**Expected agent score**: 0.35–0.55  
**Grader**: Coverage of key redlines, Kendall's tau for priority ordering, quality of proposed legal language.

---

## Setup and usage

### Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python server.py

# In another terminal, run inference
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=sk-your-key-here
export ENV_URL=http://localhost:7860
python inference.py