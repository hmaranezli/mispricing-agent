# Phase 6.2 — Shadow Intent Definition Artifact Canonical-Encoding & Digest Charter (Gate B)

> **This is a docs-only Gate B charter.** It pins the **exact durable canonical byte representation, physical variant
> discriminators, deterministic map ordering, detached digest contract, and pre-replay verification rules** for the
> corrected Gate A logical shape. It **implements nothing and authorizes nothing executable**: no runtime code, no
> tests, no test execution, no lock-test edits, no frozen-component edits, no Phase 6.1 edits, no S1-adapter edits,
> no loader/writer/verifier implementation, no predicate, no state machine, no container runtime, no executable
> integration, no Phase 6.2 runtime, no pytest, no graphify. It **does NOT alter** any Gate A logical field, logical
> variant, cardinality, unit, or validation semantic — **Gate B defines physical representation only.** It makes
> **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_gate_a_predecessor_option_sum_targeted_correction_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_field_shape_charter.md`,
> `docs/handoff/phase6_2_source_authority_determinism_targeted_amendment_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_source_boundary_charter.md`, the earlier Phase 6.2
> charters, the S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `107106775af4e59b52c7d445971897a10feb0475`

---

## 1. Base / Purpose

**Base commit:** `107106775af4e59b52c7d445971897a10feb0475`.

Gate A (`5dc757c`), as corrected by the predecessor option-sum charter (`1071067`), pinned the **logical** shape of
the sealed scenario-definition artifact. This is **Gate B**: it pins the **physical durable representation** of that
logical shape — exactly one canonical UTF-8 JSON document, the physical variant discriminators for the predecessor
option-sum and the definition union, the deterministic Silver-pair map ordering, the duplicate-rejection rule, the
canonical decimal/duration string grammars, the **detached SHA-256** digest contract, and the **pre-replay**
canonicality/integrity verification sequence. It **adds no logical field**; every physical discriminator is an
encoding artifact only.

**No capacity validation and no capacity pass is claimed by this charter** (see §19).

---

## 2. Evidence-First Input-Shape Inspection (one-to-one mapping confirmed)

**Inspected and cited:**

- **`5dc757c`** (Gate A field-shape): the closed five-field envelope, the closed `DirectionalShadowIntentDefinition`
  / `InertShadowIntentDefinition` union, the `OpaqueSilverPairKey` (two opaque text scalars), orientation
  vocabulary, exact-decimal boundary, opaque unit token, integer-ms window.
- **`1071067`** (predecessor option-sum correction): the **always-five-field** envelope; `predecessor_artifact_
  version_reference` **always present**, valued by the closed `PredecessorArtifactVersionOption = NoPredecessor |
  PredecessorReference`.
- **`abd1b41`** (source-authority amendment): two-authority law (S1 = observed; artifact = declared); logical
  determinism only; window roles (anchor/declared-duration/comparison).
- **`07135be`** (source-boundary): sealed-before-replay lifecycle; explicit single-artifact selection; no fallback.
- **The S1 canonical JSON projection** (`phase6_1_s1_storage/s1_durable_sqlite_sink.py` — `json.dumps(..., sort_keys=
  True, separators=(",",":"), ensure_ascii=False, allow_nan=False)`): cited **only as repository precedent** that a
  sorted-key, whitespace-free, NaN-free canonical JSON discipline already exists in this repo. It is **NOT**
  authorization to reuse its **generic recursive `_project`** — Gate B's encoding is a distinct, stricter,
  purpose-built closed-world profile (§4), not a generic projector.

**Mapping (one-to-one, no added logical field):** every Gate A logical element maps to exactly one canonical JSON
construct — the three direct opaque references → JSON strings; the predecessor option → a `{kind}` object variant;
the definitions map → a sorted JSON array of entry objects; orientation → ASCII enum string; boundary magnitude →
canonical-decimal JSON string; unit token → opaque JSON string; window duration → canonical-duration JSON string;
the Silver-pair key → its **two existing** opaque text components materialized as two entry members (not a fused
key). The physical `kind` / `definition_kind` discriminators are **encoding artifacts only** (`5dc757c`/`1071067`
add none). **The corrected Gate A shape maps one-to-one into one canonical physical representation without adding any
logical field; the §2 STOP condition is NOT triggered.**

---

## 3. Durable Format Selection (binding)

The artifact is **exactly one complete UTF-8 canonical JSON document**. Physical constraints:

- **UTF-8 only**; **no BOM**; **no leading or trailing whitespace**; **no trailing newline**; **no comments**;
- **no JSONL / multiple documents**; **no compression or encryption wrapper**;
- **no NaN, infinity, binary float, or JSON numeric approximation** anywhere;
- **no duplicate object member names**; **no unknown object members**;
- **no tolerant parsing, repair, coercion, defaulting, or normalization.**

The document is a single, whole, self-contained byte string; anything else is rejected (§14, §18).

---

## 4. Canonical JSON Profile (binding)

One exact canonical JSON profile, equivalent to these requirements:

- **objects encoded with deterministic member ordering** (member names ordered by the cited standard's rule);
- **arrays preserve their explicitly defined canonical order** (for `definitions_by_silver_pair`, the §7 Silver-pair
  byte order — never insertion order);
- **no insignificant whitespace** (no space between tokens, members, or array elements);
- **strings encoded as canonical JSON strings in UTF-8**;
- **reject invalid Unicode and lone surrogate code points**;
- **preserve opaque string code points exactly**;
- **NO Unicode normalization, case folding, trimming, or locale transformation**;
- **equivalent-but-differently-escaped or differently-ordered input is rejected** unless its bytes **exactly equal**
  the canonical re-encoding (§14).

The charter **cites RFC 8785 / JCS** for JSON **string and object** canonicalization (canonical string escaping,
deterministic member-name ordering, minimal whitespace), but **explicitly OVERRIDES numeric handling**: **logical
decimals and integer durations are encoded as canonical JSON STRINGS, never JSON numbers** (RFC 8785's
ECMAScript-number serialization is **not** used for any artifact value — §11, §12). No artifact value is ever a JSON
number.

---

## 5. Exact Root Object (binding)

The canonical root object contains **exactly the five corrected Gate A envelope members and no sixth member**:

1. `artifact_field_shape_version_reference`
2. `artifact_version_reference`
3. `declarer_opaque_reference`
4. `predecessor_artifact_version_reference`
5. `definitions_by_silver_pair`

(Physically serialized in the profile's deterministic member-name order; the list above is the logical roster, not a
byte order.) **`artifact_field_shape_version_reference`** is pinned to one exact ASCII literal for this profile:

```
PHASE6_2_SHADOW_INTENT_DEFINITION_ARTIFACT_FIELD_SHAPE_V1
```

The remaining opaque references (`artifact_version_reference`, `declarer_opaque_reference`) are encoded as canonical
JSON strings and remain **semantically uninterpreted** (`5dc757c` §4 / `1071067` §6).

---

## 6. Predecessor Option Physical Discriminator (binding)

`predecessor_artifact_version_reference` is encoded as **exactly one object variant**:

- **A. `NoPredecessor`:** `{"kind":"NO_PREDECESSOR"}` — **exactly one member**, **no payload**.
- **B. `PredecessorReference`:** `{"kind":"PREDECESSOR_REFERENCE","opaque_reference":"..."}` — **exactly two
  members**; `opaque_reference` is the carried opaque reference (canonical JSON string, semantically uninterpreted).

**No** null, omitted field, empty-object substitute, boolean, numeric sentinel, string sentinel, or third `kind`.
The physical **`kind`** member is an **encoding discriminator only**; it does **not** become a Gate A domain field
(the logical type remains the `1071067` `NoPredecessor | PredecessorReference` option-sum).

---

## 7. Logical Map Physical Representation (binding)

`definitions_by_silver_pair` is encoded as a **JSON array of definition-entry objects**, **never** as a JSON object
keyed by a fused Silver-pair string. Reasons: the Silver pair **remains two separate opaque components**; duplicate
encoded pairs **must remain detectable before** logical-map construction (§8); and **no concatenated / fused identity
is minted**.

Before encoding, entries are **sorted by this exact tuple**:

```
( UTF8(silver_artifact_locator_text), UTF8(silver_physical_record_position_text) )
```

using **unsigned byte-wise lexicographic comparison** on the **original, non-normalized** string code points encoded
as UTF-8 (locator compared first; position compared only to break a locator tie). **No** locale ordering,
natural-number ordering, integer parsing, case folding, Unicode normalization, or insertion-order dependence.

---

## 8. Duplicate Encoded-Key Rejection (binding)

A decoder **must examine the complete encoded entry sequence before constructing the logical map.** If two entries
contain the **same exact pair** (both `silver_artifact_locator_text` and `silver_physical_record_position_text` byte
sequences equal):

- **hard pre-flight failure** — **no** first-wins, last-wins, overwrite, merge, deduplication, or partial map.

The encoded array **must already be in strict canonical Silver-pair order** (§7). **Equal or descending adjacent keys
are invalid** (strictly ascending only) — this makes duplicates and mis-ordering detectable in a single pass.

---

## 9. Definition Variant Physical Discriminators (binding)

Each definition entry carries the **two Silver-key components plus one physical `definition_kind` discriminator**:

- **A. Directional** — `definition_kind` = `DIRECTIONAL_SHADOW_INTENT_DEFINITION`. Required logical content (exactly
  these members, no more):
  - `silver_artifact_locator_text`
  - `silver_physical_record_position_text`
  - `exposure_orientation`
  - `passive_boundary_magnitude`
  - `boundary_unit_context`
  - `hypothetical_window_duration_ms`
- **B. Inert** — `definition_kind` = `INERT_SHADOW_INTENT_DEFINITION`. Required logical content (exactly these
  members, no more):
  - `silver_artifact_locator_text`
  - `silver_physical_record_position_text`
  - `exposure_orientation`
  - `hypothetical_window_duration_ms`

**Inert encoding MUST NOT contain `passive_boundary_magnitude` or `boundary_unit_context`** (their absence is the
variant's structure, `5dc757c` §7 — not null/sentinel). The **`definition_kind`** member is a **physical
discriminator only** and does **not** add a Gate A domain field. **Unknown discriminator, missing member, extra
member, or wrong variant/member combination is a hard pre-flight failure** (§18).

---

## 10. Orientation Encoding (binding)

Encode **exact ASCII string values only**: `POSITIVE_EXPOSURE`, `NEGATIVE_EXPOSURE`, `INERT_STATE`.

- **Directional** kind admits only `POSITIVE_EXPOSURE` or `NEGATIVE_EXPOSURE`.
- **Inert** kind admits only `INERT_STATE`.
- **No** aliases, alternate case, whitespace, normalization, integer enum, sign inference, or default. Any other
  value (or a mismatch between `definition_kind` and orientation) is a hard pre-flight failure.

---

## 11. Canonical Exact-Decimal Grammar (binding)

`passive_boundary_magnitude` is encoded as a **JSON string** using **one unique canonical decimal grammar**:

- **zero is exactly `"0"`**;
- optional leading `"-"` **only** for non-zero negative values;
- **no leading `"+"`**;
- **no exponent notation**;
- integer part is `"0"` or begins with `[1-9]`;
- **no leading zeros**;
- optional fractional part begins with `"."`;
- fractional part contains digits and **ends in `[1-9]`**;
- **no trailing fractional zeros**;
- **no trailing decimal point**;
- **`"-0"` and every negative-zero spelling are forbidden**;
- **no whitespace, locale separator, NaN, infinity, or binary-float conversion**.

**The same logical exact-decimal value has exactly one encoded string representation** (canonical uniqueness). This
realizes the Gate A `5dc757c` §8 logical exact-decimal contract physically — as a string, never a JSON number.

---

## 12. Canonical Duration Grammar (binding)

`hypothetical_window_duration_ms` is encoded as a **JSON string, not a JSON number**. Canonical grammar:

- `"0"` **or** a non-zero digit `[1-9]` followed by zero or more digits `[0-9]`;
- **no sign**; **no leading zeros**; **no decimal point**; **no exponent**; **no whitespace**; **no boolean**; **no
  alternate unit**.

Decoding yields the Gate A (`5dc757c` §9) logical **exact non-negative integer milliseconds** value (and a JSON
`true`/`false`, a leading-zero form, or a numeric encoding is rejected — `bool` is not an integer here).

---

## 13. Opaque String Preservation (binding)

The following are encoded as canonical JSON strings **preserving their exact Unicode scalar sequence**:

- `silver_artifact_locator_text`
- `silver_physical_record_position_text`
- `artifact_version_reference`
- `declarer_opaque_reference`
- `PredecessorReference.opaque_reference`
- `boundary_unit_context`

**Do not** parse, normalize, trim, case-fold, classify, redact, or infer semantics. **`silver_physical_record_
position_text` remains text and is NEVER decoded as an integer** (it is the opaque medium-position text from the S1
replay row, `b06d7ed` §6 — never a number to compute on). Canonical escaping follows the §4 profile; code points are
otherwise preserved verbatim.

---

## 14. Canonicality Verification (binding)

A future verifier must **reject before S1 replay** any of:

- invalid UTF-8; BOM; whitespace / noncanonical formatting; duplicate JSON members; unknown fields; **wrong member
  order** under the canonical profile; invalid variant discriminator (`kind` / `definition_kind`); invalid variant
  shape; **unsorted definition entries**; **duplicate Silver pairs**; invalid decimal grammar; invalid duration
  grammar; null/sentinel usage; and **any bytes that do not exactly equal the canonical re-encoding of the decoded
  logical artifact**.

**No repair or canonicalization-on-behalf-of-input is permitted. Noncanonical input is rejected, not rewritten.**
The verification is the byte-exact identity check: decode → validate Gate A logical shape → re-encode canonically →
require the re-encoding's bytes to equal the input bytes exactly.

---

## 15. Detached Digest Contract (binding)

Pin **SHA-256 over the exact canonical artifact bytes**. Digest representation:

- **exactly 64 lowercase hexadecimal ASCII characters**; **no prefix**; **no uppercase**; **no whitespace**.

The digest is **DETACHED**:

- **not** inside the canonical artifact; **not** a sixth envelope field; **not** an automatically-discovered sidecar
  artifact; **not** trusted from the filename; **not** derived from a mutable alias.

One explicit **caller-supplied `SealedArtifactReference`** consists of:

- one **opaque artifact locator / reference**;
- one **expected detached SHA-256 digest**.

The future verifier:

- **reads the selected artifact bytes exactly once before S1 replay**;
- **computes SHA-256 over those exact bytes**;
- **compares against the explicitly supplied expected digest**;
- **rejects mismatch before any S1 record is consumed**;
- **never silently substitutes another artifact** (consistent with `07135be` §4 explicit single selection, no
  fallback).

**Exact runtime API remains DEFERRED.**

---

## 16. Integrity, Not Authenticity (binding)

Explicitly:

- SHA-256 digest agreement proves **only** that the bytes match the expected detached digest (**integrity**).
- It does **NOT** prove **who** authored or declared the artifact.
- It is **NOT** a digital signature.
- `declarer_opaque_reference` is **provenance metadata, not cryptographic identity**.
- **No** authenticity, authorization, trust-chain, signing-key, certificate, or non-repudiation claim is made.
- **Any future signature / authentication boundary requires a separate charter.**

---

## 17. Seal Lifecycle (binding)

An artifact is considered **physically verified for replay only after** all of:

1. exact artifact reference supplied;
2. bytes read completely;
3. detached digest matched (§15);
4. canonical-byte validation passed (§14);
5. Gate A logical validation passed (`5dc757c`/`1071067`);
6. immutable projection successfully constructed.

**All must complete before the first S1 audit record is consumed.** Afterward: **no reread, no reload, no
replacement, no mutation, no partial refresh, no second artifact** (`07135be` §5 / `abd1b41`). **No `is_sealed` field
is introduced** — sealing is the source-lifecycle property, proven by the verification sequence, not a byte field
(`5dc757c` §13).

---

## 18. Error Taxonomy (binding)

**Every Gate B violation is a pre-replay hard failure:** unreadable / incomplete artifact; digest mismatch;
malformed / noncanonical JSON; invalid UTF-8; duplicate object member; duplicate Silver pair; wrong ordering;
unknown field / `kind`; invalid decimal / duration; Gate A shape violation; inability to construct the frozen
projection.

For every one: **No S4 fallback. No S1 / Phase 6.1 mutation. No default artifact. No equality-only downgrade. No
partial replay or partial state.** The failure aborts **before** the first S1 record is consumed.

---

## 19. Anti-Actionability & Quarantine (binding)

- The encoding / digest carries **no execution meaning**.
- **No** endpoint, credential, account identifier, broker / exchange integration, callback, emission hook, quantity,
  allocation, route, live flag, or production-risk control may appear.
- **Capacity remains DEFERRED at exactly 0 emit sites.**
- **Phase 6.1 remains frozen, COMPLETE + RATIFIED.**
- **Phase 6.2 remains UNBUILT and NOT runtime-ready.**

---

## 20. Precise Post-Charter State (ratified)

Gate B pins **only**: the durable **canonical JSON bytes** (§3, §4); the **physical variant discriminators** (§6,
§9); the **map ordering** (§7); **duplicate rejection** (§8); the **decimal / integer string grammars** (§11, §12);
the **detached SHA-256 digest** (§15); and the **canonicality / integrity verification contract** (§14, §16, §17,
§18).

**Still unbuilt:** the **loader / writer / verifier runtime**; the **artifact DTO runtime**; the **predicate
runtime**; the **state machine**; the **shadow container runtime**; and **any executable integration**.

- **Phase 6.1:** frozen, COMPLETE + RATIFIED. **Capacity:** deferred (0 emit sites). **Production / live / paper /
  canary / execution / routing / actionability:** forbidden.
- **Terminal invariant (unchanged):** at most one terminal per intent; open frozen non-terminal state at replay EOF
  is valid audit state.
- **No runtime TDD becomes eligible from Gate B alone.**

---

## 21. Next Safe Gate

- **Phase 6.2 Evidence-Intersection Classification Predicate Charter** (docs-only) — the next separately-authorized
  gate. That later charter must use: the **corrected Gate A logical fields**; the **Gate B verified frozen artifact
  projection**; the **exact S1 canonical evidence paths**; and **bounded passive classification only**.
- **This charter does NOT open, draft, or perform that charter.**

**Conclusion:** the sealed scenario-definition artifact's **physical durable representation** is pinned (Gate B,
docs-only) as **exactly one complete UTF-8 canonical JSON document** (no BOM / whitespace / trailing newline /
comments / JSONL / compression / encryption / NaN / infinity / binary float / numeric approximation / duplicate
members / unknown members / tolerant parsing). The **canonical profile** cites RFC 8785 / JCS for **string + object**
canonicalization (deterministic member-name ordering, minimal whitespace, canonical UTF-8 strings, lone-surrogate
rejection, code-points preserved, no Unicode normalization / case-fold / trim / locale) but **overrides numerics**:
**all decimals and durations are canonical JSON STRINGS, never JSON numbers**. The **root object** has exactly the
five corrected Gate A members (no sixth), with `artifact_field_shape_version_reference` =
`PHASE6_2_SHADOW_INTENT_DEFINITION_ARTIFACT_FIELD_SHAPE_V1`. The **predecessor option** encodes as exactly
`{"kind":"NO_PREDECESSOR"}` (one member) or `{"kind":"PREDECESSOR_REFERENCE","opaque_reference":"..."}` (two
members) — no null / sentinel / boolean / third kind. **`definitions_by_silver_pair`** encodes as a **JSON array**
(never a fused-key object) **sorted strictly ascending** by `(UTF8(silver_artifact_locator_text),
UTF8(silver_physical_record_position_text))` under **unsigned byte-wise lexicographic** comparison on original
non-normalized code points; **equal or descending adjacent keys are invalid** and **duplicate Silver pairs are a
hard pre-flight failure** (no first/last/overwrite/merge/dedup/partial). Each **definition entry** carries the two
Silver-key text components plus a **`definition_kind`** discriminator —
`DIRECTIONAL_SHADOW_INTENT_DEFINITION` {orientation ∈ {`POSITIVE_EXPOSURE`,`NEGATIVE_EXPOSURE`},
`passive_boundary_magnitude`, `boundary_unit_context`, `hypothetical_window_duration_ms`} or
`INERT_SHADOW_INTENT_DEFINITION` {orientation = `INERT_STATE`, `hypothetical_window_duration_ms`} (inert **must not**
carry boundary/unit). **Orientation** is exact ASCII only. **`passive_boundary_magnitude`** uses the unique canonical
decimal grammar (`"0"`; minus only for non-zero negatives; no `+`/exponent/leading-zeros/trailing-fractional-zeros/
trailing-point; `"-0"` forbidden) as a **string**; **`hypothetical_window_duration_ms`** uses the canonical
non-negative-integer grammar (`"0"` or `[1-9][0-9]*`, no sign/leading-zeros/point/exponent/bool) as a **string**.
All listed opaque strings (including the position text, **never decoded as an integer**) preserve their exact code
points. A future **verifier rejects, before S1 replay,** any invalid-UTF-8 / BOM / noncanonical-format /
duplicate-member / unknown-field / wrong-order / invalid-variant / unsorted-entry / duplicate-pair / invalid-decimal
/ invalid-duration / null-sentinel input and **any bytes not byte-exactly equal to the canonical re-encoding** — it
**rejects, never repairs**. A **detached SHA-256** digest (exactly 64 lowercase hex, no prefix / uppercase /
whitespace) over the exact canonical bytes is supplied via an explicit caller-supplied **`SealedArtifactReference`**
(opaque locator + expected digest); the verifier reads the bytes once, computes, compares, and **rejects mismatch
before any S1 record is consumed**, never substituting another artifact. The digest proves **integrity, not
authenticity** — it is **not** a signature, `declarer_opaque_reference` is **not** cryptographic identity, and any
authentication/signature boundary needs a separate charter. An artifact is **physically verified for replay only
after** reference-supplied → bytes-read → digest-matched → canonical-validated → Gate-A-validated →
projection-constructed, **all before the first S1 record**, with **no reread / reload / replacement / mutation /
partial-refresh / second-artifact** afterward and **no `is_sealed` field**. Every violation is a **pre-replay hard
failure** (no S4 fallback / no S1-Phase-6.1 mutation / no default artifact / no equality-only downgrade / no partial
state). The encoding **adds no Gate A logical field** (discriminators are encoding artifacts only) and carries **no**
execution meaning; **capacity stays deferred at 0 emit sites**; **Phase 6.1 stays frozen, COMPLETE + RATIFIED**.
**Phase 6.2 remains UNBUILT and NOT runtime-ready**; the **only** next safe step is the separately-authorized **Phase
6.2 Evidence-Intersection Classification Predicate Charter**, **not opened here**. **No executable work is
authorized.**
