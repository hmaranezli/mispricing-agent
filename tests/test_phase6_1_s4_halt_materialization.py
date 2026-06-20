"""tests/test_phase6_1_s4_halt_materialization.py — Phase 6.1 S4 halt materializer.

Pins the minimal passive S4 boundary: a pure, deterministic function that packages one ALREADY-OBSERVED
structural halt carrier (OptionBLocalParseHalt / B3PassiveClientWiringError / BlockedPacket) plus the
existing S2IdentityWiringCandidate identity evidence into exactly one ObservationHaltRecord accepted by
the real S1 reference sink. Built under
`docs/handoff/phase6_1_s4_exception_routing_halt_materialization_decision_charter.md`,
`docs/handoff/phase6_1_s4_halt_payload_field_shape_charter.md`, and
`docs/handoff/phase6_1_s4_halt_payload_field_shape_narrowing_amendment.md`.

The Mortician Rule binds: S4 records an already-observed halt; it never retries, repairs, self-heals,
normalizes, enriches, back-fills, or synthesizes missing data. It mints no identity, reads no clock,
inspects the halt carrier's contents not at all, and is not the sink (S4 produces; S1 records). Forbidden
tokens/identifiers in THIS file are explicit test fixtures; the runtime module stays passive,
deterministic, identity-blind, and content-blind.
"""
import ast

import pytest

import phase6_1
from phase6_1.option_b_event_stream_reader import OptionBLocalParseHalt
from phase6_1.b3_passive_client_wiring import B3PassiveClientWiringError
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate
from phase6_1.s1_in_memory_observation_sink import (
    S1InMemoryObservationSink,
    ObservationHaltRecord,
)
from phase6_1.s4_halt_materialization import materialize_passive_halt_record


_MODULE_BASENAME = "s4_halt_materialization.py"

# the closed three logical observation attributes (field-shape charter + narrowing amendment)
_EXPECTED_PAYLOAD_KEYS = frozenset({
    "halt_origin_reference",
    "opaque_upstream_context",
    "halt_family_descriptor",
})

# identity aliases that must never leak into family_payload
_FORBIDDEN_IDENTITY_KEYS = (
    "artifact_locator", "physical_record_position", "row_offset", "read_index", "read_offset",
    "event_id", "log_id", "record_id", "message_id", "sequence_number", "uuid", "hash", "fingerprint",
    "source_id",
)


# --- deterministic carrier / identity builders ----------------------------------------------------

def _parse_halt(raw_line="{bad json"):
    return OptionBLocalParseHalt(raw_line=raw_line)


def _wiring_halt(message="cannot pipe evidence"):
    return B3PassiveClientWiringError(message)


def _blocked_packet():
    return make_blocked_packet(
        component_name="phase5_blocked_result_boundary",
        origin_component="phase5_input_provenance_preflight",
        origin_result_status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        blocked_status="BLOCKED_NEEDS_EVIDENCE",
        reason_code="BLOCKED_MISSING_REQUIRED_FIELD",
        missing_or_invalid_field="source_artifact",
        source_contract="phase5_input_schema_refinement_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE",
        human_review_required=False,
        may_retry_after_evidence=True,
        created_from_contract="phase5_blocked_result_boundary_implementation_planning.md",
        boundary_version="phase5.blocked_result_boundary.v0",
    )


def _candidate(locator="loc", position=0, payload=None):
    return S2IdentityWiringCandidate(
        forwarded_payload_or_local_halt=(payload if payload is not None else {"a": 1}),
        artifact_locator=locator,
        physical_record_position=position,
    )


def _materialize(halt=None, cand=None, cost=()):
    return materialize_passive_halt_record(
        halt_source=(halt if halt is not None else _parse_halt()),
        identity_evidence=(cand if cand is not None else _candidate()),
        opaque_cost_context=cost,
    )


def _module_path():
    import pathlib  # test-only path resolution; the S4 runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


# --- produces an exact ObservationHaltRecord accepted by the real S1 sink --------------------------

def test_produces_exact_observation_halt_record_for_each_authorized_carrier():
    for halt in (_parse_halt(), _wiring_halt(), _blocked_packet()):
        rec = _materialize(halt=halt)
        assert type(rec) is ObservationHaltRecord


def test_record_is_admitted_by_the_real_s1_reference_sink():
    for halt in (_parse_halt(), _wiring_halt(), _blocked_packet()):
        sink = S1InMemoryObservationSink()
        rec = _materialize(halt=halt)
        sink.record_observation(rec)
        assert sink.snapshot() == (rec,)


def test_envelope_slots_are_populated_passively():
    cand = _candidate(locator=object(), position=7)
    halt = _parse_halt()
    cost = object()
    rec = materialize_passive_halt_record(
        halt_source=halt, identity_evidence=cand, opaque_cost_context=cost
    )
    # identity stays envelope-level, by identity (no fallback minting)
    assert rec.identity_evidence is cand
    # neutral HALT peer marker (equal peer of SCORE)
    assert rec.observation_kind == "HALT"
    # no timestamp is manufactured (none supplied, carrier never inspected)
    assert rec.provenance_timestamp is None
    # cost context carried opaquely, by identity
    assert rec.opaque_cost_context is cost


# --- closed three-field family_payload ------------------------------------------------------------

def test_family_payload_is_the_closed_three_field_set():
    rec = _materialize()
    assert set(rec.family_payload.keys()) == set(_EXPECTED_PAYLOAD_KEYS)


def test_halt_origin_reference_is_the_carrier_by_reference():
    halt = _parse_halt()
    rec = _materialize(halt=halt)
    # the carrier is carried opaquely, by identity — never copied, parsed, or rendered
    assert rec.family_payload["halt_origin_reference"] is halt


def test_opaque_upstream_context_is_none_regardless_of_cost_context():
    # nothing is manufactured from the opaque cost context; the slot is None
    for cost in ((), object(), None, {"venue": "x"}):
        rec = _materialize(cost=cost)
        assert rec.family_payload["opaque_upstream_context"] is None
        # and the cost context itself is still carried opaquely at the envelope
        assert rec.opaque_cost_context is cost


def test_halt_family_descriptor_is_static_per_exact_type():
    d_parse = _materialize(halt=_parse_halt()).family_payload["halt_family_descriptor"]
    d_wiring = _materialize(halt=_wiring_halt()).family_payload["halt_family_descriptor"]
    d_blocked = _materialize(halt=_blocked_packet()).family_payload["halt_family_descriptor"]
    # one descriptor per carrier type, all distinct
    assert len({d_parse, d_wiring, d_blocked}) == 3
    for d in (d_parse, d_wiring, d_blocked):
        assert type(d) is str


def test_halt_family_descriptor_is_not_versioned_or_identity():
    for halt in (_parse_halt(), _wiring_halt(), _blocked_packet()):
        d = _materialize(halt=halt).family_payload["halt_family_descriptor"]
        for versiony in ("v0", "v1", "version", "uuid", "id=", "hash"):
            assert versiony not in d.lower()


def test_descriptor_is_independent_of_carrier_contents():
    # two DIFFERENT parse-halt contents must yield the SAME descriptor (contents never inspected)
    a = _materialize(halt=_parse_halt(raw_line="{first bad")).family_payload["halt_family_descriptor"]
    b = _materialize(halt=_parse_halt(raw_line="<<<utterly different>>>")).family_payload["halt_family_descriptor"]
    assert a == b


# --- identity segregation: no aliasing, no leak ---------------------------------------------------

def test_family_payload_contains_no_identity_aliases():
    payload = _materialize().family_payload
    for k in _FORBIDDEN_IDENTITY_KEYS:
        assert k not in payload, k


def test_family_payload_does_not_leak_the_candidate_or_silver_pair():
    cand = _candidate(locator="SECRET-LOCATOR", position=4242)
    rec = _materialize(cand=cand)
    payload = rec.family_payload
    values = list(payload.values())
    assert cand not in values
    assert "SECRET-LOCATOR" not in values
    assert 4242 not in values
    assert "SECRET-LOCATOR" not in repr(payload)
    assert "4242" not in repr(payload)


# --- determinism / purity / non-mutation ----------------------------------------------------------

def test_same_inputs_produce_equal_records():
    halt = _parse_halt()
    cand = _candidate()
    a = materialize_passive_halt_record(halt_source=halt, identity_evidence=cand, opaque_cost_context=())
    b = materialize_passive_halt_record(halt_source=halt, identity_evidence=cand, opaque_cost_context=())
    assert a == b


def test_does_not_mutate_inputs():
    halt = _parse_halt(raw_line="{bad")
    cand = _candidate(locator="L", position=3)
    _materialize(halt=halt, cand=cand)
    assert halt.raw_line == "{bad"
    assert cand.artifact_locator == "L"
    assert cand.physical_record_position == 3


# --- input discipline: exact-type gates -----------------------------------------------------------

def test_rejects_unknown_halt_source_types():
    for bad in ({"halt": "x"}, [1, 2], object(), "halt", 7, TypeError("plain")):
        with pytest.raises(TypeError):
            materialize_passive_halt_record(
                halt_source=bad, identity_evidence=_candidate(), opaque_cost_context=()
            )


def test_rejects_subclass_of_authorized_carrier():
    class _SubParse(OptionBLocalParseHalt):
        pass

    sub = object.__new__(_SubParse)
    with pytest.raises(TypeError):
        materialize_passive_halt_record(
            halt_source=sub, identity_evidence=_candidate(), opaque_cost_context=()
        )


def test_rejects_subclass_of_blocked_packet():
    class _SubBlocked(BlockedPacket):
        pass

    sub = object.__new__(_SubBlocked)
    with pytest.raises(TypeError):
        materialize_passive_halt_record(
            halt_source=sub, identity_evidence=_candidate(), opaque_cost_context=()
        )


def test_rejects_non_candidate_identity_evidence():
    with pytest.raises(TypeError):
        materialize_passive_halt_record(
            halt_source=_parse_halt(),
            identity_evidence={"artifact_locator": "x"},
            opaque_cost_context=(),
        )


def test_rejects_subclass_of_candidate_identity_evidence():
    class _SubCand(S2IdentityWiringCandidate):
        pass

    sub = object.__new__(_SubCand)
    with pytest.raises(TypeError):
        materialize_passive_halt_record(
            halt_source=_parse_halt(), identity_evidence=sub, opaque_cost_context=()
        )


# --- AST / source passivity, no-IO, no-inspection, no-minting -------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_traceback_logging_io_clock_random_modules():
    roots = _import_roots(_module_tree())
    for forbidden in {"traceback", "logging", "sys", "io", "os", "pathlib", "json", "csv",
                      "sqlite3", "pandas", "numpy", "tempfile", "pickle", "shelve", "hashlib",
                      "uuid", "random", "secrets", "time", "datetime", "calendar"}:
        assert forbidden not in roots, forbidden


def test_module_has_no_io_dynamic_exec_print_or_string_render_calls():
    forbidden_name_calls = {"open", "eval", "exec", "compile", "__import__", "input", "print",
                            "str", "repr", "isinstance", "id", "hash", "vars", "dir", "getattr"}
    forbidden_attrs = {"environ", "getenv", "popen", "system", "connect", "execute", "dumps",
                       "loads", "format_exc", "print_exc", "format_exception", "getLogger",
                       "write", "__dict__", "args"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_name_calls, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, node.attr


def test_module_uses_no_isinstance():
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_module_never_inspects_halt_source_attributes():
    # no `halt_source.<anything>` attribute access anywhere — the carrier is opaque, by reference only
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert node.value.id != "halt_source", node.attr


def test_module_has_no_identity_minting():
    forbidden_attrs = {"uuid4", "uuid1", "sha256", "md5", "sha1", "hexdigest", "token_hex",
                       "token_bytes", "getrandbits"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"hash", "id"}, node.func.id


def test_module_defines_no_actionability_or_recovery_surface():
    banned = ("retry", "repair", "recover", "heal", "normalize", "enrich", "severity", "priority",
              "taxonomy", "route", "routing", "readiness", "verdict", "decision", "rank", "ranking",
              "threshold", "score", "execution", "execute", "order", "sizing", "allocation",
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


def test_module_has_no_should_continue_stop_or_actionability_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        text = fh.read()
    for tok in ("should_continue", "should_stop", "should_retry", "should_trade", "trade_signal"):
        assert tok not in text, tok
