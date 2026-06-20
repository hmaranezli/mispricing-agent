"""phase6_1/market_provenance_context.py — Phase 6.1 MarketProvenanceContext passive DTO.

A frozen, immutable, methodless passive metadata container carrying exactly ten supplied non-payload
provenance attributes that travel beside the Option-B payload. Built under
``docs/handoff/phase6_1_market_provenance_context_field_shape_charter.md``.

It is pure data. The only method is ``__post_init__``, a structural guard that enforces ONLY that the
nine string attributes are exact non-empty ``str`` and that ``retrieval_epoch_ms`` is an exact
non-negative ``int``. It parses nothing, splits nothing, infers nothing, defaults nothing, casts
nothing, and validates no semantic vocabulary, market term, venue name, pair format, base/quote
consistency, buy/sell meaning, identity pattern, or cost validity. Every field is supplied verbatim by
the caller.

It is identity-segregated: it neither imports nor references the S2 Silver/System identity carrier;
``raw_snapshot_identity`` is a caller-supplied market identity string only, never derived from or merged
with that separate identity plane. It carries no payload field, no GROSS_EDGE/COST binding label, no
cost, no Silver tuple, and owns no storage. No clock, no randomness, no hashing, no identity minting.
"""
from dataclasses import dataclass


MARKET_PROVENANCE_CONTEXT_COMPONENT_NAME = "phase6_1_market_provenance_context"


@dataclass(frozen=True, slots=True)
class MarketProvenanceContext:
    """Frozen, methodless passive provenance envelope: exactly ten supplied non-payload attributes.

    The nine string attributes are exact non-empty strings; ``retrieval_epoch_ms`` is an exact
    non-negative int. All values are supplied verbatim — nothing is parsed, split, derived, normalized,
    defaulted, or minted. ``raw_snapshot_identity`` is external market identity, never S2 identity.
    """

    source_artifact: object
    source_field: object
    base_asset: object
    quote_asset: object
    instrument_id: object
    venue_scope: object
    venue_buy: object
    venue_sell: object
    retrieval_epoch_ms: object
    raw_snapshot_identity: object

    def __post_init__(self):
        for value in (
            self.source_artifact,
            self.source_field,
            self.base_asset,
            self.quote_asset,
            self.instrument_id,
            self.venue_scope,
            self.venue_buy,
            self.venue_sell,
            self.raw_snapshot_identity,
        ):
            if type(value) is not str:
                raise TypeError(
                    "MarketProvenanceContext string provenance fields must each be an exact str"
                )
            if value == "":
                raise ValueError(
                    "MarketProvenanceContext string provenance fields must each be non-empty"
                )
        if type(self.retrieval_epoch_ms) is not int:
            raise TypeError(
                "MarketProvenanceContext retrieval_epoch_ms must be an exact int"
            )
        if self.retrieval_epoch_ms < 0:
            raise ValueError(
                "MarketProvenanceContext retrieval_epoch_ms must be a non-negative integer"
            )
