"""Deterministic uncertainty × disease-anchor retrieval router.

This module contains policy logic only. It does not call an LLM, infer evidence
truth, or alter Network 1/Network 2 edges.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


INTENTS = ("MECHANISTIC", "COUNTER", "DISEASE_CONTEXT", "GENERAL")
STRATEGIES = ("fixed", "uncertainty_only", "disease_only", "combined")


@dataclass(frozen=True)
class RouteDecision:
    conformal_state: str
    anchor_tier: str
    policy: str
    rationale: str


def parse_conformal_state(value: str) -> str:
    """Map saved prediction-set strings to ACTIVE_ONLY, UNCERTAIN or INACTIVE_ONLY."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("conformal_set must be a non-empty string.")

    tokens = {token.strip().upper() for token in value.split("|") if token.strip()}
    if tokens == {"ACTIVE"}:
        return "ACTIVE_ONLY"
    if tokens == {"INACTIVE"}:
        return "INACTIVE_ONLY"
    if tokens == {"ACTIVE", "INACTIVE"}:
        return "UNCERTAIN"
    raise ValueError(
        f"Unsupported conformal_set {value!r}; expected ACTIVE, INACTIVE, "
        "or ACTIVE|INACTIVE."
    )


def validate_anchor_tier(value: str) -> str:
    tier = str(value).strip().upper()
    if tier not in {"STRONG", "MODERATE", "WEAK", "NONE"}:
        raise ValueError("anchor_tier must be STRONG, MODERATE, WEAK or NONE.")
    return tier


def derive_anchor_thresholds(
    scores,
    moderate_quantile: float = 0.25,
    strong_quantile: float = 0.75,
) -> dict[str, float]:
    """Derive reproducible score cutoffs without using DTI labels or outcomes."""
    import numpy as np

    if not 0 <= moderate_quantile < strong_quantile <= 1:
        raise ValueError("Require 0 <= moderate_quantile < strong_quantile <= 1.")

    values = np.asarray(list(scores), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 4:
        raise ValueError("At least four finite overall association scores are required.")
    if np.any((values < 0) | (values > 1)):
        raise ValueError("Open Targets overall association scores must be in [0, 1].")

    return {
        "moderate_threshold": float(np.quantile(values, moderate_quantile)),
        "strong_threshold": float(np.quantile(values, strong_quantile)),
        "moderate_quantile": float(moderate_quantile),
        "strong_quantile": float(strong_quantile),
        "n_scores": int(values.size),
    }


def classify_anchor(
    score: float | None,
    has_association: bool,
    thresholds: Mapping[str, float],
) -> str:
    """Assign NONE/WEAK/MODERATE/STRONG using frozen overall-score cutoffs."""
    if not has_association or score is None:
        return "NONE"

    value = float(score)
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Association score must be finite and in [0, 1].")

    moderate = float(thresholds["moderate_threshold"])
    strong = float(thresholds["strong_threshold"])
    if not 0 <= moderate <= strong <= 1:
        raise ValueError("Invalid anchor thresholds.")

    if value >= strong:
        return "STRONG"
    if value >= moderate:
        return "MODERATE"
    return "WEAK"


def route_prediction_set(conformal_set: str, anchor_tier: str) -> RouteDecision:
    """Apply the project's locked seven-policy table."""
    state = parse_conformal_state(conformal_set)
    anchor = validate_anchor_tier(anchor_tier)

    if state == "INACTIVE_ONLY":
        return RouteDecision(
            state, anchor, "STOP",
            "The prediction set is confidently INACTIVE; skip evidence retrieval.",
        )

    if state == "ACTIVE_ONLY":
        if anchor == "STRONG":
            policy, reason = "CONFIRM", "Confident ACTIVE prediction with a strong disease anchor."
        elif anchor == "MODERATE":
            policy, reason = "CONTEXTUALISE", "Confident ACTIVE prediction; establish disease context."
        else:
            policy, reason = "INVESTIGATE", "Confident ACTIVE prediction but weak or absent disease anchor."
        return RouteDecision(state, anchor, policy, reason)

    if anchor == "STRONG":
        policy, reason = "CHALLENGE", "Uncertain prediction with a strong disease anchor; seek counter-evidence first."
    elif anchor == "MODERATE":
        policy, reason = "CHALLENGE_CONTEXT", "Uncertain prediction; challenge it while retaining disease context."
    else:
        policy, reason = "LOW_PRIORITY", "Uncertain prediction with weak or absent disease context."
    return RouteDecision(state, anchor, policy, reason)


def intent_weights(
    strategy: str,
    conformal_set: str,
    anchor_tier: str,
) -> dict[str, int]:
    """Return relative per-candidate retrieval weights for one of four strategies.

    The numbers are weights, not probabilities. The runner converts them to an
    integer document budget using largest-remainder allocation.
    """
    strategy = str(strategy).strip().lower()
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}.")

    state = parse_conformal_state(conformal_set)
    anchor = validate_anchor_tier(anchor_tier)

    if strategy == "fixed":
        return {"MECHANISTIC": 4, "COUNTER": 3, "DISEASE_CONTEXT": 3, "GENERAL": 0}

    if strategy == "uncertainty_only":
        if state == "ACTIVE_ONLY":
            return {"MECHANISTIC": 7, "COUNTER": 1, "DISEASE_CONTEXT": 0, "GENERAL": 2}
        if state == "UNCERTAIN":
            return {"MECHANISTIC": 2, "COUNTER": 7, "DISEASE_CONTEXT": 0, "GENERAL": 1}
        return {intent: 0 for intent in INTENTS}

    if strategy == "disease_only":
        if anchor == "STRONG":
            return {"MECHANISTIC": 3, "COUNTER": 1, "DISEASE_CONTEXT": 6, "GENERAL": 0}
        if anchor == "MODERATE":
            return {"MECHANISTIC": 3, "COUNTER": 3, "DISEASE_CONTEXT": 4, "GENERAL": 0}
        return {"MECHANISTIC": 3, "COUNTER": 3, "DISEASE_CONTEXT": 0, "GENERAL": 4}

    policy = route_prediction_set(conformal_set, anchor).policy
    combined = {
        "CONFIRM": {"MECHANISTIC": 6, "COUNTER": 1, "DISEASE_CONTEXT": 3, "GENERAL": 0},
        "CONTEXTUALISE": {"MECHANISTIC": 3, "COUNTER": 1, "DISEASE_CONTEXT": 6, "GENERAL": 0},
        "INVESTIGATE": {"MECHANISTIC": 4, "COUNTER": 2, "DISEASE_CONTEXT": 1, "GENERAL": 3},
        "CHALLENGE": {"MECHANISTIC": 1, "COUNTER": 7, "DISEASE_CONTEXT": 2, "GENERAL": 0},
        "CHALLENGE_CONTEXT": {"MECHANISTIC": 1, "COUNTER": 6, "DISEASE_CONTEXT": 3, "GENERAL": 0},
        "LOW_PRIORITY": {"MECHANISTIC": 0, "COUNTER": 2, "DISEASE_CONTEXT": 1, "GENERAL": 7},
        "STOP": {intent: 0 for intent in INTENTS},
    }
    return dict(combined[policy])


def allocate_intent_budget(
    strategy: str,
    conformal_set: str,
    anchor_tier: str,
    budget: int,
) -> dict[str, int]:
    """Allocate an integer document cap exactly across retrieval intents."""
    if not isinstance(budget, int) or budget < 0:
        raise ValueError("budget must be a non-negative integer.")

    weights = intent_weights(strategy, conformal_set, anchor_tier)
    total = sum(weights.values())
    if total == 0 or budget == 0:
        return {intent: 0 for intent in INTENTS}

    raw = {intent: budget * weight / total for intent, weight in weights.items()}
    allocated = {intent: int(raw[intent]) for intent in INTENTS}
    remaining = budget - sum(allocated.values())

    order = sorted(
        INTENTS,
        key=lambda intent: (raw[intent] - allocated[intent], weights[intent], -INTENTS.index(intent)),
        reverse=True,
    )
    for intent in order[:remaining]:
        allocated[intent] += 1

    return allocated
