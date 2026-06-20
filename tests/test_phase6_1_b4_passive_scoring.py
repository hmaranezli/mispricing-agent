"""tests/test_phase6_1_b4_passive_scoring.py — Phase 6.1 B4 passive scoring runtime.

Pins the minimal passive B4 boundary: a pure, deterministic function that packages already-computed
passive pipeline outputs (the frozen `PassiveShadowInput` pass handoff) plus the ratified
`S2IdentityWiringCandidate` identity evidence into one `ObservationScoreRecord` for the S1 reference sink.
Built under `docs/handoff/phase6_1_b4_passive_scoring_planning_charter.md` and
`docs/handoff/phase6_1_b4_score_payload_field_shape_charter.md`.

B4 recomputes NO Phase 5 math (it reads already-computed values), mints no identity, emits no
actionability, and is not the sink (B4 produces; S1 records). Forbidden tokens/identifiers in THIS file
are explicit test fixtures; the runtime module stays passive, deterministic, and identity-blind.
"""
import ast

import pytest

import phase6_1
from phase5.net_edge_calculator_boundary import _make_net_edge_result
from phase6_1.passive_shadow_input import make_passive_shadow_input
from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate
from phase6_1.s1_in_memory_observation_sink import (
    S1InMemoryObservationSink,
    ObservationScoreRecord,
)
from phase6_1.b4_passive_scoring import build_passive_observation_record


_MODULE_BASENAME = "b4_passive_scoring.py"

# the five conceptual payload obligations (4720004), as string-literal keys
_EXPECTED_PAYLOAD_KEYS = frozenset({
    "passive_score_magnitude",
    "score_basis_reference",
    "score_inputs_summary",
    "score_unit_context",
    "score_family_descriptor",
})

# identity aliases that must never leak into family_payload
_FORBIDDEN_IDENTITY_KEYS = (
    "artifact_locator", "physical_record_position", "row_offset", "read_index", "read_offset",
    "event_id", "log_id", "record_id", "message_id", "sequence_number", "uuid", "hash", "fingerprint",
    "source_id",
)


def _module_path():
    import pathlib  # test-only path resolution; the B4 runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _necr(net_edge_value="0.006", net_edge_unit="proportion"):
    return _make_net_edge_result(
        component_name="phase5_net_edge_calculator_boundary",
        origin_component="phase5_net_edge_calculator_boundary",
        origin_result_status="OBSERVED",
        status="CALCULATED",
        gross_edge_value="0.010",
        gross_edge_unit="proportion",
        total_cost_value="0.004",
        total_cost_unit="proportion",
        net_edge_value=net_edge_value,
        net_edge_unit=net_edge_unit,
        cost_component_count="2",
        source_contract="phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_field="net_edge.calculated_value",
        calculation_method="gross_minus_costs",
        boundary_version="phase5.net_edge_calculator_boundary.v0",
    )


def _pass_handoff(necr=None, venue="hyperliquid", pair="BTC-USD"):
    return make_passive_shadow_input(
        net_edge_calculation_result=(necr if necr is not None else _necr()),
        source_venue=venue,
        source_pair=pair,
        observed_at_epoch_ms=1_750_000_000_000,
    )


def _candidate(locator="loc", position=0):
    return S2IdentityWiringCandidate(
        forwarded_payload_or_local_halt={"a": 1},
        artifact_locator=locator,
        physical_record_position=position,
    )


def _build(handoff=None, cand=None, cost=()):
    return build_passive_observation_record(
        pass_handoff=(handoff if handoff is not None else _pass_handoff()),
        identity_evidence=(cand if cand is not None else _candidate()),
        opaque_cost_context=cost,
    )


# --- produces an exact ObservationScoreRecord -----------------------------------------------------

def test_produces_exact_observation_score_record():
    rec = _build()
    assert type(rec) is ObservationScoreRecord


def test_envelope_slots_are_populated_passively():
    cand = _candidate(locator=object(), position=7)
    handoff = _pass_handoff()
    cost = object()
    rec = build_passive_observation_record(
        pass_handoff=handoff, identity_evidence=cand, opaque_cost_context=cost
    )
    # identity stays envelope-level, by identity
    assert rec.identity_evidence is cand
    # SCORE family marker (neutral tag)
    assert rec.observation_kind == "SCORE"
    # timestamp carried verbatim, not used as identity
    assert rec.provenance_timestamp == 1_750_000_000_000
    # cost context carried opaquely, by identity
    assert rec.opaque_cost_context is cost


def test_record_is_admitted_by_the_s1_reference_sink():
    sink = S1InMemoryObservationSink()
    rec = _build()
    sink.record_observation(rec)
    assert sink.snapshot() == (rec,)


# --- family_payload: passive obligations, no identity ---------------------------------------------

def test_family_payload_carries_the_five_passive_obligations():
    rec = _build()
    payload = rec.family_payload
    assert set(payload.keys()) == set(_EXPECTED_PAYLOAD_KEYS)


def test_passive_score_magnitude_is_the_already_computed_net_edge_value():
    necr = _necr(net_edge_value="0.0123")
    rec = _build(handoff=_pass_handoff(necr=necr))
    # read, not recomputed: the magnitude IS the already-computed Phase 5 value, carried verbatim
    assert rec.family_payload["passive_score_magnitude"] == "0.0123"


def test_score_unit_context_is_carried_upstream_unit():
    necr = _necr(net_edge_unit="proportion")
    rec = _build(handoff=_pass_handoff(necr=necr))
    assert rec.family_payload["score_unit_context"] == "proportion"


def test_score_family_descriptor_is_not_a_versioned_id():
    rec = _build()
    desc = rec.family_payload["score_family_descriptor"]
    assert isinstance(desc, str)
    # replay-explainability descriptor, not a versioned/runtime id
    for versiony in ("v0", "v1", "version", "uuid", "id="):
        assert versiony not in desc.lower()


def test_family_payload_contains_no_identity_aliases():
    rec = _build()
    payload = rec.family_payload
    for k in _FORBIDDEN_IDENTITY_KEYS:
        assert k not in payload, k


def test_family_payload_does_not_leak_the_silver_pair_or_candidate():
    cand = _candidate(locator="SECRET-LOCATOR", position=4242)
    rec = _build(cand=cand)
    payload = rec.family_payload
    values = list(payload.values())
    # the S2 candidate and its Silver-pair components must not appear anywhere in the payload
    assert cand not in values
    assert "SECRET-LOCATOR" not in values
    assert 4242 not in values
    # and not nested as a plain repr either
    assert "SECRET-LOCATOR" not in repr(payload)
    assert "4242" not in repr(payload)


# --- determinism / purity -------------------------------------------------------------------------

def test_same_inputs_produce_equal_records():
    handoff = _pass_handoff()
    cand = _candidate()
    a = build_passive_observation_record(pass_handoff=handoff, identity_evidence=cand, opaque_cost_context=())
    b = build_passive_observation_record(pass_handoff=handoff, identity_evidence=cand, opaque_cost_context=())
    assert a == b


# --- input discipline / non-mutation --------------------------------------------------------------

def test_rejects_non_candidate_identity_evidence():
    with pytest.raises(TypeError):
        build_passive_observation_record(
            pass_handoff=_pass_handoff(),
            identity_evidence={"artifact_locator": "x"},
            opaque_cost_context=(),
        )


def test_rejects_non_pass_handoff():
    with pytest.raises(TypeError):
        build_passive_observation_record(
            pass_handoff={"net_edge_value": "0.006"},
            identity_evidence=_candidate(),
            opaque_cost_context=(),
        )


def test_does_not_mutate_inputs():
    handoff = _pass_handoff()
    cand = _candidate(locator="L", position=3)
    _build(handoff=handoff, cand=cand)
    # frozen carriers stay intact; identity carried by reference, not copied/mutated
    assert handoff.source_venue == "hyperliquid"
    assert cand.artifact_locator == "L"
    assert cand.physical_record_position == 3


def test_b4_does_not_recompute_or_alter_net_edge_value():
    necr = _necr(net_edge_value="0.9999")
    handoff = _pass_handoff(necr=necr)
    _build(handoff=handoff)
    # the upstream result is untouched
    assert handoff.net_edge_calculation_result.net_edge_value == "0.9999"


# --- AST / source passivity, determinism, no-IO, no-minting ---------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_db_io_clock_random_modules():
    roots = _import_roots(_module_tree())
    for forbidden in {"sqlite3", "pandas", "numpy", "io", "os", "pathlib", "sys", "json", "csv",
                      "tempfile", "pickle", "shelve", "hashlib", "uuid", "random", "secrets",
                      "time", "datetime", "calendar"}:
        assert forbidden not in roots, forbidden


def test_module_has_no_io_or_dynamic_exec_calls():
    forbidden_calls = {"open", "eval", "exec", "compile", "__import__", "input"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_calls, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"environ", "getenv", "popen", "system", "connect", "execute",
                                     "dumps", "loads"}, node.attr


def test_module_defines_no_actionability_or_ranking_surface():
    banned = ("verdict", "decision", "recommendation", "readiness", "threshold", "rank", "ranking",
              "route", "routing", "execution", "execute", "order", "sizing", "allocation",
              "actionability", "actionable", "calculate", "compute")
    for node in ast.walk(_module_tree()):
        names = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
        for n in names:
            low = n.lower()
            for tok in banned:
                assert tok not in low, (n, tok)


def test_module_has_no_should_trade_or_actionability_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        text = fh.read()
    for tok in ("should_trade", "trade_signal", "order_size", "profit_guarantee"):
        assert tok not in text, tok


def test_module_has_no_identity_minting():
    forbidden_attrs = {"uuid4", "uuid1", "sha256", "md5", "sha1", "hexdigest", "token_hex",
                       "token_bytes", "getrandbits"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"hash", "id"}, node.func.id


def test_module_uses_no_isinstance():
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_module_does_not_reference_the_sink_class():
    # B4 produces a record; it must not touch the S1 sink class.
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Name):
            assert node.id != "S1InMemoryObservationSink"
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assert alias.name != "S1InMemoryObservationSink"
