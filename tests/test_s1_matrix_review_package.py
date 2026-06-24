"""tests/test_s1_matrix_review_package.py — non-executable S1 matrix evaluation + operator review
package (TDD).

Bu slice, PASİF REVIEWABLE S1 evidence matrix nesnesini READ-ONLY değerlendirir ve NON-EXECUTABLE
bir operator review package derler. Gemini bulgularını karşılar:
  - Critical vs non-critical sınıflandırma STATİK ve kod-içi politikadır; caller input ile
    değiştirilemez; bilinmeyen criticality fail closed.
  - Review package, matrix digest'ine bağlıdır (UI/imza katmanı "bir şey gösterip başka şey
    imzalayamaz").
  - Hiçbir signing payload / execution token / S1 append / authorization üretilmez.

İlk RED: approval.s1_matrix_review yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.s1_evidence_matrix import COLUMNS, ROW_CLASSES, construct_s1_evidence_matrix
from approval.s1_matrix_review import (
    CRITICAL_COLUMNS,
    NON_CRITICAL_COLUMNS,
    ReviewPackage,
    compile_operator_review_package,
)

_AUDIT_OK = {"status": "PASS_COMPLETE"}
_LEDGER_REFS = ("appr-0001",)


def _full_evidence(value="EVIDENCE_PRESENT"):
    return {r: {c: value for c in COLUMNS} for r in ROW_CLASSES}


def _reviewable():
    return construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK, approval_ledger_refs=_LEDGER_REFS, evidence=_full_evidence()
    )


def _standin(cells, state="REVIEWABLE", columns=COLUMNS):
    return SimpleNamespace(
        state=state, row_ids=ROW_CLASSES, column_ids=tuple(columns), cells=tuple(cells)
    )


def _cells_with(modifier):
    """Build full 324 satisfied cells, then apply modifier(cell_list)."""
    cells = [(r, c, "EVIDENCE_PRESENT") for r in ROW_CLASSES for c in COLUMNS]
    return modifier(cells)


# 1 — REVIEWABLE matrix evaluates to non-executable review package
def test_reviewable_compiles_package():
    pkg = compile_operator_review_package(_reviewable())
    assert isinstance(pkg, ReviewPackage)
    assert pkg.status == "OPERATOR_REVIEW_READY"
    assert pkg.reason == ""


# 2 — BLOCKED_INCOMPLETE matrix fails closed
def test_blocked_incomplete_fails_closed():
    ev = _full_evidence()
    del ev[ROW_CLASSES[0]][COLUMNS[0]]
    m = construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK, approval_ledger_refs=_LEDGER_REFS, evidence=ev
    )
    assert m.state == "BLOCKED_INCOMPLETE"
    pkg = compile_operator_review_package(m)
    assert pkg.status == "BLOCKED"
    assert pkg.reason == "matrix_blocked_incomplete"


# 3 — FAILED matrix fails closed
def test_failed_matrix_fails_closed():
    m = construct_s1_evidence_matrix(
        audit_summary=None, approval_ledger_refs=_LEDGER_REFS, evidence=_full_evidence()
    )
    assert m.state == "FAILED"
    pkg = compile_operator_review_package(m)
    assert pkg.status == "BLOCKED"
    assert pkg.reason == "matrix_failed"


# 4 — static criticality policy is used, not caller-provided
def test_static_criticality_no_caller_param():
    params = set(inspect.signature(compile_operator_review_package).parameters)
    for bad in ("criticality", "policy", "critical", "waiver", "override"):
        assert bad not in {p.lower() for p in params}, f"caller-provided criticality param: {bad}"
    # the two static sets are disjoint and cover all 18 columns
    assert CRITICAL_COLUMNS.isdisjoint(NON_CRITICAL_COLUMNS)
    assert set(CRITICAL_COLUMNS) | set(NON_CRITICAL_COLUMNS) == set(COLUMNS)


# 5 — unknown cell criticality fails closed
def test_unknown_criticality_fails_closed():
    cols = COLUMNS[:-1] + ("MYSTERY_COLUMN",)
    cells = [(r, c, "EVIDENCE_PRESENT") for r in ROW_CLASSES for c in cols]
    m = _standin(cells, columns=cols)
    pkg = compile_operator_review_package(m)
    assert pkg.status == "BLOCKED"
    assert pkg.reason == "unknown_cell_criticality"


# 6 — missing critical cell fails closed
def test_missing_critical_cell_fails_closed():
    crit_col = sorted(CRITICAL_COLUMNS)[0]

    def mod(cells):
        return [
            (r, c, "EVIDENCE_MISSING" if (r == ROW_CLASSES[0] and c == crit_col) else s)
            for (r, c, s) in cells
        ]

    pkg = compile_operator_review_package(_standin(_cells_with(mod)))
    assert pkg.status == "BLOCKED"
    assert pkg.reason == "missing_critical_cell"


# 7 — missing non-critical cell becomes warning only when statically allowed
def test_missing_non_critical_is_warning_only():
    noncrit_col = sorted(NON_CRITICAL_COLUMNS)[0]

    def mod(cells):
        return [
            (r, c, "EVIDENCE_MISSING" if (r == ROW_CLASSES[0] and c == noncrit_col) else s)
            for (r, c, s) in cells
        ]

    pkg = compile_operator_review_package(_standin(_cells_with(mod)))
    assert pkg.status == "OPERATOR_REVIEW_READY"
    assert any(noncrit_col in w for w in pkg.warnings)


# 8 — no implicit waiver field exists
def test_no_waiver_field():
    for name in ReviewPackage.__annotations__:
        low = name.lower()
        assert "waiver" not in low and "override" not in low, f"waiver field: {name}"


# 9 — no auto-downgrade from critical to non-critical
def test_no_auto_downgrade():
    import approval.s1_matrix_review as mod

    for name in dir(mod):
        assert "downgrade" not in name.lower(), f"downgrade surface: {name}"
    # a critical column is never also non-critical
    assert CRITICAL_COLUMNS.isdisjoint(NON_CRITICAL_COLUMNS)


# 10 — matrix digest is deterministic
def test_digest_deterministic():
    a = compile_operator_review_package(_reviewable())
    b = compile_operator_review_package(_reviewable())
    assert a.matrix_digest == b.matrix_digest
    assert len(a.matrix_digest) == 64


# 11 — changing one cell changes digest
def test_digest_changes_on_cell_change():
    base = compile_operator_review_package(_reviewable())
    ev = _full_evidence()
    ev[ROW_CLASSES[0]][COLUMNS[0]] = "EVIDENCE_NOT_APPLICABLE"
    m2 = construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK, approval_ledger_refs=_LEDGER_REFS, evidence=ev
    )
    other = compile_operator_review_package(m2)
    assert base.matrix_digest != other.matrix_digest


# 12 — review package binds digest to visible summary
def test_summary_binds_digest():
    pkg = compile_operator_review_package(_reviewable())
    assert pkg.matrix_digest in pkg.summary


# 13 — review package states REVIEWABLE is not AUTHORIZED
def test_states_reviewable_not_authorized():
    pkg = compile_operator_review_package(_reviewable())
    assert pkg.reviewable_not_authorized_statement == "REVIEWABLE is not AUTHORIZED"
    assert "REVIEWABLE is not AUTHORIZED" in pkg.summary


# 14 — review package exposes no execution token
def test_no_execution_token():
    pkg = compile_operator_review_package(_reviewable())
    assert pkg.execution_token_created is False
    assert not hasattr(pkg, "execution_token")


# 15 — review package creates no signing payload
def test_no_signing_payload():
    pkg = compile_operator_review_package(_reviewable())
    assert pkg.signing_payload_created is False
    assert not hasattr(pkg, "signing_payload")


# 16 — review package exposes no append/write/execute/sign/stream/trade/capacity API
def test_no_command_surface():
    import approval.s1_matrix_review as mod

    for name in dir(mod):
        low = name.lower()
        for banned in ("append", "write", "execute", "sign", "stream", "trade"):
            assert banned not in low, f"forbidden command surface: {name}"


# 17 — all authority flags are False
def test_all_authority_flags_false():
    pkg = compile_operator_review_package(_reviewable())
    assert pkg.s1_append_authorized is False
    assert pkg.production_stream_authorized is False
    assert pkg.signing_payload_created is False
    assert pkg.execution_token_created is False
    assert pkg.trading_authorized is False
    assert pkg.capacity_enabled is False


# 18 — imports no forbidden modules
def test_slice_imports_no_forbidden_dependency():
    import approval.s1_matrix_review as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"hashlib", "dataclasses", "typing", "__future__"}
    imported_top, imported_full = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_full.add(n.name)
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_full.add(node.module)
                imported_top.add(node.module.split(".")[0])
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"
    forbidden = (
        "sqlite",
        "raw_capture",
        "socket",
        "requests",
        "urllib",
        "http",
        "wallet",
        "clob",
        "trading",
        "capacity",
    )
    for modname in imported_full:
        low = modname.lower()
        for tok in forbidden:
            assert tok not in low, f"forbidden import: {modname}"


# 19 — no report/export/artifact file is generated
def test_no_file_generated(tmp_path):
    before = set(os.listdir(tmp_path))
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        compile_operator_review_package(_reviewable())
    finally:
        os.chdir(cwd)
    assert set(os.listdir(tmp_path)) == before


# 20 — output is passive/frozen with deterministic reason
def test_output_passive_frozen():
    pkg = compile_operator_review_package(_reviewable())
    with pytest.raises(Exception):
        pkg.status = "AUTHORIZED"  # type: ignore[misc]
    assert compile_operator_review_package(_reviewable()) == pkg
