import pytest

from src.network.router import (
    allocate_intent_budget,
    classify_anchor,
    derive_anchor_thresholds,
    parse_conformal_state,
    route_prediction_set,
)


@pytest.mark.parametrize(
    "conformal,anchor,policy",
    [
        ("ACTIVE", "STRONG", "CONFIRM"),
        ("ACTIVE", "MODERATE", "CONTEXTUALISE"),
        ("ACTIVE", "WEAK", "INVESTIGATE"),
        ("ACTIVE|INACTIVE", "STRONG", "CHALLENGE"),
        ("ACTIVE|INACTIVE", "MODERATE", "CHALLENGE_CONTEXT"),
        ("ACTIVE|INACTIVE", "NONE", "LOW_PRIORITY"),
        ("INACTIVE", "STRONG", "STOP"),
        ("INACTIVE", "NONE", "STOP"),
    ],
)
def test_locked_router_table(conformal, anchor, policy):
    assert route_prediction_set(conformal, anchor).policy == policy


def test_unknown_conformal_encoding_is_rejected():
    with pytest.raises(ValueError):
        parse_conformal_state("UNKNOWN")


def test_anchor_thresholds_are_reproducible_and_monotonic():
    thresholds = derive_anchor_thresholds([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    assert thresholds["moderate_threshold"] <= thresholds["strong_threshold"]
    assert classify_anchor(0.6, True, thresholds) == "STRONG"
    assert classify_anchor(None, False, thresholds) == "NONE"


def test_budget_allocation_is_exact_and_never_negative():
    for strategy in ("fixed", "uncertainty_only", "disease_only", "combined"):
        allocations = allocate_intent_budget(strategy, "ACTIVE|INACTIVE", "STRONG", 11)
        assert sum(allocations.values()) == 11
        assert all(value >= 0 for value in allocations.values())


def test_confident_inactive_combined_route_has_zero_budget():
    allocations = allocate_intent_budget("combined", "INACTIVE", "STRONG", 10)
    assert sum(allocations.values()) == 0


def test_fixed_strategy_is_independent_of_uncertainty_and_anchor():
    a = allocate_intent_budget("fixed", "ACTIVE", "STRONG", 10)
    b = allocate_intent_budget("fixed", "ACTIVE|INACTIVE", "NONE", 10)
    assert a == b

def test_uncertainty_only_arm_does_not_use_disease_anchor():
    strong = allocate_intent_budget("uncertainty_only", "ACTIVE|INACTIVE", "STRONG", 10)
    none = allocate_intent_budget("uncertainty_only", "ACTIVE|INACTIVE", "NONE", 10)
    assert strong == none
    assert strong["DISEASE_CONTEXT"] == 0


def test_disease_only_arm_does_not_use_conformal_state():
    active = allocate_intent_budget("disease_only", "ACTIVE", "STRONG", 10)
    uncertain = allocate_intent_budget("disease_only", "ACTIVE|INACTIVE", "STRONG", 10)
    assert active == uncertain
