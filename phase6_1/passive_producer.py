"""phase6_1/passive_producer.py — Phase 6.1 deterministic passive producer.

Implements ONLY `produce_passive_shadow_input`, a deterministic, replay-first, non-actionable
arranger. Authored under `docs/handoff/phase6_1_passive_producer_implementation_charter.md`.

The producer:
  - constructs ONLY the ratified passive socket carriers (PassiveGrossEdgeMagnitude ->
    PassivePreNetEdgeCalculationInput) via their Phase 5 factories; it never builds an actionable
    gross-edge gate carrier and never requires or synthesizes a directional intent;
  - calls ONLY the existing `calculate_net_edge` for the arithmetic (single math source; no new math);
  - on a `NetEdgeCalculationResult`, passes that exact object BY IDENTITY into the already-built
    `make_passive_shadow_input` handoff and returns the resulting `PassiveShadowInput`;
  - on a defensive non-pass carrier (e.g. a `BlockedPacket`), surfaces that exact object by identity
    and does NOT call the handoff factory (the handoff accepts only an exact pass result).

It performs no scoring, no diagnostics, no ranking, no thresholding, no logging, and no calibration.
It reads no clock and computes no temporal policy; any provenance timestamp is carried verbatim into
the handoff as passive evidence and is never interpreted. Exact-type discipline only.
"""
from phase5.net_edge_calculator_boundary import (
    calculate_net_edge,
    NetEdgeCalculationResult,
    make_passive_gross_edge_magnitude,
    make_passive_pre_net_edge_calculation_input,
)
from phase6_1.passive_shadow_input import make_passive_shadow_input

PASSIVE_PRODUCER_COMPONENT_NAME = "phase6_1_passive_producer"
PASSIVE_PRODUCER_BOUNDARY_VERSION = "phase6_1.passive_producer.v0"


def produce_passive_shadow_input(
    *,
    gross_edge_value,
    gross_edge_unit,
    cost_validity_contexts,
    source_venue,
    source_pair,
    observed_at_epoch_ms,
):
    """Arrange one passive net-edge evaluation and return the passive handoff (or a defensive carrier).

    All field validation is delegated to the existing factories: ``make_passive_gross_edge_magnitude``
    (canonical magnitude/unit), ``make_passive_pre_net_edge_calculation_input`` (non-empty exact cost
    context tuple), and ``make_passive_shadow_input`` (provenance + identity-held result). The producer
    derives nothing, re-validates nothing, and performs no arithmetic of its own.
    """
    gross_observation = make_passive_gross_edge_magnitude(
        gross_edge_value=gross_edge_value,
        gross_edge_unit=gross_edge_unit,
    )
    calculation_input = make_passive_pre_net_edge_calculation_input(
        gross_observation=gross_observation,
        cost_validity_contexts=cost_validity_contexts,
    )

    result = calculate_net_edge(calculation_input=calculation_input)

    # Defensive non-pass: surface the exact carrier by identity; never wrap it (the handoff accepts
    # only an exact pass result). Exact-type discrimination, no isinstance.
    if type(result) is not NetEdgeCalculationResult:
        return result

    # Pass result: identity pass-through into the handoff — no unpack/copy/mutate/re-instantiate.
    return make_passive_shadow_input(
        net_edge_calculation_result=result,
        source_venue=source_venue,
        source_pair=source_pair,
        observed_at_epoch_ms=observed_at_epoch_ms,
    )
