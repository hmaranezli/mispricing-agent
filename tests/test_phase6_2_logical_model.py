"""Slice A — Phase 6.2 logical model: focused RED→GREEN tests.

Covers the source-proven Gate A logical shape (envelope `5dc757c` + predecessor option-sum `1071067`,
definition variants, OpaqueSilverPairKey, exact-Decimal boundary, integer-ms duration with bool
rejection, immutable finite definitions map) and the closed lifecycle vocabulary (`e9995e7` §4). The
slot/snapshot *container* shape is deliberately NOT exercised here — it is not source-proven and Slice A
invents nothing.
"""
import dataclasses
import decimal

import pytest

from phase6_2_shadow_intent import logical_model as lm


_DEC = decimal.Decimal


def _silver(a="loc-1", p="0"):
    return lm.make_opaque_silver_pair_key(
        silver_artifact_locator_text=a, silver_physical_record_position_text=p
    )


def _directional(orientation=lm.POSITIVE_EXPOSURE, mag=_DEC("1.5"), unit="proportion", dur=840000):
    return lm.make_directional_shadow_intent_definition(
        exposure_orientation=orientation,
        passive_boundary_magnitude=mag,
        boundary_unit_context=unit,
        hypothetical_window_duration_ms=dur,
    )


def _inert(dur=840000):
    return lm.make_inert_shadow_intent_definition(
        exposure_orientation=lm.INERT_STATE, hypothetical_window_duration_ms=dur
    )


_UNSET = object()


def _artifact(*, predecessor=_UNSET, entries=()):
    if predecessor is _UNSET:
        predecessor = lm.NoPredecessor()
    return lm.make_shadow_intent_definition_artifact(
        artifact_field_shape_version_reference="PHASE6_2_SHADOW_INTENT_DEFINITION_ARTIFACT_FIELD_SHAPE_V1",
        artifact_version_reference="artifact-v1",
        declarer_opaque_reference="declarer-x",
        predecessor_artifact_version_reference=predecessor,
        definition_entries=tuple(entries),
    )


# --- closed vocabularies -------------------------------------------------------------------------

def test_orientation_vocabulary_exact():
    assert lm.POSITIVE_EXPOSURE == "POSITIVE_EXPOSURE"
    assert lm.NEGATIVE_EXPOSURE == "NEGATIVE_EXPOSURE"
    assert lm.INERT_STATE == "INERT_STATE"


def test_closed_lifecycle_states_exact_set():
    assert lm.CLOSED_LIFECYCLE_STATES == frozenset({
        "AUDIT_REPLAYED", "INTENT_RECORDED", "HYPOTHETICAL_CONDITION_MET",
        "INTENT_EXPIRED", "INTENT_RETIRED",
    })


def test_validate_lifecycle_state_accepts_each_and_rejects_unknown():
    for s in lm.CLOSED_LIFECYCLE_STATES:
        assert lm.validate_lifecycle_state(s) == s
    for bad in ("PENDING", "FILLED", "audit_replayed", "", 0, None):
        with pytest.raises(lm.LogicalModelError):
            lm.validate_lifecycle_state(bad)


# --- OpaqueSilverPairKey -------------------------------------------------------------------------

def test_silver_pair_key_preserves_verbatim_and_is_hashable_frozen():
    k = _silver("Loc A", "  42 ")
    assert k.silver_artifact_locator_text == "Loc A"
    assert k.silver_physical_record_position_text == "  42 "  # verbatim, no trim/normalize
    assert hash(k) == hash(_silver("Loc A", "  42 "))
    with pytest.raises(dataclasses.FrozenInstanceError):
        k.silver_artifact_locator_text = "x"  # frozen


def test_silver_pair_key_rejects_non_str_components():
    with pytest.raises(lm.LogicalModelError):
        lm.make_opaque_silver_pair_key(silver_artifact_locator_text=1, silver_physical_record_position_text="0")
    with pytest.raises(lm.LogicalModelError):
        lm.make_opaque_silver_pair_key(silver_artifact_locator_text="a", silver_physical_record_position_text=0)
    with pytest.raises(lm.LogicalModelError):
        lm.make_opaque_silver_pair_key(silver_artifact_locator_text="a", silver_physical_record_position_text=None)


def test_position_text_never_decoded_as_int():
    # "0" and "00" are distinct opaque text, never numerically collapsed
    assert _silver("a", "0") != _silver("a", "00")


# --- predecessor option-sum ----------------------------------------------------------------------

def test_no_predecessor_has_zero_payload_fields():
    import dataclasses
    assert dataclasses.fields(lm.NoPredecessor) == ()


def test_predecessor_reference_one_field_str_only():
    ref = lm.PredecessorReference(opaque_reference="prev-v0")
    assert ref.opaque_reference == "prev-v0"
    with pytest.raises(lm.LogicalModelError):
        lm.make_predecessor_reference(opaque_reference=7)


def test_artifact_predecessor_must_be_option_member():
    with pytest.raises(lm.LogicalModelError):
        _artifact(predecessor="NONE")  # string sentinel forbidden
    with pytest.raises(lm.LogicalModelError):
        _artifact(predecessor=None)    # None/omission forbidden at validation layer
    # both real variants accepted:
    _artifact(predecessor=lm.NoPredecessor())
    _artifact(predecessor=lm.PredecessorReference(opaque_reference="prev-v0"))


# --- directional definition ----------------------------------------------------------------------

def test_directional_valid_positive_and_negative():
    d = _directional(lm.POSITIVE_EXPOSURE)
    assert d.exposure_orientation == lm.POSITIVE_EXPOSURE
    assert d.passive_boundary_magnitude == _DEC("1.5")
    assert d.boundary_unit_context == "proportion"
    assert d.hypothetical_window_duration_ms == 840000
    assert _directional(lm.NEGATIVE_EXPOSURE).exposure_orientation == lm.NEGATIVE_EXPOSURE


def test_directional_rejects_inert_and_unknown_orientation():
    with pytest.raises(lm.LogicalModelError):
        _directional(lm.INERT_STATE)
    with pytest.raises(lm.LogicalModelError):
        _directional("LONG")


def test_directional_magnitude_must_be_finite_decimal():
    for bad in (1.5, "1.5", 2, True, _DEC("NaN"), _DEC("Infinity"), _DEC("-Infinity")):
        with pytest.raises(lm.LogicalModelError):
            _directional(mag=bad)
    # finite decimals (incl negative, zero) accepted, stored verbatim
    assert _directional(mag=_DEC("-0.25")).passive_boundary_magnitude == _DEC("-0.25")
    assert _directional(mag=_DEC("0")).passive_boundary_magnitude == _DEC("0")


def test_directional_unit_must_be_str():
    with pytest.raises(lm.LogicalModelError):
        _directional(unit=1)


def test_duration_non_negative_int_bool_rejected():
    assert _directional(dur=0).hypothetical_window_duration_ms == 0
    for bad in (True, False, -1, 1.0, "840000", None):
        with pytest.raises(lm.LogicalModelError):
            _directional(dur=bad)


# --- inert definition ----------------------------------------------------------------------------

def test_inert_valid_and_requires_inert_state():
    i = _inert()
    assert i.exposure_orientation == lm.INERT_STATE
    assert i.hypothetical_window_duration_ms == 840000
    with pytest.raises(lm.LogicalModelError):
        lm.make_inert_shadow_intent_definition(
            exposure_orientation=lm.POSITIVE_EXPOSURE, hypothetical_window_duration_ms=1
        )


def test_inert_has_no_boundary_or_unit_fields():
    import dataclasses
    names = {f.name for f in dataclasses.fields(lm.InertShadowIntentDefinition)}
    assert names == {"exposure_orientation", "hypothetical_window_duration_ms"}
    assert "passive_boundary_magnitude" not in names
    assert "boundary_unit_context" not in names


# --- envelope / definitions map ------------------------------------------------------------------

def test_artifact_envelope_exact_five_fields():
    import dataclasses
    names = tuple(f.name for f in dataclasses.fields(lm.ShadowIntentDefinitionArtifact))
    assert names == (
        "artifact_field_shape_version_reference",
        "artifact_version_reference",
        "declarer_opaque_reference",
        "predecessor_artifact_version_reference",
        "definitions_by_silver_pair",
    )


def test_empty_definitions_map_valid():
    art = _artifact(entries=())
    assert len(art.definitions_by_silver_pair) == 0


def test_definitions_map_keyed_by_silver_pair_and_immutable():
    k1, k2 = _silver("a", "0"), _silver("b", "1")
    art = _artifact(entries=((k1, _directional()), (k2, _inert())))
    assert art.definitions_by_silver_pair[k1].exposure_orientation == lm.POSITIVE_EXPOSURE
    assert art.definitions_by_silver_pair[k2].exposure_orientation == lm.INERT_STATE
    with pytest.raises(TypeError):
        art.definitions_by_silver_pair[_silver("c", "2")] = _inert()  # immutable mapping


def test_duplicate_silver_pair_key_rejected():
    k = _silver("dup", "0")
    with pytest.raises(lm.LogicalModelError):
        _artifact(entries=((k, _directional()), (k, _inert())))


def test_artifact_opaque_refs_must_be_str():
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_intent_definition_artifact(
            artifact_field_shape_version_reference=1,
            artifact_version_reference="v",
            declarer_opaque_reference="d",
            predecessor_artifact_version_reference=lm.NoPredecessor(),
            definition_entries=(),
        )


def test_artifact_rejects_non_key_entry_and_non_definition_value():
    with pytest.raises(lm.LogicalModelError):
        _artifact(entries=(("not-a-key", _inert()),))
    with pytest.raises(lm.LogicalModelError):
        _artifact(entries=((_silver(), "not-a-definition"),))


def test_artifact_and_definitions_are_frozen():
    art = _artifact()
    with pytest.raises(dataclasses.FrozenInstanceError):
        art.artifact_version_reference = "x"
    with pytest.raises(dataclasses.FrozenInstanceError):
        _directional().passive_boundary_magnitude = _DEC("9")


# --- Slice-A hardening: constructor-bypass, slotting, error-surface -------------------------------

def test_direct_construction_validates_field_bearing_dtos():
    with pytest.raises(lm.LogicalModelError):
        lm.OpaqueSilverPairKey(silver_artifact_locator_text=1, silver_physical_record_position_text="0")
    with pytest.raises(lm.LogicalModelError):
        lm.PredecessorReference(opaque_reference=7)
    with pytest.raises(lm.LogicalModelError):
        lm.DirectionalShadowIntentDefinition(
            exposure_orientation="LONG", passive_boundary_magnitude=_DEC("1"),
            boundary_unit_context="u", hypothetical_window_duration_ms=1,
        )
    with pytest.raises(lm.LogicalModelError):
        lm.InertShadowIntentDefinition(
            exposure_orientation=lm.POSITIVE_EXPOSURE, hypothetical_window_duration_ms=1,
        )


def test_field_bearing_dtos_are_keyword_only():
    with pytest.raises(TypeError):
        lm.OpaqueSilverPairKey("a", "0")  # positional construction rejected (kw_only)


def test_artifact_cannot_be_constructed_directly():
    for attempt in (
        lambda: lm.ShadowIntentDefinitionArtifact(),
        lambda: lm.ShadowIntentDefinitionArtifact("a", "b", "c", lm.NoPredecessor(), {}),
        lambda: lm.ShadowIntentDefinitionArtifact(
            artifact_field_shape_version_reference="a", artifact_version_reference="b",
            declarer_opaque_reference="c", predecessor_artifact_version_reference=lm.NoPredecessor(),
            definitions_by_silver_pair={},
        ),
    ):
        with pytest.raises(lm.LogicalModelError):
            attempt()


def test_artifact_revalidates_bypassed_nested_key():
    poison = object.__new__(lm.OpaqueSilverPairKey)  # bypass __post_init__
    object.__setattr__(poison, "silver_artifact_locator_text", 123)
    object.__setattr__(poison, "silver_physical_record_position_text", "0")
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_intent_definition_artifact(
            artifact_field_shape_version_reference="v", artifact_version_reference="v",
            declarer_opaque_reference="d", predecessor_artifact_version_reference=lm.NoPredecessor(),
            definition_entries=((poison, _inert()),),
        )


def test_artifact_revalidates_bypassed_nested_definition():
    poison = object.__new__(lm.InertShadowIntentDefinition)  # bypass __post_init__
    object.__setattr__(poison, "exposure_orientation", lm.INERT_STATE)
    object.__setattr__(poison, "hypothetical_window_duration_ms", -5)
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_intent_definition_artifact(
            artifact_field_shape_version_reference="v", artifact_version_reference="v",
            declarer_opaque_reference="d", predecessor_artifact_version_reference=lm.NoPredecessor(),
            definition_entries=((_silver(), poison),),
        )


def test_unhashable_orientation_raises_logical_model_error():
    with pytest.raises(lm.LogicalModelError):
        _directional(orientation=["POSITIVE_EXPOSURE"])  # unhashable: must not leak raw TypeError
    with pytest.raises(lm.LogicalModelError):
        lm.make_inert_shadow_intent_definition(
            exposure_orientation={"x"}, hypothetical_window_duration_ms=1
        )


def test_no_dict_on_all_instances_and_extra_field_injection_fails():
    instances = (
        _silver(), lm.NoPredecessor(), lm.PredecessorReference(opaque_reference="p"),
        _directional(), _inert(), _artifact(),
    )
    for obj in instances:
        assert not hasattr(obj, "__dict__")  # slotted: no storage for injected fields
    # frozen forbids reassigning a declared field
    with pytest.raises(dataclasses.FrozenInstanceError):
        _silver().silver_artifact_locator_text = "x"
    # slotted + frozen: an unknown attribute can never be stored (the frozen+slots __setattr__
    # raises; CPython surfaces this as TypeError for a non-declared name) and leaves nothing behind
    target = _inert()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
        target.injected_extra = 1
    assert not hasattr(target, "injected_extra")
