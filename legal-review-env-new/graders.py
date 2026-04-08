"""
Programmatic graders for the three LegalReviewEnv tasks.
All graders return a float in [0.0, 1.0].
They are deterministic given the same inputs.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

from models import Reward


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[_\-\s]+", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()


def _fuzzy_match(candidate: str, reference_list: List[str]) -> bool:
    """Return True if candidate matches any item in reference_list (fuzzy)."""
    cn = _normalise(candidate)
    for ref in reference_list:
        rn = _normalise(ref)
        # Direct match
        if cn == rn:
            return True
        # Substring match (both directions, min 4 chars)
        if len(cn) >= 4 and len(rn) >= 4:
            if cn in rn or rn in cn:
                return True
        # Token overlap: ≥50% of shorter token set must overlap
        ct = set(cn.split())
        rt = set(rn.split())
        overlap = ct & rt
        shorter = min(len(ct), len(rt))
        if shorter > 0 and len(overlap) / shorter >= 0.5:
            return True
    return False


# ---------------------------------------------------------------------------
# Task 1 — Clause Identification Grader
# ---------------------------------------------------------------------------

def grade_clause_identification(
    submitted: List[str],
    ground_truth: List[str]
) -> Reward:
    """
    Precision + recall of clause identification.
    F1 score used as the total reward.
    """
    if not submitted:
        return Reward(total=0.0, precision=0.0, recall=0.0)

    # Compute precision: how many submitted clauses are in ground truth
    tp_precision = sum(1 for s in submitted if _fuzzy_match(s, ground_truth))
    precision = tp_precision / len(submitted)

    # Compute recall: how many ground truth clauses are found in submitted
    tp_recall = sum(1 for g in ground_truth if _fuzzy_match(g, submitted))
    recall = tp_recall / len(ground_truth)

    # F1
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return Reward(
        total=round(f1, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        breakdown={"true_positives": tp_recall, "submitted": len(submitted), "ground_truth": len(ground_truth)}
    )


# ---------------------------------------------------------------------------
# Task 2 — Risk Flagging Grader
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {"low": 0, "medium": 1, "high": 2}

def _severity_distance(pred: str, gold: str) -> float:
    """1.0 if exact match, 0.5 if adjacent, 0.0 if off by 2."""
    d = abs(_SEVERITY_MAP.get(pred, 1) - _SEVERITY_MAP.get(gold, 1))
    return [1.0, 0.5, 0.0][d]


def _rationale_quality(rationale: str, gold_keywords: List[str]) -> float:
    """
    Score 0–1 based on keyword coverage and minimum length.
    Length ≥ 20 words required. Each keyword hit adds to score.
    """
    words = rationale.lower().split()
    if len(words) < 10:
        return 0.0
    if not gold_keywords:
        return 0.7 if len(words) >= 15 else 0.4
    hits = sum(1 for kw in gold_keywords if kw.lower() in rationale.lower())
    coverage = hits / len(gold_keywords)
    # Combine length bonus with keyword coverage
    length_bonus = min(1.0, len(words) / 40)
    return round(0.6 * coverage + 0.4 * length_bonus, 4)


def grade_risk_flagging(
    submitted_risks: List[Dict[str, Any]],
    ground_truth_risks: List[Dict[str, Any]]
) -> Reward:
    """
    Grade each submitted risk against ground truth risks.
    Scores: detection (recall), severity accuracy, rationale quality.
    Overall = 0.4*recall + 0.3*severity_acc + 0.3*rationale_quality
    """
    if not submitted_risks:
        return Reward(total=0.0, recall=0.0, severity_accuracy=0.0, rationale_quality=0.0)

    gt_clauses = [r["clause_reference"] for r in ground_truth_risks]
    matched_gt = set()
    severity_scores = []
    rationale_scores = []

    for sub in submitted_risks:
        sub_ref = sub.get("clause_reference", "")
        # Find best matching ground truth risk
        best_gt = None
        for i, gt in enumerate(ground_truth_risks):
            if i in matched_gt:
                continue
            if _fuzzy_match(sub_ref, [gt["clause_reference"]]):
                best_gt = (i, gt)
                break

        if best_gt is None:
            # Still give partial credit for severity if clause is close
            severity_scores.append(0.0)
            rationale_scores.append(_rationale_quality(sub.get("rationale", ""), []))
        else:
            idx, gt = best_gt
            matched_gt.add(idx)
            sev_score = _severity_distance(sub.get("severity", "low"), gt["severity"])
            severity_scores.append(sev_score)
            rat_score = _rationale_quality(
                sub.get("rationale", ""),
                gt.get("keywords", [])
            )
            rationale_scores.append(rat_score)

    # Recall: what fraction of ground truth risks were detected
    recall = len(matched_gt) / len(ground_truth_risks)
    avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0.0
    avg_rationale = sum(rationale_scores) / len(rationale_scores) if rationale_scores else 0.0

    total = 0.4 * recall + 0.3 * avg_severity + 0.3 * avg_rationale

    return Reward(
        total=round(total, 4),
        recall=round(recall, 4),
        severity_accuracy=round(avg_severity, 4),
        rationale_quality=round(avg_rationale, 4),
        breakdown={
            "matched_risks": len(matched_gt),
            "submitted_risks": len(submitted_risks),
            "ground_truth_risks": len(ground_truth_risks)
        }
    )


# ---------------------------------------------------------------------------
# Task 3 — Negotiation Strategy Grader
# ---------------------------------------------------------------------------

def _priority_order_score(submitted_redlines: List[Dict], ground_truth_redlines: List[Dict]) -> float:
    """
    Score how well the agent's priority ordering matches ground truth.
    Uses Spearman rank correlation approximation.
    Only considers matched pairs.
    """
    gt_priority = {r["clause_reference"]: r["priority"] for r in ground_truth_redlines}
    matched_pairs: List[Tuple[int, int]] = []

    for sub in submitted_redlines:
        ref = sub.get("clause_reference", "")
        sub_prio = sub.get("priority", 99)
        for gt_ref, gt_prio in gt_priority.items():
            if _fuzzy_match(ref, [gt_ref]):
                matched_pairs.append((sub_prio, gt_prio))
                break

    if len(matched_pairs) < 2:
        return 0.5  # Not enough data to assess ordering

    # Simple rank correlation: count concordant vs discordant pairs
    concordant = 0
    discordant = 0
    n = len(matched_pairs)
    for i in range(n):
        for j in range(i + 1, n):
            s1, g1 = matched_pairs[i]
            s2, g2 = matched_pairs[j]
            if (s1 < s2 and g1 < g2) or (s1 > s2 and g1 > g2):
                concordant += 1
            elif (s1 < s2 and g1 > g2) or (s1 > s2 and g1 < g2):
                discordant += 1

    total_pairs = concordant + discordant
    if total_pairs == 0:
        return 0.5
    tau = concordant / total_pairs  # Range [0, 1]
    return round(tau, 4)


def _proposed_language_quality(proposed: str, original: str) -> float:
    """
    Heuristic check that proposed language is substantive and different.
    Checks: minimum length, doesn't just repeat original, contains legal terms.
    """
    legal_terms = [
        "shall", "provided", "not to exceed", "within", "days", "written",
        "notice", "terminate", "refund", "liability", "indemnif", "waive",
        "mutual", "reasonable", "material", "breach", "cure", "pro-rata"
    ]
    if len(proposed.split()) < 8:
        return 0.2
    # Penalise if proposed is too similar to original (copy-paste)
    orig_words = set(original.lower().split())
    prop_words = set(proposed.lower().split())
    overlap = len(orig_words & prop_words) / max(len(orig_words), 1)
    if overlap > 0.8:
        return 0.3

    hits = sum(1 for t in legal_terms if t in proposed.lower())
    legal_score = min(1.0, hits / 3)
    return round(0.4 + 0.6 * legal_score, 4)


def grade_negotiation_strategy(
    submitted_redlines: List[Dict[str, Any]],
    ground_truth_redlines: List[Dict[str, Any]]
) -> Reward:
    """
    Grade negotiation strategy on:
    - Coverage (recall of high-priority items)
    - Priority ordering (Kendall's tau approximation)
    - Proposed language quality
    Overall = 0.35*coverage + 0.35*priority + 0.30*language
    """
    if not submitted_redlines:
        return Reward(total=0.0, recall=0.0, breakdown={"error": "no redlines submitted"})

    gt_refs = [r["clause_reference"] for r in ground_truth_redlines]
    matched = set()

    language_scores = []
    for sub in submitted_redlines:
        ref = sub.get("clause_reference", "")
        for i, gt in enumerate(ground_truth_redlines):
            if i in matched and _fuzzy_match(ref, [gt["clause_reference"]]):
                break
            if _fuzzy_match(ref, [gt["clause_reference"]]):
                matched.add(i)
                lang_score = _proposed_language_quality(
                    sub.get("proposed_language", ""),
                    sub.get("current_language", "")
                )
                language_scores.append(lang_score)
                break

    coverage = len(matched) / len(ground_truth_redlines)
    priority_score = _priority_order_score(submitted_redlines, ground_truth_redlines)
    avg_language = sum(language_scores) / len(language_scores) if language_scores else 0.0

    total = 0.35 * coverage + 0.35 * priority_score + 0.30 * avg_language

    return Reward(
        total=round(total, 4),
        recall=round(coverage, 4),
        rationale_quality=round(avg_language, 4),
        breakdown={
            "coverage": round(coverage, 4),
            "priority_ordering": round(priority_score, 4),
            "language_quality": round(avg_language, 4),
            "matched": len(matched),
            "ground_truth": len(ground_truth_redlines)
        }
    )
