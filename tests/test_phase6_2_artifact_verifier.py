"""Slice B — Phase 6.2 artifact verification: focused RED→GREEN tests.

Exercises the Gate-B (`474cc6f`) fixed-schema canonical-byte + detached SHA-256 verification: one-read
discipline, digest-before-parse ordering, strict UTF-8/JSON with duplicate-member detection, exact
variant/member/grammar/order validation, Slice-A logical projection, and byte-for-byte canonical
re-encoding. No writer, sidecar, fallback, S1 access, or second artifact.
"""
import hashlib
import json

import pytest

from phase6_2_shadow_intent import logical_model as lm
from phase6_2_shadow_intent import artifact_verifier as av


FSV = "PHASE6_2_SHADOW_INTENT_DEFINITION_ARTIFACT_FIELD_SHAPE_V1"


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(b):
    return hashlib.sha256(b).hexdigest()


def _root(*, predecessor=None, definitions=()):
    if predecessor is None:
        predecessor = {"kind": "NO_PREDECESSOR"}
    return {
        "artifact_field_shape_version_reference": FSV,
        "artifact_version_reference": "v1",
        "declarer_opaque_reference": "decl",
        "predecessor_artifact_version_reference": predecessor,
        "definitions_by_silver_pair": list(definitions),
    }


def _dir(loc, pos, orient="POSITIVE_EXPOSURE", mag="1.5", unit="proportion", dur="840000"):
    return {
        "definition_kind": "DIRECTIONAL_SHADOW_INTENT_DEFINITION",
        "silver_artifact_locator_text": loc, "silver_physical_record_position_text": pos,
        "exposure_orientation": orient, "passive_boundary_magnitude": mag,
        "boundary_unit_context": unit, "hypothetical_window_duration_ms": dur,
    }


def _inert(loc, pos, dur="840000"):
    return {
        "definition_kind": "INERT_SHADOW_INTENT_DEFINITION",
        "silver_artifact_locator_text": loc, "silver_physical_record_position_text": pos,
        "exposure_orientation": "INERT_STATE", "hypothetical_window_duration_ms": dur,
    }


class _Spy:
    """Caller-owned binary stream spy: counts reads; forbids seek/close/reread."""

    def __init__(self, data):
        self._data = data
        self.reads = 0
        self.closed = False

    def read(self, *a, **k):
        self.reads += 1
        return self._data

    def seek(self, *a, **k):
        raise AssertionError("verify_artifact must not seek the caller-owned stream")

    def close(self, *a, **k):
        self.closed = True
        raise AssertionError("verify_artifact must not close the caller-owned stream")


def _ref(digest):
    return av.make_sealed_artifact_reference(
        opaque_artifact_locator="opaque-locator", expected_detached_sha256_digest=digest
    )


def _verify(data, digest=None):
    spy = _Spy(data)
    result = av.verify_artifact(reference=_ref(_digest(data) if digest is None else digest), binary_stream=spy)
    return result, spy


def _expect_fail(data, digest=None, contains=None):
    spy = _Spy(data)
    with pytest.raises(av.ArtifactVerificationError) as exc:
        av.verify_artifact(reference=_ref(_digest(data) if digest is None else digest), binary_stream=spy)
    if contains is not None:
        assert contains in str(exc.value)
    return spy


# --- reference shape ------------------------------------------------------------------------------

def test_reference_is_frozen_slotted_two_fields():
    import dataclasses
    r = _ref(_digest(b"x"))
    names = tuple(f.name for f in dataclasses.fields(av.SealedArtifactReference))
    assert names == ("opaque_artifact_locator", "expected_detached_sha256_digest")
    assert not hasattr(r, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.opaque_artifact_locator = "y"


def test_invalid_digest_grammar_fails_before_read():
    for bad in ("ABC", "g" * 64, "0" * 63, "0" * 65, _digest(b"x").upper(), 123):
        spy = _Spy(b"{}")
        with pytest.raises(av.ArtifactVerificationError):
            av.verify_artifact(reference=_ref(bad), binary_stream=spy)
        assert spy.reads == 0  # digest grammar rejected before any read


# --- one-read + digest ----------------------------------------------------------------------------

def test_success_reads_exactly_once_and_never_closes():
    data = _canon(_root())
    result, spy = _verify(data)
    assert spy.reads == 1
    assert spy.closed is False
    assert type(result) is lm.ShadowIntentDefinitionArtifact


def test_every_post_read_failure_reads_exactly_once():
    cases = [
        _canon(_root()) + b"\n",                      # trailing newline (byte mismatch)
        b'{"a":1,"a":2}',                             # duplicate member
        _canon({"unexpected": "x"}),                  # wrong root members
        b'\xff\xfe',                                  # invalid UTF-8
    ]
    for data in cases:
        spy = _Spy(data)
        with pytest.raises(av.ArtifactVerificationError):
            av.verify_artifact(reference=_ref(_digest(data)), binary_stream=spy)
        assert spy.reads == 1


def test_digest_mismatch_precedes_parsing():
    spy = _Spy(b"this is not json at all")
    with pytest.raises(av.ArtifactVerificationError) as exc:
        av.verify_artifact(reference=_ref(_digest(b"different")), binary_stream=spy)
    assert "digest" in str(exc.value)  # failed on digest, never reached the parser
    assert spy.reads == 1


# --- encoding hygiene -----------------------------------------------------------------------------

def test_bom_rejected():
    data = b"\xef\xbb\xbf" + _canon(_root())
    _expect_fail(data)


def test_invalid_utf8_rejected():
    _expect_fail(b"\xff\xfe\xfa")


def test_leading_whitespace_and_trailing_newline_rejected():
    _expect_fail(b" " + _canon(_root()))
    _expect_fail(_canon(_root()) + b"\n")


def test_duplicate_object_member_rejected_before_dict():
    _expect_fail(b'{"a":"x","a":"y"}', contains="duplicate")


def test_noncanonical_member_order_fails_byte_identity():
    reordered = {
        "artifact_version_reference": "v1",
        "artifact_field_shape_version_reference": FSV,
        "declarer_opaque_reference": "decl",
        "predecessor_artifact_version_reference": {"kind": "NO_PREDECESSOR"},
        "definitions_by_silver_pair": [],
    }
    data = json.dumps(reordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _expect_fail(data)


def test_noncanonical_string_escaping_fails_byte_identity():
    data = _canon(_root()).replace(b'"v1"', b'"\\u0076\\u0031"')  # "v1" escaped -> noncanonical
    _expect_fail(data)


def test_lone_surrogate_rejected():
    data = _canon(_root()).replace(b'"decl"', b'"\\ud800"')
    _expect_fail(data)


# --- json type discipline -------------------------------------------------------------------------

def test_json_number_where_string_required_rejected():
    root = _root(definitions=[_inert("a", "0")])
    root["definitions_by_silver_pair"][0]["hypothetical_window_duration_ms"] = 840000  # number, not string
    _expect_fail(_canon(root))


def test_json_null_and_bool_rejected():
    r1 = _root(); r1["artifact_version_reference"] = None
    _expect_fail(_canon(r1))
    r2 = _root(); r2["artifact_version_reference"] = True
    _expect_fail(_canon(r2))


def test_nan_infinity_rejected():
    _expect_fail(b'{"x":NaN}')
    _expect_fail(b'{"x":Infinity}')


# --- structural variants --------------------------------------------------------------------------

def test_unknown_and_missing_root_members_rejected():
    extra = _root(); extra["sixth"] = "x"
    _expect_fail(_canon(extra))
    missing = _root(); del missing["declarer_opaque_reference"]
    _expect_fail(_canon(missing))


def test_field_shape_literal_enforced():
    r = _root(); r["artifact_field_shape_version_reference"] = "WRONG_VERSION"
    _expect_fail(_canon(r))


def test_predecessor_variants_and_third_kind():
    # PredecessorReference accepted
    ref_pred = {"kind": "PREDECESSOR_REFERENCE", "opaque_reference": "prev"}
    result, _ = _verify(_canon(_root(predecessor=ref_pred)))
    assert type(result.predecessor_artifact_version_reference) is lm.PredecessorReference
    assert result.predecessor_artifact_version_reference.opaque_reference == "prev"
    # third kind rejected
    _expect_fail(_canon(_root(predecessor={"kind": "MAYBE"})))
    # NO_PREDECESSOR with extra member rejected
    _expect_fail(_canon(_root(predecessor={"kind": "NO_PREDECESSOR", "opaque_reference": "x"})))
    # PREDECESSOR_REFERENCE missing opaque_reference rejected
    _expect_fail(_canon(_root(predecessor={"kind": "PREDECESSOR_REFERENCE"})))


def test_definition_variants_and_member_sets():
    # directional + inert valid
    d = _dir("a", "0"); i = _inert("b", "1")
    result, _ = _verify(_canon(_root(definitions=[d, i])))
    assert len(result.definitions_by_silver_pair) == 2
    # inert carrying a boundary -> extra member rejected
    bad_inert = _inert("a", "0"); bad_inert["passive_boundary_magnitude"] = "1.5"
    _expect_fail(_canon(_root(definitions=[bad_inert])))
    # directional missing unit rejected
    bad_dir = _dir("a", "0"); del bad_dir["boundary_unit_context"]
    _expect_fail(_canon(_root(definitions=[bad_dir])))
    # unknown definition_kind rejected
    bad_kind = _inert("a", "0"); bad_kind["definition_kind"] = "OTHER"
    _expect_fail(_canon(_root(definitions=[bad_kind])))


def test_orientation_must_match_kind():
    _expect_fail(_canon(_root(definitions=[_dir("a", "0", orient="INERT_STATE")])))
    bad = _inert("a", "0"); bad["exposure_orientation"] = "POSITIVE_EXPOSURE"
    _expect_fail(_canon(_root(definitions=[bad])))


# --- grammars -------------------------------------------------------------------------------------

def test_invalid_decimal_grammar_rejected():
    for bad in ("+1", "1e3", " 1 ", "", "abc", "01", "1.50", "-0", "1."):
        _expect_fail(_canon(_root(definitions=[_dir("a", "0", mag=bad)])))


def test_valid_decimal_forms_accepted():
    for good in ("0", "-0.25", "100", "0.001", "1.5"):
        result, _ = _verify(_canon(_root(definitions=[_dir("a", "0", mag=good)])))
        key = next(iter(result.definitions_by_silver_pair))
        import decimal
        assert result.definitions_by_silver_pair[key].passive_boundary_magnitude == decimal.Decimal(good)


def test_invalid_duration_grammar_rejected():
    for bad in ("01", "-1", "1.0", "1e3", " 1", ""):
        _expect_fail(_canon(_root(definitions=[_inert("a", "0", dur=bad)])))


# --- ordering / duplicates ------------------------------------------------------------------------

def test_strictly_ascending_silver_order_enforced():
    # equal pairs (duplicate) rejected
    _expect_fail(_canon(_root(definitions=[_inert("a", "0"), _inert("a", "0")])))
    # descending rejected
    _expect_fail(_canon(_root(definitions=[_inert("b", "0"), _inert("a", "0")])))
    # ascending accepted (locator first, then position)
    result, _ = _verify(_canon(_root(definitions=[_inert("a", "0"), _inert("a", "1"), _inert("b", "0")])))
    assert len(result.definitions_by_silver_pair) == 3


# --- projection ----------------------------------------------------------------------------------

def test_projection_uses_exact_slice_a_types_and_is_immutable():
    result, _ = _verify(_canon(_root(definitions=[_dir("a", "0"), _inert("b", "1")])))
    assert type(result) is lm.ShadowIntentDefinitionArtifact
    for k, v in result.definitions_by_silver_pair.items():
        assert type(k) is lm.OpaqueSilverPairKey
        assert type(v) in (lm.DirectionalShadowIntentDefinition, lm.InertShadowIntentDefinition)
    with pytest.raises(TypeError):
        result.definitions_by_silver_pair[lm.make_opaque_silver_pair_key(
            silver_artifact_locator_text="z", silver_physical_record_position_text="9")] = None


def test_no_public_writer_surface():
    # Slice B exposes verification only — no artifact-authoring/writer/serialize entrypoint.
    for forbidden in ("write_artifact", "serialize_artifact", "encode_artifact", "make_artifact_bytes", "dump"):
        assert not hasattr(av, forbidden)


# --- duration signed-64 range (Slice B) -----------------------------------------------------------

_MAXD = "9223372036854775807"        # 2^63 - 1
_MAXD_PLUS_1 = "9223372036854775808"


def test_duration_max_text_accepted_and_round_trip():
    data = _canon(_root(definitions=[_inert("a", "0", dur=_MAXD)]))
    result, spy = _verify(data)
    assert spy.reads == 1
    key = next(iter(result.definitions_by_silver_pair))
    assert result.definitions_by_silver_pair[key].hypothetical_window_duration_ms == 9223372036854775807


def test_duration_zero_text_accepted():
    result, _ = _verify(_canon(_root(definitions=[_inert("a", "0", dur="0")])))
    key = next(iter(result.definitions_by_silver_pair))
    assert result.definitions_by_silver_pair[key].hypothetical_window_duration_ms == 0


def test_duration_overflow_and_overlong_rejected_without_raw_valueerror():
    # MAX + 1 (19 digits) rejected
    _expect_fail(_canon(_root(definitions=[_inert("a", "0", dur=_MAXD_PLUS_1)])))
    # 20-digit value rejected
    _expect_fail(_canon(_root(definitions=[_inert("a", "0", dur="1" + "0" * 19)])))
    # 5000-digit all-numeric value rejected as ArtifactVerificationError (no raw ValueError leak),
    # exactly one read
    data = _canon(_root(definitions=[_inert("a", "0", dur="9" * 5000)]))
    spy = _Spy(data)
    with pytest.raises(av.ArtifactVerificationError):
        av.verify_artifact(reference=_ref(_digest(data)), binary_stream=spy)
    assert spy.reads == 1


# --- reference self-validation (Slice B) ----------------------------------------------------------

def test_reference_direct_construction_self_validates():
    valid = _digest(b"x")
    with pytest.raises(av.ArtifactVerificationError):
        av.SealedArtifactReference(opaque_artifact_locator=1, expected_detached_sha256_digest=valid)
    with pytest.raises(av.ArtifactVerificationError):
        av.SealedArtifactReference(opaque_artifact_locator="l", expected_detached_sha256_digest="NOTHEX")
    with pytest.raises(av.ArtifactVerificationError):
        av.make_sealed_artifact_reference(opaque_artifact_locator="l", expected_detached_sha256_digest="short")
    # valid construction succeeds
    r = av.SealedArtifactReference(opaque_artifact_locator="l", expected_detached_sha256_digest=valid)
    assert r.expected_detached_sha256_digest == valid


def test_forged_or_non_reference_fails_before_read():
    poison = object.__new__(av.SealedArtifactReference)  # bypass __post_init__
    object.__setattr__(poison, "opaque_artifact_locator", "l")
    object.__setattr__(poison, "expected_detached_sha256_digest", "NOT_A_VALID_DIGEST")
    spy = _Spy(b"{}")
    with pytest.raises(av.ArtifactVerificationError):
        av.verify_artifact(reference=poison, binary_stream=spy)
    assert spy.reads == 0
    spy2 = _Spy(b"{}")
    with pytest.raises(av.ArtifactVerificationError):
        av.verify_artifact(reference="not a reference", binary_stream=spy2)
    assert spy2.reads == 0


# --- read / error-surface normalization (Slice B) -------------------------------------------------

class _RaisingRead:
    def __init__(self, exc):
        self._exc = exc
        self.reads = 0

    def read(self, *a, **k):
        self.reads += 1
        raise self._exc


def test_missing_read_normalized():
    class _NoRead:
        pass
    with pytest.raises(av.ArtifactVerificationError):
        av.verify_artifact(reference=_ref(_digest(b"x")), binary_stream=_NoRead())


def test_read_raising_ordinary_exceptions_normalized():
    for exc in (ValueError("closed file"), OSError("io"), Exception("boom")):
        s = _RaisingRead(exc)
        with pytest.raises(av.ArtifactVerificationError):
            av.verify_artifact(reference=_ref(_digest(b"x")), binary_stream=s)
        assert s.reads == 1


def test_read_raising_memoryerror_reraised_unwrapped():
    s = _RaisingRead(MemoryError())
    with pytest.raises(MemoryError):
        av.verify_artifact(reference=_ref(_digest(b"x")), binary_stream=s)


def test_read_raising_base_exceptions_unwrapped():
    for exc in (KeyboardInterrupt(), SystemExit(), GeneratorExit()):
        s = _RaisingRead(exc)
        with pytest.raises(type(exc)):
            av.verify_artifact(reference=_ref(_digest(b"x")), binary_stream=s)


def test_read_returning_non_bytes_normalized():
    class _StrRead:
        def read(self, *a, **k):
            return "not bytes"
    with pytest.raises(av.ArtifactVerificationError):
        av.verify_artifact(reference=_ref(_digest(b"x")), binary_stream=_StrRead())


# --- parser recursion normalization (Slice B) -----------------------------------------------------

def test_deeply_nested_json_normalized_to_verification_error():
    data = b"[" * 20000 + b"]" * 20000
    spy = _Spy(data)
    with pytest.raises(av.ArtifactVerificationError):
        av.verify_artifact(reference=_ref(_digest(data)), binary_stream=spy)
    assert spy.reads == 1
