"""phase5/post_profitability_evidence_envelope_boundary.py — atomic implementation of the
`phase5_post_profitability_evidence_envelope_boundary` component: `PostProfitabilityEvidenceEnvelope`.

Per the component planning artifact
(`phase5_post_profitability_evidence_envelope_implementation_planning.md`), this implements ONLY a
frozen, repr-safe, anti-truthiness, anti-coercion, factory-only explicit evidence aggregation
carrier. It wraps exactly ONE :class:`NetEdgeCalculationResult` (stored by identity) alongside
explicitly supplied market-topology / size / time / provenance evidence.

It is an explicit evidence aggregation carrier only. It is NOT a profitability pass certificate, NOT
proof that the net-edge profitability gate evaluated the wrapped result, NOT actionable, NOT
trade-ready, NOT executable, NOT paper-ready, NOT live-ready, and NOT an order / signal / candidate.

Discipline (single-provenance V1):

- every field is explicitly supplied by the caller; the carrier derives nothing from the wrapped
  result and reads nothing from any upstream object;
- no parsing of provenance strings, no inference of venue/base/quote/instrument/side/size/time from
  any field, no defaulting, no clock/time, no network, and no case/unit normalization;
- `calculation_result` must be an exact :class:`NetEdgeCalculationResult` (``type(...) is ...`` — no
  isinstance, so subclasses, halt carriers, dicts, duck-typed records, and arbitrary objects are
  rejected); an exact halt carrier here is a misroute;
- every other field is an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
  subclasses rejected); ``observed_size`` is a canonical unsigned decimal string and
  ``observed_at_epoch_ms`` / ``staleness_threshold_ms`` are canonical unsigned integer strings,
  preserved verbatim;
- it returns no halt carrier and runs no market or economic evaluation.
"""
import re

from dataclasses import dataclass, fields as dataclass_fields

from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult
from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

POST_PROFITABILITY_EVIDENCE_ENVELOPE_COMPONENT_NAME = (
    "phase5_post_profitability_evidence_envelope_boundary"
)
BOUNDARY_VERSION = "phase5.post_profitability_evidence_envelope_boundary.v0"

# Canonical unsigned decimal string: integer part is "0" or a non-zero-leading run, optional
# fractional part (no sign, no exponent, no leading zeros beyond a single "0").
_CANONICAL_UNSIGNED_DECIMAL = re.compile(r"(0|[1-9]\d*)(\.\d+)?")
# Canonical unsigned integer string: "0" or a non-zero-leading run (no sign, no decimal, no exponent).
_CANONICAL_UNSIGNED_INT = re.compile(r"0|[1-9]\d*")

# Plain string fields (exact, non-empty, non-whitespace str; no numeric pattern).
_PLAIN_STR_FIELDS = (
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "size_unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "boundary_version",
)


class PostProfitabilityEvidenceEnvelopeTruthinessError(TypeError):
    """Raised when a PostProfitabilityEvidenceEnvelope is used in a truthiness/length context."""


class PostProfitabilityEvidenceEnvelopeCoercionError(TypeError):
    """Raised when a PostProfitabilityEvidenceEnvelope is coerced to a number, string, or bytes."""


class PostProfitabilityEvidenceEnvelopeTypeError(TypeError):
    """Raised when the factory receives a wrong-typed field value (carrier or string fields)."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the evidence-envelope boundary."""


@dataclass(frozen=True, repr=False, init=False)
class PostProfitabilityEvidenceEnvelope:
    """A frozen, anti-coercion carrier aggregating one net-edge result with explicit evidence.

    Construct only through :func:`make_post_profitability_evidence_envelope`. Direct/positional
    construction is not supported. The carrier asserts no profitability, no actionability, and no
    readiness; it only holds an exact :class:`NetEdgeCalculationResult` (by identity) alongside the
    explicitly supplied market-topology / size / time / provenance evidence.
    """

    component_name: object
    calculation_result: object
    venue: object
    instrument_id: object
    base_asset: object
    quote_asset: object
    side: object
    observed_size: object
    size_unit: object
    observed_at_epoch_ms: object
    staleness_threshold_ms: object
    source_contract: object
    source_artifact: object
    source_field: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise PostProfitabilityEvidenceEnvelopeTruthinessError(
            "PostProfitabilityEvidenceEnvelope must not be evaluated for truthiness; inspect fields."
        )

    def __len__(self):
        raise PostProfitabilityEvidenceEnvelopeTruthinessError(
            "PostProfitabilityEvidenceEnvelope has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise PostProfitabilityEvidenceEnvelopeCoercionError(
            "PostProfitabilityEvidenceEnvelope must not be coerced to int."
        )

    def __float__(self):
        raise PostProfitabilityEvidenceEnvelopeCoercionError(
            "PostProfitabilityEvidenceEnvelope must not be coerced to float."
        )

    def __complex__(self):
        raise PostProfitabilityEvidenceEnvelopeCoercionError(
            "PostProfitabilityEvidenceEnvelope must not be coerced to complex."
        )

    def __index__(self):
        raise PostProfitabilityEvidenceEnvelopeCoercionError(
            "PostProfitabilityEvidenceEnvelope must not be coerced to an index."
        )

    def __str__(self):
        raise PostProfitabilityEvidenceEnvelopeCoercionError(
            "PostProfitabilityEvidenceEnvelope must not be coerced to str."
        )

    def __bytes__(self):
        raise PostProfitabilityEvidenceEnvelopeCoercionError(
            "PostProfitabilityEvidenceEnvelope must not be coerced to bytes."
        )

    # --- safe debug repr only (component_name + boundary_version; no topology/size/time/provenance/
    #     result values; no profitability/actionability/readiness meaning) ---
    def __repr__(self):
        return (
            "PostProfitabilityEvidenceEnvelope(component_name={!r}, boundary_version={!r})".format(
                self.component_name, self.boundary_version
            )
        )


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the evidence-envelope boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a calculation result).
    - Anything else → return ``None``; subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). The offending object is never routed, passed through,
    converted, serialized, or reinterpreted, and is never coerced (bool/len/int/float/str/bytes),
    repr'd, equality-compared, or introspected — only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "evidence-envelope boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "evidence-envelope boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None


def _require_str_field(name, value):
    """Validate one plain string field: exact str (TypeError), non-empty/non-whitespace (ValueError)."""
    if type(value) is not str:
        raise PostProfitabilityEvidenceEnvelopeTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def make_post_profitability_evidence_envelope(
    *,
    calculation_result,
    venue,
    instrument_id,
    base_asset,
    quote_asset,
    side,
    observed_size,
    size_unit,
    observed_at_epoch_ms,
    staleness_threshold_ms,
    source_contract,
    source_artifact,
    source_field,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`PostProfitabilityEvidenceEnvelope`.

    ``calculation_result`` must be an exact :class:`NetEdgeCalculationResult` (``type(...) is ...``);
    an exact halt carrier is a misroute (:class:`MisroutedHaltCarrierError`), and any other wrong type
    (including ``None`` / dict / float / duck-typed / subclass) raises
    :class:`PostProfitabilityEvidenceEnvelopeTypeError`. It is stored by identity — never copied,
    unpacked, or serialized. Every other field must be an exact, non-empty, non-whitespace ``str``
    (str subclasses rejected); ``observed_size`` must match a canonical unsigned decimal and
    ``observed_at_epoch_ms`` / ``staleness_threshold_ms`` must match a canonical unsigned integer, all
    preserved verbatim. Nothing is derived, parsed, inferred, defaulted, clocked, or normalized. Error
    messages use only field names and ``type(value).__name__`` — never ``str(value)``/``repr(value)``.
    """
    # calculation_result: an exact halt carrier is a misroute (raise before the type error).
    reject_misrouted_halt_carrier(calculation_result)
    if type(calculation_result) is not NetEdgeCalculationResult:
        raise PostProfitabilityEvidenceEnvelopeTypeError(
            "field 'calculation_result' must be an exact NetEdgeCalculationResult, not "
            + type(calculation_result).__name__
        )

    # Plain string fields: exact str, non-empty, non-whitespace.
    plain_values = {
        "venue": venue,
        "instrument_id": instrument_id,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "side": side,
        "size_unit": size_unit,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "boundary_version": boundary_version,
    }
    for name in _PLAIN_STR_FIELDS:
        _require_str_field(name, plain_values[name])

    # observed_size: exact str, non-empty, canonical unsigned decimal — preserved verbatim.
    if type(observed_size) is not str:
        raise PostProfitabilityEvidenceEnvelopeTypeError(
            "field 'observed_size' must be a str, not " + type(observed_size).__name__
        )
    if observed_size.strip() == "":
        raise ValueError("field 'observed_size' must be a non-empty, non-whitespace string")
    if _CANONICAL_UNSIGNED_DECIMAL.fullmatch(observed_size) is None:
        raise ValueError("field 'observed_size' must be a canonical unsigned decimal string")

    # observed_at_epoch_ms / staleness_threshold_ms: exact str, non-empty, canonical unsigned integer.
    for name, value in (
        ("observed_at_epoch_ms", observed_at_epoch_ms),
        ("staleness_threshold_ms", staleness_threshold_ms),
    ):
        if type(value) is not str:
            raise PostProfitabilityEvidenceEnvelopeTypeError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise ValueError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )
        if _CANONICAL_UNSIGNED_INT.fullmatch(value) is None:
            raise ValueError(
                "field {!r} must be a canonical unsigned integer string".format(name)
            )

    envelope = object.__new__(PostProfitabilityEvidenceEnvelope)
    object.__setattr__(
        envelope, "component_name", POST_PROFITABILITY_EVIDENCE_ENVELOPE_COMPONENT_NAME
    )
    # calculation_result stored by identity (no copy/unpack/serialize).
    object.__setattr__(envelope, "calculation_result", calculation_result)
    object.__setattr__(envelope, "observed_size", observed_size)
    object.__setattr__(envelope, "observed_at_epoch_ms", observed_at_epoch_ms)
    object.__setattr__(envelope, "staleness_threshold_ms", staleness_threshold_ms)
    for name in _PLAIN_STR_FIELDS:
        object.__setattr__(envelope, name, plain_values[name])
    return envelope


# Defensive guard: the declared dataclass field set must remain the closed 15-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "calculation_result",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "size_unit",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "boundary_version",
)
assert tuple(f.name for f in dataclass_fields(PostProfitabilityEvidenceEnvelope)) == \
    _EXPECTED_FIELD_NAMES
