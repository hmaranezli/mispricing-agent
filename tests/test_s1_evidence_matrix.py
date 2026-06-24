"""tests/test_s1_evidence_matrix.py — passive S1 Stream Authorization Evidence Matrix construction
(TDD).

Bu slice, daha önce RATIFIYE edilmiş S1 Stream Authorization Evidence Matrix Construction Boundary
Charter'ına göre matrisi YALNIZCA PASİF, REVIEWABLE bir nesne olarak kurar. 18 row class × 18 column
= 324 hücre. Matris hiçbir zaman AUTHORIZED olamaz; her hücre pasif evidence-status taşır. Eksik
kanıt → BLOCKED/INCOMPLETE; bilinmeyen anahtar / duplicate ID / PASS-COMPLETE olmayan audit / eksik
approval-ledger referansı → fail closed. Geçerli kurulum bile S1 append / production stream /
paper/live / trading / wallet / capacity yetkilendirmez.

İlk RED: approval.s1_evidence_matrix yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.s1_evidence_matrix import (
    COLUMNS,
    ROW_CLASSES,
    S1EvidenceMatrix,
    construct_s1_evidence_matrix,
)

_AUDIT_OK = {"status": "PASS_COMPLETE"}
_LEDGER_REFS = ("appr-0001",)


def _full_evidence(rows=ROW_CLASSES, cols=COLUMNS):
    return {r: {c: "EVIDENCE_PRESENT" for c in cols} for r in rows}


def _construct(**over):
    kw = dict(
        audit_summary=_AUDIT_OK,
        approval_ledger_refs=_LEDGER_REFS,
        evidence=_full_evidence(),
    )
    kw.update(over)
    return construct_s1_evidence_matrix(**kw)


# 1 — exactly 18 row classes are required
def test_eighteen_row_classes():
    assert len(ROW_CLASSES) == 18
    assert len(set(ROW_CLASSES)) == 18
    bad_rows = ROW_CLASSES[:-1]  # 17
    m = _construct(evidence=_full_evidence(rows=bad_rows), audit_summary=_AUDIT_OK)
    # construct uses default row_ids=ROW_CLASSES; pass explicit short row_ids
    m = construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK,
        approval_ledger_refs=_LEDGER_REFS,
        evidence=_full_evidence(rows=bad_rows),
        row_ids=bad_rows,
    )
    assert m.state == "FAILED"
    assert m.reason == "row_count_must_be_18"


# 2 — exactly 18 columns are required
def test_eighteen_columns():
    assert len(COLUMNS) == 18
    assert len(set(COLUMNS)) == 18
    bad_cols = COLUMNS[:-1]  # 17
    m = construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK,
        approval_ledger_refs=_LEDGER_REFS,
        evidence=_full_evidence(cols=bad_cols),
        column_ids=bad_cols,
    )
    assert m.state == "FAILED"
    assert m.reason == "column_count_must_be_18"


# 3 — matrix expands to exactly 324 cells
def test_matrix_has_324_cells():
    m = _construct()
    assert m.state == "REVIEWABLE"
    assert m.cell_count == 324
    assert len(m.cells) == 324


# 4 — row IDs are deterministic
def test_row_ids_deterministic():
    a = _construct()
    b = _construct()
    assert a.row_ids == ROW_CLASSES == b.row_ids


# 5 — column IDs are deterministic
def test_column_ids_deterministic():
    a = _construct()
    b = _construct()
    assert a.column_ids == COLUMNS == b.column_ids
    # cell order is deterministic too
    assert a.cells == b.cells


# 6 — duplicate row ID fails closed
def test_duplicate_row_id_fails_closed():
    dup = (ROW_CLASSES[0],) + ROW_CLASSES[1:]  # still 18 but first repeated below
    dup = (ROW_CLASSES[0],) + ROW_CLASSES  # 19 with a duplicate
    dup = ROW_CLASSES[:-1] + (ROW_CLASSES[0],)  # 18 length, with a duplicate of row 0
    m = construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK,
        approval_ledger_refs=_LEDGER_REFS,
        evidence=_full_evidence(),
        row_ids=dup,
    )
    assert m.state == "FAILED"
    assert m.reason == "duplicate_row_id"


# 7 — duplicate column ID fails closed
def test_duplicate_column_id_fails_closed():
    dup = COLUMNS[:-1] + (COLUMNS[0],)  # 18 length, with a duplicate of col 0
    m = construct_s1_evidence_matrix(
        audit_summary=_AUDIT_OK,
        approval_ledger_refs=_LEDGER_REFS,
        evidence=_full_evidence(),
        column_ids=dup,
    )
    assert m.state == "FAILED"
    assert m.reason == "duplicate_column_id"


# 8 — missing audit summary fails closed
def test_missing_audit_summary_fails_closed():
    m = _construct(audit_summary=None)
    assert m.state == "FAILED"
    assert m.reason == "missing_audit_summary"


# 9 — audit summary not PASS / COMPLETE fails closed
def test_audit_not_pass_complete_fails_closed():
    m = _construct(audit_summary={"status": "FAIL"})
    assert m.state == "FAILED"
    assert m.reason == "audit_summary_not_pass_complete"


# 10 — missing approval ledger reference fails closed
def test_missing_ledger_reference_fails_closed():
    m = _construct(approval_ledger_refs=())
    assert m.state == "FAILED"
    assert m.reason == "missing_approval_ledger_reference"


# 11 — unknown evidence key fails closed
def test_unknown_evidence_key_fails_closed():
    ev = _full_evidence()
    ev["BOGUS_ROW"] = {c: "EVIDENCE_PRESENT" for c in COLUMNS}
    m = _construct(evidence=ev)
    assert m.state == "FAILED"
    assert m.reason == "unknown_evidence_key"


# 12 — missing required cell evidence blocks matrix
def test_missing_cell_blocks_matrix():
    ev = _full_evidence()
    del ev[ROW_CLASSES[0]][COLUMNS[0]]  # remove one of the 324 cells
    m = _construct(evidence=ev)
    assert m.state == "BLOCKED_INCOMPLETE"
    assert m.reason == "incomplete_matrix"


# 13 — all required passive evidence can make matrix REVIEWABLE only
def test_full_evidence_is_reviewable_only():
    m = _construct()
    assert m.state == "REVIEWABLE"
    assert m.reason == ""
    assert m.state != "AUTHORIZED"


# 14 — REVIEWABLE matrix still does not authorize S1 append
def test_reviewable_does_not_authorize():
    m = _construct()
    assert m.s1_append_authorized is False
    assert m.production_stream_authorized is False
    assert m.trading_authorized is False
    assert m.capacity_enabled is False


# 15 — matrix exposes no append command / write command
def test_no_append_or_write_command():
    import approval.s1_evidence_matrix as mod

    for name in dir(mod):
        low = name.lower()
        for banned in ("append", "write", "commit", "insert", "stream", "flush", "execute", "authorize_"):
            assert banned not in low, f"forbidden command surface: {name}"


# 16 — matrix imports no S1 DB/raw/network/wallet/signing/trading/capacity modules
def test_slice_imports_no_forbidden_dependency():
    import approval.s1_evidence_matrix as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"dataclasses", "typing", "__future__"}
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
        "signing",
        "trading",
        "capacity",
    )
    for modname in imported_full:
        low = modname.lower()
        for tok in forbidden:
            assert tok not in low, f"forbidden import: {modname}"


# 17 — clean raw audit alone is not sufficient
def test_audit_alone_insufficient():
    m = _construct(approval_ledger_refs=())
    assert m.state == "FAILED"
    assert m.reason == "missing_approval_ledger_reference"


# 18 — approval ledger record alone is not sufficient
def test_ledger_alone_insufficient():
    m = _construct(audit_summary=None)
    assert m.state == "FAILED"
    assert m.reason == "missing_audit_summary"


# 19 — output is passive/frozen with deterministic reason
def test_output_passive_frozen():
    m = _construct()
    assert isinstance(m, S1EvidenceMatrix)
    with pytest.raises(Exception):
        m.state = "AUTHORIZED"  # type: ignore[misc]
    # constructing twice gives identical deterministic result
    assert _construct() == m


# 20 — no report/export/artifact file is generated by the slice
def test_no_file_generated(tmp_path):
    before = set(os.listdir(tmp_path))
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        _construct()
        _construct(audit_summary=None)
    finally:
        os.chdir(cwd)
    after = set(os.listdir(tmp_path))
    assert before == after
