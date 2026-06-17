"""tests/test_phase5_gross_edge_observation_boundary.py — pins the atomic offline/TDD implementation
of the `phase5_gross_edge_observation_boundary` single observed gross-edge carrier slice.

This implements ONLY the atomic `GrossEdgeObservation` — a frozen, scalar-only, anti-truthiness,
anti-coercion carrier of exactly one explicitly observed gross-edge fact — plus a misrouted
halt-carrier guard. It is not actionable, not a trade signal, not a calculator input, not an
aggregate, and not a parser. Construction is keyword-only via make_gross_edge_observation; positional
construction is rejected (init=False); every field is an exact non-empty str; gross_edge_value and
observed_size are canonical exact decimal strings (no float parsing); observed_size may not be
negative; observed_at_epoch_ms and staleness_threshold_ms are exact integer strings; venue_scope is a
fixed enum with SINGLE_VENUE/CROSS_VENUE venue relationships; reject_misrouted_halt_carrier raises for
exact BlockedPacket / NoEligibleHaltPacket only. Static hardcoded values only; no IO.
"""
import dataclasses

import pytest

from phase5.gross_edge_observation_boundary import (
    GrossEdgeObservation,
    make_gross_edge_observation,
    reject_misrouted_halt_carrier,
    GROSS_EDGE_VENUE_SCOPE_SINGLE,
    GROSS_EDGE_VENUE_SCOPE_CROSS,
    GrossEdgeTruthinessError,
    GrossEdgeCoercionError,
    GrossEdgeConstructionError,
    GrossEdgeVenueScopeError,
    MisroutedHaltCarrierError,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)


PLANNED_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "edge_direction",
    "base_asset",
    "quote_asset",
    "instrument_id",
    "venue_scope",
    "venue_buy",
    "venue_sell",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "gross_edge_value",
    "gross_edge_unit",
    "gross_edge_source_contract",
    "gross_edge_source_artifact",
    "gross_edge_source_field",
    "observed_size",
    "size_unit",
    "depth_source_contract",
    "depth_source_artifact",
    "depth_source_field",
    "boundary_version",
]

FORBIDDEN_FIELDS = [
    "total_cost", "net_cost", "effective_cost", "net_edge", "profit", "expected_profit",
    "readiness", "trade_score", "eligibility", "trade_size", "order_size", "allocation",
    "valid_until",
]


def _valid_kwargs(**overrides):
    kwargs = dict(
        component_name="phase5_gross_edge_observation_boundary",
        origin_component="phase5_gross_edge_source_component",
        origin_result_status="OBSERVED",
        status="GROSS_EDGE_OBSERVED",
        edge_direction="LONG",
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope=GROSS_EDGE_VENUE_SCOPE_SINGLE,
        venue_buy="HYPERLIQUID",
        venue_sell="HYPERLIQUID",
        observed_at_epoch_ms="1781637248000",
        staleness_threshold_ms="60000",
        gross_edge_value="12.34",
        gross_edge_unit="bps",
        gross_edge_source_contract="phase5_gross_edge_observation_boundary_implementation_planning.md",
        gross_edge_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        gross_edge_source_field="signals.gross_edge_bps",
        observed_size="100",
        size_unit="base_amount",
        depth_source_contract="phase5_gross_edge_observation_boundary_implementation_planning.md",
        depth_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        depth_source_field="book.top_depth_base",
        boundary_version="phase5.gross_edge_observation_boundary.v0",
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
    assert GrossEdgeObservation.__name__ == "GrossEdgeObservation"


def test_venue_scope_constants():
    assert GROSS_EDGE_VENUE_SCOPE_SINGLE == "SINGLE_VENUE"
    assert GROSS_EDGE_VENUE_SCOPE_CROSS == "CROSS_VENUE"


def test_keyword_construction_works():
    p = make_gross_edge_observation(**_valid_kwargs())
    assert isinstance(p, GrossEdgeObservation)


def test_exact_fields():
    p = make_gross_edge_observation(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(p)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_no_forbidden_fields():
    names = {f.name for f in dataclasses.fields(GrossEdgeObservation)}
    for banned in FORBIDDEN_FIELDS:
        assert banned not in names, f"forbidden field present: {banned}"


def test_frozen_and_direct_construction_rejected():
    p = make_gross_edge_observation(**_valid_kwargs())
    assert dataclasses.is_dataclass(p)
    assert p.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.status = "MUTATED"
    with pytest.raises(TypeError):
        GrossEdgeObservation("phase5_gross_edge_observation_boundary")


def test_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_gross_edge_observation("phase5_gross_edge_observation_boundary")


# ---- exact-str / None / container / numeric enforcement ----
def test_none_rejected_for_every_field():
    assert issubclass(GrossEdgeConstructionError, TypeError)
    for name in PLANNED_FIELDS:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(**{name: None}))


def test_container_values_rejected():
    for bad in [(), ("a",), ["1"], {"k": "v"}, {1, 2}, frozenset({1})]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(base_asset=bad))


def test_non_string_scalars_rejected():
    for bad in [0, 1, False, True, 3.14, 12, -1]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(base_asset=bad))


def test_str_subclass_rejected_exact_type():
    class _StrSub(str):
        pass
    with pytest.raises(GrossEdgeConstructionError):
        make_gross_edge_observation(**_valid_kwargs(base_asset=_StrSub("BTC")))


def test_empty_and_whitespace_rejected():
    for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(base_asset=bad))


def test_hostile_value_rejected_without_str_repr_eq():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
    with pytest.raises(GrossEdgeConstructionError):
        make_gross_edge_observation(**_valid_kwargs(gross_edge_source_field=_Hostile()))


# ---- canonical decimal: gross_edge_value (negative allowed) ----
def test_gross_edge_value_accepts_canonical_including_negative():
    for good in ["0", "0.0", "12", "12.34", "-0.25", "-100", "100"]:
        p = make_gross_edge_observation(**_valid_kwargs(gross_edge_value=good))
        assert p.gross_edge_value == good


def test_gross_edge_value_rejects_noncanonical():
    for bad in ["1e-3", "+1", " 1", "1 ", "1.", ".1", "NaN", "Infinity", "-Infinity",
                "", "   ", "1,234", "--1", "1.2.3", "-"]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(gross_edge_value=bad))


def test_gross_edge_value_rejects_numeric_type():
    for bad in [0, 0.0, 12.34, -1, True]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(gross_edge_value=bad))


# ---- canonical decimal: observed_size (non-negative) ----
def test_observed_size_accepts_nonnegative_canonical():
    for good in ["0", "0.0", "12", "12.34", "100"]:
        p = make_gross_edge_observation(**_valid_kwargs(observed_size=good))
        assert p.observed_size == good


def test_observed_size_rejects_negative():
    for bad in ["-0.25", "-100", "-0", "-0.0"]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(observed_size=bad))


def test_observed_size_rejects_noncanonical():
    for bad in ["1e-3", "+1", " 1", "1.", ".1", "NaN", "", "   "]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(observed_size=bad))


# ---- exact integer string fields ----
def test_epoch_and_staleness_accept_integer_strings():
    p = make_gross_edge_observation(**_valid_kwargs(
        observed_at_epoch_ms="0", staleness_threshold_ms="123456789"))
    assert p.observed_at_epoch_ms == "0"
    assert p.staleness_threshold_ms == "123456789"


def test_epoch_and_staleness_reject_non_integer_strings():
    for field in ("observed_at_epoch_ms", "staleness_threshold_ms"):
        for bad in ["-1", "1.0", "1e3", "+1", " 1", "1 ", "", "NaN", "0x1", "12.34"]:
            with pytest.raises(GrossEdgeConstructionError):
                make_gross_edge_observation(**_valid_kwargs(**{field: bad}))


# ---- venue rules ----
def test_venue_scope_must_be_allowed_value():
    assert issubclass(GrossEdgeVenueScopeError, TypeError)
    for bad in ["", "single_venue", "NOT_A_SCOPE", "NONE", "N/A", "SINGLE", "CROSS"]:
        with pytest.raises((GrossEdgeVenueScopeError, GrossEdgeConstructionError)):
            make_gross_edge_observation(**_valid_kwargs(venue_scope=bad))


def test_single_venue_requires_equal_buy_sell():
    p = make_gross_edge_observation(**_valid_kwargs(
        venue_scope=GROSS_EDGE_VENUE_SCOPE_SINGLE, venue_buy="HL", venue_sell="HL"))
    assert p.venue_scope == "SINGLE_VENUE"
    with pytest.raises(GrossEdgeVenueScopeError):
        make_gross_edge_observation(**_valid_kwargs(
            venue_scope=GROSS_EDGE_VENUE_SCOPE_SINGLE, venue_buy="HL", venue_sell="BINANCE"))


def test_cross_venue_requires_distinct_buy_sell():
    p = make_gross_edge_observation(**_valid_kwargs(
        venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS, venue_buy="HYPERLIQUID", venue_sell="BINANCE"))
    assert p.venue_scope == "CROSS_VENUE"
    with pytest.raises(GrossEdgeVenueScopeError):
        make_gross_edge_observation(**_valid_kwargs(
            venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS, venue_buy="HL", venue_sell="HL"))


def test_no_venue_sentinels():
    for bad in ["NOT_APPLICABLE", "NONE", "N/A", "null", "none"]:
        with pytest.raises(GrossEdgeVenueScopeError):
            make_gross_edge_observation(**_valid_kwargs(
                venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS, venue_buy="HYPERLIQUID", venue_sell=bad))


# ---- direction ----
def test_edge_direction_allowed_set():
    for good in ["LONG", "SHORT", "CROSS_VENUE"]:
        p = make_gross_edge_observation(**_valid_kwargs(edge_direction=good))
        assert p.edge_direction == good


def test_edge_direction_rejects_unknown():
    for bad in ["BUY", "SELL", "long", "", "UP"]:
        with pytest.raises(GrossEdgeConstructionError):
            make_gross_edge_observation(**_valid_kwargs(edge_direction=bad))


# ---- anti-truthiness / anti-coercion ----
def test_anti_truthiness():
    p = make_gross_edge_observation(**_valid_kwargs())
    assert issubclass(GrossEdgeTruthinessError, TypeError)
    with pytest.raises(GrossEdgeTruthinessError):
        bool(p)
    with pytest.raises(GrossEdgeTruthinessError):
        len(p)
    with pytest.raises(GrossEdgeTruthinessError):
        _ = "y" if p else "n"


def test_anti_coercion():
    p = make_gross_edge_observation(**_valid_kwargs())
    assert issubclass(GrossEdgeCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(GrossEdgeCoercionError):
            fn(p)
    with pytest.raises(GrossEdgeCoercionError):
        import operator
        operator.index(p)


# ---- safe repr ----
def test_repr_safe_and_limited():
    p = make_gross_edge_observation(**_valid_kwargs(
        gross_edge_value="-0.25", observed_size="100",
        observed_at_epoch_ms="1781637248000", staleness_threshold_ms="60000",
        gross_edge_source_field="signals.gross_edge_bps"))
    r = repr(p)
    assert "phase5_gross_edge_observation_boundary" in r   # component_name
    assert "GROSS_EDGE_OBSERVED" in r                      # status
    assert "LONG" in r                                     # edge_direction
    assert "BTC" in r                                      # base_asset
    assert "USD" in r                                      # quote_asset
    assert "BTC-USD-PERP" in r                             # instrument_id
    assert "SINGLE_VENUE" in r                             # venue_scope
    # values / timestamps / provenance must NOT leak
    assert "-0.25" not in r
    assert "1781637248000" not in r
    assert "60000" not in r
    assert "signals.gross_edge_bps" not in r
    low = r.lower()
    for banned in ["profit", "ready", "tradeable", "data quality", "truth"]:
        assert banned not in low


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
