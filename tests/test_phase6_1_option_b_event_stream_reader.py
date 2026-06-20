"""tests/test_phase6_1_option_b_event_stream_reader.py — Phase 6.1 Option-B event-stream reader.

Pins the micro-scoped Option-B reader: a dumb, blind, deterministic physical parser for the pinned
JSONL-style line-oriented event artifact (one physical line = one logical event). The reader consumes
an in-memory text stream (``io.StringIO``) and yields, per physical line, an immutable tripartite
envelope ``(parsed_payload_or_local_halt, artifact_locator, physical_record_position)``.

Authored under ``docs/handoff/phase6_1_option_b_reader_io_design_charter.md`` (and the serialization /
contract charters it references). The reader: carries the caller-supplied ``artifact_locator`` verbatim;
derives ``physical_record_position`` only from the active stream's own position mechanics (never a
counter/``enumerate``); performs NO semantic validation; and surfaces a malformed physical line as an
immutable local IO-halt payload (never raised, never silently dropped).

Forbidden tokens / identifiers appearing in THIS file are explicit test fixtures; the reader runtime
must keep its closed, module-scoped surface (no os/pathlib/sys, no uuid/hashlib/random/time/datetime,
no B1/B2/B3/Phase5/producer imports, no enumerate, no global, no swallowing try/except).
"""
import ast
import io

import pytest

import phase6_1
from phase6_1.option_b_event_stream_reader import (
    read_option_b_event_stream,
    OptionBEventEnvelope,
    OptionBLocalParseHalt,
)


_READER_BASENAME = "option_b_event_stream_reader.py"


def _reader_path():
    import pathlib  # test-only path resolution; the reader runtime itself imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _READER_BASENAME


def _reader_tree():
    with open(_reader_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _reader_text():
    with open(_reader_path(), "r", encoding="utf-8") as fh:
        return fh.read()


def _stream(text):
    return io.StringIO(text)


# --- happy path: one immutable envelope per physical line -----------------------------------------

def test_yields_one_envelope_per_physical_line():
    text = '{"gross_magnitude": "12.34", "unit": "usd", "venue": "hl", "pair": "BTC"}\n' \
           '{"gross_magnitude": "0.5", "unit": "usd", "venue": "hl", "pair": "ETH"}\n' \
           '{"gross_magnitude": "9", "unit": "usd", "venue": "hl", "pair": "SOL"}\n'
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert len(envelopes) == 3
    for env in envelopes:
        assert type(env) is OptionBEventEnvelope
    assert envelopes[0].parsed_payload_or_local_halt == {
        "gross_magnitude": "12.34", "unit": "usd", "venue": "hl", "pair": "BTC"
    }
    assert envelopes[2].parsed_payload_or_local_halt == {
        "gross_magnitude": "9", "unit": "usd", "venue": "hl", "pair": "SOL"
    }


def test_envelope_is_not_a_dict_and_is_immutable():
    text = '{"a": 1}\n'
    (env,) = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert type(env) is not dict
    assert not isinstance(env, dict)
    with pytest.raises(Exception):
        env.artifact_locator = "tampered"
    with pytest.raises(Exception):
        env.physical_record_position = 999


def test_envelope_carries_exactly_three_parts():
    text = '{"a": 1}\n'
    (env,) = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert hasattr(env, "parsed_payload_or_local_halt")
    assert hasattr(env, "artifact_locator")
    assert hasattr(env, "physical_record_position")


# --- locator pass-through: carried verbatim, by identity ------------------------------------------

def test_locator_is_carried_verbatim_by_identity():
    sentinel = object()  # opaque caller-supplied locator; must be passed through unchanged
    text = '{"a": 1}\n{"b": 2}\n'
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator=sentinel))
    for env in envelopes:
        assert env.artifact_locator is sentinel


def test_locator_not_normalized_for_pathlike_value():
    locator = "../relative/portable/locator.jsonl"  # reader must NOT absolutize/normalize/join this
    text = '{"a": 1}\n'
    (env,) = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator=locator))
    assert env.artifact_locator == "../relative/portable/locator.jsonl"
    assert env.artifact_locator is locator


# --- physical position: derived from the stream, not a counter ------------------------------------

def test_position_is_stream_offset_not_enumerate_counter():
    # Lines of differing length: a plain 0,1,2 counter would NOT match the byte/char offsets.
    line0 = '{"a": 1}\n'          # starts at offset 0
    line1 = '{"bb": 22}\n'        # starts at offset len(line0)
    line2 = '{"ccc": 333}\n'      # starts at offset len(line0)+len(line1)
    text = line0 + line1 + line2
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    positions = [env.physical_record_position for env in envelopes]
    assert positions == [0, len(line0), len(line0) + len(line1)]
    # Explicitly distinct from a 0,1,2 enumerate/counter:
    assert positions != [0, 1, 2]


def test_position_matches_independent_stream_tell():
    text = '{"a": 1}\n{"bb": 22}\n'
    # Independently recompute the stream's own start-of-line offsets.
    probe = _stream(text)
    expected = []
    while True:
        pos = probe.tell()
        if probe.readline() == "":
            break
        expected.append(pos)
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert [env.physical_record_position for env in envelopes] == expected


# --- malformed line: local halt envelope, no raise, no silent drop --------------------------------

def test_malformed_line_yields_local_halt_envelope_preserving_locator_and_position():
    good = '{"a": 1}\n'
    bad = 'this-is-not-json\n'
    good2 = '{"b": 2}\n'
    text = good + bad + good2
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    # No silent drop: every physical line produced exactly one envelope.
    assert len(envelopes) == 3
    assert type(envelopes[0].parsed_payload_or_local_halt) is dict
    assert type(envelopes[1].parsed_payload_or_local_halt) is OptionBLocalParseHalt
    assert type(envelopes[2].parsed_payload_or_local_halt) is dict
    # The halt envelope still carries the medium identity for the bad line.
    assert envelopes[1].artifact_locator == "loc"
    assert envelopes[1].physical_record_position == len(good)
    # The raw malformed line is preserved verbatim (uninterpreted).
    assert envelopes[1].parsed_payload_or_local_halt.raw_line == bad


def test_malformed_line_does_not_raise():
    text = '{"a": 1}\nnot-json\n'
    # Materialising the whole generator must not raise.
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert len(envelopes) == 2
    assert type(envelopes[1].parsed_payload_or_local_halt) is OptionBLocalParseHalt


def test_blank_line_is_a_halt_not_a_silent_skip():
    text = '{"a": 1}\n   \n{"b": 2}\n'  # whitespace-only middle line is malformed, not dropped
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert len(envelopes) == 3
    assert type(envelopes[1].parsed_payload_or_local_halt) is OptionBLocalParseHalt


def test_local_halt_is_immutable():
    text = 'nope\n'
    (env,) = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    halt = env.parsed_payload_or_local_halt
    assert type(halt) is OptionBLocalParseHalt
    with pytest.raises(Exception):
        halt.raw_line = "tampered"


# --- semantic ignorance: syntactically valid but semantically absurd JSON passes -------------------

def test_semantically_absurd_but_valid_json_is_emitted_successfully():
    # Negative magnitude, nonsense unit, blank venue, null pair — all business-absurd, all valid JSON.
    text = '{"gross_magnitude": "-999999", "unit": "@@@", "venue": "", "pair": null}\n' \
           '{"gross_magnitude": "not-a-number", "edge_direction": "UP", "sizing": 9000}\n'
    envelopes = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="loc"))
    assert len(envelopes) == 2
    # No semantic rejection: both parse into payload dicts, carried verbatim.
    assert type(envelopes[0].parsed_payload_or_local_halt) is dict
    assert envelopes[0].parsed_payload_or_local_halt["gross_magnitude"] == "-999999"
    assert envelopes[0].parsed_payload_or_local_halt["pair"] is None
    assert type(envelopes[1].parsed_payload_or_local_halt) is dict
    assert envelopes[1].parsed_payload_or_local_halt["sizing"] == 9000


def test_payload_authored_identity_fields_are_left_in_payload_not_promoted():
    # A payload that lies about identity: the reader must NOT trust these as the envelope identity.
    text = '{"event_id": "PAYLOAD-LIE", "row_offset": 4242, "uuid": "x", "gross_magnitude": "1"}\n'
    (env,) = list(read_option_b_event_stream(text_stream=_stream(text), artifact_locator="medium-loc"))
    # Envelope identity comes from the medium, not the payload.
    assert env.artifact_locator == "medium-loc"
    assert env.physical_record_position == 0
    # Payload's lying fields stay inside the payload, untouched and unpromoted.
    assert env.parsed_payload_or_local_halt["event_id"] == "PAYLOAD-LIE"
    assert env.parsed_payload_or_local_halt["row_offset"] == 4242


def test_empty_stream_yields_no_envelopes():
    envelopes = list(read_option_b_event_stream(text_stream=_stream(""), artifact_locator="loc"))
    assert envelopes == []


# --- AST / source anti-cheat locks ----------------------------------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_reader_uses_no_enumerate():
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "enumerate", "physical position must come from the stream, not enumerate"


def test_reader_has_no_global_statement():
    for node in ast.walk(_reader_tree()):
        assert not isinstance(node, ast.Global), "no module/application counter state via global"


def test_reader_imports_no_filesystem_or_path_modules():
    roots = _import_roots(_reader_tree())
    for forbidden in {"os", "sys", "pathlib", "shutil", "tempfile", "glob", "io"}:
        assert forbidden not in roots, forbidden


def test_reader_imports_no_identity_minting_or_clock_modules():
    roots = _import_roots(_reader_tree())
    for forbidden in {"uuid", "hashlib", "random", "secrets", "time", "datetime", "calendar"}:
        assert forbidden not in roots, forbidden


def test_reader_imports_no_b1_b2_b3_phase5_producer():
    mods = set()
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    for m in mods:
        assert not m.startswith("phase5"), m
        assert not m.startswith("phase6_1.b1"), m
        assert not m.startswith("phase6_1.b2"), m
        assert not m.startswith("phase6_1.b3"), m
        assert not m.startswith("phase6_1.passive_producer"), m


def test_reader_does_no_path_or_open_io():
    forbidden_calls = {"open", "eval", "exec", "compile", "__import__", "input"}
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_calls, node.func.id
        if isinstance(node, ast.Attribute):
            # `.tell()`/`.readline()` on the caller-supplied stream are the permitted IO surface.
            assert node.attr not in {"environ", "getenv", "popen", "system"}, node.attr


def test_reader_no_try_except_swallows_malformed_lines():
    # Every except handler must NOT silently swallow (no bare pass/continue/break, no re-raise of the
    # parse error). The malformed-line behaviour test proves a halt envelope is emitted instead.
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.ExceptHandler):
            for inner in ast.walk(node):
                assert not isinstance(inner, ast.Pass), "except must not swallow with pass"
                assert not isinstance(inner, ast.Continue), "except must not drop the line with continue"
                assert not isinstance(inner, ast.Break), "except must not abort the stream with break"
                assert not isinstance(inner, ast.Raise), "except must not re-raise on malformed line"


def test_reader_has_at_least_one_try_handling_parse_failure():
    tries = [n for n in ast.walk(_reader_tree()) if isinstance(n, ast.Try)]
    assert tries, "reader must defensively handle physical parse failure"


def test_reader_has_no_edge_direction_or_actionability_tokens():
    text = _reader_text()
    for tok in ("edge_direction", "staleness", "capacity", "ShadowIntent", "sizing", "routing"):
        assert tok not in text, tok
