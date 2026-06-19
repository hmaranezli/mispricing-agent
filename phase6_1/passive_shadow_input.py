"""phase6_1/passive_shadow_input.py — Phase 6.1 Slice 0A passive carrier.

Implements ONLY `PassiveShadowInput`, its keyword-only factory `make_passive_shadow_input`, and the
factory's validation. Authored under `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`.

`PassiveShadowInput` is a frozen, slotted, anti-coercion carrier that:
  - references exactly ONE Phase 5 `NetEdgeCalculationResult` BY IDENTITY (never copies, mutates,
    recomputes, coerces, or reinterprets it);
  - carries minimal market provenance — venue, pair, and one explicit UTC epoch-millisecond integer;
  - carries `capacity_pass_reference`, whose Slice 0A meaning is exactly `None` / deferred. The
    capacity gate is structurally complete but non-activatable (0 emit sites), so no capacity pass
    token exists yet; any non-deferred value fails fast and this field must never be read as
    "capacity validated."

It is passive, diagnostic-free, and replay-first. It performs NO economic calculation, NO scoring,
NO readiness verdict, and exposes no actionability semantics. The factory validates only; it derives
nothing. No IO, no network, no clock, no env, no randomness.
"""
from dataclasses import dataclass, fields as dataclass_fields

from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult


PASSIVE_SHADOW_INPUT_COMPONENT_NAME = "phase6_1_passive_shadow_input"
PASSIVE_SHADOW_INPUT_BOUNDARY_VERSION = "phase6_1.passive_shadow_input.v0"


class PassiveShadowInputTypeError(TypeError):
    """Raised for direct construction or for a wrong-typed field value at the factory."""


class PassiveShadowInputValueError(ValueError):
    """Raised for a correctly-typed but out-of-contract field value (e.g. empty or negative)."""


class PassiveShadowInputCapacityError(TypeError):
    """Raised when `capacity_pass_reference` is anything other than the deferred `None`."""


class PassiveShadowInputTruthinessError(TypeError):
    """Raised when a PassiveShadowInput is used in a truthiness/length context."""


class PassiveShadowInputCoercionError(TypeError):
    """Raised when a PassiveShadowInput is coerced to a number, string, or bytes."""


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class PassiveShadowInput:
    """A frozen, slotted, anti-coercion passive carrier. Construct only through
    :func:`make_passive_shadow_input`; direct construction is physically blocked. The carrier holds an
    identity reference to one Phase 5 result plus minimal provenance; it audits nothing, joins nothing,
    derives nothing, and decides nothing.
    """

    component_name: object
    boundary_version: object
    net_edge_calculation_result: object
    capacity_pass_reference: object
    source_venue: object
    source_pair: object
    observed_at_epoch_ms: object

    # --- direct construction is physically blocked (no-arg, positional, keyword) ---
    def __init__(self, *args, **kwargs):
        raise PassiveShadowInputTypeError(
            "PassiveShadowInput cannot be constructed directly; use make_passive_shadow_input(...)."
        )

    # --- anti-truthiness ---
    def __bool__(self):
        raise PassiveShadowInputTruthinessError(
            "PassiveShadowInput must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise PassiveShadowInputTruthinessError(
            "PassiveShadowInput has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise PassiveShadowInputCoercionError("PassiveShadowInput must not be coerced to int.")

    def __float__(self):
        raise PassiveShadowInputCoercionError("PassiveShadowInput must not be coerced to a real number.")

    def __complex__(self):
        raise PassiveShadowInputCoercionError("PassiveShadowInput must not be coerced to complex.")

    def __index__(self):
        raise PassiveShadowInputCoercionError("PassiveShadowInput must not be coerced to an index.")

    def __str__(self):
        raise PassiveShadowInputCoercionError("PassiveShadowInput must not be coerced to str.")

    def __bytes__(self):
        raise PassiveShadowInputCoercionError("PassiveShadowInput must not be coerced to bytes.")

    # --- safe debug repr only (component_name + boundary_version; no provenance/value leak) ---
    def __repr__(self):
        return "PassiveShadowInput(component_name={!r}, boundary_version={!r})".format(
            object.__getattribute__(self, "component_name"),
            object.__getattribute__(self, "boundary_version"),
        )


_CALLER_SUPPLIED_STR_FIELDS = ("source_venue", "source_pair")


def _require_str_field(name, value):
    """Validate one provenance field: exact `str` (TypeError), non-empty/non-whitespace (ValueError).

    Messages use only the field name and ``type(value).__name__`` — never the value itself.
    """
    if type(value) is not str:
        raise PassiveShadowInputTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise PassiveShadowInputValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def make_passive_shadow_input(
    *,
    net_edge_calculation_result,
    source_venue,
    source_pair,
    observed_at_epoch_ms,
    capacity_pass_reference=None,
):
    """Keyword-only constructor for a single :class:`PassiveShadowInput`.

    ``component_name`` and ``boundary_version`` are NOT parameters — they are set internally from the
    module constants. The Phase 5 result is referenced by identity (exact type only). The epoch is one
    explicit non-negative UTC millisecond integer (``type(value) is int`` — bools rejected, since
    ``type(True) is bool``; strings/floats/datetimes rejected). ``capacity_pass_reference`` must be the
    deferred ``None``. Nothing is copied, derived, or recomputed.
    """
    # Phase 5 profitability-pass source: exact-type identity reference only.
    if type(net_edge_calculation_result) is not NetEdgeCalculationResult:
        raise PassiveShadowInputTypeError(
            "net_edge_calculation_result must be an exact NetEdgeCalculationResult, not {}".format(
                type(net_edge_calculation_result).__name__
            )
        )

    # Minimal market provenance.
    _require_str_field("source_venue", source_venue)
    _require_str_field("source_pair", source_pair)

    # One explicit UTC epoch-millisecond integer; reject bool and any non-int coercion.
    if type(observed_at_epoch_ms) is not int:
        raise PassiveShadowInputTypeError(
            "observed_at_epoch_ms must be an exact int (UTC epoch milliseconds), not {}".format(
                type(observed_at_epoch_ms).__name__
            )
        )
    if observed_at_epoch_ms < 0:
        raise PassiveShadowInputValueError(
            "observed_at_epoch_ms must be a non-negative UTC epoch-millisecond integer"
        )

    # Capacity remains deferred for Slice 0A: only the deferred None is admissible.
    if capacity_pass_reference is not None:
        raise PassiveShadowInputCapacityError(
            "capacity_pass_reference must be the deferred None at Slice 0A; capacity is not validated "
            "and no capacity pass token exists yet (got {})".format(
                type(capacity_pass_reference).__name__
            )
        )

    psi = object.__new__(PassiveShadowInput)
    object.__setattr__(psi, "component_name", PASSIVE_SHADOW_INPUT_COMPONENT_NAME)
    object.__setattr__(psi, "boundary_version", PASSIVE_SHADOW_INPUT_BOUNDARY_VERSION)
    object.__setattr__(psi, "net_edge_calculation_result", net_edge_calculation_result)
    object.__setattr__(psi, "capacity_pass_reference", None)
    object.__setattr__(psi, "source_venue", source_venue)
    object.__setattr__(psi, "source_pair", source_pair)
    object.__setattr__(psi, "observed_at_epoch_ms", observed_at_epoch_ms)
    return psi


# Defensive guard: the declared field set must remain the closed 7-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "boundary_version",
    "net_edge_calculation_result",
    "capacity_pass_reference",
    "source_venue",
    "source_pair",
    "observed_at_epoch_ms",
)
assert tuple(f.name for f in dataclass_fields(PassiveShadowInput)) == _EXPECTED_FIELD_NAMES
