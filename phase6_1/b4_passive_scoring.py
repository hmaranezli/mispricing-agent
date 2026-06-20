"""phase6_1/b4_passive_scoring.py — Phase 6.1 B4 passive scoring runtime.

A pure, stateless, deterministic passive boundary that packages **already-computed** passive pipeline
outputs into one `ObservationScoreRecord` for the S1 in-memory reference sink. Built under
`docs/handoff/phase6_1_b4_passive_scoring_planning_charter.md` and
`docs/handoff/phase6_1_b4_score_payload_field_shape_charter.md`.

`build_passive_observation_record` consumes the frozen pass handoff (`PassiveShadowInput`, which already
references the Phase 5 net-edge result by identity) plus the ratified `S2IdentityWiringCandidate` identity
evidence, and constructs an `ObservationScoreRecord`. It **recomputes no Phase 5 math** — it reads
already-computed values and packages them passively. It mints no identity, emits no actionability, applies
no threshold or ranking, and is **not** the sink (it produces; S1 records).

Contract honoured here:

  - Identity is placed **only** in the envelope `identity_evidence` slot (the opaque Silver pair stays
    indivisible and external to the payload); it is never copied, aliased, derived, or promoted into
    `family_payload`.
  - `family_payload` is passive diagnostic content under the five conceptual obligations: a passive
    magnitude (the already-computed net-edge value, read verbatim), an opaque by-reference basis link (the
    frozen result, basis provenance — not identity), a passive inputs summary, opaque upstream unit
    context, and a non-versioned family descriptor for replay explainability.
  - `provenance_timestamp` is a timestamp only; `opaque_cost_context` is carried opaquely (Cell-3
    deferred). No randomness, clock, network, filesystem, external state, or hidden state.
"""
from phase6_1.passive_shadow_input import PassiveShadowInput
from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate
from phase6_1.s1_in_memory_observation_sink import ObservationScoreRecord


B4_PASSIVE_SCORING_COMPONENT_NAME = "phase6_1_b4_passive_scoring"

# A passive, non-versioned family descriptor for replay explainability (not a versioned/runtime id).
_FAMILY_DESCRIPTOR = "passive_net_edge_diagnostic"


def build_passive_observation_record(*, pass_handoff, identity_evidence, opaque_cost_context):
    """Package one frozen `PassiveShadowInput` pass handoff plus its `S2IdentityWiringCandidate` identity
    evidence into one `ObservationScoreRecord` for the S1 sink.

    Already-computed passive values are read and packaged verbatim — no Phase 5 recomputation, no
    threshold, no ranking, no actionability. Identity is placed only in the envelope slot; the cost
    context is carried opaquely. A non-`PassiveShadowInput` handoff or non-`S2IdentityWiringCandidate`
    evidence fails fast (exact-type boundary discipline). Pure and deterministic: same input, same record.
    """
    if type(pass_handoff) is not PassiveShadowInput:
        raise TypeError(
            "build_passive_observation_record requires an exact PassiveShadowInput pass handoff"
        )
    if type(identity_evidence) is not S2IdentityWiringCandidate:
        raise TypeError(
            "build_passive_observation_record requires an exact S2IdentityWiringCandidate as identity evidence"
        )

    result = pass_handoff.net_edge_calculation_result
    family_payload = {
        "passive_score_magnitude": result.net_edge_value,
        "score_basis_reference": result,
        "score_inputs_summary": (pass_handoff.source_venue, pass_handoff.source_pair),
        "score_unit_context": result.net_edge_unit,
        "score_family_descriptor": _FAMILY_DESCRIPTOR,
    }
    return ObservationScoreRecord(
        identity_evidence=identity_evidence,
        observation_kind="SCORE",
        provenance_timestamp=pass_handoff.observed_at_epoch_ms,
        opaque_cost_context=opaque_cost_context,
        family_payload=family_payload,
    )
