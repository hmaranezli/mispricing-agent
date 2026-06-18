"""tests/test_phase5_profitability_threshold_policy_context.py — pins the atomic offline/TDD
implementation of the FIRST carrier slice of the `phase5_net_edge_profitability_gate_boundary`
component: `ProfitabilityThresholdPolicyContext`.

This implements ONLY the atomic `ProfitabilityThresholdPolicyContext` — a frozen, anti-truthiness,
anti-coercion carrier of explicit threshold policy data and provenance — plus a misrouted halt-carrier
guard. Per the planning artifact (`phase5_net_edge_profitability_gate_implementation_planning.md`) it
is NOT `NetEdgeProfitabilityGate`, NOT `net_edge_profitability_preflight`, NOT a comparator/calculator,
and it performs no IO/network/env/datetime/random/subprocess. It carries declared threshold metadata
only: it does NOT compare `threshold_value` to zero, does NOT interpret profitability, does NOT compare
`threshold_unit` to any result unit, does NOT parse provenance, and does NOT compute/infer/default a
threshold. Construction is keyword-only via `make_profitability_threshold_policy_context`; positional
construction is rejected (`init=False`); every field is an exact non-empty `str`; `threshold_value` is
a canonical signed decimal string (negative/zero/positive all valid). Static hardcoded values only;
no IO.
"""
import dataclasses

import pytest

from phase5.net_edge_profitability_gate_boundary import (
    ProfitabilityThresholdPolicyContext,
    make_profitability_threshold_policy_context,
    reject_misrouted_halt_carrier,
    ProfitabilityThresholdPolicyTruthinessError,
    ProfitabilityThresholdPolicyCoercionError,
    ProfitabilityThresholdPolicyConstructionError,
    MisroutedHaltCarrierError,
    PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)

PLANNED_FIELDS = [
    "component_name",
    "threshold_value",
    "threshold_unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "policy_id",
    "boundary_version",
]

FORBIDDEN_FIELDS = [
    "net_edge_value", "net_edge_unit", "actionable", "eligible", "ready", "readiness",
    "executable", "trade", "order", "allocation", "paper_live", "live", "profitability",
    "venue", "base_asset", "quote_asset", "instrument_id",
]

METADATA_STR_FIELDS = [
    "component_name", "threshold_unit", "source_contract", "source_artifact",
    "source_field", "policy_id", "boundary_version",
]


def _valid_kwargs(**overrides):
    kwargs = dict(
        component_name="phase5_net_edge_profitability_gate_boundary",
        threshold_value="1.25",
        threshold_unit="bps",
        source_contract="phase5_net_edge_profitability_gate_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="policy.min_net_edge_bps",
        policy_id="POLICY_MIN_NET_EDGE_V1",
        boundary_version="phase5.net_edge_profitability_gate_boundary.v0",
    )
    kwargs.update(overrides)
    return kwargs


def _valid_blocked_packet():
    return make_blocked_packet(
        component_name="phase5_blocked_result_boundary",
        origin_component="phase5_input_provenance_preflight",
        origin_result_status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        blocked_status="BLOCKED_NEEDS_EVIDENCE",
        reason_code="BLOCKED_MISSING_REQUIRED_PROVENANCE_FIELD",
        missing_or_invalid_field="provenance.source_artifact",
        source_contract="phase5_fail_closed_blocked_state_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="provenance.source_artifact",
        deterministic_next_action="HALT_FAIL_CLOSED",
        human_review_required=True,
        may_retry_after_evidence=True,
        created_from_contract="phase5_blocked_result_boundary_implementation_planning.md",
        boundary_version="phase5.blocked_result_boundary.v0",
    )


def _valid_no_eligible_packet():
    return make_no_eligible_halt_packet(
        component_name="phase5_no_eligible_halt_propagation_boundary",
        origin_component="phase5_eligibility_source_component",
        origin_result_status="NO_ELIGIBLE",
        status="NO_ELIGIBLE",
        no_eligible_reason="NO_ELIGIBLE_CANDIDATE_WITHIN_CHECKED_SCOPE",
        source_contract="phase5_no_eligible_handling_schema_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="HALT_BYPASS_NO_ELIGIBLE",
        boundary_version="phase5.no_eligible_halt_propagation_boundary.v0",
    )


# ---- identity / shape ----
def test_canonical_name():
    assert ProfitabilityThresholdPolicyContext.__name__ == "ProfitabilityThresholdPolicyContext"


def test_component_name_constant():
    assert PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME == "phase5_net_edge_profitability_gate_boundary"


def test_keyword_construction_works():
    p = make_profitability_threshold_policy_context(**_valid_kwargs())
    assert isinstance(p, ProfitabilityThresholdPolicyContext)


def test_exact_fields():
    p = make_profitability_threshold_policy_context(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(p)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_no_forbidden_fields():
    names = {f.name for f in dataclasses.fields(ProfitabilityThresholdPolicyContext)}
    for banned in FORBIDDEN_FIELDS:
        assert banned not in names, f"forbidden field present: {banned}"


def test_frozen_dataclass():
    p = make_profitability_threshold_policy_context(**_valid_kwargs())
    assert dataclasses.is_dataclass(p)
    assert p.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.threshold_value = "9.99"


def test_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_profitability_threshold_policy_context("phase5_net_edge_profitability_gate_boundary")


def test_direct_positional_construction_rejected():
    with pytest.raises(TypeError):
        ProfitabilityThresholdPolicyContext("phase5_net_edge_profitability_gate_boundary")


# ---- exact-str / None / container / numeric enforcement ----
def test_none_rejected_for_every_field():
    assert issubclass(ProfitabilityThresholdPolicyConstructionError, TypeError)
    for name in PLANNED_FIELDS:
        with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
            make_profitability_threshold_policy_context(**_valid_kwargs(**{name: None}))


def test_container_values_rejected():
    for bad in [(), ("a",), ["1"], {"k": "v"}, {1, 2}, frozenset({1})]:
        with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
            make_profitability_threshold_policy_context(**_valid_kwargs(threshold_unit=bad))


def test_non_string_scalars_rejected():
    for bad in [0, 1, False, True, 3.14, 12, -1]:
        with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
            make_profitability_threshold_policy_context(**_valid_kwargs(policy_id=bad))


def test_threshold_value_must_be_string_not_number():
    for bad in [0, 0.0, 1, 1.25, -1, True]:
        with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
            make_profitability_threshold_policy_context(**_valid_kwargs(threshold_value=bad))


def test_threshold_value_decimal_object_rejected():
    from decimal import Decimal
    with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
        make_profitability_threshold_policy_context(**_valid_kwargs(threshold_value=Decimal("1.25")))


def test_str_subclass_rejected_exact_type():
    class _StrSub(str):
        pass
    with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
        make_profitability_threshold_policy_context(**_valid_kwargs(threshold_unit=_StrSub("bps")))


def test_empty_and_whitespace_metadata_rejected():
    for field in METADATA_STR_FIELDS:
        for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
            with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
                make_profitability_threshold_policy_context(**_valid_kwargs(**{field: bad}))


def test_hostile_field_value_rejected_without_str_repr_eq():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
    with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
        make_profitability_threshold_policy_context(**_valid_kwargs(source_field=_Hostile()))


# ---- canonical signed decimal threshold_value ----
def test_threshold_value_accepts_canonical_signed_decimals():
    for good in ["0", "1", "1.25", "-1", "-0.5", "0.000001", "100", "-100", "12.34"]:
        p = make_profitability_threshold_policy_context(**_valid_kwargs(threshold_value=good))
        assert p.threshold_value == good   # preserved verbatim


def test_threshold_value_rejects_noncanonical_strings():
    for bad in ["", " ", "+1", "01", "1.", ".1", "-.1", "1.0.0", "1E-7", "1e-7",
                "NaN", "Infinity", "-Infinity", "inf", "  1", "1 ", "1,000", "--1", "-"]:
        with pytest.raises(ProfitabilityThresholdPolicyConstructionError):
            make_profitability_threshold_policy_context(**_valid_kwargs(threshold_value=bad))


def test_negative_zero_positive_thresholds_all_valid():
    for value in ["-2.5", "0", "0.0", "3.75"]:
        p = make_profitability_threshold_policy_context(**_valid_kwargs(threshold_value=value))
        assert p.threshold_value == value   # no sign morality, no zero comparison, no normalization


def test_threshold_unit_is_case_sensitive_exact_str():
    for unit in ["bps", "BPS", "USD", "PERCENT", "percentage"]:
        p = make_profitability_threshold_policy_context(**_valid_kwargs(threshold_unit=unit))
        assert p.threshold_unit == unit


# ---- anti-truthiness / anti-coercion ----
def test_anti_truthiness():
    p = make_profitability_threshold_policy_context(**_valid_kwargs())
    assert issubclass(ProfitabilityThresholdPolicyTruthinessError, TypeError)
    with pytest.raises(ProfitabilityThresholdPolicyTruthinessError):
        bool(p)
    with pytest.raises(ProfitabilityThresholdPolicyTruthinessError):
        len(p)
    with pytest.raises(ProfitabilityThresholdPolicyTruthinessError):
        _ = "y" if p else "n"


def test_anti_coercion():
    p = make_profitability_threshold_policy_context(**_valid_kwargs())
    assert issubclass(ProfitabilityThresholdPolicyCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(ProfitabilityThresholdPolicyCoercionError):
            fn(p)
    with pytest.raises(ProfitabilityThresholdPolicyCoercionError):
        import operator
        operator.index(p)


# ---- safe repr ----
def test_repr_safe_and_limited():
    p = make_profitability_threshold_policy_context(**_valid_kwargs(
        threshold_value="-0.5", source_field="policy.min_net_edge_bps",
        policy_id="POLICY_MIN_NET_EDGE_V1"))
    r = repr(p)
    assert "phase5_net_edge_profitability_gate_boundary" in r   # component_name (safe identifier)
    assert "POLICY_MIN_NET_EDGE_V1" in r                        # policy_id (safe identifier)
    # threshold value and sensitive provenance must NOT leak through repr
    assert "-0.5" not in r
    assert "policy.min_net_edge_bps" not in r                   # source_field
    assert "phase4c_batch_1781637248" not in r                  # source_artifact
    # The class name / component_name / policy_id legitimately contain "profit"/"edge"; strip those
    # known-safe identifiers, then assert no OTHER economic/readiness wording leaked in.
    residual = (r.replace("ProfitabilityThresholdPolicyContext", "")
                 .replace("phase5_net_edge_profitability_gate_boundary", "")
                 .replace("POLICY_MIN_NET_EDGE_V1", "").lower())
    for banned in ["profit", "edge", "ready", "actionable", "tradeable", "data quality", "truth"]:
        assert banned not in residual


# ---- misrouted halt carrier protection ----
def test_misroute_rejects_exact_blocked_packet():
    assert issubclass(MisroutedHaltCarrierError, TypeError)
    with pytest.raises(MisroutedHaltCarrierError):
        reject_misrouted_halt_carrier(_valid_blocked_packet())


def test_misroute_rejects_exact_no_eligible_packet():
    with pytest.raises(MisroutedHaltCarrierError):
        reject_misrouted_halt_carrier(_valid_no_eligible_packet())


def test_misroute_message_uses_type_name_only():
    with pytest.raises(MisroutedHaltCarrierError) as exc:
        reject_misrouted_halt_carrier(_valid_blocked_packet())
    assert "BlockedPacket" in str(exc.value)


def test_misroute_subclass_not_treated_as_exact_halt_carrier():
    class _BSub(BlockedPacket):
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0

    class _NSub(NoEligibleHaltPacket):
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0

    assert reject_misrouted_halt_carrier(object.__new__(_BSub)) is None
    assert reject_misrouted_halt_carrier(object.__new__(_NSub)) is None


def test_misroute_returns_none_for_non_halt_without_introspection():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __bool__(self):
            raise AssertionError("bool must not be called")
        def __len__(self):
            raise AssertionError("len must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
        def __getattr__(self, name):
            raise AssertionError("introspection must not happen")

    for benign in [None, 0, "x", object(), _Hostile()]:
        assert reject_misrouted_halt_carrier(benign) is None


# ---- no gate / comparator / packet behavior in this slice ----
def test_no_gate_or_comparator_symbols_exported():
    import phase5.net_edge_profitability_gate_boundary as mod
    for banned in [
        "compare_net_edge",
        "evaluate_profitability",
        "net_edge_threshold_evaluation",
    ]:
        assert not hasattr(mod, banned), f"forbidden symbol exported in carrier slice: {banned}"


def test_no_module_clock_or_io_usage():
    with open("phase5/net_edge_profitability_gate_boundary.py", encoding="utf-8") as f:
        src = f.read()
    for forbidden in ["import time", "time.time(", "datetime.", "import os", "import random",
                      "subprocess.", "open(", "import json", ".upper(", ".lower(", ".casefold(",
                      "float("]:
        assert forbidden not in src, f"forbidden code usage in carrier module: {forbidden}"
