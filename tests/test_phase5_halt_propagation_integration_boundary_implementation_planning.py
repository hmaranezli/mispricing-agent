"""tests/test_phase5_halt_propagation_integration_boundary_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_halt_propagation_integration_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; keeps BlockedPacket and
NoEligibleHaltPacket as separate EXACT-type halt carriers with no shared GenericHaltPacket /
BaseHaltPacket / union / polymorphic hierarchy and no isinstance-based generic acceptance; bars any
cross-conversion between BLOCKED / CONTRACT_VIOLATION and NO_ELIGIBLE; requires both carriers to
bypass calculator/net-edge/friction/trading/reporting-economic paths; rules unknown input out of
NO_ELIGIBLE as a contract/integration misuse path rejected without str/repr/introspection; bars all
coercion / numeric / boolean / default conversion; pins pass-through identity and success-path
continuity without defining the eligible/actionable payload schema; states no runtime edit and no
central handoff/memory edit; keeps the no-claims / no-downstream-authorization boundary; restates the
future-implementation gate; carries the standard no-claims block; and avoids ready/complete/safe/
absolute-risk and source-trust framing — while asserting no forbidden over-claim wording appears
anywhere and forbidden positive-claim phrases appear only inside the explicit framing / no-claims /
prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_halt_propagation_integration_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

FORBIDDEN_PACKET_NAMES = [
    "BaseHaltPacket", "GenericHaltPacket", "HaltPacket",
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
    assert os.path.isfile(DOC), f"halt-propagation integration planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "halt-propagation integration planning doc is empty"


def test_component_name_present():
    assert "phase5_halt_propagation_integration_boundary" in _read()


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_integration_boundary_scope():
    low = _read().lower()
    assert "integration boundary only, not a calculator" in low


def test_exact_type_carrier_separation():
    text = _read()
    low = text.lower()
    assert "blockedpacket is the evidence/provenance/contract failure halt carrier" in low
    assert "noeligiblehaltpacket is the non-error no-candidate halt carrier" in low
    assert "they are separate exact-type halt carriers" in low
    assert "type(x) is blockedpacket" in low
    assert "type(x) is noeligiblehaltpacket" in low
    assert "no isinstance-based generic halt acceptance" in low


def test_no_shared_halt_hierarchy():
    low = _read().lower()
    assert "no shared basehaltpacket, generichaltpacket, haltpacket, union packet, or polymorphic halt hierarchy" in low
    # The forbidden names appear only inside the prohibition sentence; pin that they are each named
    # there so the ban is explicit (not that they are absent — the ban itself must reference them).
    for name in FORBIDDEN_PACKET_NAMES:
        assert name.lower() in low, f"forbidden shared-halt name not explicitly banned: {name}"


def test_no_cross_conversion():
    low = _read().lower()
    assert "blockedpacket must not be converted, downgraded, translated, wrapped, or re-emitted as noeligiblehaltpacket" in low
    assert "noeligiblehaltpacket must not be converted, upgraded, translated, wrapped, or re-emitted as blockedpacket" in low
    assert "contract_violation must not become no_eligible" in low
    assert "no_eligible must not become blocked, contract_violation, observed, eligible, or success" in low


def test_bypass_halt_behavior():
    low = _read().lower()
    assert "blockedpacket bypasses calculator/net-edge/friction/trading/reporting-economic paths as a fail-closed error halt" in low
    assert "noeligiblehaltpacket bypasses calculator/net-edge/friction/trading/reporting-economic paths as a non-error no-candidate halt" in low
    assert "both may only be routed toward a future non-economic reporting/output boundary" in low
    assert "neither may call or imply net-edge calculation" in low
    assert "neither may trigger parser/loader/artifact reader/endpoint/paper/live runner behavior" in low


def test_unknown_input_is_not_no_eligible():
    low = _read().lower()
    assert "unknown object, raw dict, generic mapping, arbitrary object, subclass, or attribute-guessed record is not no_eligible" in low
    assert "unknown input is a contract/integration misuse path" in low
    assert "future implementation must reject it with a strict typeerror/contract-violation-style error or fail-closed boundary violation, and must not mask it as noeligiblehaltpacket" in low
    assert "no str/repr/introspection of the unknown object" in low
    assert "type(obj).__name__" in low


def test_no_coercion():
    low = _read().lower()
    assert "halt carriers must never be coerced into bool, int, float, str, bytes, none, empty, zero, false, default, eligible=false, edge=0, cost=0, net_edge=0, gross_edge=0, no-op success, or calculator input" in low
    assert "future implementation must not call bool(), len(), int(), float(), str(), bytes(), repr(), or equality on halt carrier payloads" in low
    assert "it must preserve the anti-truthiness/anti-coercion guarantees" in low


def test_pass_through_identity():
    low = _read().lower()
    assert "an exact blockedpacket input must be returned/carried identically if routed to the blocked halt output" in low
    assert "an exact noeligiblehaltpacket input must be returned/carried identically if routed to the no-eligible halt output" in low
    assert "no mutation, downgrade, upgrade, wrapping, copying, enrichment, repair, inference, or field rewriting" in low


def test_success_path_continuity():
    low = _read().lower()
    assert "if the future integration boundary receives a valid non-halt actionable payload type, it must pass it through identically to the later calculator-eligible path" in low
    assert "it must not mutate, coerce, parse, enrich, repair, infer, or attach economic meaning to that payload" in low
    assert "the exact actionable payload type and calculator input schema are deferred to a later calculator/input-boundary task" in low
    assert "this planning task must not define the eligible payload schema" in low


def test_no_claims_continuity():
    low = _read().lower()
    assert "the boundary asserts no source truth, data quality, data integrity, source reliability, safety, readiness, profitability, alpha, edge, net-edge, execution, trading, or paper/live property" in low
    assert "the boundary authorizes no net-edge calculator, no friction engine, no trading, no reporting runtime, no paper/live readiness, and no next-component implementation" in low


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
