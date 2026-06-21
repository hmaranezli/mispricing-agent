"""tests/test_phase6_1_s5_runner.py — Phase 6.1 S5 in-memory runner orchestration.

Pins the dumb, strictly-synchronous, single-threaded S5 coordinator that drives the frozen
Reader -> S2 -> {pass path | halt path} -> S1 reference sink pipeline, one record at a time, to natural
EOF. S5 manufactures no provenance/identity/payload/timestamp/cursor; it carries the caller-supplied
passive contexts and routes ratified structural halt carriers to S4 by exact type. Raw component
exceptions propagate (hard fail-fast); nothing is swallowed, dropped, retried, or repaired.

Forbidden tokens/identifiers appearing in THIS test file are explicit fixtures; the runtime module must
contain none of them.
"""
import ast
import inspect
import io

import pytest

import phase6_1
import phase6_1.s5_runner as s5_runner
from phase6_1.s5_runner import (
    run_in_memory_shadow_pipeline,
    S5RunnerUnexpectedOutputError,
    S5_RUNNER_COMPONENT_NAME,
)
from phase6_1.s1_in_memory_observation_sink import (
    S1InMemoryObservationSink,
    ObservationScoreRecord,
    ObservationHaltRecord,
)
from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate
from phase6_1.option_b_event_stream_reader import OptionBLocalParseHalt
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext
from phase6_1.b2_pass_path_ingestion import (
    B2PassPathIngestionValueError,
    B2PassPathIngestionTypeError,
)


_MODULE_BASENAME = "s5_runner.py"

# one valid pass payload line; gross/cost units cohere at "proportion" so net == gross == "7".
_PASS_LINE = (
    '{"gross_magnitude": "7", "unit": "proportion", "venue": "hl", "pair": "BTC", '
    '"observed_at_epoch_ms": "1750000000000"}\n'
)
# one malformed line -> reader emits an OptionBLocalParseHalt in the payload slot.
_MALFORMED_LINE = '{bad json not parseable\n'

_EXPECTED_INPUTS = (
    "text_stream", "artifact_locator", "market_provenance_context",
    "gross_edge_binding_label_context", "evidence_epoch_tolerance_ms", "observation_sink",
)


def _provenance():
    return MarketProvenanceContext(
        source_artifact="docs/handoff/replay_artifact_lines",
        source_field="replay.line",
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="hyperliquid_perp",
        venue_buy="hyperliquid",
        venue_sell="hyperliquid",
        retrieval_epoch_ms=1_750_000_000_500,   # != observed so the frozen anti-copy lock passes
        raw_snapshot_identity="market-identity-0001",
    )


def _label():
    return GrossEdgeBindingLabelContext(
        normalized_field_name="gross_edge_magnitude",
        source_field="raw.gross_magnitude",
    )


def _run(text, sink=None, tol=0, locator="loc"):
    sink = S1InMemoryObservationSink() if sink is None else sink
    run_in_memory_shadow_pipeline(
        text_stream=io.StringIO(text),
        artifact_locator=locator,
        market_provenance_context=_provenance(),
        gross_edge_binding_label_context=_label(),
        evidence_epoch_tolerance_ms=tol,
        observation_sink=sink,
    )
    return sink


def _module_path():
    import pathlib  # test-only path resolution; the runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _module_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return fh.read()


# --- equal-peer routing: pass + halt, in order ----------------------------------------------------

def test_pass_and_halt_recorded_as_equal_peers_in_order():
    snap = _run(_PASS_LINE + _MALFORMED_LINE).snapshot()
    assert len(snap) == 2
    assert type(snap[0]) is ObservationScoreRecord
    assert type(snap[1]) is ObservationHaltRecord


def test_pass_path_produces_score_with_net_equal_gross():
    snap = _run(_PASS_LINE + _MALFORMED_LINE).snapshot()
    score = snap[0]
    assert score.observation_kind == "SCORE"
    assert score.family_payload["passive_score_magnitude"] == "7"   # net == gross (zero cost)
    assert type(score.identity_evidence) is S2IdentityWiringCandidate
    assert score.identity_evidence.forwarded_payload_or_local_halt == {
        "gross_magnitude": "7", "unit": "proportion", "venue": "hl", "pair": "BTC",
        "observed_at_epoch_ms": "1750000000000",
    }


def test_halt_path_materializes_local_parse_halt():
    snap = _run(_PASS_LINE + _MALFORMED_LINE).snapshot()
    halt = snap[1]
    assert halt.observation_kind == "HALT"
    assert halt.family_payload["halt_family_descriptor"] == "passive_local_parse_halt"
    assert type(halt.family_payload["halt_origin_reference"]) is OptionBLocalParseHalt
    # same local-halt object is preserved as the S2 forwarded payload (never dropped/reclassified)
    assert halt.identity_evidence.forwarded_payload_or_local_halt is (
        halt.family_payload["halt_origin_reference"]
    )


def test_identity_evidence_carried_unchanged_with_opaque_silver_pair():
    snap = _run(_PASS_LINE + _MALFORMED_LINE, locator="artifact-XYZ").snapshot()
    for record in snap:
        assert type(record.identity_evidence) is S2IdentityWiringCandidate
        assert record.identity_evidence.artifact_locator == "artifact-XYZ"
        assert type(record.identity_evidence.physical_record_position) is int


# --- EOF clean stop -------------------------------------------------------------------------------

def test_empty_stream_is_a_clean_stop_with_no_records():
    snap = _run("").snapshot()
    assert snap == ()


def test_natural_exhaustion_emits_no_synthetic_trailing_record():
    snap = _run(_PASS_LINE).snapshot()
    assert len(snap) == 1
    assert type(snap[0]) is ObservationScoreRecord


# --- crash boundary: raw exceptions propagate, never wrapped into S4 halts -------------------------

def test_missing_required_key_propagates_and_is_not_wrapped_into_a_halt():
    bad = '{"unit": "proportion", "venue": "hl", "pair": "BTC", "observed_at_epoch_ms": "1750000000000"}\n'
    sink = S1InMemoryObservationSink()
    with pytest.raises(B2PassPathIngestionValueError):
        _run(bad, sink=sink)
    assert sink.snapshot() == ()   # no halt manufactured from a raw exception


def test_non_dict_parsed_payload_propagates_as_type_error_not_a_halt():
    sink = S1InMemoryObservationSink()
    with pytest.raises(B2PassPathIngestionTypeError):
        _run("[1, 2, 3]\n", sink=sink)
    assert sink.snapshot() == ()


def test_unexpected_client_wiring_output_is_a_hard_fail_fast(monkeypatch):
    # a returned object that is neither a pass handoff nor a ratified halt carrier must hard-fail,
    # never be silently dropped and never be routed.
    monkeypatch.setattr(s5_runner, "wire_passive_shadow_input", lambda **kwargs: object())
    sink = S1InMemoryObservationSink()
    with pytest.raises(S5RunnerUnexpectedOutputError):
        _run(_PASS_LINE, sink=sink)
    assert sink.snapshot() == ()


# --- signature / fixture-context discipline -------------------------------------------------------

def test_signature_is_exactly_the_six_keyword_only_passive_inputs():
    sig = inspect.signature(run_in_memory_shadow_pipeline)
    assert tuple(sig.parameters) == _EXPECTED_INPUTS
    for p in sig.parameters.values():
        assert p.kind is inspect.Parameter.KEYWORD_ONLY
        assert p.default is inspect.Parameter.empty


def test_component_name_constant():
    assert S5_RUNNER_COMPONENT_NAME == "phase6_1_s5_runner"


def test_no_per_event_context_lookup_registry_or_dict():
    # S5 carries the single caller-supplied contexts directly; it builds NO dict/registry/cache/resolver.
    for node in ast.walk(_module_tree()):
        assert not isinstance(node, ast.Dict), "S5 must build no dict (no per-event context registry)"
    text = _module_text()
    for forbidden in ("registry", "resolver", "lookup", "cache", "_by_", "matching"):
        assert forbidden not in text, forbidden


# --- AST: strictly synchronous, no async/yield/try/isinstance --------------------------------------

def test_module_is_strictly_synchronous_no_async_yield_try_or_isinstance():
    banned_nodes = (
        ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom,
        ast.AsyncFor, ast.AsyncWith, ast.Try, ast.While,
    )
    for node in ast.walk(_module_tree()):
        assert not isinstance(node, banned_nodes), type(node).__name__
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_only_phase6_1_and_phase5_roots_no_concurrency_or_io():
    roots = _import_roots(_module_tree())
    assert roots <= {"phase6_1", "phase5"}, roots
    for forbidden in {"asyncio", "threading", "multiprocessing", "queue", "concurrent",
                      "socket", "sqlite3", "pickle", "json", "os", "sys", "pathlib", "io", "time"}:
        assert forbidden not in roots, forbidden


def test_module_defines_one_function_and_one_error_type():
    tree = _module_tree()
    func_names = [n.name for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert func_names == ["run_in_memory_shadow_pipeline"], func_names
    class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert class_names == ["S5RunnerUnexpectedOutputError"], class_names


def test_module_has_no_durable_storage_or_serialization_surface():
    text = _module_text()
    for forbidden in ("sqlite", "parquet", "pickle", "open(", "serialize", "checkpoint",
                      "durable", "persist"):
        assert forbidden not in text, forbidden
