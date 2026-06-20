"""tests/test_phase6_1_s2_identity_wiring_candidate.py — Phase 6.1 S2 identity wiring candidate.

Pins the passive, stateless, per-envelope S2 identity wiring router defined by
`docs/handoff/phase6_1_s2_identity_wiring_boundary_contract_charter.md`. The router consumes exactly one
frozen `OptionBEventEnvelope` (from the ratified Option-B reader) and returns exactly one strictly
immutable `S2IdentityWiringCandidate` that:

  - forwards `parsed_payload_or_local_halt` onward UNCHANGED, by identity (no normalization);
  - carries the Silver pair `(artifact_locator, physical_record_position)` intact and opaque — never
    hashed, concatenated, cast, derived, collapsed, or minted into a synthetic key.

It is a router, not a computer: it normalizes nothing, scores nothing, decides nothing. Pass envelopes
and `OptionBLocalParseHalt` envelopes route through the SAME function with identity preserved. This slice
produces a *candidate carried by runtime*; it does NOT declare S2 fully UNBLOCKED.

Forbidden tokens/identifiers in THIS file are explicit test fixtures; the router runtime must stay
identity-blind (no hashlib/uuid/random/time/datetime/os/sys/pathlib/io; no f-strings/join/concat identity
construction; immutable, non-dict carrier).
"""
import ast
import io

import pytest

import phase6_1
from phase6_1.option_b_event_stream_reader import (
    OptionBEventEnvelope,
    OptionBLocalParseHalt,
    read_option_b_event_stream,
)
from phase6_1.s2_identity_wiring_candidate import (
    S2IdentityWiringCandidate,
    route_option_b_envelope_to_s2_identity_candidate,
)


_MODULE_BASENAME = "s2_identity_wiring_candidate.py"


def _module_path():
    import pathlib  # test-only path resolution; the router runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _module_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return fh.read()


def _envelope(payload, locator, position):
    return OptionBEventEnvelope(
        parsed_payload_or_local_halt=payload,
        artifact_locator=locator,
        physical_record_position=position,
    )


# --- happy path: one envelope -> one immutable candidate, identity preserved -----------------------

def test_routes_parsed_payload_envelope_to_candidate():
    payload = {"gross_magnitude": "12.34", "unit": "usd", "venue": "hl", "pair": "BTC"}
    locator = object()  # opaque caller-supplied locator
    env = _envelope(payload, locator, 7)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    assert type(candidate) is S2IdentityWiringCandidate
    # payload forwarded UNCHANGED by identity
    assert candidate.forwarded_payload_or_local_halt is payload
    # Silver pair carried intact and opaque
    assert candidate.artifact_locator is locator
    assert candidate.physical_record_position == 7
    assert type(candidate.physical_record_position) is int  # not cast/normalized


def test_candidate_binds_exactly_the_three_contract_fields():
    env = _envelope({"a": 1}, "loc", 0)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    assert hasattr(candidate, "forwarded_payload_or_local_halt")
    assert hasattr(candidate, "artifact_locator")
    assert hasattr(candidate, "physical_record_position")


def test_candidate_is_not_a_dict_and_is_immutable():
    env = _envelope({"a": 1}, "loc", 3)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    assert type(candidate) is not dict
    assert not isinstance(candidate, dict)
    assert not hasattr(candidate, "__dict__")  # slotted; carries no mutable mapping
    with pytest.raises(Exception):
        candidate.artifact_locator = "tampered"
    with pytest.raises(Exception):
        candidate.physical_record_position = 999
    with pytest.raises(Exception):
        candidate.forwarded_payload_or_local_halt = {"x": 1}


# --- opaque silver pair: passed through by identity, never collapsed ------------------------------

def test_locator_passed_through_by_identity():
    locator = ["portable", "relative", "locator"]  # mutable sentinel proves no copy/normalize
    env = _envelope({"a": 1}, locator, 11)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    assert candidate.artifact_locator is locator


def test_silver_pair_not_collapsed_into_a_key():
    locator = "loc-XYZ"
    env = _envelope({"a": 1}, locator, 42)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    # The two facts remain separate, intact, and un-concatenated.
    assert candidate.artifact_locator == "loc-XYZ"
    assert candidate.physical_record_position == 42
    # No collapsed/synthetic key was produced anywhere on the carrier.
    for forbidden in ("loc-XYZ:42", "loc-XYZ42", "loc-XYZ_42", "42loc-XYZ"):
        assert forbidden not in repr(candidate)


# --- pass/halt symmetry: same function, identity preserved for halts -------------------------------

def test_local_parse_halt_envelope_routes_through_same_function():
    halt = OptionBLocalParseHalt(raw_line="this-is-not-json\n")
    locator = object()
    env = _envelope(halt, locator, 5)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    assert type(candidate) is S2IdentityWiringCandidate
    # halt payload forwarded by identity, NOT dropped or reclassified
    assert candidate.forwarded_payload_or_local_halt is halt
    # halt identity preserves the SAME locator + position
    assert candidate.artifact_locator is locator
    assert candidate.physical_record_position == 5


def test_pass_and_halt_use_identical_routing_shape():
    locator = object()
    pass_env = _envelope({"a": 1}, locator, 9)
    halt_env = _envelope(OptionBLocalParseHalt(raw_line="x\n"), locator, 9)
    pass_c = route_option_b_envelope_to_s2_identity_candidate(envelope=pass_env)
    halt_c = route_option_b_envelope_to_s2_identity_candidate(envelope=halt_env)
    # Both produce the same carrier type with identical locator + position handling.
    assert type(pass_c) is S2IdentityWiringCandidate
    assert type(halt_c) is S2IdentityWiringCandidate
    assert pass_c.artifact_locator is halt_c.artifact_locator
    assert pass_c.physical_record_position == halt_c.physical_record_position


# --- explicit normalization boundary: payload untouched -------------------------------------------

def test_payload_is_not_normalized_or_validated():
    # Semantically absurd but structurally present payload: must pass through verbatim by identity.
    payload = {"gross_magnitude": "-999999", "unit": "@@@", "venue": "", "pair": None, "sizing": 9000}
    env = _envelope(payload, "loc", 1)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    assert candidate.forwarded_payload_or_local_halt is payload
    assert candidate.forwarded_payload_or_local_halt["gross_magnitude"] == "-999999"
    assert candidate.forwarded_payload_or_local_halt["pair"] is None


def test_payload_authored_identity_is_not_promoted():
    payload = {"event_id": "PAYLOAD-LIE", "row_offset": 4242, "uuid": "x"}
    env = _envelope(payload, "medium-loc", 0)
    candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
    # Envelope identity comes from the medium pair, never from the payload's lying fields.
    assert candidate.artifact_locator == "medium-loc"
    assert candidate.physical_record_position == 0
    assert candidate.forwarded_payload_or_local_halt["event_id"] == "PAYLOAD-LIE"


# --- input discipline: frozen reader client-only --------------------------------------------------

def test_rejects_non_envelope_input():
    for bad in ({"a": 1}, [1, 2, 3], "envelope", object(), 42):
        with pytest.raises(TypeError):
            route_option_b_envelope_to_s2_identity_candidate(envelope=bad)


def test_rejects_envelope_subclass():
    class _Sub(OptionBEventEnvelope):
        pass

    sub = _Sub(parsed_payload_or_local_halt={"a": 1}, artifact_locator="loc", physical_record_position=0)
    with pytest.raises(TypeError):
        route_option_b_envelope_to_s2_identity_candidate(envelope=sub)


# --- integration with the real frozen reader (proves the island still feeds this client) ----------

def test_integration_real_reader_stream_routes_each_envelope():
    text = '{"a": 1}\nnot-json\n{"b": 2}\n'
    locator = object()
    candidates = [
        route_option_b_envelope_to_s2_identity_candidate(envelope=env)
        for env in read_option_b_event_stream(text_stream=io.StringIO(text), artifact_locator=locator)
    ]
    assert len(candidates) == 3
    for c in candidates:
        assert type(c) is S2IdentityWiringCandidate
        assert c.artifact_locator is locator
    # positions came from the stream, carried intact through the router
    assert [c.physical_record_position for c in candidates] == [0, len('{"a": 1}\n'),
                                                                len('{"a": 1}\n') + len('not-json\n')]
    # the malformed middle line is a halt, forwarded by identity, not dropped
    assert type(candidates[1].forwarded_payload_or_local_halt) is OptionBLocalParseHalt


# --- AST / source identity-blindness locks --------------------------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_minting_clock_or_io_modules():
    roots = _import_roots(_module_tree())
    for forbidden in {"hashlib", "uuid", "random", "secrets", "time", "datetime", "calendar",
                      "os", "sys", "pathlib", "io"}:
        assert forbidden not in roots, forbidden


def test_module_only_imports_dataclasses_and_the_reader():
    roots = _import_roots(_module_tree())
    external = roots - {"phase6_1"}
    assert external <= {"dataclasses"}, external


def test_module_imports_only_required_reader_symbols():
    imported = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("phase6_1"):
            assert node.module == "phase6_1.option_b_event_stream_reader", node.module
            for alias in node.names:
                imported.add(alias.name)
    # Only the envelope type is strictly required (for the exact-type input guard).
    assert imported <= {"OptionBEventEnvelope"}, imported


def test_module_uses_no_fstring_or_join_or_concat_identity_construction():
    for node in ast.walk(_module_tree()):
        assert not isinstance(node, ast.JoinedStr), "no f-strings (identity construction risk)"
        if isinstance(node, ast.Attribute):
            assert node.attr != "join", "no str.join identity construction"
        if isinstance(node, ast.BinOp):
            assert not isinstance(node.op, (ast.Add, ast.Mod)), "no concat/%-format identity construction"


def test_module_uses_no_identity_minting_calls():
    forbidden_attrs = {"uuid4", "uuid1", "sha256", "md5", "sha1", "hexdigest", "token_hex",
                       "token_bytes", "getrandbits"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"hash", "id"}, node.func.id


def test_module_uses_no_enumerate_or_global_or_open():
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"enumerate", "open", "eval", "exec", "compile", "__import__"}
        assert not isinstance(node, ast.Global)


def test_carrier_is_frozen_dataclass_with_slots():
    import dataclasses
    assert dataclasses.is_dataclass(S2IdentityWiringCandidate)
    assert S2IdentityWiringCandidate.__dataclass_params__.frozen is True


def test_module_has_no_actionability_tokens():
    text = _module_text()
    for tok in ("edge_direction", "staleness", "capacity", "ShadowIntent", "sizing", "routing"):
        assert tok not in text, tok
