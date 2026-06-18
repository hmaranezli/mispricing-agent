"""tests/test_phase5_post_profitability_evidence_envelope_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_post_profitability_evidence_envelope_boundary`
component (docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; pins the single future carrier
`PostProfitabilityEvidenceEnvelope` with factory `make_post_profitability_evidence_envelope`; pins
the exact 15-field carrier field set and the exact 14-parameter keyword-only factory shape; pins the
frozen/repr-safe/anti-truthiness/anti-coercion/factory-only carrier rules; pins exact-type
identity-storage of `NetEdgeCalculationResult`; pins exact-str / canonical-decimal / canonical-int
field rules and their literal regexes; pins the single-provenance-only V1 rule with mixed-source
aggregation deferred and forbidden; pins the no-derivation / no-reach-back rule; bars
parser/inference/default/clock/network/case-unit-normalization; bans `re-attach/recover/reconstruct/
hydrate/enrich/resolve` language; pins the wrong-type/misroute failure taxonomy and the
never-returns-BlockedPacket / never-returns-NoEligibleHaltPacket / never-evaluates-market rule; pins
the explicit non-actionability disclaimer and the banned output names; states no runtime edit, no
implementation file, and no central handoff/memory edit; restates the future-implementation gate;
carries the standard no-claims block; and asserts no forbidden over-claim wording appears anywhere
while forbidden positive-claim phrases appear only inside the explicit framing / no-claims /
prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_post_profitability_evidence_envelope_implementation_planning.md")
PHASE5_DIR = os.path.join(REPO, "phase5")
RUNTIME_FILE = os.path.join(PHASE5_DIR, "post_profitability_evidence_envelope_boundary.py")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

FIELD_SET = [
    "component_name",
    "calculation_result",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "size_unit",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "boundary_version",
]

FACTORY_PARAMS = [
    "calculation_result",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "size_unit",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "boundary_version",
]

BANNED_NAMES = [
    "ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
    "Opportunity", "ExecutionPayload", "Signal", "OrderIntent", "Fillable",
    "Tradable", "Candidate",
]

REATTACH_BANNED_TERMS = [
    "re-attach", "recover", "reconstruct", "hydrate", "enrich", "resolve",
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
    assert os.path.isfile(DOC), f"post-profitability evidence envelope planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "planning doc is empty"


def test_component_name_present():
    assert "phase5_post_profitability_evidence_envelope_boundary" in _read()


def test_future_names_and_factory_shape_pinned():
    text = _read()
    low = text.lower()
    assert "PostProfitabilityEvidenceEnvelope" in text
    assert "make_post_profitability_evidence_envelope" in low
    assert "make_post_profitability_evidence_envelope(" in low
    assert "*," in text, "factory must be pinned as keyword-only"
    for param in FACTORY_PARAMS:
        assert param in low, f"factory parameter missing: {param}"
    assert "this planning task must not implement" in low


def test_carrier_field_set_pinned():
    low = _read().lower()
    for field in FIELD_SET:
        assert field in low, f"carrier field missing: {field}"


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_envelope_role():
    low = _read().lower()
    assert "it is an explicit evidence aggregation carrier only" in low
    assert "it is not a profitability pass certificate" in low
    assert "it is not proof that netedgeprofitabilitygate evaluated the result" in low
    assert "it is not a calculator" in low
    assert "it is not a parser" in low
    assert "it is not an adapter" in low
    assert "it is not a gate" in low
    assert ("it is not a venue/liquidity/balance/sizing/trading/reporting/paper-live component"
            in low)
    assert "it must not decide whether to trade" in low


def test_non_actionability_disclaimer_pinned():
    low = _read().lower()
    disclaimer = (
        "this envelope is an explicit evidence aggregation carrier only. it is not a "
        "profitability pass certificate, not proof that netedgeprofitabilitygate evaluated the "
        "result, not actionable, not trade-ready, not executable, not paper-ready, not "
        "live-ready, and not an order/signal/candidate."
    )
    assert disclaimer in low, "exact non-actionability disclaimer missing"


def test_banned_output_names_pinned():
    text = _read()
    for banned in BANNED_NAMES:
        assert banned in text, f"banned output name must be pinned as prohibited: {banned}"


def test_reattach_language_banned():
    low = _read().lower()
    assert ("this planning artifact bans re-attach, recover, reconstruct, hydrate, enrich, and "
            "resolve language" in low)
    assert "explicitly supplied evidence aggregation only" in low
    for term in REATTACH_BANNED_TERMS:
        assert term in low, f"reattach-family term must be named in the ban: {term}"


def test_carrier_rules_pinned():
    low = _read().lower()
    assert "frozen, repr-safe, anti-truthiness, anti-coercion, factory-only" in low
    assert ("calculation_result must be exact netedgecalculationresult by type(); subclasses and "
            "duck-typed objects are rejected" in low)
    assert "calculation_result must be stored by identity, not copied, unpacked, or serialized" in low
    assert ("all other fields must be exact str, non-empty, non-whitespace; str subclasses are "
            "rejected" in low)
    assert "side is exact str only" in low
    assert "no enum validation" in low
    assert "no semantic interpretation" in low
    assert "size_unit is exact str only; no unit conversion or normalization" in low


def test_numeric_field_regexes_pinned():
    text = _read()
    low = text.lower()
    assert "observed_size must be an unsigned canonical decimal string" in low
    assert "observed_at_epoch_ms must be a canonical unsigned integer string" in low
    assert "staleness_threshold_ms must be a canonical unsigned integer string" in low
    assert r"0|[1-9]\d*(\.\d+)?" in text, "observed_size canonical regex missing"
    assert r"0|[1-9]\d*" in text, "canonical unsigned integer regex missing"


def test_single_provenance_v1_rule_pinned():
    low = _read().lower()
    assert "v1 is single-provenance aggregation only" in low
    assert ("all envelope market topology/size/time fields are asserted to come from the single "
            "explicit source_contract/source_artifact/source_field supplied to the factory" in low)
    assert "mixed-source aggregation is explicitly deferred and forbidden in v1" in low


def test_no_derivation_no_reachback_pinned():
    low = _read().lower()
    assert ("no field may be derived from calculation_result, source_artifact, source_field, or "
            "any upstream object" in low)
    assert "no reach-back to grossedgeobservation" in low


def test_no_parser_inference_default_clock_pinned():
    low = _read().lower()
    assert "do not parse source_artifact or source_field" in low
    assert ("do not infer venue/base/quote/instrument/side/size/time from any other field" in low)
    assert "no defaults" in low
    assert "no clock/time/datetime/now" in low
    assert "no network/api probes" in low
    assert "no case or unit normalization" in low


def test_failure_taxonomy_pinned():
    text = _read()
    low = text.lower()
    assert "PostProfitabilityEvidenceEnvelopeTypeError" in text
    assert "MisroutedHaltCarrierError" in text
    assert ("exact blockedpacket or exact noeligiblehaltpacket passed as calculation_result -> "
            "misroutedhaltcarriererror" in low)
    assert ("wrong type / none / dict / float / duck / subclass calculation_result -> "
            "postprofitabilityevidenceenvelopetypeerror" in low)
    assert ("wrong type / none / dict / float / str subclass / hostile object for string fields "
            "-> postprofitabilityevidenceenvelopetypeerror" in low)
    assert "empty or whitespace string fields -> valueerror" in low
    assert ("malformed observed_size / observed_at_epoch_ms / staleness_threshold_ms -> valueerror"
            in low)
    assert "this component must never return blockedpacket" in low
    assert "this component must never return noeligiblehaltpacket" in low
    assert "this component must never perform market/economic evaluation" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert ("this task does not edit the central handoff/memory file and performs no memory "
            "closeout" in low)


def test_no_implementation_file_or_runtime_symbols():
    assert not os.path.isfile(RUNTIME_FILE), \
        "planning task must not create the runtime envelope module"
    if os.path.isdir(PHASE5_DIR):
        for name in os.listdir(PHASE5_DIR):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(PHASE5_DIR, name), encoding="utf-8") as f:
                src = f.read()
            assert "class PostProfitabilityEvidenceEnvelope" not in src, \
                f"runtime carrier class must not exist yet (found in {name})"
            assert "def make_post_profitability_evidence_envelope" not in src, \
                f"runtime factory must not exist yet (found in {name})"


def test_future_implementation_gate():
    low = _read().lower()
    assert ("future implementation must be separately authorized, component-scoped, offline, "
            "tdd-first, and declared-provenance" in low)
    assert "this planning artifact does not authorize implementation" in low


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no alpha", "no actionability", "no readiness",
                 "no paper readiness", "no live readiness", "no execution readiness",
                 "no safety guarantee", "no data-quality guarantee", "no source-truth guarantee"]:
        assert term in low, f"no-claims term missing: {term}"
    assert ("this envelope is an explicit evidence aggregation only and asserts no tradeable "
            "property" in low)


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
