"""tests/test_phase5_no_eligible_halt_propagation_boundary_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_no_eligible_halt_propagation_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; keeps NO_ELIGIBLE semantically separate
from BLOCKED / CONTRACT_VIOLATION (and not encoded as a BlockedPacket); defines NO_ELIGIBLE as a
non-error halt with no numeric/boolean coercion (never 0/False/None/empty/default/edge=0/eligible=
false); requires a halt/bypass away from calculator/net-edge/friction/trading; requires a strict
typed/frozen future input (no dict/Mapping/arbitrary/attribute guessing); pins the canonical output
name NoEligibleHaltPacket (atomic, frozen/scalar-only, anti-coercion) with its declared fields and the
forbidden alternative names; requires NoEligibleTruthinessError and NoEligibleCoercionError; pins
pass-through immutability; bars numeric/economic fields; keeps the no-claims / no-downstream-
authorization boundary; states no runtime edit and no central handoff/memory edit; restates the
future-implementation gate; carries the standard no-claims block; and avoids ready/complete/safe/
absolute-risk and source-trust framing — while asserting no forbidden over-claim wording appears
anywhere and forbidden positive-claim phrases appear only inside the explicit framing / no-claims /
prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_no_eligible_halt_propagation_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

PACKET_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "no_eligible_reason",
    "source_contract",
    "source_artifact",
    "source_field",
    "deterministic_next_action",
    "boundary_version",
]

FORBIDDEN_PACKET_NAMES = [
    "EmptyPacket", "NonePacket", "FalseResult", "ZeroResult", "SkipPacket", "NoEligibleResult",
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
    assert os.path.isfile(DOC), f"no-eligible planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "no-eligible planning doc is empty"


def test_component_name_present():
    assert "phase5_no_eligible_halt_propagation_boundary" in _read()


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_halt_propagation_scope():
    low = _read().lower()
    assert "halt-propagation boundary only, not an eligibility calculator" in low


def test_semantic_separation():
    low = _read().lower()
    assert "blocked / contract_violation is the evidence/provenance/contract failure path" in low
    assert "no_eligible is the no actionable candidate / no eligible item state within a separately authorized eligibility component" in low
    assert "no_eligible must not be encoded as a blockedpacket" in low
    assert "a blockedpacket must not be downgraded or translated into no_eligible" in low
    assert "no_eligible must not be upgraded into observed or eligible" in low


def test_non_error_halt_semantics():
    low = _read().lower()
    assert "no_eligible is not a data-quality, source-truth, safety, readiness, profitability, or edge claim" in low
    assert "no_eligible is not a contract violation by itself" in low
    assert "it means only that a future component declared no eligible candidate within its checked scope" in low
    assert "it authorizes no trade, no net-edge calculation, and no paper/live action" in low


def test_no_numeric_boolean_coercion():
    low = _read().lower()
    assert "no_eligible must never be represented as 0, false, empty list, empty dict, none, default packet, or missing value" in low
    assert "no_eligible must never be used as gross_edge=0, net_edge=0, cost=0, eligible=false, or no-op success" in low
    assert "future implementation must prohibit truthiness and coercion with explicit custom typeerror subclasses" in low


def test_halt_bypass_rule():
    low = _read().lower()
    assert "a no_eligible signal must bypass calculator/net-edge/friction/trading paths" in low
    assert "it may be carried toward a future reporting/output boundary only as a declared no-eligible state" in low
    assert "it must not call or imply net-edge calculation" in low
    assert "it must not trigger artifact reader, parser, loader, endpoint, or live/paper runner behavior" in low


def test_input_boundary():
    low = _read().lower()
    assert "this planning document must not define raw market-data parsing" in low
    assert "future implementation must accept only a typed/frozen no-eligible source result from a separately authorized upstream component" in low
    assert "it must reject raw dicts, generic mapping, arbitrary objects, and attribute-guessed records" in low
    assert "no ad-hoc key guessing or object introspection is allowed" in low


def test_output_boundary():
    text = _read()
    low = text.lower()
    assert "the future no-eligible halt signal must be explicitly named noeligiblehaltpacket" in low
    assert "the future noeligiblehaltpacket must be atomic, explicit, frozen/scalar-only, and anti-coercion" in low
    missing = [f for f in PACKET_FIELDS if f not in low]
    assert not missing, f"packet fields missing: {missing}"
    assert "it must not reuse blockedpacket" in low
    assert "it must not be named emptypacket, nonepacket, falseresult, zeroresult, skippacket, generic haltpacket, or noeligibleresult" in low
    assert "the schema must be explicit and scalar-only, with the exact field list finalized in the later implementation slice" in low


def test_pass_through_immutability():
    low = _read().lower()
    assert "future downstream components must pass through a no-eligible halt signal identically, without mutation, downgrade, upgrade, coercion, or reinterpretation" in low
    assert "this mirrors the blockedpacket pass-through discipline while keeping no_eligible semantically separate from blockedpacket" in low


def test_explicit_anticoercion_errors():
    text = _read()
    assert "NoEligibleTruthinessError" in text
    assert "NoEligibleCoercionError" in text
    low = text.lower()
    assert "future implementation must define noeligibletruthinesserror and noeligiblecoercionerror as custom typeerror subclasses for truthiness and coercion attempts" in low


def test_no_numeric_economic_fields():
    low = _read().lower()
    assert "noeligiblehaltpacket must not expose or imply gross_edge, net_edge, cost, spread, profitability, pnl, sizing, execution, paper/live readiness, or tradeability fields" in low


def test_no_claims_continuity():
    low = _read().lower()
    assert "the boundary asserts no source truth, data quality, data integrity, source reliability, safety, readiness, profitability, alpha, edge, net-edge, execution, trading, or paper/live property" in low
    assert "the boundary authorizes no downstream calculation and no next-component implementation" in low


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
