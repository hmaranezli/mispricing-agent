"""phase6_1/option_b_event_stream_reader.py — Phase 6.1 Option-B event-stream reader.

A dumb, blind, deterministic physical parser for the pinned Option-B JSONL-style line-oriented event
artifact, where **one physical line = exactly one logical event**. Built under
``docs/handoff/phase6_1_option_b_reader_io_design_charter.md`` (and the field-shape / contract charters
it references). It is a separate boundary from the frozen single-artifact snapshot reader
(``b1_replay_depth_artifact_reader.py``), which it neither touches nor retrofits.

Contract (architecture pins honoured here):

  - **Tripartite envelope.** Per physical line the reader yields exactly one immutable
    ``OptionBEventEnvelope`` carrying ``(parsed_payload_or_local_halt, artifact_locator,
    physical_record_position)``. The envelope is not a dict and never travels as a bare payload.
  - **Blind locator.** ``artifact_locator`` is caller-supplied and carried verbatim, by identity. The
    reader never derives, normalises, joins, absolutises, parses, validates, or mutates it (no os /
    pathlib / sys path logic anywhere).
  - **Intrinsic IO position.** ``physical_record_position`` is read from the active stream's own
    position mechanics (``stream.tell()`` captured before each ``readline()``). It is never a global /
    application / persisted / cross-file counter, and never an ``enumerate`` index.
  - **Dumb parser.** The reader structurally parses one physical line into a payload via ``json.loads``
    and performs NO semantic/business validation (no price, unit, venue, cost, freshness, or scoring
    judgement of any kind).
  - **Local halt restraint.** A physical line that is not valid JSON yields an immutable
    ``OptionBLocalParseHalt`` in the envelope's payload slot — never raised, never silently dropped —
    preserving the medium identity (locator + position) of the bad line. This is a *local* IO halt only;
    it designs no S4 global halt schema and no shadow-log materialisation.
  - **Medium vs payload.** Identity is medium metadata; the reader never reads identity from, or writes
    it into, the payload. Payload-authored identity fields (event_id/row_offset/uuid/…) are left inside
    the payload and are never promoted to the envelope identity.

No network, no environment, no clock, no randomness, no filesystem path logic; the only IO is over the
caller-supplied in-memory text stream.
"""
import json
from dataclasses import dataclass


OPTION_B_EVENT_STREAM_READER_COMPONENT_NAME = "phase6_1_option_b_event_stream_reader"


@dataclass(frozen=True, slots=True)
class OptionBLocalParseHalt:
    """Immutable local IO-halt marker for a physical line that could not be structurally parsed.

    Carries the malformed physical line verbatim and uninterpreted. It is a *local* parse halt only —
    it is NOT an S4 materialised halt and defines no shadow-log schema.
    """

    raw_line: object


@dataclass(frozen=True, slots=True)
class OptionBEventEnvelope:
    """Immutable tripartite envelope emitted once per physical line.

    ``parsed_payload_or_local_halt`` is either the structurally-parsed payload (on a valid line) or an
    :class:`OptionBLocalParseHalt` (on a malformed line). ``artifact_locator`` and
    ``physical_record_position`` are medium metadata carried verbatim from the caller / the active
    stream; they are never sourced from the payload.
    """

    parsed_payload_or_local_halt: object
    artifact_locator: object
    physical_record_position: object


def read_option_b_event_stream(*, text_stream, artifact_locator):
    """Yield one immutable :class:`OptionBEventEnvelope` per physical line of ``text_stream``.

    ``text_stream`` is any caller-supplied text stream exposing ``tell()`` / ``readline()`` (e.g.
    ``io.StringIO``); the reader opens nothing and discovers no paths. ``artifact_locator`` is an opaque
    caller-supplied medium identity, carried verbatim into every envelope.

    The reader is a generator: it reads exactly one physical line per step, captures the stream's own
    start-of-record position before reading, structurally parses the line, and emits the tripartite
    envelope. A line that is not valid JSON becomes an :class:`OptionBLocalParseHalt` payload (never
    raised, never dropped). No semantic validation is performed.
    """
    while True:
        physical_record_position = text_stream.tell()
        line = text_stream.readline()
        if line == "":
            break
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = OptionBLocalParseHalt(raw_line=line)
        yield OptionBEventEnvelope(
            parsed_payload_or_local_halt=payload,
            artifact_locator=artifact_locator,
            physical_record_position=physical_record_position,
        )
