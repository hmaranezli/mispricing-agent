# Phase 6.2 — Lifecycle-Slot / Dual-Snapshot Exactness Targeted Correction Charter

> **This is a docs-only targeted exactness correction charter.** It marks the prior field-shape amendment charter
> (`85de568`) **UNRATIFIED** and supersedes **only** the five enumerated exactness defects below — it does **not**
> redesign the slot/snapshot model. It **implements nothing and authorizes nothing executable**: no runtime code, no
> tests, no fixtures, no package files, no prior-charter file edits, no generated files, no DTO instance, no loader,
> no state machine, no `Step` algorithm, no replay loop, no SQLite, no artifact read, no persistence, no emission, no
> Phase 6.1 edits, no S1-adapter edits, no Gate A/B edits, no frozen-component edits, no pytest, no graphify, and no
> commit beyond this single docs file. It does **not** amend, edit, delete, rebase, or force-push `85de568`. It
> corrects `85de568` **only** through the exact supersession map in §2. It makes **no** Phase 6.2 runtime/paper/live/
> production readiness claim. It is subordinate to the full Phase 6.2 charter chain — Gate A (`5dc757c`, `1071067`),
> Gate B (`474cc6f`), conceptual field-shape (`ef26f59`), lifecycle (`e9995e7`), multi-event context (`999a109`),
> predicate-precedence / decimal-source (`d7204d6`→`457d279`-chain), replay-step atomicity (`44791ce`→`457d279`),
> reconstruction-runtime planning (`457d279`), the S1 durable-storage charters, and `CLAUDE.md` — and where any
> conflict arises, those govern **except** for the narrow, explicitly-mapped corrections in §2.

**Base:** `85de5683558c5a9832a4636ad715376347532bef`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `85de5683558c5a9832a4636ad715376347532bef`.

`85de568` pinned the Slice-A lifecycle slot, the closed root-evidence option-sum, and the two `Step`-role snapshot
containers, but left **five exactness defects** that block a clean Slice-A runtime extension: (1) `EstablishedRootContext`
text scalars were not constrained against empty / whitespace-only content; (2) the anchor-timestamp grammar was
described in prose but not pinned to an exact **ASCII-only** lexical grammar (and risked `\d`/Unicode-digit drift);
(3)–(4) the two snapshot containers were left with **ambiguous representation choices** ("e.g. a `frozenset`, or a
`MappingProxyType`-guarded membership view"), **unnamed factories**, and **no exact field-name / factory-signature**
pin; (5) the document carried "e.g." / implementation-alternative / optional-representation language that admits more
than one legal shape.

**`85de568` is hereby marked UNRATIFIED.** This correction supersedes **only** the defects in §3–§7 below; every
preserved clause of `85de568` (§8) stands intact. `85de568` itself is **not** edited, deleted, amended, rebased, or
force-pushed — it remains in history; this charter governs the corrected shape going forward.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Exact Supersession Map to `85de568` (binding)

Each row supersedes **only** the quoted/identified clause of `85de568`; everything else in `85de568` stands.

| `85de568` § | Identified clause | Precise replacement (this charter) |
|---|---|---|
| §4.1 `EstablishedRootContext` | "`source_venue_context_text` / `source_pair_context_text` … exact `str`, opaque, verbatim" (no blank constraint) | **§3:** each is exact `str` **and** `value.strip() != ""`; empty and every whitespace-only Unicode string are invalid; accepted text preserved verbatim (no trim/normalize/repair/coerce). |
| §4.1 `EstablishedRootEvidence` | `provenance_anchor_timestamp_text` "canonical non-negative integer decimal text (the `str(int)` form: `0` or `[1-9]\d*` …)" | **§4:** exact ASCII grammar `"0" \| [1-9][0-9]*`; ASCII digits only; `\d` / Unicode decimal digits / sign / fraction / exponent / whitespace / leading zeros **banned**; validation is **lexical** (no `int()` conversion requirement). |
| §5.1 `ShadowLifecycleSnapshot` | "built from an explicit ordered tuple of `(OpaqueSilverPairKey, ShadowIntentLifecycleSlot)` entries"; factory named only as "a maker"; "an immutable `MappingProxyType` over a non-retained local dict" | **§5:** exact class `ShadowLifecycleSnapshot`; exact ordered field set `slots_by_identity`; exact factory `make_shadow_lifecycle_snapshot(*, slot_entries)`; `slot_entries` an exact `tuple` of exact 2-tuples; stored representation exactly `MappingProxyType` over a newly-built non-retained local dict; no caller dict accepted/retained; content-based order-independent equality. |
| §5.2 `SeenTargetPairsSnapshot` | "an immutable members view (**e.g.** a `frozenset` of `OpaqueSilverPairKey`, **or** a `MappingProxyType`-guarded membership view)"; factory named only as "a maker" | **§6:** exact class `SeenTargetPairsSnapshot`; exact ordered field set `seen_target_pairs`; exact factory `make_seen_target_pairs_snapshot(*, members)`; stored representation exactly a `frozenset` of exact `OpaqueSilverPairKey` values; `members` an exact `tuple`; duplicate members rejected **before** frozenset construction (no silent dedup); set-content order-independent equality. |
| §5/§6 throughout | every "e.g.", "analogous to", "or a … view", optional-representation, and unnamed-factory surface for these pinned types | **§7:** removed/superseded. No alternative class, field, representation, or factory name is legal for these types. |

The supersession is **exactness-only**: the slot's three-field shape (`ShadowIntentLifecycleSlot`), the root-evidence
option-sum, the lifecycle/root compatibility matrix, and all behavior remain exactly as in `85de568` §8's preserved
set.

---

## 3. `EstablishedRootContext` — Corrected Exact Field Table (binding)

`EstablishedRootContext` — `@dataclass(frozen=True, slots=True, kw_only=True)`, methodless, self-validating:

| # | Field | Type | Corrected validation |
|---|---|---|---|
| 1 | `source_venue_context_text` | `str` | `type(value) is str` **and** `value.strip() != ""` |
| 2 | `source_pair_context_text` | `str` | `type(value) is str` **and** `value.strip() != ""` |

- **Blank rule:** the empty string `""` and **every** whitespace-only Unicode string (any string whose `.strip()`
  yields `""` — including ASCII space/tab/newline and Unicode whitespace such as `U+00A0`, `U+2003`, `U+3000`,
  `U+200B`-class blanks as Python `str.strip()` treats them) are **invalid** → `LogicalModelError`.
- **Verbatim preservation:** accepted text is stored **exactly as received** — `.strip()` is used **only** for the
  emptiness test, **never** to trim, normalize, repair, or coerce the stored value.

*Source proof:* `457d279` precedence §5 / §10 (`score_inputs_summary` is exactly two **text** scalars; malformed /
empty context is structurally invalid) and the established Slice-C/D non-blank context contract (whitespace-only
context elements are rejected).

---

## 4. Anchor Timestamp — Corrected Exact Lexical Grammar (binding)

`EstablishedRootEvidence` — `@dataclass(frozen=True, slots=True, kw_only=True)`, exact ordered fields:

| # | Field | Type | Corrected validation |
|---|---|---|---|
| 1 | `root_context` | `EstablishedRootContext` | exact type; both nested scalars revalidated (§3) |
| 2 | `provenance_anchor_timestamp_text` | `str` | exact `str`; matches the exact ASCII grammar below |

**Canonical anchor grammar (exact):**

```
"0" | [1-9][0-9]*
```

- **ASCII digits only.** The character class is the literal ASCII set `0`–`9` (`[0-9]`), **not** `\d`.
- **Banned:** `\d` (which matches Unicode decimal digits), any non-ASCII / Unicode decimal digit (e.g. `١`, `७`,
  Arabic-Indic / Devanagari digits), a leading sign (`+`/`-`), any fractional part (`.`…), any exponent (`e`/`E`…),
  any whitespace (leading, trailing, or internal), and any leading zero (so `"00"`, `"007"`, `"0123"` are invalid;
  `"0"` alone is valid).
- **Lexical validation only.** Acceptance is decided by the lexical grammar (e.g. an explicit ASCII-only regex
  `^(0|[1-9][0-9]*)$` compiled **without** relying on `\d`, or an equivalent explicit ASCII scan). **No `int()`
  conversion is required** to validate; the value is carried verbatim as the canonical decimal text.

*Source proof:* `457d279` precedence §6 — `provenance_timestamp` equals the payload integer's canonical decimal text
in `str(int)` form, which is exactly `"0" | [1-9][0-9]*` over ASCII digits. (Note: the **Phase-5 magnitude** lexis
`-?\d+(\.\d+)?` with Unicode `\d` — Slice D `f6c428e` — governs *magnitudes*, **not** this timestamp anchor; the
two grammars are deliberately distinct and must not be conflated.)

---

## 5. `ShadowLifecycleSnapshot` — Corrected Exact Shape (binding)

- **Exact class:** `ShadowLifecycleSnapshot`.
- **Exact ordered field set:** `slots_by_identity` (one field).
- **Exact stored representation:** `MappingProxyType` over a **newly-built, non-retained local `dict`** mapping
  exact `OpaqueSilverPairKey` values → exact `ShadowIntentLifecycleSlot` values. **No caller dict is accepted or
  retained** (the maker takes a tuple, not a mapping); the local dict is discarded after wrapping, so the published
  mapping has no external mutable alias.
- **Key invariant:** each map key **MUST equal** `slot.shadow_intent_identity_reference` (mismatch → reject).
- **Empty snapshot is valid** (`slots_by_identity` over an empty map).
- **Factory-only:** direct construction raises `LogicalModelError` (mirroring `ShadowIntentDefinitionArtifact`).
- **Exact factory:** `make_shadow_lifecycle_snapshot(*, slot_entries)`.
  - `slot_entries` must be an **exact `tuple`** of **exact 2-tuples** `(OpaqueSilverPairKey, ShadowIntentLifecycleSlot)`.
  - **Reject before publication** (single bounded O(n) pass): a non-tuple `slot_entries`; any entry that is not an
    exact 2-tuple; a forged/wrong-typed key (defensive `OpaqueSilverPairKey` revalidation); a forged/wrong-typed
    slot (defensive `ShadowIntentLifecycleSlot` revalidation, including the §8 lifecycle/root invariant); a
    **duplicate key**; and any **key ≠ `slot.shadow_intent_identity_reference`** mismatch.
- **Ordering has no semantic meaning;** equality is **content-based and order-independent** (two snapshots with the
  same key→slot content compare equal regardless of `slot_entries` order or insertion history). Snapshots are not
  required to be hashable.

---

## 6. `SeenTargetPairsSnapshot` — Corrected Exact Shape (binding)

- **Exact class:** `SeenTargetPairsSnapshot`.
- **Exact ordered field set:** `seen_target_pairs` (one field).
- **Exact stored representation:** a **`frozenset` of exact `OpaqueSilverPairKey` values** (no `MappingProxyType`
  alternative, no membership-view alternative).
- **Factory-only:** direct construction raises `LogicalModelError`.
- **Exact factory:** `make_seen_target_pairs_snapshot(*, members)`.
  - `members` must be an **exact `tuple`**.
  - Every member is defensively revalidated as an exact `OpaqueSilverPairKey` (forged/non-key member → reject).
  - **Duplicate members are rejected before frozenset construction** — **no silent deduplication** (a duplicate in
    the input tuple is a structural error, not a set-collapse).
- **Empty snapshot is valid.**
- Equality is **set-content equality and order-independent.** Snapshots are not required to be hashable.

---

## 7. Remove Ambiguity (binding)

For the four pinned types (`EstablishedRootContext`, `EstablishedRootEvidence`, `ShadowLifecycleSnapshot`,
`SeenTargetPairsSnapshot`):

- Every "e.g.", "analogous to", "or a … view", optional/alternative representation, and unnamed-factory surface from
  `85de568` is **removed / superseded**.
- **No alternative class name, field name, stored representation, or factory name is legal.** The exact names and
  representations of §3–§6 are the **only** legal forms:
  - classes: `EstablishedRootContext`, `EstablishedRootEvidence`, `NoRootEvidence`, `ShadowIntentLifecycleSlot`,
    `ShadowLifecycleSnapshot`, `SeenTargetPairsSnapshot`;
  - container fields: `slots_by_identity`, `seen_target_pairs`;
  - factories: `make_shadow_lifecycle_snapshot(*, slot_entries)`,
    `make_seen_target_pairs_snapshot(*, members)`;
  - representations: `MappingProxyType` over a non-retained local dict (shadow); `frozenset` of keys (seen).

---

## 8. Preserved Unchanged from `85de568` (affirmed)

The following `85de568` provisions stand **intact** (not superseded):

- **Root-evidence option-sum** `NoRootEvidence | EstablishedRootEvidence` (the option-sum structure itself; only the
  nested validations of §3/§4 are tightened).
- **Lifecycle / root compatibility matrix:** `AUDIT_REPLAYED ⟺ NoRootEvidence`; each of `INTENT_RECORDED`,
  `HYPOTHETICAL_CONDITION_MET`, `INTENT_EXPIRED`, `INTENT_RETIRED` `⟺ EstablishedRootEvidence`; permanent
  unit-mismatch = `AUDIT_REPLAYED` + `NoRootEvidence`, distinguished structurally by the seen-pair snapshot.
- **`ShadowIntentLifecycleSlot`** exact three-field shape (`shadow_intent_identity_reference: OpaqueSilverPairKey`,
  `lifecycle_state`, `root_evidence`).
- **Manifest-resident `exposure_orientation`** (never duplicated into the slot).
- **Firewalled-deferred `hypothetical_outcome_reference`** (its own future charter; not required by Slice E).
- **Slice-A ownership** of all these carriers and the **`logical_model` intra-package leaf** import direction.
- **Complete `object.__new__` defensive revalidation** through the single closed `LogicalModelError` surface (never
  catching `BaseException`/`MemoryError`/`KeyboardInterrupt`, never leaking raw `AttributeError`/`TypeError`/`KeyError`).
- **No `Step` algorithm, no inert-proposal logic, no classify-all/apply-all, no lifecycle application/mutation, no
  replay loop, and no Slice E behavior** is defined.

---

## 9. Corrected Legal / Illegal Construction Matrix (binding)

| Construction attempt | Outcome |
|---|---|
| `EstablishedRootContext` with two non-blank `str` scalars | ✅ accept (verbatim) |
| `EstablishedRootContext` with `""` or whitespace-only (`" "`, `"\t"`, `" "`, `"　"`, …) scalar | ❌ `LogicalModelError` |
| `EstablishedRootContext` with non-`str` scalar | ❌ `LogicalModelError` |
| `provenance_anchor_timestamp_text` = `"0"` / `"123"` / `"9223372036854775807"` | ✅ accept |
| `provenance_anchor_timestamp_text` = `"00"` / `"007"` / `"-1"` / `"+1"` / `"1.0"` / `"1e3"` / `" 1"` / `"1 "` / `""` | ❌ `LogicalModelError` |
| `provenance_anchor_timestamp_text` = Unicode-digit `"١"` / `"१२३"` (matches `\d` but not ASCII `[0-9]`) | ❌ `LogicalModelError` |
| `ShadowLifecycleSnapshot(...)` direct construction | ❌ `LogicalModelError` |
| `make_shadow_lifecycle_snapshot(slot_entries=())` (empty) | ✅ accept (empty proxy) |
| `make_shadow_lifecycle_snapshot` with a `dict`/`list` `slot_entries` (not exact tuple) | ❌ `LogicalModelError` |
| `make_shadow_lifecycle_snapshot` with an entry that is not an exact 2-tuple | ❌ `LogicalModelError` |
| `make_shadow_lifecycle_snapshot` with duplicate key | ❌ `LogicalModelError` |
| `make_shadow_lifecycle_snapshot` with forged key / forged slot | ❌ `LogicalModelError` |
| `make_shadow_lifecycle_snapshot` with key ≠ `slot.shadow_intent_identity_reference` | ❌ `LogicalModelError` |
| `SeenTargetPairsSnapshot(...)` direct construction | ❌ `LogicalModelError` |
| `make_seen_target_pairs_snapshot(members=())` (empty) | ✅ accept (empty frozenset) |
| `make_seen_target_pairs_snapshot` with non-tuple `members` | ❌ `LogicalModelError` |
| `make_seen_target_pairs_snapshot` with duplicate members | ❌ `LogicalModelError` (no silent dedup) |
| `make_seen_target_pairs_snapshot` with forged/non-key member | ❌ `LogicalModelError` |
| two snapshots with same content, different entry/member order | ✅ compare **equal** |

---

## 10. Planned RED → GREEN Test Matrix (for the LATER separately-authorized Slice-A runtime extension only)

These belong to a **future** human-authorized Slice-A runtime extension TDD task; **none is authorized or written
here.**

| # | RED (must fail before impl) | GREEN (minimal impl satisfies) | Maps to |
|---|---|---|---|
| 1 | `EstablishedRootContext` rejects `""` and each whitespace-only Unicode blank (`" "`, `"\t"`, `"\n"`, `" "`, `" "`, `"　"`) per scalar | `strip() != ""` guard per scalar | §3 |
| 2 | `EstablishedRootContext` preserves a non-blank value **verbatim** (no trim/normalize) including surrounding-significant text | store received value unchanged | §3 |
| 3 | anchor accepts `"0"`, `"123"`, max-int text | ASCII-grammar match | §4 |
| 4 | anchor rejects leading-zero (`"00"`,`"007"`), sign, fraction, exponent, whitespace, empty | ASCII `^(0\|[1-9][0-9]*)$` | §4 |
| 5 | anchor rejects Unicode digits `"١"`/`"१२३"` (proves ASCII-only, not `\d`) | ASCII-only class, no `\d` | §4 |
| 6 | `ShadowLifecycleSnapshot` direct construction raises; field is exactly `slots_by_identity`; empty valid | factory-only + `MappingProxyType` over non-retained dict | §5 |
| 7 | `make_shadow_lifecycle_snapshot(*, slot_entries)` rejects non-tuple, non-2-tuple entry, duplicate key, forged key/slot, key/slot mismatch | bounded O(n) revalidation pass | §5/§9 |
| 8 | duplicate-factory-input: two identical keys in `slot_entries` rejected (not last-wins) | duplicate detection before publication | §5/§9 |
| 9 | **alias resistance:** published `slots_by_identity` is a read-only proxy; mutation attempt fails; no caller handle mutates it (input tuple mutated after build does not affect snapshot) | non-retained local dict + proxy | §5 |
| 10 | `SeenTargetPairsSnapshot` direct construction raises; field is exactly `seen_target_pairs`; empty valid | factory-only + frozenset | §6 |
| 11 | `make_seen_target_pairs_snapshot(*, members)` rejects non-tuple, duplicate member (no silent dedup), forged/non-key member | revalidation before frozenset build | §6/§9 |
| 12 | content/order-independent equality for both snapshots (reordered `slot_entries`/`members` ⇒ equal) | content/set equality | §5/§6 |
| 13 | exact factory **signatures**: keyword-only `slot_entries` / `members`; positional or misnamed call fails | `(*, slot_entries)` / `(*, members)` | §5/§6/§7 |
| 14 | exact **names**: no alternative class/field/representation/factory name resolves | only §3–§7 names exist | §7 |
| 15 | dependency-direction lock + Slice-E/F absence lock unchanged | leaf preserved; `atomic_replay_step.py`/`reconstruction.py` absent | §8 |

**Regression:** the extension must keep the established selected regression
(`-k "lock or forbidden or quarantine or durable_sqlite"`) green and add focused Slice-A tests; **no broad pytest,
no opportunistic refactor, no adjacent-slice implementation.**

---

## 11. Unresolved Items

- **None.** Every corrected field, grammar, representation, factory name, and signature is exact and source-proven
  from the chain (precedence §5/§6; the established non-blank context and ASCII-canonical-timestamp contracts). No
  invention and no open choice remains for these types.

---

## 12. Exclusions / Precise Post-Charter State (ratified)

- **`85de568` is UNRATIFIED;** this charter supersedes only §3–§7's exactness defects and preserves §8. `85de568`
  is not edited/deleted/amended/rebased/force-pushed.
- **No `Step` algorithm, inert proposals, classify/apply ordering, lifecycle application/mutation, replay loop,
  SQLite, artifact read, persistence, emission, execution, routing, or actionability** is defined here.
- **The Slice-A runtime extension remains BLOCKED pending independent review of this correction.** **Slice E / F / G
  remain blocked.** **Capacity remains DEFERRED at exactly 0 emit sites.** **Phase 6.2 remains INCOMPLETE and NOT
  runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED. Production / live / paper / canary / execution / routing /
  actionability forbidden. Historical S1 evidence read verbatim, never censored.

**Conclusion:** `85de568` is marked **UNRATIFIED** and corrected on exactness only. `EstablishedRootContext`'s two
text scalars must each be exact `str` with `value.strip() != ""` (empty and every whitespace-only Unicode string
invalid), preserved **verbatim** with no trim/normalize/repair. `provenance_anchor_timestamp_text` is pinned to the
exact **ASCII** grammar `"0" | [1-9][0-9]*` — ASCII digits only, **banning** `\d`/Unicode digits/sign/fraction/
exponent/whitespace/leading-zeros — validated **lexically** with no `int()` requirement. The shadow container is
exactly **`ShadowLifecycleSnapshot`** with the single field **`slots_by_identity`** stored as a `MappingProxyType`
over a newly-built, non-retained local dict (`OpaqueSilverPairKey → ShadowIntentLifecycleSlot`, key ==
`slot.shadow_intent_identity_reference`, no caller dict accepted/retained, empty valid), factory-only via
**`make_shadow_lifecycle_snapshot(*, slot_entries)`** taking an exact tuple of exact 2-tuples that rejects duplicate
keys / malformed entries / forged keys+slots / key-slot mismatch before publication, with content-based
order-independent equality. The seen container is exactly **`SeenTargetPairsSnapshot`** with the single field
**`seen_target_pairs`** stored as a `frozenset` of exact `OpaqueSilverPairKey` values, factory-only via
**`make_seen_target_pairs_snapshot(*, members)`** taking an exact tuple that rejects duplicate members **before**
frozenset construction (no silent dedup) and forged/non-key members, empty valid, with set-content order-independent
equality. Every "e.g." / alternative-representation / "frozenset or MappingProxyType" / optional / unnamed-factory
surface for these types is removed — **no alternative class, field, representation, or factory name is legal.** The
root-evidence option-sum, lifecycle/root compatibility matrix, manifest-resident `exposure_orientation`,
firewalled-deferred `hypothetical_outcome_reference`, Slice-A ownership + `logical_model` leaf direction, complete
`object.__new__` defensive revalidation, and the no-`Step`/no-application/no-replay-loop/no-Slice-E exclusions are
**preserved**. **No unresolved items.** The **Slice-A runtime extension stays blocked pending independent review;
Slice E/F/G stay blocked; capacity deferred at 0 emit sites; Phase 6.2 remains INCOMPLETE and NOT runtime-ready. No
executable work is authorized.**
