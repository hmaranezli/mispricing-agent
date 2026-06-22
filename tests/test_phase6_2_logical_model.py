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


def test_duration_signed64_range_endpoints():
    assert lm.MIN_HYPOTHETICAL_WINDOW_DURATION_MS == 0
    assert lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS == 9223372036854775807  # 2^63 - 1
    _max = lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS
    # endpoints accepted (factory + direct construction), both variants
    assert _directional(dur=0).hypothetical_window_duration_ms == 0
    assert _directional(dur=_max).hypothetical_window_duration_ms == _max
    assert _inert(dur=_max).hypothetical_window_duration_ms == _max
    assert lm.InertShadowIntentDefinition(
        exposure_orientation=lm.INERT_STATE, hypothetical_window_duration_ms=_max
    ).hypothetical_window_duration_ms == _max
    # MAX + 1 rejected (factory + direct construction)
    with pytest.raises(lm.LogicalModelError):
        _directional(dur=_max + 1)
    with pytest.raises(lm.LogicalModelError):
        lm.InertShadowIntentDefinition(
            exposure_orientation=lm.INERT_STATE, hypothetical_window_duration_ms=_max + 1
        )


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


# =================================================================================================
# Slice-A Runtime Extension — Lifecycle Slot / Root-Evidence / Dual-Snapshot value types
# Effective ratified contract: 85de568 as superseded by 38eccce (exactness), 9fc7749 (U+200B
# source-fidelity), 01331ec (typo). Historical superseded clauses do not govern.
# =================================================================================================

from types import MappingProxyType as _MP  # noqa: E402


def _ctx(v="hyperliquid", p="BTC-USD"):
    return lm.EstablishedRootContext(source_venue_context_text=v, source_pair_context_text=p)


def _established(anchor="1700000000000"):
    return lm.EstablishedRootEvidence(root_context=_ctx(), provenance_anchor_timestamp_text=anchor)


def _slot(key=None, state=lm.INTENT_RECORDED, root=_UNSET):
    if key is None:
        key = _silver()
    if root is _UNSET:
        root = _established()
    return lm.ShadowIntentLifecycleSlot(
        shadow_intent_identity_reference=key, lifecycle_state=state, root_evidence=root
    )


# --- EstablishedRootContext: strip semantics + U+200B verbatim acceptance ------------------------

def test_established_root_context_accepts_two_nonblank_str_verbatim():
    c = lm.EstablishedRootContext(source_venue_context_text=" Hyper Liquid ", source_pair_context_text="BTC")
    assert c.source_venue_context_text == " Hyper Liquid "   # verbatim, surrounding ws preserved
    assert c.source_pair_context_text == "BTC"


def test_established_root_context_u200b_only_and_containing_accepted_verbatim():
    zwsp = "​"
    c = lm.EstablishedRootContext(source_venue_context_text=zwsp, source_pair_context_text=zwsp + "BTC")
    assert c.source_venue_context_text == zwsp           # U+200B alone is non-blank, accepted verbatim
    assert c.source_pair_context_text == zwsp + "BTC"    # zero-width char not stripped


def test_established_root_context_rejects_empty_and_strip_blanks():
    blanks = ("", " ", "\t", "\n", " ", " ", "　", "  \t\n ")
    for b in blanks:
        assert b.strip() == ""  # proof: each reduces to "" under Python str.strip()
        with pytest.raises(lm.LogicalModelError):
            lm.EstablishedRootContext(source_venue_context_text=b, source_pair_context_text="BTC")
        with pytest.raises(lm.LogicalModelError):
            lm.EstablishedRootContext(source_venue_context_text="venue", source_pair_context_text=b)


def test_established_root_context_rejects_non_str_and_is_frozen_slotted_kw_only():
    for bad in (1, None, b"x", ["v"]):
        with pytest.raises(lm.LogicalModelError):
            lm.EstablishedRootContext(source_venue_context_text=bad, source_pair_context_text="BTC")
    c = _ctx()
    assert not hasattr(c, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.source_venue_context_text = "x"
    with pytest.raises(TypeError):
        lm.EstablishedRootContext("venue", "pair")  # positional rejected (kw_only)


# --- EstablishedRootEvidence: ASCII-only canonical anchor timestamp -------------------------------

def test_established_root_evidence_accepts_canonical_anchor_and_context():
    for ok in ("0", "1", "123", "9223372036854775807"):
        e = lm.EstablishedRootEvidence(root_context=_ctx(), provenance_anchor_timestamp_text=ok)
        assert e.provenance_anchor_timestamp_text == ok
        assert e.root_context.source_venue_context_text == "hyperliquid"


def test_established_root_evidence_rejects_noncanonical_anchor_text():
    bad = ("00", "007", "0123", "-1", "+1", "1.0", "1e3", " 1", "1 ", "", "1_000", "abc")
    for b in bad:
        with pytest.raises(lm.LogicalModelError):
            lm.EstablishedRootEvidence(root_context=_ctx(), provenance_anchor_timestamp_text=b)


def test_established_root_evidence_rejects_unicode_digit_anchor():
    # ASCII digits only — \d / Unicode decimal digits are banned even though they are "digits"
    for uni in ("١", "१२३", "１"):  # ١, १२३, １ (fullwidth)
        with pytest.raises(lm.LogicalModelError):
            lm.EstablishedRootEvidence(root_context=_ctx(), provenance_anchor_timestamp_text=uni)


def test_established_root_evidence_rejects_non_str_anchor_and_non_context():
    with pytest.raises(lm.LogicalModelError):
        lm.EstablishedRootEvidence(root_context=_ctx(), provenance_anchor_timestamp_text=123)
    with pytest.raises(lm.LogicalModelError):
        lm.EstablishedRootEvidence(root_context="not-a-context", provenance_anchor_timestamp_text="1")
    # forged context (object.__new__ bypass) revalidated
    poison = object.__new__(lm.EstablishedRootContext)
    object.__setattr__(poison, "source_venue_context_text", "")
    object.__setattr__(poison, "source_pair_context_text", "BTC")
    with pytest.raises(lm.LogicalModelError):
        lm.EstablishedRootEvidence(root_context=poison, provenance_anchor_timestamp_text="1")


def test_no_root_evidence_is_zero_field_slotted():
    assert dataclasses.fields(lm.NoRootEvidence) == ()
    assert not hasattr(lm.NoRootEvidence(), "__dict__")


# --- ShadowIntentLifecycleSlot: lifecycle/root compatibility matrix -------------------------------

def test_slot_audit_replayed_requires_no_root_evidence():
    s = _slot(state=lm.AUDIT_REPLAYED, root=lm.NoRootEvidence())
    assert s.lifecycle_state == lm.AUDIT_REPLAYED
    assert type(s.root_evidence) is lm.NoRootEvidence
    with pytest.raises(lm.LogicalModelError):
        _slot(state=lm.AUDIT_REPLAYED, root=_established())  # established root illegal for AUDIT_REPLAYED


def test_slot_established_states_require_established_root_evidence():
    for state in (lm.INTENT_RECORDED, lm.HYPOTHETICAL_CONDITION_MET, lm.INTENT_EXPIRED, lm.INTENT_RETIRED):
        s = _slot(state=state, root=_established())
        assert s.lifecycle_state == state
        assert type(s.root_evidence) is lm.EstablishedRootEvidence
        with pytest.raises(lm.LogicalModelError):
            _slot(state=state, root=lm.NoRootEvidence())  # NoRootEvidence illegal for established states


def test_slot_rejects_invalid_state_identity_and_root_variant():
    with pytest.raises(lm.LogicalModelError):
        _slot(state="PENDING")
    with pytest.raises(lm.LogicalModelError):
        _slot(key="not-a-key")
    with pytest.raises(lm.LogicalModelError):
        _slot(root="not-a-variant")
    with pytest.raises(lm.LogicalModelError):
        _slot(root=lm.NoPredecessor())  # wrong (non-root) variant type


def test_slot_is_frozen_slotted_kw_only_and_revalidates_forged_nested():
    s = _slot()
    assert not hasattr(s, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.lifecycle_state = lm.INTENT_EXPIRED
    with pytest.raises(TypeError):
        lm.ShadowIntentLifecycleSlot(_silver(), lm.INTENT_RECORDED, _established())  # positional rejected
    # forged identity key inside the slot is revalidated on construction
    poison = object.__new__(lm.OpaqueSilverPairKey)
    object.__setattr__(poison, "silver_artifact_locator_text", 7)
    object.__setattr__(poison, "silver_physical_record_position_text", "0")
    with pytest.raises(lm.LogicalModelError):
        lm.ShadowIntentLifecycleSlot(
            shadow_intent_identity_reference=poison, lifecycle_state=lm.AUDIT_REPLAYED,
            root_evidence=lm.NoRootEvidence(),
        )


# --- ShadowLifecycleSnapshot: factory-only, exact field, alias resistance, equality ---------------

def test_shadow_snapshot_exact_field_and_factory_builds_mappingproxy():
    k = _silver("a", "0")
    snap = lm.make_shadow_lifecycle_snapshot(slot_entries=((k, _slot(key=k)),))
    assert tuple(f.name for f in dataclasses.fields(lm.ShadowLifecycleSnapshot)) == ("slots_by_identity",)
    assert type(snap.slots_by_identity) is _MP
    assert snap.slots_by_identity[k].lifecycle_state == lm.INTENT_RECORDED


def test_shadow_snapshot_empty_valid_and_direct_construction_raises():
    empty = lm.make_shadow_lifecycle_snapshot(slot_entries=())
    assert len(empty.slots_by_identity) == 0
    with pytest.raises(lm.LogicalModelError):
        lm.ShadowLifecycleSnapshot(slots_by_identity={})
    with pytest.raises(lm.LogicalModelError):
        lm.ShadowLifecycleSnapshot()


def test_shadow_snapshot_alias_resistance_and_immutability():
    k = _silver("a", "0")
    snap = lm.make_shadow_lifecycle_snapshot(slot_entries=((k, _slot(key=k)),))
    with pytest.raises(TypeError):
        snap.slots_by_identity[k] = _slot(key=k)  # read-only proxy, no mutation
    with pytest.raises(TypeError):
        del snap.slots_by_identity[k]


def test_shadow_snapshot_rejects_caller_dict_and_malformed_entries():
    k = _silver("a", "0")
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries={k: _slot(key=k)})  # not an exact tuple
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=[(k, _slot(key=k))])  # list, not tuple
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=((k, _slot(key=k), "extra"),))  # 3-tuple
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=((k,),))  # 1-tuple
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=(["k", _slot(key=k)],))  # entry is list


def test_shadow_snapshot_rejects_duplicate_key_forged_and_key_slot_mismatch():
    k1, k2 = _silver("a", "0"), _silver("b", "1")
    # duplicate key
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=((k1, _slot(key=k1)), (k1, _slot(key=k1))))
    # key != slot.shadow_intent_identity_reference
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=((k1, _slot(key=k2)),))
    # forged key
    pk = object.__new__(lm.OpaqueSilverPairKey)
    object.__setattr__(pk, "silver_artifact_locator_text", 1)
    object.__setattr__(pk, "silver_physical_record_position_text", "0")
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=((pk, _slot(key=k1)),))
    # forged slot (bypassed __post_init__, illegal state/root invariant)
    ps = object.__new__(lm.ShadowIntentLifecycleSlot)
    object.__setattr__(ps, "shadow_intent_identity_reference", k1)
    object.__setattr__(ps, "lifecycle_state", lm.INTENT_RECORDED)
    object.__setattr__(ps, "root_evidence", lm.NoRootEvidence())  # illegal pairing
    with pytest.raises(lm.LogicalModelError):
        lm.make_shadow_lifecycle_snapshot(slot_entries=((k1, ps),))


def test_shadow_snapshot_equality_is_content_based_and_order_independent():
    k1, k2 = _silver("a", "0"), _silver("b", "1")
    s1, s2 = _slot(key=k1), _slot(key=k2, state=lm.HYPOTHETICAL_CONDITION_MET)
    a = lm.make_shadow_lifecycle_snapshot(slot_entries=((k1, s1), (k2, s2)))
    b = lm.make_shadow_lifecycle_snapshot(slot_entries=((k2, s2), (k1, s1)))  # reversed order
    assert a == b
    c = lm.make_shadow_lifecycle_snapshot(slot_entries=((k1, s1),))
    assert a != c


# --- SeenTargetPairsSnapshot: factory-only, frozenset, duplicate rejection, equality --------------

def test_seen_pairs_snapshot_exact_field_and_factory_builds_frozenset():
    k1, k2 = _silver("a", "0"), _silver("b", "1")
    snap = lm.make_seen_target_pairs_snapshot(members=(k1, k2))
    assert tuple(f.name for f in dataclasses.fields(lm.SeenTargetPairsSnapshot)) == ("seen_target_pairs",)
    assert type(snap.seen_target_pairs) is frozenset
    assert snap.seen_target_pairs == frozenset({k1, k2})


def test_seen_pairs_snapshot_empty_valid_and_direct_construction_raises():
    empty = lm.make_seen_target_pairs_snapshot(members=())
    assert empty.seen_target_pairs == frozenset()
    with pytest.raises(lm.LogicalModelError):
        lm.SeenTargetPairsSnapshot(seen_target_pairs=frozenset())
    with pytest.raises(lm.LogicalModelError):
        lm.SeenTargetPairsSnapshot()


def test_seen_pairs_snapshot_rejects_non_tuple_duplicate_and_forged_members():
    k1 = _silver("a", "0")
    with pytest.raises(lm.LogicalModelError):
        lm.make_seen_target_pairs_snapshot(members=[k1])  # list, not tuple
    with pytest.raises(lm.LogicalModelError):
        lm.make_seen_target_pairs_snapshot(members={k1})  # set, not tuple
    with pytest.raises(lm.LogicalModelError):
        lm.make_seen_target_pairs_snapshot(members=(k1, k1))  # duplicate — no silent dedup
    with pytest.raises(lm.LogicalModelError):
        lm.make_seen_target_pairs_snapshot(members=("not-a-key",))
    pk = object.__new__(lm.OpaqueSilverPairKey)
    object.__setattr__(pk, "silver_artifact_locator_text", 1)
    object.__setattr__(pk, "silver_physical_record_position_text", "0")
    with pytest.raises(lm.LogicalModelError):
        lm.make_seen_target_pairs_snapshot(members=(pk,))


def test_seen_pairs_snapshot_equality_is_set_content_order_independent():
    k1, k2 = _silver("a", "0"), _silver("b", "1")
    a = lm.make_seen_target_pairs_snapshot(members=(k1, k2))
    b = lm.make_seen_target_pairs_snapshot(members=(k2, k1))  # reversed
    assert a == b
    c = lm.make_seen_target_pairs_snapshot(members=(k1,))
    assert a != c


# --- Slice-A ownership: logical_model remains an intra-package leaf ------------------------------

def test_logical_model_is_intra_package_leaf_stdlib_only():
    import ast
    import os
    src = os.path.join(os.path.dirname(lm.__file__), "logical_model.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    # no Phase 6.2 sibling, Phase 6.1, S1-storage, or Phase 5 imports — stdlib only
    for mod in imported:
        assert not mod.startswith("phase6_2_shadow_intent."), mod
        assert not mod.startswith("phase6_1"), mod
        assert not mod.startswith("phase5"), mod
