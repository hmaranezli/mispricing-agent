"""tests/test_phase6_1_diagnostic_ev_non_actionability.py — Phase 6.1 Slice 0E.

Locks that the passive diagnostic value can never become actionability. `diagnostic_passive_value`
remains an exact finite float or None, CARRIED only — never compared, thresholded, ranked,
truthiness-tested, or turned into an EV/score/readiness/verdict anywhere in the phase6_1 runtime.

Each structural detector below is "teeth-proven": it is first shown to FLAG a crafted violating
snippet, then shown to find NOTHING in the real runtime. This prevents vacuous structural tests.

Every token/identifier string in THIS file is an explicit test fixture; the runtime must contain none
of the forbidden ones.
"""
import ast
import math
import os
import pathlib
import re

import pytest

import phase6_1
from phase5.net_edge_calculator_boundary import _make_net_edge_result
from phase6_1.passive_shadow_input import make_passive_shadow_input
from phase6_1.shadow_observation import (
    make_shadow_observation,
    ShadowObservationTypeError,
    ShadowObservationValueError,
)


_VALUE_NAME = "diagnostic_passive_value"
_ORDER_OR_EQ_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)


# --- runtime discovery ----------------------------------------------------------------------------

def _runtime_files():
    pkg_dir = pathlib.Path(phase6_1.__file__).resolve().parent
    return sorted(p for p in pkg_dir.glob("*.py"))


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --- deterministic builders -----------------------------------------------------------------------

def _psi():
    necr = _make_net_edge_result(
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
    return make_passive_shadow_input(
        net_edge_calculation_result=necr,
        source_venue="hyperliquid",
        source_pair="BTC-USD",
        observed_at_epoch_ms=1_750_000_000_000,
    )


def _obs(**overrides):
    kwargs = dict(
        source=_psi(),
        replay_artifact_id="replay-fixture-0001",
        replay_sequence_index=0,
        diagnostic_recorded_at_ms=1_750_000_000_500,
    )
    kwargs.update(overrides)
    return make_shadow_observation(**kwargs)


# --- detectors (operate on an AST tree) -----------------------------------------------------------

def _ordering_or_threshold_offenses(tree):
    """Compare nodes where the diagnostic value Name is a DIRECT operand under an ordering/equality
    operator. Allows ``is``/``is not`` (None deferral) and ``type(value) is float`` (value nested in a
    call, not a direct operand)."""
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left] + list(node.comparators)
            direct = any(isinstance(o, ast.Name) and o.id == _VALUE_NAME for o in operands)
            if direct and any(isinstance(op, _ORDER_OR_EQ_OPS) for op in node.ops):
                hits.append(ast.dump(node))
    return hits


def _truthiness_offenses(tree):
    """Bare truthiness of the diagnostic value Name in a boolean context. Allows an explicit
    ``... is not None`` Compare (its test is a Compare, not a bare Name)."""
    hits = []

    def _is_value_name(n):
        return isinstance(n, ast.Name) and n.id == _VALUE_NAME

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.IfExp)) and _is_value_name(node.test):
            hits.append(ast.dump(node))
        elif isinstance(node, ast.BoolOp):
            if any(_is_value_name(v) for v in node.values):
                hits.append(ast.dump(node))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and _is_value_name(node.operand):
            hits.append(ast.dump(node))
    return hits


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


def _token_hits(token, text):
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, text, re.IGNORECASE) is not None


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


# --- 1./2. no ordering/threshold/equality comparison on the diagnostic value ----------------------

def test_ordering_detector_has_teeth():
    bad = ast.parse("if diagnostic_passive_value > 0.5:\n    pass\n")
    assert _ordering_or_threshold_offenses(bad)
    # allowed forms must NOT be flagged
    ok_isnone = ast.parse("if diagnostic_passive_value is not None:\n    pass\n")
    ok_type = ast.parse("x = type(diagnostic_passive_value) is float\n")
    ok_finite = ast.parse("x = math.isfinite(diagnostic_passive_value)\n")
    assert _ordering_or_threshold_offenses(ok_isnone) == []
    assert _ordering_or_threshold_offenses(ok_type) == []
    assert _ordering_or_threshold_offenses(ok_finite) == []


def test_runtime_has_no_ordering_or_threshold_comparison_on_diagnostic_value():
    offenders = []
    for path in _runtime_files():
        if _ordering_or_threshold_offenses(ast.parse(_read(path))):
            offenders.append(os.path.basename(str(path)))
    assert offenders == [], "ordering/threshold comparison on diagnostic value: %r" % offenders


def test_truthiness_detector_has_teeth():
    assert _truthiness_offenses(ast.parse("if diagnostic_passive_value:\n    pass\n"))
    assert _truthiness_offenses(ast.parse("x = not diagnostic_passive_value\n"))
    assert _truthiness_offenses(ast.parse("x = diagnostic_passive_value and 1\n"))
    assert _truthiness_offenses(ast.parse("if diagnostic_passive_value is not None:\n    pass\n")) == []


def test_runtime_has_no_truthiness_test_on_diagnostic_value():
    offenders = []
    for path in _runtime_files():
        if _truthiness_offenses(ast.parse(_read(path))):
            offenders.append(os.path.basename(str(path)))
    assert offenders == [], "truthiness test on diagnostic value: %r" % offenders


# --- 3. no EV formula / identifiers ---------------------------------------------------------------

_EV_TOKENS = (
    "p_success", "psuccess", "limit_edge", "limitedge", "expected_value",
    "diagnostic_expected_value", "passive_diagnostic_ev", "ev_formula", "ev_value",
)


def test_ev_token_scanner_has_teeth():
    snippet = "diagnostic_expected_value = p_success * limit_edge\n"
    assert any(_token_hits(tok, snippet) for tok in _EV_TOKENS)


def test_runtime_has_no_ev_formula_identifiers():
    violations = []
    for path in _runtime_files():
        text = _read(path)
        for tok in _EV_TOKENS:
            if _token_hits(tok, text):
                violations.append((os.path.basename(str(path)), tok))
    assert violations == [], "EV-formula identifiers in runtime: %r" % violations


# --- 4./6. no actionability / readiness / ranking / threshold surface ------------------------------

_BANNED_SURFACE_SUBSTRINGS = (
    "calculate", "compute", "derive", "score", "readiness",
    "actionability", "actionable", "recommendation", "verdict",
    "rank", "ranking", "threshold",
)

# S1 in-memory sink: an EXACT-NAME, per-basename name-surface exception authorized by
# docs/handoff/phase6_1_s1_score_record_name_lock_exception_charter.md. ONLY the exact defined name
# "ObservationScoreRecord" is permitted, and ONLY in this one basename. The substring "score" stays
# globally banned; no other score-containing name and no other banned substring (incl. rank/ranking/
# threshold) is touched.
_NAME_SURFACE_ALLOWLIST_BY_BASENAME = {
    "s1_in_memory_observation_sink.py": frozenset({"ObservationScoreRecord"}),
}


def test_surface_detector_has_teeth():
    bad = ast.parse("def score_threshold():\n    pass\n")
    names = _defined_names(bad)
    assert any(
        any(tok in n.lower() for tok in _BANNED_SURFACE_SUBSTRINGS) for n in names
    )


def test_runtime_has_no_actionability_or_ranking_surface():
    offenders = []
    for path in _runtime_files():
        basename = os.path.basename(str(path))
        allowed_names = _NAME_SURFACE_ALLOWLIST_BY_BASENAME.get(basename, frozenset())
        for name in _defined_names(ast.parse(_read(path))):
            if name in allowed_names:
                continue
            low = name.lower()
            if any(tok in low for tok in _BANNED_SURFACE_SUBSTRINGS):
                offenders.append((basename, name))
    assert offenders == [], "actionability/ranking surface in runtime: %r" % offenders


# --- module-scoped IO-lock exception (single allowlisted replay depth reader) ---------------------
# Mirror of the exception in tests/test_phase6_1_forbidden_token_locks.py, authorized by
# docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md. Keyed on EXACTLY
# one basename and closed: only the "json" token, the closed import allowlist {pathlib, json, csv}, and
# a READ-ONLY open() are tolerated for that one module; every other module and every other forbidden
# surface stay banned.

_READER_BASENAME = "b1_replay_depth_artifact_reader.py"
_READER_IMPORT_ALLOWLIST = {"pathlib", "json", "csv"}
_READER_TOKEN_ALLOWLIST = {"json"}

# Option-B event-stream reader: a TOKEN-ONLY "json" exception, authorized by
# docs/handoff/phase6_1_option_b_reader_io_lock_exception_amendment_charter.md. NO import/open/IO/path
# exception is granted to this basename; it stays under the package-wide import and IO scans unchanged
# (it uses no open() and imports nothing forbidden). Only the "json" source token is tolerated.
_OPTION_B_READER_BASENAME = "option_b_event_stream_reader.py"
_OPTION_B_READER_TOKEN_ALLOWLIST = {"json"}

# Per-basename source-token allowlist consulted ONLY by the forbidden-token scan below.
_TOKEN_ALLOWLIST_BY_BASENAME = {
    _READER_BASENAME: _READER_TOKEN_ALLOWLIST,
    _OPTION_B_READER_BASENAME: _OPTION_B_READER_TOKEN_ALLOWLIST,
}


def _open_is_read_only(node):
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


# --- 4(bis). Slice 0D forbidden-token lock still holds (self-contained re-assert) ------------------

_FORBIDDEN_TOKENS = (
    "json", "ledger", "serialize", "serialization", "to_json", "to_dict",
    "wallet", "balance", "private", "secret",
    "order", "routing", "route", "execution", "execute", "allocation", "sizing",
    "signal", "candidate", "trade", "paper", "live",
)


def test_slice0d_forbidden_token_lock_still_holds():
    violations = []
    for path in _runtime_files():
        basename = os.path.basename(str(path))
        text = _read(path)
        allowed = _TOKEN_ALLOWLIST_BY_BASENAME.get(basename, frozenset())
        for tok in _FORBIDDEN_TOKENS:
            if tok in allowed:
                continue
            if _token_hits(tok, text):
                violations.append((basename, tok))
    assert violations == [], "forbidden tokens in runtime: %r" % violations


# --- 5. Slice 0D import / IO locks still hold (self-contained re-assert) ---------------------------

_FORBIDDEN_IMPORT_ROOTS = {
    "requests", "http", "socket", "websocket", "websockets", "urllib", "aiohttp",
    "subprocess", "sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "ssl", "smtplib",
    "ftplib", "telnetlib", "pickle", "shelve", "os", "sys", "pathlib", "shutil", "tempfile", "io",
}
_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input"}


def test_slice0d_import_and_io_locks_still_hold():
    import_offenders = []
    call_offenders = []
    for path in _runtime_files():
        basename = os.path.basename(str(path))
        is_reader = basename == _READER_BASENAME
        tree = ast.parse(_read(path))
        roots = _import_roots(tree)
        if is_reader:
            roots = roots - _READER_IMPORT_ALLOWLIST
        bad = roots & _FORBIDDEN_IMPORT_ROOTS
        if bad:
            import_offenders.append((basename, sorted(bad)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in _FORBIDDEN_CALL_NAMES:
                    continue
                if is_reader and name == "open" and _open_is_read_only(node):
                    continue
                call_offenders.append((basename, name))
    assert import_offenders == [], "forbidden imports: %r" % import_offenders
    assert call_offenders == [], "forbidden IO/exec calls: %r" % call_offenders


# --- diagnostic_passive_value is CARRIED, and its contract is unchanged ----------------------------

def test_diagnostic_passive_value_is_carried_round_trip():
    obs = _obs(diagnostic_passive_value=0.0036)
    assert obs.diagnostic_passive_value == 0.0036
    obs_none = _obs()
    assert obs_none.diagnostic_passive_value is None


def test_diagnostic_passive_value_contract_is_exact_finite_float_or_none():
    assert _obs(diagnostic_passive_value=0.0).diagnostic_passive_value == 0.0
    assert _obs(diagnostic_passive_value=None).diagnostic_passive_value is None
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ShadowObservationValueError):
            _obs(diagnostic_passive_value=bad)
    for bad in (1, True, "0.0036"):
        with pytest.raises(ShadowObservationTypeError):
            _obs(diagnostic_passive_value=bad)
