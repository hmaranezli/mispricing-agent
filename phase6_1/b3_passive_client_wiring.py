"""phase6_1/b3_passive_client_wiring.py — Phase 6.1 Master B3 passive client wiring.

Implements ONLY `wire_passive_shadow_input`, a stateless, synchronous, deterministic dumb-pipe client.
Authored under `docs/handoff/phase6_1_master_b3_client_wiring_charter.md`.

Master B3 here is a thin adapter: it reads, by exact field access, the passive inputs the producer
needs from B2 normalized evidence, performs one value-preserving lexical adaptation (the canonical
unsigned-int provenance epoch string -> int), calls `produce_passive_shadow_input` exactly once, and
returns the producer's output unchanged (by identity) — whether a pass handoff or a defensive carrier.

It derives nothing, scores nothing, logs nothing, keeps no state, reads no clock, and never swallows a
failure. It talks to the producer, not to Phase 5. Exact-type discipline only.
"""
from phase6_1.b2_normalization_contract import NormalizedEvidenceMaterial
from phase6_1.passive_producer import produce_passive_shadow_input

B3_PASSIVE_CLIENT_WIRING_COMPONENT_NAME = "phase6_1_b3_passive_client_wiring"
B3_PASSIVE_CLIENT_WIRING_BOUNDARY_VERSION = "phase6_1.b3_passive_client_wiring.v0"

# The B2 binding role that carries the gross-edge magnitude/unit (a B2 structural discriminator).
_GROSS_EDGE_BINDING_ROLE = "GROSS_EDGE"


class B3PassiveClientWiringError(TypeError):
    """Raised when B3 receives evidence it cannot pipe through (wrong type, missing/ambiguous gross
    binding, or a non-canonical provenance epoch). B3 fails fast — it never silently drops or hides."""


def wire_passive_shadow_input(*, normalized_evidence_material, cost_validity_contexts):
    """Pipe one passive B2 evidence frame to the producer and return the producer output unchanged.

    ``normalized_evidence_material`` must be an exact :class:`NormalizedEvidenceMaterial`; B3 reads its
    one ``GROSS_EDGE`` binding's magnitude/unit and the raw snapshot's venue/pair/observed-epoch by
    exact field access (no derivation). ``cost_validity_contexts`` is forwarded verbatim by identity
    (the minimal path supplies a zero-valued cost context; real-cost assembly is a separate, deferred
    concern). The producer's return value is returned as-is — never unpacked, copied, mutated, wrapped,
    or dropped.
    """
    if type(normalized_evidence_material) is not NormalizedEvidenceMaterial:
        raise B3PassiveClientWiringError(
            "normalized_evidence_material must be an exact NormalizedEvidenceMaterial, not "
            + type(normalized_evidence_material).__name__
        )

    raw = normalized_evidence_material.raw_snapshot
    bindings = normalized_evidence_material.normalized_field_bindings

    gross_bindings = tuple(
        b for b in bindings if b.binding_role == _GROSS_EDGE_BINDING_ROLE
    )
    if len(gross_bindings) != 1:
        raise B3PassiveClientWiringError(
            "exactly one GROSS_EDGE binding is required to wire the gross magnitude"
        )
    magnitude = gross_bindings[0].unit_bound_magnitude

    # Value-preserving lexical adaptation only: a canonical non-negative integer string -> int.
    # No float, no datetime, no timezone, no clock, no temporal branching. Fail fast on a bad shape.
    epoch_text = raw.observed_at_epoch_ms
    if type(epoch_text) is not str or not epoch_text.isdigit():
        raise B3PassiveClientWiringError(
            "observed_at_epoch_ms must be a plain non-negative integer string"
        )
    observed_at_epoch_ms = int(epoch_text)

    return produce_passive_shadow_input(
        gross_edge_value=magnitude.magnitude,
        gross_edge_unit=magnitude.unit,
        cost_validity_contexts=cost_validity_contexts,
        source_venue=raw.venue,
        source_pair=raw.pair,
        observed_at_epoch_ms=observed_at_epoch_ms,
    )
