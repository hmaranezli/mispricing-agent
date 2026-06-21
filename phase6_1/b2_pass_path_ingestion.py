"""phase6_1/b2_pass_path_ingestion.py — Phase 6.1 B2 pass-path ingestion mapping.

A pure, stateless, deterministic mapping that consumes EXACTLY three ratified passive inputs — one
Option-B ``parsed_payload`` mapping, one :class:`MarketProvenanceContext`, and one
:class:`GrossEdgeBindingLabelContext` — and assembles ONE exact ``PublicRawSnapshotRecord`` through the
frozen ``make_public_raw_snapshot_record``. Built under
``docs/handoff/phase6_1_b2_pass_path_ingestion_mapping_contract_charter.md``.

Mapping facts (zero fabrication):
  - Record-level provenance and market identity (``source_artifact``, record-level ``source_field``,
    ``base_asset``, ``quote_asset``, ``instrument_id``, ``venue_scope``, ``venue_buy``, ``venue_sell``,
    ``retrieval_epoch_ms``, ``raw_snapshot_identity``) come ONLY from ``MarketProvenanceContext``.
  - ``venue``, ``pair`` and ``observed_at_epoch_ms`` come ONLY from the payload.
  - ``field_payload`` is exactly ONE GROSS_EDGE binding entry: its ``magnitude``/``unit`` come from the
    payload, its ``normalized_field_name`` and binding-level ``source_field`` come ONLY from
    ``GrossEdgeBindingLabelContext`` (the binding-level ``source_field`` is NEVER aliased from the
    record-level one), and ``binding_role`` is the structural constant ``"GROSS_EDGE"``.

Precision-safe seal: the gross magnitude and unit are carried as verbatim strings; a non-string (e.g. a
numeric) magnitude HALTS structurally and is NEVER cast, rounded, scaled, or reformatted. The only
permitted numeric carriage is the lossless non-negative-int -> canonical-string for
``observed_at_epoch_ms``; a float or negative value HALTS.

This boundary builds NO COST binding and invents no cost placeholder (COST/Cell-3 stay separately gated);
it never imports, inspects, copies, or falls back to the separate S2 system-identity plane
(``raw_snapshot_identity`` is Market Identity from the provenance context only); and it contains no loop,
stream iteration, retry, repair, self-heal, EOF/cursor handling, storage, or pipeline trigger. Any
required source absent from the three inputs is a structural ingestion halt — never a fabricated value.
The frozen B2 anti-copy lock (observed != str(retrieval)) is enforced downstream and surfaced, not repaired.
"""
from phase6_1.b2_normalization_contract import make_public_raw_snapshot_record
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext


B2_PASS_PATH_INGESTION_COMPONENT_NAME = "phase6_1_b2_pass_path_ingestion"


class B2PassPathIngestionTypeError(TypeError):
    """Raised when an input has the wrong exact type (non-dict payload, wrong context carrier, a
    non-string magnitude/unit/venue/pair, or a non-(str|non-negative-int) observed timestamp)."""


class B2PassPathIngestionValueError(ValueError):
    """Raised for a correctly-typed but structurally-incomplete input: a missing required payload key or
    a negative observed timestamp integer. No value is ever fabricated to fill the gap."""


def ingest_pass_path_snapshot_record(
    *, parsed_payload, market_provenance_context, gross_edge_binding_label_context
):
    """Assemble one exact ``PublicRawSnapshotRecord`` from the three ratified passive inputs.

    ``parsed_payload`` must be an exact ``dict`` carrying the keys ``gross_magnitude``, ``unit``,
    ``venue``, ``pair`` (each a verbatim string) and ``observed_at_epoch_ms`` (a verbatim string, or a
    non-negative int carried losslessly to its canonical string). ``market_provenance_context`` is an
    exact :class:`MarketProvenanceContext`; ``gross_edge_binding_label_context`` is an exact
    :class:`GrossEdgeBindingLabelContext`. Nothing is parsed, split, inferred, defaulted, or minted.
    """
    if type(market_provenance_context) is not MarketProvenanceContext:
        raise B2PassPathIngestionTypeError(
            "market_provenance_context must be an exact MarketProvenanceContext"
        )
    if type(gross_edge_binding_label_context) is not GrossEdgeBindingLabelContext:
        raise B2PassPathIngestionTypeError(
            "gross_edge_binding_label_context must be an exact GrossEdgeBindingLabelContext"
        )
    if type(parsed_payload) is not dict:
        raise B2PassPathIngestionTypeError("parsed_payload must be an exact dict")

    if "gross_magnitude" not in parsed_payload:
        raise B2PassPathIngestionValueError("parsed_payload is missing required key 'gross_magnitude'")
    if "unit" not in parsed_payload:
        raise B2PassPathIngestionValueError("parsed_payload is missing required key 'unit'")
    if "venue" not in parsed_payload:
        raise B2PassPathIngestionValueError("parsed_payload is missing required key 'venue'")
    if "pair" not in parsed_payload:
        raise B2PassPathIngestionValueError("parsed_payload is missing required key 'pair'")
    if "observed_at_epoch_ms" not in parsed_payload:
        raise B2PassPathIngestionValueError(
            "parsed_payload is missing required key 'observed_at_epoch_ms'"
        )

    gross_magnitude = parsed_payload["gross_magnitude"]
    if type(gross_magnitude) is not str:
        raise B2PassPathIngestionTypeError(
            "payload 'gross_magnitude' must be an exact str carried verbatim; a numeric magnitude is "
            "rejected without coercion (losslessness cannot be guaranteed)"
        )
    unit = parsed_payload["unit"]
    if type(unit) is not str:
        raise B2PassPathIngestionTypeError("payload 'unit' must be an exact str carried verbatim")
    venue = parsed_payload["venue"]
    if type(venue) is not str:
        raise B2PassPathIngestionTypeError("payload 'venue' must be an exact str carried verbatim")
    pair = parsed_payload["pair"]
    if type(pair) is not str:
        raise B2PassPathIngestionTypeError("payload 'pair' must be an exact str carried verbatim")

    observed_raw = parsed_payload["observed_at_epoch_ms"]
    if type(observed_raw) is str:
        observed_at_epoch_ms = observed_raw
    elif type(observed_raw) is int:
        # bool is excluded structurally because ``type(True) is bool``, not int.
        if observed_raw < 0:
            raise B2PassPathIngestionValueError(
                "payload 'observed_at_epoch_ms' int must be non-negative for canonical carriage"
            )
        observed_at_epoch_ms = str(observed_raw)
    else:
        raise B2PassPathIngestionTypeError(
            "payload 'observed_at_epoch_ms' must be an exact str or a non-negative int; a float (or any "
            "other type) is rejected without coercion"
        )

    # Exactly one GROSS_EDGE binding entry. binding_role is the structural constant; magnitude/unit are
    # verbatim payload strings; both labels come ONLY from the binding-label context. No COST entry, and
    # no zero-cost-evidence label (a GROSS_EDGE binding carries none).
    gross_edge_binding_entry = (
        ("normalized_field_name", gross_edge_binding_label_context.normalized_field_name),
        ("source_field", gross_edge_binding_label_context.source_field),
        ("binding_role", "GROSS_EDGE"),
        ("magnitude", gross_magnitude),
        ("unit", unit),
    )
    field_payload = (gross_edge_binding_entry,)

    return make_public_raw_snapshot_record(
        source_artifact=market_provenance_context.source_artifact,
        source_field=market_provenance_context.source_field,
        venue=venue,
        pair=pair,
        base_asset=market_provenance_context.base_asset,
        quote_asset=market_provenance_context.quote_asset,
        instrument_id=market_provenance_context.instrument_id,
        venue_scope=market_provenance_context.venue_scope,
        venue_buy=market_provenance_context.venue_buy,
        venue_sell=market_provenance_context.venue_sell,
        retrieval_epoch_ms=market_provenance_context.retrieval_epoch_ms,
        observed_at_epoch_ms=observed_at_epoch_ms,
        raw_snapshot_identity=market_provenance_context.raw_snapshot_identity,
        field_payload=field_payload,
    )
