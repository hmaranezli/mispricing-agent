"""phase6_1/shadow_observation.py — Phase 6.1 Slice 0B passive replay-artifact carrier.

Implements ONLY `ShadowObservation`, its keyword-only factory `make_shadow_observation`, and the
factory's validation. Authored under `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` and
`docs/handoff/phase6_1_shadow_input_wrapper_charter.md`.

`ShadowObservation` is a frozen, slotted, anti-coercion carrier that:
  - references exactly ONE `PassiveShadowInput` BY IDENTITY (its only admissible source; no dict,
    external mapping, raw Phase 5 object, or halt carrier may bypass it);
  - carries immutable replay-identity fields (artifact id + sequence index) sufficient for later
    replay reference;
  - carries a required `diagnostic_recorded_at_ms` — one explicit non-negative UTC epoch-millisecond
    integer;
  - optionally carries one passive `diagnostic_passive_value` float (finite only; NaN/Infinity
    rejected). It is a value supplied from elsewhere, never derived here.

It is passive and replay-first. It performs NO calculation, NO scoring, NO readiness/actionability
verdict, and has NO external-output-sink or persistence methods (those belong to a later, separately
authorized slice). The factory validates only. No IO, no network, no clock, no env, no randomness.
"""
import math
from dataclasses import dataclass, fields as dataclass_fields

from phase6_1.passive_shadow_input import PassiveShadowInput


SHADOW_OBSERVATION_COMPONENT_NAME = "phase6_1_shadow_observation"
SHADOW_OBSERVATION_BOUNDARY_VERSION = "phase6_1.shadow_observation.v0"


class ShadowObservationTypeError(TypeError):
    """Raised for direct construction or for a wrong-typed field value at the factory."""


class ShadowObservationValueError(ValueError):
    """Raised for a correctly-typed but out-of-contract value (empty, negative, NaN, or Infinity)."""


class ShadowObservationTruthinessError(TypeError):
    """Raised when a ShadowObservation is used in a truthiness/length context."""


class ShadowObservationCoercionError(TypeError):
    """Raised when a ShadowObservation is coerced to a number, string, or bytes."""


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class ShadowObservation:
    """A frozen, slotted, anti-coercion passive carrier. Construct only through
    :func:`make_shadow_observation`; direct construction is physically blocked. The carrier holds an
    identity reference to one `PassiveShadowInput` plus immutable replay-identity and recorded-time
    fields; it audits nothing, joins nothing, derives nothing, and decides nothing.
    """

    component_name: object
    boundary_version: object
    source: object
    replay_artifact_id: object
    replay_sequence_index: object
    diagnostic_recorded_at_ms: object
    diagnostic_passive_value: object

    # --- direct construction is physically blocked (no-arg, positional, keyword) ---
    def __init__(self, *args, **kwargs):
        raise ShadowObservationTypeError(
            "ShadowObservation cannot be constructed directly; use make_shadow_observation(...)."
        )

    # --- anti-truthiness ---
    def __bool__(self):
        raise ShadowObservationTruthinessError(
            "ShadowObservation must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise ShadowObservationTruthinessError(
            "ShadowObservation has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise ShadowObservationCoercionError("ShadowObservation must not be coerced to int.")

    def __float__(self):
        raise ShadowObservationCoercionError("ShadowObservation must not be coerced to a real number.")

    def __complex__(self):
        raise ShadowObservationCoercionError("ShadowObservation must not be coerced to complex.")

    def __index__(self):
        raise ShadowObservationCoercionError("ShadowObservation must not be coerced to an index.")

    def __str__(self):
        raise ShadowObservationCoercionError("ShadowObservation must not be coerced to str.")

    def __bytes__(self):
        raise ShadowObservationCoercionError("ShadowObservation must not be coerced to bytes.")

    # --- safe debug repr only (component_name + boundary_version; no provenance/value leak) ---
    def __repr__(self):
        return "ShadowObservation(component_name={!r}, boundary_version={!r})".format(
            object.__getattribute__(self, "component_name"),
            object.__getattribute__(self, "boundary_version"),
        )


def _require_str_field(name, value):
    """Validate one field: exact `str` (TypeError), non-empty/non-whitespace (ValueError).

    Messages use only the field name and ``type(value).__name__`` — never the value itself.
    """
    if type(value) is not str:
        raise ShadowObservationTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise ShadowObservationValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def _require_non_negative_int(name, value):
    """Validate one field as an exact non-negative int; bool rejected (``type(True) is bool``)."""
    if type(value) is not int:
        raise ShadowObservationTypeError(
            "field {!r} must be an exact int, not {}".format(name, type(value).__name__)
        )
    if value < 0:
        raise ShadowObservationValueError(
            "field {!r} must be a non-negative integer".format(name)
        )


def make_shadow_observation(
    *,
    source,
    replay_artifact_id,
    replay_sequence_index,
    diagnostic_recorded_at_ms,
    diagnostic_passive_value=None,
):
    """Keyword-only constructor for a single :class:`ShadowObservation`.

    ``component_name`` and ``boundary_version`` are NOT parameters — set internally from the module
    constants. ``source`` must be an exact :class:`PassiveShadowInput` (referenced by identity; no
    dict, external mapping, or raw Phase 5 object/halt carrier may bypass it). ``diagnostic_recorded_at_ms`` is one
    explicit non-negative UTC millisecond integer. ``diagnostic_passive_value`` is optional; when
    supplied it must be a finite float (NaN/Infinity rejected). Nothing is copied or derived.
    """
    # Only a PassiveShadowInput may enter, by exact-type identity.
    if type(source) is not PassiveShadowInput:
        raise ShadowObservationTypeError(
            "source must be an exact PassiveShadowInput, not {}".format(type(source).__name__)
        )

    # Immutable replay-identity fields.
    _require_str_field("replay_artifact_id", replay_artifact_id)
    _require_non_negative_int("replay_sequence_index", replay_sequence_index)

    # Required recorded time: one explicit non-negative UTC epoch-millisecond integer.
    _require_non_negative_int("diagnostic_recorded_at_ms", diagnostic_recorded_at_ms)

    # Optional passive diagnostic float: exact float, finite only.
    if diagnostic_passive_value is not None:
        if type(diagnostic_passive_value) is not float:
            raise ShadowObservationTypeError(
                "diagnostic_passive_value must be an exact float or None, not {}".format(
                    type(diagnostic_passive_value).__name__
                )
            )
        if not math.isfinite(diagnostic_passive_value):
            raise ShadowObservationValueError(
                "diagnostic_passive_value must be a finite float; NaN/Infinity are rejected"
            )

    obs = object.__new__(ShadowObservation)
    object.__setattr__(obs, "component_name", SHADOW_OBSERVATION_COMPONENT_NAME)
    object.__setattr__(obs, "boundary_version", SHADOW_OBSERVATION_BOUNDARY_VERSION)
    object.__setattr__(obs, "source", source)
    object.__setattr__(obs, "replay_artifact_id", replay_artifact_id)
    object.__setattr__(obs, "replay_sequence_index", replay_sequence_index)
    object.__setattr__(obs, "diagnostic_recorded_at_ms", diagnostic_recorded_at_ms)
    object.__setattr__(obs, "diagnostic_passive_value", diagnostic_passive_value)
    return obs


# Defensive guard: the declared field set must remain the closed 7-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "boundary_version",
    "source",
    "replay_artifact_id",
    "replay_sequence_index",
    "diagnostic_recorded_at_ms",
    "diagnostic_passive_value",
)
assert tuple(f.name for f in dataclass_fields(ShadowObservation)) == _EXPECTED_FIELD_NAMES
