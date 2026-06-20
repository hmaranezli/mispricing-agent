"""tests/test_phase6_1_forbidden_token_locks.py — Phase 6.1 Slice 0D.

Structural locks over the WHOLE phase6_1 runtime package:
  - a global forbidden-token source scan (word-boundary exact; no substring false positives);
  - an AST forbidden-import / forbidden-IO-API scan (runtime stays local, passive, replay-first, no-IO);
  - an AST no-`isinstance` lock (exact-type boundary discipline only);
  - an AST no calculation/readiness/actionability surface lock;
  - forbidden/foreign-payload fail-fast at the 0A/0B/0C entrypoints, with halt carriers proven to be
    type/provenance boundary violations — NOT actionability errors.

Every token/identifier string in THIS file is an explicit test fixture permitted by the Slice 0D
charter; the runtime source must contain none of them.
"""
import ast
import os
import pathlib
import re

import pytest

import phase6_1
from phase5.net_edge_calculator_boundary import _make_net_edge_result, NetEdgeCalculationResult
from phase5.blocked_result_boundary import make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import make_no_eligible_halt_packet
from phase6_1.passive_shadow_input import (
    PassiveShadowInput,
    make_passive_shadow_input,
    PassiveShadowInputTypeError,
)
from phase6_1.shadow_observation import (
    ShadowObservation,
    make_shadow_observation,
    ShadowObservationTypeError,
)
from phase6_1.provenance_chain_lock import (
    verify_provenance_chain,
    ShadowProvenanceTypeError,
)


# --- runtime file discovery (tests excluded; only the package source) -----------------------------

def _runtime_files():
    pkg_dir = pathlib.Path(phase6_1.__file__).resolve().parent
    return sorted(p for p in pkg_dir.glob("*.py"))


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --- deterministic builders -----------------------------------------------------------------------

def _necr():
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


def _psi():
    return make_passive_shadow_input(
        net_edge_calculation_result=_necr(),
        source_venue="hyperliquid",
        source_pair="BTC-USD",
        observed_at_epoch_ms=1_750_000_000_000,
    )


def _obs():
    return make_shadow_observation(
        source=_psi(),
        replay_artifact_id="replay-fixture-0001",
        replay_sequence_index=0,
        diagnostic_recorded_at_ms=1_750_000_000_500,
    )


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


def _no_eligible_packet():
    return make_no_eligible_halt_packet(
        component_name="phase5_no_eligible_halt_propagation_boundary",
        origin_component="phase5_net_edge_profitability_gate_boundary",
        origin_result_status="NO_ELIGIBLE",
        status="NO_ELIGIBLE",
        no_eligible_reason="NET_EDGE_BELOW_THRESHOLD",
        source_contract="phase5_no_eligible_halt_propagation_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_no_eligible_halt_propagation_boundary_implementation_planning.md",
        source_field="net_edge.threshold_decision",
        deterministic_next_action="HALT_NO_ELIGIBLE",
        boundary_version="phase5.no_eligible_halt_propagation_boundary.v0",
    )


# --- module-scoped IO-lock exception (single allowlisted replay depth reader) ---------------------
# Authorized by docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md. The
# exception is keyed on EXACTLY one basename and is closed: it tolerates the "json" token, the closed
# import allowlist {pathlib, json, csv}, and a READ-ONLY open() — and nothing else. Every other module
# stays under the full no-IO posture, and every other forbidden surface (write/append open, network
# imports, env/secrets, subprocess, dynamic exec, actionability tokens) stays banned for the reader too.

_READER_BASENAME = "b1_replay_depth_artifact_reader.py"
_READER_IMPORT_ALLOWLIST = {"pathlib", "json", "csv"}
_READER_TOKEN_ALLOWLIST = {"json"}

# Option-B event-stream reader: a TOKEN-ONLY "json" exception, authorized by
# docs/handoff/phase6_1_option_b_reader_io_lock_exception_amendment_charter.md. This basename is granted
# NO import/open/IO/path exception — it stays under the package-wide import and IO/dynamic-exec scans
# unchanged (it uses no open() and imports nothing forbidden). Only the "json" source token is tolerated.
_OPTION_B_READER_BASENAME = "option_b_event_stream_reader.py"
_OPTION_B_READER_TOKEN_ALLOWLIST = {"json"}

# Per-basename source-token allowlist consulted ONLY by the forbidden-token scan below.
_TOKEN_ALLOWLIST_BY_BASENAME = {
    _READER_BASENAME: _READER_TOKEN_ALLOWLIST,
    _OPTION_B_READER_BASENAME: _OPTION_B_READER_TOKEN_ALLOWLIST,
}


def _open_is_read_only(node):
    """True iff this ``open(...)`` Call is read-only: mode absent/default, or a string literal mode
    carrying no write/append/update flag ('w', 'a', 'x', '+'). A non-literal mode cannot be proven
    read-only and is rejected."""
    mode = None
    if len(node.args) >= 2:
        mode = node.args[1]
    for kw in node.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return True
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return not any(flag in mode.value for flag in ("w", "a", "x", "+"))
    return False


# --- 1. global forbidden-token source scan (word-boundary exact) ----------------------------------

_FORBIDDEN_TOKENS = (
    "json", "ledger", "serialize", "serialization", "to_json", "to_dict",
    "wallet", "balance", "private", "secret",
    "order", "routing", "route", "execution", "execute", "allocation", "sizing",
    "signal", "candidate", "trade", "paper", "live",
)


def _token_hits(token, text):
    # exact word-boundary match: not flanked by an alphanumeric or underscore. Avoids substring false
    # positives such as "route" inside an unrelated word.
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def test_runtime_source_is_free_of_forbidden_tokens():
    violations = []
    for path in _runtime_files():
        basename = os.path.basename(str(path))
        text = _read(path)
        allowed = _TOKEN_ALLOWLIST_BY_BASENAME.get(basename, frozenset())
        for token in _FORBIDDEN_TOKENS:
            if token in allowed:
                continue
            if _token_hits(token, text):
                violations.append((basename, token))
    assert violations == [], "forbidden tokens in phase6_1 runtime: %r" % violations


# --- 3a. AST forbidden-import / forbidden-IO-API scan ---------------------------------------------

_FORBIDDEN_IMPORT_ROOTS = {
    "requests", "http", "socket", "socketserver", "websocket", "websockets", "urllib", "aiohttp",
    "subprocess", "sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "ssl", "smtplib", "ftplib",
    "telnetlib", "pickle", "shelve", "os", "sys", "pathlib", "shutil", "tempfile", "io",
}
_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input"}


def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
    return roots


def test_runtime_has_no_forbidden_imports():
    offenders = []
    for path in _runtime_files():
        basename = os.path.basename(str(path))
        tree = ast.parse(_read(path))
        roots = _import_roots(tree)
        if basename == _READER_BASENAME:
            roots = roots - _READER_IMPORT_ALLOWLIST
        bad = roots & _FORBIDDEN_IMPORT_ROOTS
        if bad:
            offenders.append((basename, sorted(bad)))
    assert offenders == [], "forbidden imports in phase6_1 runtime: %r" % offenders


def test_runtime_has_no_io_or_dynamic_exec_calls():
    offenders = []
    for path in _runtime_files():
        basename = os.path.basename(str(path))
        is_reader = basename == _READER_BASENAME
        tree = ast.parse(_read(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in _FORBIDDEN_CALL_NAMES:
                    continue
                # Module-scoped exception: the single allowlisted reader may use a READ-ONLY open()
                # for its local artifact. Any open() in any other module, any write/append/non-literal
                # open even here, and every dynamic-exec call everywhere stay banned.
                if is_reader and name == "open" and _open_is_read_only(node):
                    continue
                offenders.append((basename, name))
    assert offenders == [], "forbidden IO/dynamic-exec calls in phase6_1 runtime: %r" % offenders


# --- 3b. AST no-isinstance lock (exact-type discipline) -------------------------------------------

def test_runtime_uses_no_isinstance():
    offenders = []
    for path in _runtime_files():
        tree = ast.parse(_read(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "isinstance":
                    offenders.append(os.path.basename(str(path)))
    assert offenders == [], "isinstance used in phase6_1 runtime: %r" % offenders


# --- 6. AST no calculation/readiness/actionability surface ----------------------------------------

_BANNED_NAME_SUBSTRINGS = (
    "calculate", "compute", "derive", "score", "readiness",
    "actionability", "actionable", "recommendation", "verdict",
)


def _defined_names(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.append(tgt.id)
    return names


def test_runtime_has_no_calculation_or_actionability_surface():
    offenders = []
    for path in _runtime_files():
        tree = ast.parse(_read(path))
        for name in _defined_names(tree):
            low = name.lower()
            if any(tok in low for tok in _BANNED_NAME_SUBSTRINGS):
                offenders.append((os.path.basename(str(path)), name))
    assert offenders == [], "calculation/actionability surface in phase6_1 runtime: %r" % offenders


# --- 4. forbidden/foreign payload fail-fast at every entrypoint ------------------------------------

class _FakePayload:
    """A foreign object that is NOT any approved Phase 5/6.1 type."""


def test_make_passive_shadow_input_rejects_fake_payloads():
    for bad in (_FakePayload(), {"net_edge_value": "0.006"}, [1, 2, 3], _blocked_packet()):
        with pytest.raises(PassiveShadowInputTypeError):
            make_passive_shadow_input(
                net_edge_calculation_result=bad,
                source_venue="hyperliquid",
                source_pair="BTC-USD",
                observed_at_epoch_ms=1_750_000_000_000,
            )


def test_make_passive_shadow_input_rejects_net_edge_subclass():
    class _Sub(NetEdgeCalculationResult):
        pass

    sub = object.__new__(_Sub)
    with pytest.raises(PassiveShadowInputTypeError):
        make_passive_shadow_input(
            net_edge_calculation_result=sub,
            source_venue="hyperliquid",
            source_pair="BTC-USD",
            observed_at_epoch_ms=1_750_000_000_000,
        )


def test_make_shadow_observation_rejects_fake_payloads():
    for bad in (_FakePayload(), {"source": "x"}, [1], _blocked_packet(), _necr()):
        with pytest.raises(ShadowObservationTypeError):
            make_shadow_observation(
                source=bad,
                replay_artifact_id="replay-fixture-0001",
                replay_sequence_index=0,
                diagnostic_recorded_at_ms=1_750_000_000_500,
            )


def test_make_shadow_observation_rejects_passive_input_subclass():
    class _Sub(PassiveShadowInput):
        pass

    sub = object.__new__(_Sub)
    with pytest.raises(ShadowObservationTypeError):
        make_shadow_observation(
            source=sub,
            replay_artifact_id="replay-fixture-0001",
            replay_sequence_index=0,
            diagnostic_recorded_at_ms=1_750_000_000_500,
        )


def test_verify_provenance_chain_rejects_fake_payloads():
    for bad in (_FakePayload(), {"source": "x"}, [1], _necr(), _psi()):
        with pytest.raises(ShadowProvenanceTypeError):
            verify_provenance_chain(bad)


# --- halt carriers are type/provenance boundary violations, NOT actionability errors --------------

def test_halt_carriers_are_type_boundary_not_actionability():
    for packet in (_blocked_packet(), _no_eligible_packet()):
        with pytest.raises(ShadowProvenanceTypeError) as exc_info:
            verify_provenance_chain(packet)
        raised = exc_info.type
        assert issubclass(raised, TypeError)
        assert "actionab" not in raised.__name__.lower()
        assert "violation" not in raised.__name__.lower()
