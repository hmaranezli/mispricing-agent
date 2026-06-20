"""phase6_1/s1_in_memory_observation_sink.py — Phase 6.1 S1 in-memory reference sink.

An instance-bound, pure-Python, append-only **passive** reference sink for S1 contract testing, built
under `docs/handoff/phase6_1_s1_runtime_sink_tdd_planning_charter.md`, the Slice-0B record-model charter,
and the exact-name name-lock exception `docs/handoff/phase6_1_s1_score_record_name_lock_exception_charter.md`.
It lets future B4/S4 work target S1 behaviour **without committing to any physical storage medium** — an
in-memory list is a test substrate here, never a storage-engine choice.

It holds two frozen, passive observation DTO families — `ObservationScoreRecord` and
`ObservationHaltRecord` — over a common logical envelope of five fields: `identity_evidence`,
`observation_kind`, `provenance_timestamp`, `opaque_cost_context`, `family_payload`. `identity_evidence`
is the ratified `S2IdentityWiringCandidate` (the opaque Silver pair, borrowed by reference);
`family_payload` and `opaque_cost_context` stay opaque. The DTOs are pure data: zero methods, zero math,
zero logic.

`S1InMemoryObservationSink.record_observation` admits ONLY an exact `ObservationScoreRecord` or
`ObservationHaltRecord` (exact type, no subclass) whose `identity_evidence` is an exact
`S2IdentityWiringCandidate`, and appends it to an instance-bound list. `snapshot()` returns an immutable
tuple copy; the instance-bound list is never handed out by reference. The sink ranks nothing, decides
nothing, normalises nothing, inspects no payload meaning, and mints no identity (no clock, no randomness,
no hashing, no filesystem, no DB). `provenance_timestamp` is a timestamp only, never an identity.
"""
from dataclasses import dataclass

from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate


S1_IN_MEMORY_OBSERVATION_SINK_COMPONENT_NAME = "phase6_1_s1_in_memory_observation_sink"


@dataclass(frozen=True)
class ObservationScoreRecord:
    """Frozen, passive observation DTO for the future B4 score family.

    Carries the common logical envelope; `family_payload` holds opaque score-family content. This DTO is
    pure data — no methods, no math, no logic. It defines no score behaviour of any kind.
    """

    identity_evidence: object
    observation_kind: object
    provenance_timestamp: object
    opaque_cost_context: object
    family_payload: object


@dataclass(frozen=True)
class ObservationHaltRecord:
    """Frozen, passive observation DTO for the future S4 materialized-halt family.

    Carries the common logical envelope; `family_payload` holds opaque halt-family content. This DTO is
    pure data — no methods, no math, no logic. It defines no halt taxonomy of any kind.
    """

    identity_evidence: object
    observation_kind: object
    provenance_timestamp: object
    opaque_cost_context: object
    family_payload: object


class S1ObservationSinkTypeError(TypeError):
    """Raised when `record_observation` receives anything other than an exact `ObservationScoreRecord`
    or `ObservationHaltRecord` carrying an exact `S2IdentityWiringCandidate` as its identity evidence."""


class S1InMemoryObservationSink:
    """Instance-bound, append-only, passive in-memory reference sink.

    State lives only on the instance (`self._records`); two instances share nothing. The public surface is
    exactly one append (`record_observation`) plus one immutable readback (`snapshot`). The sink records
    and retains; it ranks, filters, decides, normalises, and scores nothing.
    """

    def __init__(self):
        self._records = []

    def record_observation(self, record):
        """Append one exact `ObservationScoreRecord` / `ObservationHaltRecord` whose `identity_evidence`
        is an exact `S2IdentityWiringCandidate`. Anything else fails fast (exact-type boundary discipline;
        no subclass admission). Nothing is derived, normalised, or minted."""
        if type(record) is not ObservationScoreRecord and type(record) is not ObservationHaltRecord:
            raise S1ObservationSinkTypeError(
                "record_observation accepts only an exact ObservationScoreRecord or ObservationHaltRecord"
            )
        if type(record.identity_evidence) is not S2IdentityWiringCandidate:
            raise S1ObservationSinkTypeError(
                "record.identity_evidence must be an exact S2IdentityWiringCandidate"
            )
        self._records.append(record)

    def snapshot(self):
        """Return an immutable tuple copy of the appended observations, in append sequence. The
        instance-bound list is never exposed by reference, so later appends never mutate a prior
        snapshot."""
        return tuple(self._records)
