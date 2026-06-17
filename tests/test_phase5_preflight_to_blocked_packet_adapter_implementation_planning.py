"""tests/test_phase5_preflight_to_blocked_packet_adapter_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_preflight_to_blocked_packet_adapter` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; scopes the adapter to a format boundary
that converts only blocked / contract-violation preflight results into a BlockedPacket; forbids
success-path conversion (with a programmatic misuse error, never None/empty/silent); fixes the
deterministic BLOCKED-vs-CONTRACT_VIOLATION 1:1 mapping with no downgrade/upgrade/default; pins the
origin stamp and the explicit source->destination field map; requires the strict typed/frozen
PreflightResult input (no dict/Mapping/attribute guessing); bars parser/loader/verifier/SHA256/
artifact-reader behavior and raw-market consumption; excludes NO_ELIGIBLE handling; keeps the
no-claims / no-downstream-authorization boundary; states no runtime edit and no central handoff/memory
edit in this task; restates the future-implementation gate; carries the standard no-claims block; and
avoids ready/complete/safe/absolute-risk and source-trust framing — while asserting no forbidden
over-claim wording appears anywhere and forbidden positive-claim phrases appear only inside the
explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_preflight_to_blocked_packet_adapter_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

GATE_STATUSES = [
    "PLANNING_GATE_OBSERVED",
    "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
    "PLANNING_GATE_CONTRACT_VIOLATION",
]

SOURCE_FIELDS = [
    "status",
    "blocked_status",
    "blocked_reason",
    "missing_or_invalid_field",
    "source_contract",
    "source_artifact",
    "source_field",
    "deterministic_next_action",
    "human_review_required",
    "may_retry_after_evidence",
]

DESTINATION_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "blocked_status",
    "reason_code",
    "missing_or_invalid_field",
    "source_contract",
    "source_artifact",
    "source_field",
    "deterministic_next_action",
    "human_review_required",
    "may_retry_after_evidence",
    "created_from_contract",
    "boundary_version",
]

FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

FORBIDDEN_WORDING = [
    "eliminates all risk", "eliminates risk", "zero risk", "tamper-proof",
    "verified truth", "clean data", "trusted data", "is immutable",
    "guarantees correctness", "is impossible", "cannot happen",
    "final phase 5 contract", "last critical piece", "is complete", "is perfect",
    "is now safe", "fully complete", "the last piece",
    "source is trusted", "data is valid",
]


def _read():
    assert os.path.isfile(DOC), f"adapter planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "adapter planning doc is empty"


def test_component_name_present():
    assert "phase5_preflight_to_blocked_packet_adapter" in _read()


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_format_boundary_scope():
    low = _read().lower()
    assert "format-boundary adapter only" in low
    assert "must not validate, parse, repair, enrich, infer, downgrade, or interpret source data" in low


def test_success_path_rejection():
    low = _read().lower()
    assert "a planning_gate_observed or success-like preflight result must not be converted into a blockedpacket" in low
    assert "the later adapter implementation must raise a programmatic misuse error" in low
    assert "it must never return none, never return an empty/default packet, and never silently pass" in low


def test_deterministic_mapping():
    text = _read()
    missing = [s for s in GATE_STATUSES if s not in text]
    assert not missing, f"gate statuses missing: {missing}"
    low = text.lower()
    assert "planning_gate_blocked_needs_evidence maps to a blockedpacket with blocked/evidence-needed semantics" in low
    assert "planning_gate_contract_violation maps to a blockedpacket with contract-violation semantics" in low
    assert "no downgrade from contract_violation to blocked" in low
    assert "no upgrade from blocked to observed" in low
    assert "no default/empty/false/zero conversion" in low


def test_origin_stamp():
    low = _read().lower()
    assert "origin_component must be phase5_input_provenance_preflight" in low
    assert "component_name must identify the adapter/boundary result consistently" in low
    assert "source contract/artifact/field values must be carried from declared preflight result fields only" in low


def test_explicit_field_map_present():
    low = _read().lower()
    missing_src = [f for f in SOURCE_FIELDS if f not in low]
    assert not missing_src, f"source fields missing: {missing_src}"
    missing_dst = [f for f in DESTINATION_FIELDS if f not in low]
    assert not missing_dst, f"destination fields missing: {missing_dst}"
    assert "mapping must be explicit; no arbitrary dict parsing, no attribute introspection, no heuristic key guessing" in low


def test_strict_input_type():
    low = _read().lower()
    assert "the later adapter implementation must accept only the explicit typed/frozen preflightresult emitted by phase5_input_provenance_preflight" in low
    assert "it must reject raw dicts, generic mapping, arbitrary objects, or attribute-guessed records" in low


def test_adapter_boundary():
    low = _read().lower()
    assert "the adapter may call make_blocked_packet only in a later implementation slice" in low
    assert "it must not construct parser/loader/verifier/sha256/artifact-reader behavior" in low
    assert "it must not consume raw market records or source artifacts" in low
    assert "it must not inspect values for market truth/data quality/source reliability/economic meaning" in low


def test_no_eligible_excluded():
    low = _read().lower()
    assert "this adapter must not handle no_eligible or economic/business-ineligibility states" in low
    assert "no_eligible is a separate later boundary and must not be encoded as a blockedpacket" in low


def test_no_claims_continuity():
    low = _read().lower()
    assert "the adapter asserts no source truth, data quality, source reliability, profitability, readiness, safety, edge, net-edge, execution, or trading property" in low
    assert "the adapter authorizes no downstream calculation or next component" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert "this task does not edit the central handoff/memory file and performs no memory closeout" in low


def test_future_implementation_gate():
    low = _read().lower()
    assert "any implementation requires separate explicit authorization, failing tests first, declared provenance, component-scoped work, and offline/tdd scope" in low
    assert "does not authorize implementation or selecting the next component" in low


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no profitability", "no alpha",
                 "no live readiness", "no paper readiness", "no economics readiness",
                 "no safety guarantee", "no data-quality guarantee", "no data-integrity guarantee"]:
        assert term in low, f"no-claims term missing: {term}"


def test_no_forbidden_overclaim_wording_anywhere():
    low = _read().lower()
    hits = [w for w in FORBIDDEN_WORDING if w in low]
    assert not hits, f"forbidden over-claim wording present: {hits}"


def test_forbidden_claims_only_in_framing_no_claims_or_prohibited_outputs():
    text = _read()
    body = _strip_block(text, FRAMING_START, FRAMING_END)
    body = _strip_block(body, NO_CLAIMS_START, NO_CLAIMS_END)
    body = _strip_block(body, PROHIBITED_OUT_START, PROHIBITED_OUT_END).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) outside allowed sections: {hits}"


def test_generated_artifacts_not_referenced_as_tracked():
    text = _read()
    low = text.lower()
    assert "untracked" in low, "must state generated artifacts are untracked"
    assert "git add ." not in text, "must not reference blanket staging"
