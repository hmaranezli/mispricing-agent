"""phase6_1/b1_depth_source_contract.py — Phase 6.1 B1 replay depth source contract.

Pins ONLY an immutable, provenance-tagged market-depth evidence carrier and its keyword-only, exact-type,
fail-fast factory. Authored under `docs/handoff/phase6_1_b1_depth_source_amendment_charter.md`.

This is a replay-artifact-only contract: it reads no artifact, performs no fetch, and decides nothing.
``observed_size`` is carried verbatim as evidence; it is never parsed, compared, normalized, aggregated,
or interpreted here, and B1 never judges whether depth is enough or insufficient. The carrier imports
nothing from B2, B3, or Phase 5, builds no Slice-0 carrier, writes no output, reads no environment, and
does no network or file access. Exact-type discipline only (``type(value) is ExactType``); no silent
coercion; no default fallbacks; missing/malformed fields fail fast. ``depth_observed_at_epoch_ms`` is the
source-observed depth time and is kept semantically distinct from the retrieval/freeze time
``depth_retrieval_epoch_ms``.
"""
import re
from dataclasses import dataclass, fields as dataclass_fields


B1_DEPTH_SOURCE_CONTRACT_COMPONENT_NAME = "phase6_1_b1_depth_source_contract"
B1_DEPTH_SOURCE_CONTRACT_BOUNDARY_VERSION = "phase6_1.b1_depth_source_contract.v0"


class B1DepthSourceTypeError(TypeError):
    """Raised for direct construction or a wrong-typed field value at the factory."""


class B1DepthSourceValueError(ValueError):
    """Raised for a correctly-typed but out-of-contract value (empty, whitespace, negative, non-canonical,
    or a timestamp that is not kept distinct)."""


class B1DepthSourceTruthinessError(TypeError):
    """Raised when the carrier is used in a truthiness/length context."""


class B1DepthSourceCoercionError(TypeError):
    """Raised when the carrier is coerced to a number, string, or bytes."""


# --- shared anti-coercion behavior (no metaclass; one mixin of dunders) ---------------------------

class _AntiCoercion:
    __slots__ = ()

    def __bool__(self):
        raise B1DepthSourceTruthinessError("B1 depth carrier must not be evaluated for truthiness.")

    def __len__(self):
        raise B1DepthSourceTruthinessError("B1 depth carrier has no length; inspect fields instead.")

    def __int__(self):
        raise B1DepthSourceCoercionError("B1 depth carrier must not be coerced to int.")

    def __float__(self):
        raise B1DepthSourceCoercionError("B1 depth carrier must not be coerced to a real number.")

    def __complex__(self):
        raise B1DepthSourceCoercionError("B1 depth carrier must not be coerced to complex.")

    def __index__(self):
        raise B1DepthSourceCoercionError("B1 depth carrier must not be coerced to an index.")

    def __str__(self):
        raise B1DepthSourceCoercionError("B1 depth carrier must not be coerced to str.")

    def __bytes__(self):
        raise B1DepthSourceCoercionError("B1 depth carrier must not be coerced to bytes.")


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class PublicDepthSourceRecord(_AntiCoercion):
    """Immutable, provenance-tagged market-depth evidence record. Construct only through
    :func:`make_public_depth_source_record`; direct construction is physically blocked. ``observed_size``
    is evidence carried verbatim — no judgement about it is made here."""

    component_name: object
    boundary_version: object
    observed_size: object
    size_unit: object
    depth_source_field: object
    depth_source_artifact: object
    depth_source_contract: object
    depth_observed_at_epoch_ms: object
    depth_retrieval_epoch_ms: object
    depth_snapshot_identity: object

    def __init__(self, *args, **kwargs):
        raise B1DepthSourceTypeError(
            "PublicDepthSourceRecord cannot be constructed directly; use "
            "make_public_depth_source_record(...)."
        )

    def __repr__(self):
        return "PublicDepthSourceRecord(depth_snapshot_identity={!r})".format(
            object.__getattribute__(self, "depth_snapshot_identity")
        )


# --- validation helpers (exact-type, fail-fast, no coercion) --------------------------------------

def _require_str(name, value):
    if type(value) is not str:
        raise B1DepthSourceTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise B1DepthSourceValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def _require_non_negative_int(name, value):
    # bool is rejected because ``type(True) is bool`` (not int).
    if type(value) is not int:
        raise B1DepthSourceTypeError(
            "field {!r} must be an exact int, not {}".format(name, type(value).__name__)
        )
    if value < 0:
        raise B1DepthSourceValueError(
            "field {!r} must be a non-negative integer".format(name)
        )


# A canonical unsigned integer string: digits only, no sign, no separators, no leading zeros
# (``"0"`` is the sole zero form). A verbatim carrier check — no int parsing, no arithmetic.
_CANONICAL_UNSIGNED_INT_STR = re.compile(r"0|[1-9][0-9]*")


def _require_canonical_unsigned_int_str(name, value):
    if type(value) is not str:
        raise B1DepthSourceTypeError(
            "field {!r} must be a canonical unsigned integer string, not {}".format(
                name, type(value).__name__
            )
        )
    if value.strip() == "":
        raise B1DepthSourceValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )
    if _CANONICAL_UNSIGNED_INT_STR.fullmatch(value) is None:
        raise B1DepthSourceValueError(
            "field {!r} must be a canonical unsigned integer string (digits only, no sign, no "
            "separators, no leading zeros)".format(name)
        )


# --- keyword-only factory -------------------------------------------------------------------------

def make_public_depth_source_record(
    *,
    observed_size,
    size_unit,
    depth_source_field,
    depth_source_artifact,
    depth_source_contract,
    depth_observed_at_epoch_ms,
    depth_retrieval_epoch_ms,
    depth_snapshot_identity,
):
    """Build one :class:`PublicDepthSourceRecord`. ``observed_size``, ``size_unit``,
    ``depth_source_field``, ``depth_source_artifact``, ``depth_source_contract``, and
    ``depth_snapshot_identity`` are exact non-empty strings carried verbatim; ``observed_size`` is
    evidence only and is never parsed or judged. ``depth_observed_at_epoch_ms`` is a canonical unsigned
    integer string (the source-observed depth time); ``depth_retrieval_epoch_ms`` is an exact
    non-negative UTC millisecond int (the retrieval/freeze time). The two timestamps are semantically
    distinct and must be supplied independently — the observed time may not be a stringified copy of the
    retrieval time. Nothing is mapped, derived, or decided."""
    _require_str("observed_size", observed_size)
    _require_str("size_unit", size_unit)
    _require_str("depth_source_field", depth_source_field)
    _require_str("depth_source_artifact", depth_source_artifact)
    _require_str("depth_source_contract", depth_source_contract)
    _require_canonical_unsigned_int_str("depth_observed_at_epoch_ms", depth_observed_at_epoch_ms)
    _require_non_negative_int("depth_retrieval_epoch_ms", depth_retrieval_epoch_ms)
    _require_str("depth_snapshot_identity", depth_snapshot_identity)

    # Time-isolation / anti-copy lock: the source-observed depth time must not be a stringified copy of
    # the retrieval/freeze time. The two are semantically distinct timestamps and must be supplied
    # independently; a silent substitution would invite lookahead bias. No magnitude comparison is done
    # — only an exact-string identity rejection.
    if depth_observed_at_epoch_ms == str(depth_retrieval_epoch_ms):
        raise B1DepthSourceValueError(
            "field 'depth_observed_at_epoch_ms' must not equal str(depth_retrieval_epoch_ms); the "
            "source-observed depth time and the retrieval/freeze time are distinct timestamps"
        )

    record = object.__new__(PublicDepthSourceRecord)
    object.__setattr__(record, "component_name", B1_DEPTH_SOURCE_CONTRACT_COMPONENT_NAME)
    object.__setattr__(record, "boundary_version", B1_DEPTH_SOURCE_CONTRACT_BOUNDARY_VERSION)
    object.__setattr__(record, "observed_size", observed_size)
    object.__setattr__(record, "size_unit", size_unit)
    object.__setattr__(record, "depth_source_field", depth_source_field)
    object.__setattr__(record, "depth_source_artifact", depth_source_artifact)
    object.__setattr__(record, "depth_source_contract", depth_source_contract)
    object.__setattr__(record, "depth_observed_at_epoch_ms", depth_observed_at_epoch_ms)
    object.__setattr__(record, "depth_retrieval_epoch_ms", depth_retrieval_epoch_ms)
    object.__setattr__(record, "depth_snapshot_identity", depth_snapshot_identity)
    return record


# Defensive guard: the declared field set must remain a closed contract.
assert tuple(f.name for f in dataclass_fields(PublicDepthSourceRecord)) == (
    "component_name", "boundary_version", "observed_size", "size_unit", "depth_source_field",
    "depth_source_artifact", "depth_source_contract", "depth_observed_at_epoch_ms",
    "depth_retrieval_epoch_ms", "depth_snapshot_identity",
)
