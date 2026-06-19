"""tests/test_phase6_1_passive_shadow_input.py — Phase 6.1 Slice 0A.

Pins the atomic offline/TDD implementation of `PassiveShadowInput`: a passive, frozen, slotted,
anti-coercion carrier that references exactly one Phase 5 `NetEdgeCalculationResult` BY IDENTITY and
carries minimal market provenance (venue, pair, observed UTC epoch-ms) plus a deferred
`capacity_pass_reference`. It performs NO economic/diagnostic/scoring/readiness calculation, exposes
no actionability verdict, and constructs nothing live. Replay-first only: every input here is static
and deterministic — no network, no clock, no env, no IO.

The `_FORBIDDEN_TOKENS` list and the actionability-token strings in this test file are the EXPLICIT
test fixtures permitted by the Slice 0A charter; they must NOT appear in the Phase 6.1 runtime source.
"""
import datetime
import os

import pytest

from phase5.net_edge_calculator_boundary import (
    NetEdgeCalculationResult,
    _make_net_edge_result,
)
from phase6_1.passive_shadow_input import (
    PassiveShadowInput,
    make_passive_shadow_input,
    PassiveShadowInputTypeError,
    PassiveShadowInputValueError,
    PassiveShadowInputCapacityError,
    PassiveShadowInputTruthinessError,
    PassiveShadowInputCoercionError,
)


# --- deterministic, replay-first helpers (no network / clock / IO) ---------------------------------

def _real_net_edge_result():
    """Construct one genuine Phase 5 NetEdgeCalculationResult from static canonical strings."""
    return _make_net_edge_result(
        component_name="phase5_net_edge_calculator_boundary",
        origin_component="phase5_net_edge_calculator_boundary",
        origin_result_status="OBSERVED",
        status="CALCULATED",
        gross_edge_value="0.010",
        gross_edge_unit="proportion",
        total_cost_value="0.004",
        total_cost_unit="proportion",
        net_edge_value="0.006",
        net_edge_unit="proportion",
        cost_component_count="2",
        source_contract="phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_field="net_edge.calculated_value",
        calculation_method="gross_minus_costs",
        boundary_version="phase5.net_edge_calculator_boundary.v0",
    )


def _make(**overrides):
    kwargs = dict(
        net_edge_calculation_result=_real_net_edge_result(),
        source_venue="hyperliquid",
        source_pair="BTC-USD",
        observed_at_epoch_ms=1_750_000_000_000,
    )
    kwargs.update(overrides)
    return make_passive_shadow_input(**kwargs)


# --- 1. exact-type acceptance/rejection for the NetEdgeCalculationResult reference -----------------

def test_accepts_and_holds_net_edge_calculation_result_by_identity():
    necr = _real_net_edge_result()
    psi = _make(net_edge_calculation_result=necr)
    assert psi.net_edge_calculation_result is necr


def test_rejects_non_net_edge_calculation_result_reference():
    with pytest.raises(PassiveShadowInputTypeError):
        _make(net_edge_calculation_result=object())


# --- 2. rejects dict/list/set mutable field values ------------------------------------------------

@pytest.mark.parametrize("bad", [{"a": 1}, ["x"], {"y"}])
def test_rejects_mutable_container_as_net_edge_reference(bad):
    with pytest.raises(PassiveShadowInputTypeError):
        _make(net_edge_calculation_result=bad)


@pytest.mark.parametrize("bad", [{"v": 1}, ["BTC-USD"], {"hyperliquid"}])
def test_rejects_mutable_container_as_provenance_field(bad):
    with pytest.raises(PassiveShadowInputTypeError):
        _make(source_venue=bad)


# --- 3. rejects subclass / isinstance leakage -----------------------------------------------------

def test_rejects_net_edge_result_subclass_instance():
    class _SubResult(NetEdgeCalculationResult):
        pass

    sub = object.__new__(_SubResult)  # an isinstance(...) of NetEdgeCalculationResult, wrong exact type
    assert isinstance(sub, NetEdgeCalculationResult)
    with pytest.raises(PassiveShadowInputTypeError):
        _make(net_edge_calculation_result=sub)


def test_rejects_str_subclass_provenance():
    class _SubStr(str):
        pass

    with pytest.raises(PassiveShadowInputTypeError):
        _make(source_venue=_SubStr("hyperliquid"))


# --- 4. rejects bool-as-int and silent numeric coercion -------------------------------------------

@pytest.mark.parametrize("bad", [True, False])
def test_rejects_bool_as_epoch(bad):
    with pytest.raises(PassiveShadowInputTypeError):
        _make(observed_at_epoch_ms=bad)


@pytest.mark.parametrize("bad", ["1750000000000", 1.0, 1750000000000.0])
def test_rejects_non_int_epoch_coercion(bad):
    with pytest.raises(PassiveShadowInputTypeError):
        _make(observed_at_epoch_ms=bad)


def test_rejects_negative_epoch():
    with pytest.raises(PassiveShadowInputValueError):
        _make(observed_at_epoch_ms=-1)


# --- 5. rejects non-deferred capacity_pass_reference ----------------------------------------------

def test_capacity_pass_reference_defaults_to_deferred_none():
    psi = _make()
    assert psi.capacity_pass_reference is None


@pytest.mark.parametrize("bad", ["PASSED", 1, True, object(), {"capacity": "ok"}])
def test_rejects_non_deferred_capacity_pass_reference(bad):
    with pytest.raises(PassiveShadowInputCapacityError):
        _make(capacity_pass_reference=bad)


# --- 6. rejects naive datetime / string timestamp inputs ------------------------------------------

def test_rejects_naive_datetime_timestamp():
    with pytest.raises(PassiveShadowInputTypeError):
        _make(observed_at_epoch_ms=datetime.datetime(2026, 6, 19, 12, 0, 0))


def test_rejects_timezone_local_string_timestamp():
    with pytest.raises(PassiveShadowInputTypeError):
        _make(observed_at_epoch_ms="2026-06-19T12:00:00+03:00")


# --- 7. zero calculation / no actionability methods -----------------------------------------------

def test_no_calculation_or_actionability_methods_exist():
    psi = _make()
    public_attrs = [n for n in dir(psi) if not n.startswith("_")]
    expected_fields = {
        "component_name",
        "boundary_version",
        "net_edge_calculation_result",
        "capacity_pass_reference",
        "source_venue",
        "source_pair",
        "observed_at_epoch_ms",
    }
    assert set(public_attrs) == expected_fields
    # none of the closed fields is callable (pure data carrier, no methods)
    for name in public_attrs:
        assert not callable(getattr(psi, name))
    banned_substrings = (
        "calculate", "compute", "score", "expected_value", "diagnostic",
        "slippage", "readiness", "actionable",
    )
    for name in dir(psi):
        low = name.lower()
        assert not any(tok in low for tok in banned_substrings), name


# --- 8. frozen / slotted / no dynamic attribute injection -----------------------------------------

def test_frozen_blocks_attribute_set():
    psi = _make()
    with pytest.raises(Exception):
        psi.source_venue = "kraken"


def test_slotted_blocks_dynamic_attribute_injection():
    psi = _make()
    assert not hasattr(psi, "__dict__")
    with pytest.raises(AttributeError):
        object.__setattr__(psi, "injected_attr", 1)


def test_direct_construction_is_blocked():
    with pytest.raises(PassiveShadowInputTypeError):
        PassiveShadowInput()


# --- anti-coercion (requirement 8) ----------------------------------------------------------------

def test_anti_coercion_dunders_raise():
    psi = _make()
    with pytest.raises(PassiveShadowInputTruthinessError):
        bool(psi)
    with pytest.raises(PassiveShadowInputTruthinessError):
        len(psi)
    for fn in (int, float, complex):
        with pytest.raises(PassiveShadowInputCoercionError):
            fn(psi)
    with pytest.raises(PassiveShadowInputCoercionError):
        str(psi)
    with pytest.raises(PassiveShadowInputCoercionError):
        bytes(psi)


# --- 9. forbidden actionability tokens absent from Phase 6.1 runtime (test fixtures excepted) ------

_FORBIDDEN_TOKENS = (
    "wallet", "balance", "private account", "api secret", "secret",
    "order intent", "orderintent", "order", "routing", "route",
    "execution", "execute", "allocation", "sizing",
    "tradecandidate", "signal", "candidate",
    "live_trade", "live trade", "paper_trade", "paper trade",
)


def test_forbidden_tokens_absent_from_phase6_1_runtime_source():
    import phase6_1.passive_shadow_input as runtime_mod

    runtime_path = runtime_mod.__file__
    assert os.path.basename(runtime_path) == "passive_shadow_input.py"
    with open(runtime_path, "r", encoding="utf-8") as fh:
        source_low = fh.read().lower()
    present = [tok for tok in _FORBIDDEN_TOKENS if tok in source_low]
    assert present == [], "forbidden actionability tokens leaked into runtime: %r" % present
