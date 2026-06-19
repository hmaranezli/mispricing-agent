"""tests/test_phase5_capacity_constraint_evidence_boundary_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_capacity_constraint_evidence_boundary`
component (docs-only planning, offline, read-only).

This boundary, if ever authorized, is framed as a passive **constitutional safety barrier / airgap**,
NOT a downstream Phase 6 component and NOT an actionable decision engine. Slice 0 is a structural
multi-source join auditor over exactly four already-implemented Phase 5 carriers; it computes no
min(), no final capacity, no order size, no allocation, and no exposure. Runs no batch, fetches no
endpoint, builds no engine, edits no runtime code, and asserts no runtime module exists.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_capacity_constraint_evidence_boundary_implementation_planning.md")
RUNTIME = os.path.join(REPO, "phase5", "capacity_constraint_evidence_boundary.py")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"
CARRIER_CONTRACT_START = "<!-- CARRIER-CONTRACT-START -->"
CARRIER_CONTRACT_END = "<!-- CARRIER-CONTRACT-END -->"

EXPECTED_COMPONENT = "phase5_capacity_constraint_evidence_boundary"

# The exact pinned factory name for the future carrier-only slice.
FACTORY_NAME = "make_capacity_constraint_evidence_context"

# The exact closed field set for CapacityConstraintEvidenceContext (exactly these, no others).
CARRIER_FIELD_SET = [
    "component_name",
    "boundary_version",
    "post_profitability_source_contract",
    "post_profitability_source_artifact",
    "post_profitability_source_field",
    "venue_readiness_source_contract",
    "venue_readiness_source_artifact",
    "venue_readiness_source_field",
    "liquidity_capacity_source_contract",
    "liquidity_capacity_source_artifact",
    "liquidity_capacity_source_field",
    "capital_margin_source_contract",
    "capital_margin_source_artifact",
    "capital_margin_source_field",
]

# Fields/tokens the carrier must explicitly NOT store (computed / status / runtime tokens).
CARRIER_EXCLUDED_FIELDS = [
    "join_status", "binding_status", "identity_status", "freshness_status", "unit_status",
    "audited_evidence_count", "observed_size", "available_capacity", "required_capital",
    "final_capacity", "computed_min", "order_size", "allocation", "exposure", "balance",
    "route", "reservation", "wallet",
]

# The exactly-four source carriers Slice 0 consumes (already implemented Phase 5 carriers).
SOURCE_CARRIERS = [
    "PostProfitabilityEvidenceEnvelope",
    "VenueInstrumentReadinessStateContext",
    "LiquidityCapacityEvidenceContext",
    "CapitalMarginEvidenceContext",
]

# Other Phase 5 carriers that must NOT be named as sources (enforces "exactly four").
NON_SOURCE_CARRIERS = [
    "GrossEdgeObservation",
    "GrossEdgeSourceResult",
    "ObservableCostObservation",
    "ObservableCostSourceResult",
    "ObservableCostValidityContext",
    "NetEdgeCalculationResult",
    "ProfitabilityThresholdPolicyContext",
    "PreNetEdgeCalculationInput",
]

# External input-schema record-identity / provenance tokens that MUST NOT be declared as carrier
# source fields (they live only in phase5/const.py for the input-provenance preflight).
FORBIDDEN_CARRIER_FIELDS = ["batch_id", "run_id", "observation_id", "provenance_status"]

PINNED_PHRASES = [
    "NO ORDER EXISTS",
    "no order size, no allocation, no routing, no execution preparation",
    "no Phase 6 bridge",
    "not an actionable decision engine",
    "no sizing",
    "no exposure runtime",
    "no balance runtime",
    "no wallet reservation",
    "no paper/live readiness",
    "no min()",
    "no final capacity",
]

CAPACITY_REASON_TOKENS = [
    "CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE",
    "CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE",
    "CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE",
    "CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH",
    "CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH",
    "CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE",
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
    "is complete", "is perfect", "is now safe", "fully complete", "the last piece",
]


def _read():
    assert os.path.isfile(DOC), f"capacity-constraint planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


# ---- existence / framing ----

def test_doc_exists():
    assert _read().strip(), "planning doc is empty"


def test_read_only_planning_framing():
    low = _read().lower()
    assert "implementation-planning only, not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_constitutional_safety_barrier_airgap_framing():
    low = _read().lower()
    assert "constitutional safety barrier" in low
    assert "airgap" in low


def test_flat_phase5_naming_no_phase_5_5():
    text = _read()
    assert EXPECTED_COMPONENT in text
    assert "phase5.5" not in text.lower()
    assert "phase 5.5" not in text.lower()
    assert "phase6" not in text.lower().replace("phase 6 bridge", "")  # "no Phase 6 bridge" is allowed


def test_component_and_context_names_present():
    text = _read()
    assert "CapacityConstraintEvidenceBoundary" in text
    assert "CapacityConstraintEvidenceContext" in text


# ---- source carriers (exactly four) ----

def test_exactly_four_source_carriers_named():
    text = _read()
    for c in SOURCE_CARRIERS:
        assert c in text, f"source carrier missing: {c}"
    for c in NON_SOURCE_CARRIERS:
        assert c not in text, f"non-source carrier must not be named as a source: {c}"


def test_forbidden_invented_carrier_fields_absent():
    # The four external record-identity / provenance tokens must never be DECLARED as carrier
    # fields. They may appear only inside the explicit carrier-contract exclusions block, which
    # pins them as never-stored. Anywhere outside that block they remain forbidden.
    text = _read()
    body = _strip_block(text, CARRIER_CONTRACT_START, CARRIER_CONTRACT_END)
    for f in FORBIDDEN_CARRIER_FIELDS:
        assert f not in body, f"forbidden invented carrier field declared outside exclusions: {f}"


# ---- slice 0 structural-join scope ----

def test_slice0_structural_multi_source_join_only():
    low = _read().lower()
    assert "slice 0" in low
    assert "structural multi-source join" in low
    assert "auditor" in low


def test_passive_context_has_no_computed_capacity():
    low = _read().lower()
    assert "no computed capacity value" in low


# ---- binding rules over proven-present fields ----

def test_binding_rules_documented():
    text = _read()
    low = text.lower()
    # 4-way identity convergence
    assert "venue" in low and "instrument_id" in low and "base_asset" in low and "quote_asset" in low
    assert "identity convergence" in low
    # side binding only PostProfitability <-> CapitalMargin
    assert "side binding" in low
    # size binding across the three size-bearing carriers
    assert "size binding" in low
    # unit binding
    assert "unit binding" in low
    # time/freshness binding only for liquidity/capital epoch+tolerance fields
    assert "time" in low and ("freshness" in low or "staleness" in low)
    assert "liquidity_snapshot_epoch_ms" in text
    assert "evidence_epoch_tolerance_ms" in text
    assert "required_capital_epoch_ms" in text
    assert "available_free_capital_snapshot_epoch_ms" in text
    assert "observed_at_epoch_ms" in text


# ---- fail-closed taxonomy + reason vocabulary ----

def test_fail_closed_branch_priority_and_taxonomy():
    low = _read().lower()
    assert "fail closed" in low or "fail-closed" in low
    assert "branch priority" in low
    for term in ["missing", "malformed", "stale", "identity-mismatch", "unit-mismatch", "undefined"]:
        assert term in low, f"blocked taxonomy term missing: {term}"


def test_reason_tokens_pinned_doc_only():
    text = _read()
    for token in CAPACITY_REASON_TOKENS:
        assert token in text, f"capacity reason token missing: {token}"
        assert token.startswith("CAPACITY_CONSTRAINT_"), token


def test_blocked_reuses_existing_packet_semantics_no_new_schema():
    text = _read()
    low = text.lower()
    assert "BlockedPacket" in text
    assert "BLOCKED_NEEDS_EVIDENCE" in text
    assert "no new packet" in low


# ---- pinned no-go phrases ----

def test_pinned_no_go_phrases_present():
    text = _read()
    for phrase in PINNED_PHRASES:
        assert phrase in text, f"pinned no-go phrase missing: {phrase!r}"


def test_distinguishes_passive_constraint_from_exposure_and_balance_runtime():
    low = _read().lower()
    assert "passive" in low
    assert "exposure runtime" in low
    assert "balance runtime" in low


# ---- marker blocks ----

def test_no_claims_block_present():
    text = _read()
    assert NO_CLAIMS_START in text and NO_CLAIMS_END in text


def test_prohibited_outputs_block_present():
    text = _read()
    assert PROHIBITED_OUT_START in text and PROHIBITED_OUT_END in text


def test_marker_pairs_balanced():
    text = _read()
    assert text.count(NO_CLAIMS_START) == text.count(NO_CLAIMS_END) == 1
    assert text.count(PROHIBITED_OUT_START) == text.count(PROHIBITED_OUT_END) == 1
    assert text.count(FRAMING_START) == text.count(FRAMING_END) == 1


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


# ---- charter amendment: carrier-only slice, factory, closed field set ----

def test_carrier_contract_block_present_and_balanced():
    text = _read()
    assert text.count(CARRIER_CONTRACT_START) == text.count(CARRIER_CONTRACT_END) == 1


def test_carrier_only_implementation_slice_pinned():
    low = _read().lower()
    assert "carrier-only implementation slice" in low
    assert "tdd sequencing unit" in low
    # the carrier-only slice does not authorize the Slice 0 join auditor / gate / preflight
    assert "not authorization for the slice 0" in low
    assert "gate" in low and "preflight" in low
    # not a bridge, not a downstream component
    assert "no phase 6 bridge" in low
    assert "not a downstream component" in low


def test_factory_name_and_signature_pinned():
    text = _read()
    low = text.lower()
    assert FACTORY_NAME in text, f"factory name not pinned: {FACTORY_NAME}"
    assert "keyword-only" in low
    assert "direct construction" in low and "blocked" in low
    assert "verbatim" in low
    assert "non-empty" in low and "non-whitespace" in low
    assert "exact str" in low or "exactly str" in low
    assert "no implicit coercion" in low or "no coercion" in low


def test_carrier_closed_field_set_pinned_exactly():
    text = _read()
    for f in CARRIER_FIELD_SET:
        assert f in text, f"closed carrier field missing: {f}"
    low = text.lower()
    assert "exactly" in low
    assert "fourteen" in low or "14" in text
    assert "and no others" in low
    # audited_evidence_count must NOT be a stored carrier field (allowed only in exclusions block)
    body = _strip_block(text, CARRIER_CONTRACT_START, CARRIER_CONTRACT_END)
    assert "audited_evidence_count" not in body


def test_exactly_four_rule_is_invariant_not_stored_data():
    low = _read().lower()
    assert "doc/test invariant" in low
    assert "not stored data" in low


def test_carrier_excludes_status_and_computed_fields():
    text = _read()
    for f in CARRIER_EXCLUDED_FIELDS:
        assert f in text, f"carrier exclusion not documented: {f}"
    assert "*_status" in text


def test_repr_exposure_pinned_to_two_fields_only():
    text = _read()
    low = text.lower()
    assert "component_name" in text and "boundary_version" in text
    assert "repr" in low
    assert "only" in low


def test_carrier_safety_properties_pinned():
    low = _read().lower()
    for prop in ["frozen", "repr-safe", "anti-truthiness", "anti-coercion", "factory-only"]:
        assert prop in low, f"carrier safety property missing: {prop}"
    assert "no env" in low
    for src in ["config", "files", "db", "network", "time"]:
        assert src in low, f"missing no-IO source: {src}"
    for verb in ["derives", "computes", "compares", "audits", "validates", "infers", "decides"]:
        assert verb in low, f"missing nothing-verb: {verb}"


# ---- runtime must remain absent (planning batch only) ----

def test_runtime_module_absent():
    assert not os.path.isfile(RUNTIME), \
        "planning batch must not create phase5/capacity_constraint_evidence_boundary.py"
