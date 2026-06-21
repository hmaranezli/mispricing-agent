"""phase6_1/s5_runner.py — Phase 6.1 S5 in-memory runner (dumb synchronous coordinator).

A strictly synchronous, single-threaded, deterministic coordinator that drives one passive observation
run end-to-end IN MEMORY: the frozen Option-B reader -> S2 identity wiring -> {pass path | halt path} ->
the S1 in-memory reference sink, one record at a time, to natural stream exhaustion. Built under the S5
Runner in-memory orchestration TDD slice.

S5 is a dumb coordinator: it hands objects to frozen components and routes their outputs by EXACT TYPE.
It manufactures no provenance, binding labels, identity, payload fields, timestamps, positions, or context
providers; it carries the caller-supplied passive contexts unchanged. It performs no payload/business
inspection (no magnitude/unit/venue/pair/edge/cost reading), no ranking/priority, and treats the SCORE
and HALT families as equal peers — neither dropped, reordered, or prioritized.

Dispatch (structural carrier type only):
  - the S2 identity evidence's forwarded payload is an ``OptionBLocalParseHalt`` -> materialized by S4
    into an ``ObservationHaltRecord``;
  - otherwise the parsed payload flows pass-path (B2 ingestion -> B2 normalizer -> Cell-3 zero-cost
    source -> B3) and, on a ``PassiveShadowInput`` pass handoff, B4 builds an ``ObservationScoreRecord``;
  - a returned ratified ``BlockedPacket`` carrier is materialized by S4 as a HALT peer;
  - any other returned output is an unexpected coordinator fault and HARD-FAILS.

No self-healing: no retry, reread, repair, fallback, default, payload/adapter synthesis, normalization,
or exception swallowing inside S5. Raw component exceptions (TypeError/KeyError/ValueError/... and any
unexpected exception) propagate unwrapped as hard fail-fast — they are NEVER converted into S4 halts; only
ratified structural halt carriers reach S4. Natural reader exhaustion is a passive clean stop: no synthetic
EOF record, no halt, no readiness marker, no reconnect, no polling. Outputs go only to the caller-supplied
S1 in-memory reference sink (no file, no database, no on-disk medium, and no re-encoding). Single
caller-supplied contexts only — S5 holds no per-event context map and runs no key-to-context selection.
"""
from phase6_1.option_b_event_stream_reader import (
    read_option_b_event_stream,
    OptionBLocalParseHalt,
)
from phase6_1.s2_identity_wiring_candidate import route_option_b_envelope_to_s2_identity_candidate
from phase6_1.b2_pass_path_ingestion import ingest_pass_path_snapshot_record
from phase6_1.b2_replay_normalization import normalize_replay_snapshot_to_evidence_material
from phase6_1.cell3_passive_cost_context_source import build_passive_zero_cost_validity_contexts
from phase6_1.b3_passive_client_wiring import wire_passive_shadow_input
from phase6_1.b4_passive_scoring import build_passive_observation_record
from phase6_1.s4_halt_materialization import materialize_passive_halt_record
from phase6_1.passive_shadow_input import PassiveShadowInput
from phase5.blocked_result_boundary import BlockedPacket


S5_RUNNER_COMPONENT_NAME = "phase6_1_s5_runner"


class S5RunnerUnexpectedOutputError(RuntimeError):
    """Raised when the passive client wiring returns an output that is neither an exact pass handoff
    (``PassiveShadowInput``) nor a ratified structural halt carrier (``BlockedPacket``). S5 never drops,
    never wraps it into an S4 halt, and never self-heals — an unexpected coordinator output hard-fails."""


def run_in_memory_shadow_pipeline(
    *,
    text_stream,
    artifact_locator,
    market_provenance_context,
    gross_edge_binding_label_context,
    evidence_epoch_tolerance_ms,
    observation_sink,
):
    """Synchronously drive one passive observation run to natural EOF, recording into ``observation_sink``.

    For each physical line the frozen reader yields one envelope; S2 wires it to one identity-evidence carrier;
    S5 routes by exact carrier type to the equal-peer HALT or SCORE family and records the result. The
    caller supplies the single passive ``market_provenance_context`` / ``gross_edge_binding_label_context``
    (used for the pass event) and the ``observation_sink``; S5 manufactures nothing. Returns ``None`` —
    all output is appended to the supplied sink.
    """
    for envelope in read_option_b_event_stream(
        text_stream=text_stream, artifact_locator=artifact_locator
    ):
        identity_candidate = route_option_b_envelope_to_s2_identity_candidate(envelope=envelope)
        forwarded = identity_candidate.forwarded_payload_or_local_halt

        # Halt peer: a ratified structural local-parse-halt carrier, routed to S4 by exact type.
        if type(forwarded) is OptionBLocalParseHalt:
            observation_sink.record_observation(
                materialize_passive_halt_record(
                    halt_source=forwarded,
                    identity_evidence=identity_candidate,
                    opaque_cost_context=None,
                )
            )
            continue

        # Pass peer: hand the parsed payload through the frozen pass path. S5 inspects no payload field.
        raw_snapshot = ingest_pass_path_snapshot_record(
            parsed_payload=forwarded,
            market_provenance_context=market_provenance_context,
            gross_edge_binding_label_context=gross_edge_binding_label_context,
        )
        normalized_evidence_material = normalize_replay_snapshot_to_evidence_material(
            raw_snapshot=raw_snapshot,
            evidence_epoch_tolerance_ms=evidence_epoch_tolerance_ms,
        )
        cost_validity_contexts = build_passive_zero_cost_validity_contexts()
        pass_or_carrier = wire_passive_shadow_input(
            normalized_evidence_material=normalized_evidence_material,
            cost_validity_contexts=cost_validity_contexts,
        )

        if type(pass_or_carrier) is PassiveShadowInput:
            observation_sink.record_observation(
                build_passive_observation_record(
                    pass_handoff=pass_or_carrier,
                    identity_evidence=identity_candidate,
                    opaque_cost_context=cost_validity_contexts,
                )
            )
            continue

        # A returned ratified halt carrier is the equal HALT peer of a score.
        if type(pass_or_carrier) is BlockedPacket:
            observation_sink.record_observation(
                materialize_passive_halt_record(
                    halt_source=pass_or_carrier,
                    identity_evidence=identity_candidate,
                    opaque_cost_context=cost_validity_contexts,
                )
            )
            continue

        raise S5RunnerUnexpectedOutputError(
            "passive client wiring returned neither a PassiveShadowInput nor a ratified halt carrier"
        )
