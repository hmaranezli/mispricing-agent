"""phase6_1/s4_halt_materialization.py — Phase 6.1 S4 halt materializer.

A pure, stateless, deterministic passive boundary that packages one **already-observed** structural halt
carrier into exactly one ``ObservationHaltRecord`` for the S1 in-memory reference sink. Built under
``docs/handoff/phase6_1_s4_exception_routing_halt_materialization_decision_charter.md``,
``docs/handoff/phase6_1_s4_halt_payload_field_shape_charter.md``, and
``docs/handoff/phase6_1_s4_halt_payload_field_shape_narrowing_amendment.md``.

The Mortician Rule binds: ``materialize_passive_halt_record`` records a halt that some upstream component
already observed; it never retries, repairs, self-heals, normalizes, enriches, back-fills, or synthesizes
missing data. It mints no identity, reads no clock, and is **not** the sink (it produces; S1 records).

Contract honoured here:

  - ``halt_source`` must be exactly one authorized carrier type — ``OptionBLocalParseHalt``,
    ``B3PassiveClientWiringError``, or ``BlockedPacket`` — admitted by exact type identity (no subclass,
    no ``isinstance``). It is carried opaquely **by reference** as ``halt_origin_reference``; its
    contents (fields/args/message) are never read, parsed, stringified, or rendered.
  - ``halt_family_descriptor`` is a non-versioned, passive descriptor chosen by a static mapping keyed
    **only** on the exact carrier type — never derived from the object's contents.
  - ``opaque_upstream_context`` is ``None`` here: there is no pre-existing passive upstream context that
    can be borrowed by reference without inspecting the opaque cost context, so nothing is manufactured
    (per the narrowing amendment's safe-fallback rule).
  - Identity is the existing exact ``S2IdentityWiringCandidate``, placed only in the envelope slot; no
    fallback identity is ever minted. ``observation_kind`` is the neutral HALT peer marker;
    ``provenance_timestamp`` is ``None`` (none supplied, nothing manufactured); ``opaque_cost_context``
    is carried opaquely by reference.

No clock, no randomness, no hashing, no filesystem, no network, no identity minting of any kind.
"""
from phase6_1.option_b_event_stream_reader import OptionBLocalParseHalt
from phase6_1.b3_passive_client_wiring import B3PassiveClientWiringError
from phase5.blocked_result_boundary import BlockedPacket
from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate
from phase6_1.s1_in_memory_observation_sink import ObservationHaltRecord


S4_HALT_MATERIALIZATION_COMPONENT_NAME = "phase6_1_s4_halt_materialization"

# Static, non-versioned passive halt-family descriptors keyed ONLY on the exact carrier type. The map
# never inspects an object's contents; lookup is by exact type identity, so a subclass type never matches
# and an unauthorized carrier is rejected.
_HALT_FAMILY_DESCRIPTOR_BY_TYPE = {
    OptionBLocalParseHalt: "passive_local_parse_halt",
    B3PassiveClientWiringError: "passive_client_wiring_halt",
    BlockedPacket: "passive_blocked_packet_halt",
}


def materialize_passive_halt_record(*, halt_source, identity_evidence, opaque_cost_context):
    """Package one already-observed halt carrier into one ``ObservationHaltRecord`` for the S1 sink.

    ``halt_source`` must be an exact authorized carrier (``OptionBLocalParseHalt`` /
    ``B3PassiveClientWiringError`` / ``BlockedPacket``); anything else, including a subclass, fails fast.
    ``identity_evidence`` must be an exact ``S2IdentityWiringCandidate``. The carrier is carried opaquely
    by reference; the family descriptor comes from a static type-keyed mapping; the upstream-context slot
    is ``None`` (nothing manufactured from the opaque cost context). Pure and deterministic: same inputs,
    same record. The Mortician Rule holds — a halt is recorded, never retried or repaired.
    """
    descriptor = _HALT_FAMILY_DESCRIPTOR_BY_TYPE.get(type(halt_source))
    if descriptor is None:
        raise TypeError(
            "materialize_passive_halt_record requires an exact authorized halt carrier "
            "(OptionBLocalParseHalt, B3PassiveClientWiringError, or BlockedPacket)"
        )
    if type(identity_evidence) is not S2IdentityWiringCandidate:
        raise TypeError(
            "materialize_passive_halt_record requires an exact S2IdentityWiringCandidate as identity evidence"
        )

    family_payload = {
        "halt_origin_reference": halt_source,
        "opaque_upstream_context": None,
        "halt_family_descriptor": descriptor,
    }
    return ObservationHaltRecord(
        identity_evidence=identity_evidence,
        observation_kind="HALT",
        provenance_timestamp=None,
        opaque_cost_context=opaque_cost_context,
        family_payload=family_payload,
    )
