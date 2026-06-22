# Phase 6.2 — Slice-E Manifest-Lookup Closed-Domain "e.g." Micro-Correction Charter

> **This is a docs-only single-contradiction micro-correction charter.** It marks the prior Slice-E manifest/
> duplicate/error-surface correction charter (`ff92ad0`) **historical and UNRATIFIED** for **exactly one**
> contradiction — an open-ended "e.g." manifest-lookup-domain clause in a charter that simultaneously claims zero
> "e.g." / residual ambiguity — and supersedes **only** that one sentence. It **implements nothing and authorizes
> nothing executable**: no runtime code, no tests, no fixtures, no `atomic_replay_step.py`, no `reconstruction.py`,
> no lock edits, no prior-charter edits, no generated files, no pytest, no graphify, and no commit beyond this single
> docs file. It does **not** edit, amend, delete, rebase, or force-push `ff92ad0`. It corrects `ff92ad0` **only**
> through the one-clause supersession map in §2. It defines **no Step algorithm behavior** beyond the corrected
> lookup-domain boundary. It is subordinate to the full Phase 6.2 chain — the planning / atomicity / precedence /
> duplicate-root / lifecycle / multi-event / Gate A/B charters, the sealed Slice-A/B/C/D contracts, the prior Slice-E
> exact-shape charter (`85d1ba6`, already UNRATIFIED) and its correction (`ff92ad0`), and `CLAUDE.md` — and where any
> conflict arises, those govern **except** for the narrow, explicitly-mapped correction in §2.

**Base:** `ff92ad04c9713e238d51261df8bb2aa289e99de7`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `ff92ad04c9713e238d51261df8bb2aa289e99de7`.

`ff92ad0` §4 (its line 96) defines the manifest-lookup `KeyError`-normalization site with an **open-ended** clause —
"a key the contract guarantees present, **e.g.** re-reading the definition for a row-start / established targeted
slot" — while the same charter's §10 asserts "no 'e.g.' … or residual ambiguity." That is a self-contradiction: the
"e.g." leaves the set of legal `M[key]` lookup keys un-closed. The normative rule (one lookup site, `KeyError`
normalized there) is correct; only the **open-ended enumeration of which keys may reach that site** is defective.

**`ff92ad0` is hereby marked historical and UNRATIFIED for exactly this one contradiction.** Every other `ff92ad0`
clause (and the effective `85d1ba6` clauses it preserved) stands intact (§4). `ff92ad0` is **not** edited/deleted/
amended/rebased/force-pushed.

**No capacity validation and no capacity pass is claimed by this charter.**

---

## 2. Exact One-Clause Quote-Anchored Supersession Map to `ff92ad0` (binding)

| `ff92ad0` site | Quoted clause (line 96) | Precise replacement |
|---|---|---|
| §4 manifest-lookup bullet | "**`KeyError` is normalized to `AtomicReplayStepError(STEP_MANIFEST_DEFINITION_ABSENT, message)` only at this exact `M[key]` lookup site** (a key the contract guarantees present, **e.g.** re-reading the definition for a row-start / established targeted slot)." | The exhaustive closed rule in §3. The single `M[key]` lookup site, its two-category closed key domain, and the `KeyError`-normalization-only-there contract replace the open-ended "e.g." clause verbatim. |

This is the **only** supersession. The normative single-site rule and `STEP_MANIFEST_DEFINITION_ABSENT` mapping are
unchanged — only the open-ended key enumeration is closed.

---

## 3. Corrected Closed-Domain Manifest-Lookup Rule (binding)

The single contract-defined `M[key]` lookup site (i.e.
`frozen_manifest_projection.definitions_by_silver_pair[key]`) may be invoked **only** for:

1. **the current projected Silver-pair key, after it has been classified as a manifest target**; and
2. **each row-start lifecycle-slot identity key whose manifest definition is actually reached by the preserved
   strict-lazy precedence.**

**No other key class, speculative lookup, diagnostic lookup, iteration-driven lookup, prefetch, scan, fallback,
retry, or lookup site is legal.**

- `KeyError` remains normalized to `AtomicReplayStepError(STEP_MANIFEST_DEFINITION_ABSENT, message)` **only at this
  single code site**, for **either** of the two exhaustive key categories above and for **no** other.
- **Membership checks remain branches / no-ops and are never `KeyError` sites** (target-vs-non-target classification
  uses membership / Slice-D `silver_pair_intersects`; a non-target row is an irrelevant no-op).

### 3.1 Closed lookup-domain table

| Key reaching `M[key]` | Legal? | `KeyError` → |
|---|---|---|
| current projected Silver-pair key, **after** manifest-target classification | ✅ category 1 | `STEP_MANIFEST_DEFINITION_ABSENT` |
| row-start lifecycle-slot identity key **reached** by strict-lazy precedence | ✅ category 2 | `STEP_MANIFEST_DEFINITION_ABSENT` |
| any other key; speculative / diagnostic / iteration-driven / prefetch / scan / fallback / retry lookup | ❌ illegal (no such site) | n/a |
| membership test (`key in M`) | ✅ branch / no-op | never a `KeyError` site |

---

## 4. Preserved Unchanged (affirmed)

Every other `ff92ad0` clause and effective `85d1ba6` clause stands intact:

- the concrete manifest type `ShadowIntentDefinitionArtifact` (parameter `frozen_manifest_projection`;
  `"FrozenManifestProjection"` only a prose role; no such class/alias/symbol created);
- **whole-artifact ownership** — Slice E receives the complete `ShadowIntentDefinitionArtifact` and resolves per-key
  on demand; Slice F/G never pre-resolve/inject a single definition;
- the corrected **duplicate semantics** (`STEP_DUPLICATE_ROOT` for any target already in `current_seen_pairs`,
  independent of lifecycle/root/terminal/kind/later-fields, including the committed-seen `AUDIT_REPLAYED`+
  `NoRootEvidence` unit-mismatch pair; immediate, before terminal handling/later projections);
- the closed **ten-reason vocabulary**;
- the error surface `AtomicReplayStepError(ValueError)` with `__init__(self, reason, message)` and `.reason`;
- the **result-constructor mapping** (`__post_init__` revalidation failure → `STEP_PUBLICATION_INVARIANT_VIOLATION`;
  input-boundary failures mapped to the input reasons);
- the **identity** postconditions, **error precedence**, **exception discipline**, opaque-`raw_evidence_row`
  strict-lazy projection rule, **classify-all/apply-all atomicity**, terminal absorption, lifecycle legality,
  determinism, and all passive-only exclusions.

**No Step implementation behavior is defined beyond the corrected lookup-domain boundary.**

---

## 5. Corrected Future RED → GREEN Requirement (for the later Slice-E TDD — NOT opened here)

The later separately-authorized Slice-E TDD task must prove:

- the `M[key]` lookup is reached **only** for (1) a current projected Silver-pair key already classified as a
  manifest target, and (2) a row-start lifecycle-slot identity key actually reached by strict-lazy precedence — and
  a `KeyError` at that single site for **either** category normalizes to `STEP_MANIFEST_DEFINITION_ABSENT`;
- a **static AST lock** forbidding every other manifest lookup: exactly one subscripting site against
  `definitions_by_silver_pair`, no speculative / diagnostic / iteration-driven / prefetch / scan / fallback / retry
  lookup, and membership tests never on the `KeyError` path.

All other `ff92ad0` / `85d1ba6` future RED→GREEN requirements remain unchanged.

---

## 6. Unresolved Items

- **None.** The single open-ended clause is closed exhaustively. The corrected closed-domain rule (§3) introduces no
  "e.g.", "for example", "such as", alternative category, or residual open-ended wording; the only occurrences of
  those tokens in this charter are **verbatim quotations of the superseded `ff92ad0` defect** (§1–§2) required to
  identify it — they are not normative hedges.

---

## 7. Exclusions / Precise Post-Charter State (ratified)

- Docs-only: no runtime/tests/fixtures/prior-charter/lock edits; `atomic_replay_step.py` and `reconstruction.py`
  not created; Slice F/G not opened. `ff92ad0` not edited/deleted/amended/rebased/force-pushed; `85d1ba6` remains
  UNRATIFIED.
- **Slice E remains BLOCKED pending independent review and ratification.** **Slice F/G remain blocked.** **Capacity
  remains 0.** **Phase 6.2 remains INCOMPLETE and NOT runtime-ready;** execution / routing / actionability / live /
  paper / canary behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE + RATIFIED.

**Conclusion:** `ff92ad0` is marked historical and **UNRATIFIED** for exactly one contradiction — its line-96
open-ended "e.g." manifest-lookup clause inside a charter claiming zero "e.g." / residual ambiguity. That sentence is
superseded by the exhaustive closed rule: the single contract-defined `M[key]` lookup site may be invoked **only**
for (1) the current projected Silver-pair key after manifest-target classification and (2) each row-start
lifecycle-slot identity key actually reached by the preserved strict-lazy precedence, with **no** other key class,
speculative / diagnostic / iteration-driven lookup, prefetch, scan, fallback, retry, or lookup site legal; `KeyError`
remains normalized to `STEP_MANIFEST_DEFINITION_ABSENT` **only** at that single site for either category, and
membership checks remain branches / no-ops and never `KeyError` sites. All other `ff92ad0` and effective `85d1ba6`
clauses — concrete `ShadowIntentDefinitionArtifact` type, whole-artifact ownership, duplicate semantics, ten-reason
vocabulary, `AtomicReplayStepError(reason, message)` with `.reason`, result-constructor mapping, identity rules,
precedence, atomicity, and exclusions — are **preserved unchanged**, **no unresolved items** remain, and **Slice E
stays BLOCKED pending independent review; Slice F/G blocked; capacity 0; Phase 6.2 INCOMPLETE and NOT runtime-ready.
No executable work is authorized.**
