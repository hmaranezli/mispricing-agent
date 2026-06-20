"""tests/test_phase6_1_b3_passive_client_wiring.py — Phase 6.1 Master B3 client wiring slice.

Locks Master B3 as a stateless, synchronous dumb-pipe client: it exact-field-reads passive B2
normalized evidence, calls produce_passive_shadow_input ONCE, and forwards the producer's output by
identity (pass or defensive). Authored under docs/handoff/phase6_1_master_b3_client_wiring_charter.md.

Adapter behavior is isolated from Phase 5 math by monkeypatching the producer; two minimal real
integration tests exercise the genuine producer path with hand-built passive carriers. Fixtures are
passive-only and built from scratch; no actionable Phase 5 fixture is imported.
"""
import ast
import inspect

import pytest

import phase6_1.b3_passive_client_wiring as b3
from phase6_1.b3_passive_client_wiring import (
    wire_passive_shadow_input,
    B3PassiveClientWiringError,
)
from phase6_1.b2_normalization_contract import (
    PublicRawSnapshotRecord,
    NormalizedEvidenceMaterial,
    make_public_raw_snapshot_record,
    make_unit_bound_magnitude,
    make_normalized_evidence_field_binding,
    make_normalized_evidence_material,
)
from phase6_1.passive_shadow_input import PassiveShadowInput
from phase5.pre_net_edge_calculation_input_boundary import make_observable_cost_validity_context
from phase5.observable_cost_friction_boundary import (
    make_observable_cost_observation,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
)
from phase5.blocked_result_boundary import BlockedPacket


# ---- passive-only fixtures (built from scratch; no actionable carrier) ----
def _raw(observed="1749990000000", venue="HYPERLIQUID", pair="BTC-USD"):
    return make_public_raw_snapshot_record(
        source_artifact="replay-fixture (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        venue=venue,
        pair=pair,
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="SINGLE_VENUE",
        venue_buy=venue,
        venue_sell=venue,
        retrieval_epoch_ms=1_750_000_000_000,
        observed_at_epoch_ms=observed,
        raw_snapshot_identity="replay-fixture-0001",
        field_payload=(("bid", "0.50"), ("ask", "0.60")),
    )


def _gross_binding(value="12.34", unit="bps"):
    return make_normalized_evidence_field_binding(
        normalized_field_name="gross_edge",
        source_field="summary.gross_edge",
        binding_role="GROSS_EDGE",
        unit_bound_magnitude=make_unit_bound_magnitude(magnitude=value, unit=unit),
    )


def _cost_binding(value="2.00", unit="bps"):
    return make_normalized_evidence_field_binding(
        normalized_field_name="total_cost",
        source_field="summary.total_cost",
        binding_role="COST",
        unit_bound_magnitude=make_unit_bound_magnitude(magnitude=value, unit=unit),
    )


def _material(bindings=None, observed="1749990000000", venue="HYPERLIQUID", pair="BTC-USD"):
    return make_normalized_evidence_material(
        raw_snapshot=_raw(observed=observed, venue=venue, pair=pair),
        normalized_field_bindings=bindings if bindings is not None else (_gross_binding(),),
        evidence_epoch_tolerance_ms=0,
    )


def _cost_obs(value="0", unit="bps"):
    digits = value.lstrip("-").replace(".", "")
    is_zero = set(digits) <= {"0"}
    evidence = ("explicitly observed zero cost from fees.maker_fee_bps" if is_zero
                else OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE)
    return make_observable_cost_observation(
        component_name="phase5_observable_cost_friction_boundary",
        origin_component="phase5_observed_cost_source_component",
        origin_result_status="OBSERVED",
        status="OBSERVABLE_COST_OBSERVED",
        cost_component_type="TAKER_FEE",
        signed_decimal_value=value,
        unit=unit,
        source_contract="phase5_observable_cost_friction_boundary_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="fees.taker_fee_bps",
        zero_cost_evidence=evidence,
        boundary_version="phase5.observable_cost_friction_boundary.v0",
    )


def _ctx(value="0", unit="bps"):
    return make_observable_cost_validity_context(
        cost_observation=_cost_obs(value=value, unit=unit),
        valid_from_epoch_ms="0",
        valid_until_epoch_ms="100000000000000",
        validity_source_contract="phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md",
        validity_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        validity_source_field="validity.fee_schedule_window",
        validity_assertion_type="DECLARED_VALIDITY_INTERVAL",
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )


class _Recorder:
    def __init__(self, ret=None):
        self.calls = []
        self.ret = ret

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.ret


# ---- minimal real integration (genuine producer path) ----
def test_pass_path_returns_real_passive_shadow_input():
    out = wire_passive_shadow_input(
        normalized_evidence_material=_material(),
        cost_validity_contexts=(_ctx(value="0", unit="bps"),),
    )
    assert type(out) is PassiveShadowInput
    assert out.net_edge_calculation_result.net_edge_value == "12.34"
    assert out.source_venue == "HYPERLIQUID"
    assert out.source_pair == "BTC-USD"
    assert out.observed_at_epoch_ms == 1749990000000
    assert out.capacity_pass_reference is None


def test_defensive_path_returns_blocked_packet_by_identity():
    out = wire_passive_shadow_input(
        normalized_evidence_material=_material(),
        cost_validity_contexts=(_ctx(value="2.00", unit="usd"),),
    )
    assert type(out) is BlockedPacket
    assert type(out) is not PassiveShadowInput


# ---- adapter isolation via monkeypatched producer ----
def test_b3_calls_producer_once_with_extracted_fields(monkeypatch):
    rec = _Recorder(ret=object())
    monkeypatch.setattr(b3, "produce_passive_shadow_input", rec)
    ctxs = (_ctx(value="0", unit="bps"),)
    wire_passive_shadow_input(
        normalized_evidence_material=_material(),
        cost_validity_contexts=ctxs,
    )
    assert len(rec.calls) == 1
    kw = rec.calls[0]
    assert kw["gross_edge_value"] == "12.34"
    assert kw["gross_edge_unit"] == "bps"
    assert kw["source_venue"] == "HYPERLIQUID"
    assert kw["source_pair"] == "BTC-USD"
    assert kw["observed_at_epoch_ms"] == 1749990000000
    assert type(kw["observed_at_epoch_ms"]) is int
    assert kw["cost_validity_contexts"] is ctxs


def test_b3_forwards_pass_output_by_identity(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(b3, "produce_passive_shadow_input", _Recorder(ret=sentinel))
    out = wire_passive_shadow_input(
        normalized_evidence_material=_material(),
        cost_validity_contexts=(_ctx(),),
    )
    assert out is sentinel


def test_b3_forwards_defensive_output_by_identity(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(b3, "produce_passive_shadow_input", _Recorder(ret=sentinel))
    out = wire_passive_shadow_input(
        normalized_evidence_material=_material(),
        cost_validity_contexts=(_ctx(),),
    )
    assert out is sentinel


def test_invalid_epoch_fails_defensively_and_producer_not_called(monkeypatch):
    rec = _Recorder(ret=object())
    monkeypatch.setattr(b3, "produce_passive_shadow_input", rec)
    bad_raw = object.__new__(PublicRawSnapshotRecord)
    object.__setattr__(bad_raw, "venue", "HYPERLIQUID")
    object.__setattr__(bad_raw, "pair", "BTC-USD")
    object.__setattr__(bad_raw, "observed_at_epoch_ms", "not-a-number")
    mat = object.__new__(NormalizedEvidenceMaterial)
    object.__setattr__(mat, "raw_snapshot", bad_raw)
    object.__setattr__(mat, "normalized_field_bindings", (_gross_binding(),))
    with pytest.raises(B3PassiveClientWiringError):
        wire_passive_shadow_input(
            normalized_evidence_material=mat, cost_validity_contexts=(_ctx(),)
        )
    assert rec.calls == []


def test_missing_gross_edge_binding_fails_defensively(monkeypatch):
    rec = _Recorder(ret=object())
    monkeypatch.setattr(b3, "produce_passive_shadow_input", rec)
    with pytest.raises(B3PassiveClientWiringError):
        wire_passive_shadow_input(
            normalized_evidence_material=_material(bindings=(_cost_binding(),)),
            cost_validity_contexts=(_ctx(),),
        )
    assert rec.calls == []


def test_non_material_input_fails_defensively(monkeypatch):
    rec = _Recorder(ret=object())
    monkeypatch.setattr(b3, "produce_passive_shadow_input", rec)
    with pytest.raises(B3PassiveClientWiringError):
        wire_passive_shadow_input(
            normalized_evidence_material={"raw": 1}, cost_validity_contexts=(_ctx(),)
        )
    assert rec.calls == []


# ---- AST / source locks on the B3 module ----
def _b3_tree():
    return ast.parse(inspect.getsource(b3))


def test_b3_signature_is_keyword_only():
    params = inspect.signature(wire_passive_shadow_input).parameters.values()
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params)


def test_b3_uses_no_isinstance():
    for node in ast.walk(_b3_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_b3_has_no_protocol_any():
    names = set()
    for node in ast.walk(_b3_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    assert names & {"Protocol", "Any"} == set()


def test_b3_is_clock_blind():
    tree = _b3_tree()
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots & {"time", "datetime", "calendar"} == set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"now", "utcnow", "today", "monotonic", "time", "perf_counter"}


def test_b3_has_no_concurrency_constructs():
    tree = _b3_tree()
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots & {"asyncio", "threading", "multiprocessing", "queue", "concurrent", "sched"} == set()


def test_b3_has_no_try_except_swallowing():
    for node in ast.walk(_b3_tree()):
        assert not isinstance(node, ast.Try), "B3 must not swallow/convert failures via try/except"


def test_b3_has_no_toxic_actionable_imports_or_tokens():
    tree = _b3_tree()
    tokens = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                tokens.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                tokens.add(node.module)
            for a in node.names:
                tokens.add(a.name)
        elif isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
    blob = " ".join(tokens).lower()
    for toxic in ("grossedgeobservation", "edge_direction", "shadowintent", "shadow_intent",
                  "capacity", "staleness", "shadowscore", "diagnostic_ev"):
        assert toxic not in blob, toxic


def test_b3_calls_producer_not_phase5_directly():
    tree = _b3_tree()
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert "phase5" not in roots, "B3 must talk to the producer, not Phase 5"
    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    assert "produce_passive_shadow_input" in referenced
    for forbidden in ("calculate_net_edge", "make_passive_shadow_input",
                      "make_passive_gross_edge_magnitude",
                      "make_passive_pre_net_edge_calculation_input"):
        assert forbidden not in referenced, forbidden


def test_b3_is_stateless_no_module_mutable_state():
    tree = ast.parse(inspect.getsource(b3))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assert isinstance(target, ast.Name) and target.id.isupper(), (
                    "module-level state must be UPPERCASE constants only"
                )
