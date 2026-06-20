"""phase6_1/s2_identity_wiring_candidate.py — Phase 6.1 S2 identity wiring evidence carrier.

A passive, stateless, per-envelope wiring client defined by
``docs/handoff/phase6_1_s2_identity_wiring_boundary_contract_charter.md``. It consumes exactly one frozen
``OptionBEventEnvelope`` from the ratified, frozen Option-B reader (as a client — it never modifies,
widens, or reshapes the reader) and returns exactly one strictly immutable ``S2IdentityWiringCandidate``.

Contract honoured here:

  - **Single unpacking point.** This client is the one place an ``OptionBEventEnvelope`` is opened; its
    three parts are handed onward and the envelope is not re-opened downstream.
  - **Explicit normalization boundary.** ``parsed_payload_or_local_halt`` is forwarded onward UNCHANGED,
    by identity. The client performs NO payload mapping, coercion, defaulting, unit math, venue logic,
    freshness checks, cost interpretation, scoring, or business/semantic judgement.
  - **Opaque Silver pair.** ``artifact_locator`` and ``physical_record_position`` are copied through from
    the envelope intact and opaque — never hashed, concatenated, cast, derived, fingerprinted, or
    collapsed into a synthetic key. They remain two separate inherited facts carried by reference.
  - **Pass/halt symmetry.** A parsed-payload envelope and an ``OptionBLocalParseHalt`` envelope are
    handled by the SAME function; a local parse-halt preserves the same locator + position and is never
    dropped or reclassified.

This slice produces runtime-carried S2 identity evidence; it does NOT declare S2 fully UNBLOCKED, and it
defines no durable identity, no log schema, and no S4 halt materialisation. It is identity-blind: no
clock, no randomness, no hashing, no filesystem, no identity minting of any kind.
"""
from dataclasses import dataclass

from phase6_1.option_b_event_stream_reader import OptionBEventEnvelope


S2_IDENTITY_WIRING_CANDIDATE_COMPONENT_NAME = "phase6_1_s2_identity_wiring_candidate"


@dataclass(frozen=True, slots=True)
class S2IdentityWiringCandidate:
    """Immutable per-envelope S2 identity evidence carrier.

    ``forwarded_payload_or_local_halt`` is the envelope's payload (parsed payload or
    ``OptionBLocalParseHalt``), forwarded onward unchanged by identity. ``artifact_locator`` and
    ``physical_record_position`` are the opaque Silver pair, carried verbatim from the envelope. This is
    runtime-carried evidence only — not a durable/final identity and not a declaration that S2 is
    UNBLOCKED.
    """

    forwarded_payload_or_local_halt: object
    artifact_locator: object
    physical_record_position: object


def route_option_b_envelope_to_s2_identity_candidate(*, envelope):
    """Map one frozen :class:`OptionBEventEnvelope` to one :class:`S2IdentityWiringCandidate`.

    The envelope is opened exactly once; its payload is forwarded onward by identity (no normalization)
    and its Silver pair ``(artifact_locator, physical_record_position)`` is carried through intact and
    opaque. Pass and local-halt envelopes are handled identically. A non-envelope input fails fast
    (exact-type boundary discipline); nothing is minted, derived, or mutated.
    """
    if type(envelope) is not OptionBEventEnvelope:
        raise TypeError(
            "route_option_b_envelope_to_s2_identity_candidate requires an exact OptionBEventEnvelope"
        )
    return S2IdentityWiringCandidate(
        forwarded_payload_or_local_halt=envelope.parsed_payload_or_local_halt,
        artifact_locator=envelope.artifact_locator,
        physical_record_position=envelope.physical_record_position,
    )
