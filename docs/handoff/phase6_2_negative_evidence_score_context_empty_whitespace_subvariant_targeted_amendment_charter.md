# Phase 6.2 — Negative-Evidence Score-Context Empty/Whitespace Subvariant Targeted Amendment Charter

> **This is a docs-only targeted micro-amendment charter.** It narrowly extends **only** the closed Case-5
> `MALFORMED_SCORE_INPUTS_SUMMARY` subvariant set and pins the **source-proven** context-shape invariant for
> `score_inputs_summary` — it does **NOT** redesign the fixture architecture, the seven-case partition, the
> projector, or any predicate. It **implements nothing and authorizes nothing executable**: no runtime code,
> no tests, no fixture code, no package, no DTO, no adapter, no Phase 6.1 edits, no S1 edits, no Gate A/B
> edits, no prior-charter file edits, no lock-test edits, no config, no generated-file edits, no pytest, no
> graphify. It is exactly one docs file and corrects the negative-evidence fixture charters **only** through
> the supersession map in §3. It makes **no** Phase 6.2 runtime/paper/live/production readiness claim. It is
> subordinate to `docs/handoff/phase6_2_negative_evidence_fixture_boundary_charter.md` (`b4368fd`),
> `docs/handoff/phase6_2_negative_evidence_case_isolation_relevance_harness_micro_correction_charter.md`
> (`045caea`), `docs/handoff/phase6_2_reconstruction_runtime_tdd_planning_slice_charter.md` (`457d279`), the
> predicate + precedence/decimal-consistency charters (`474cc6f`, `d7204d6`), the full Phase 6.2 chain, the
> S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises, those govern **except** for the
> narrow, explicitly-mapped supersession in §3.

**Base:** `0ddc8990026fbed80910da6755a532c643208351`

---

## 1. Base / Purpose

**Base commit:** `0ddc8990026fbed80910da6755a532c643208351`.

Slice C (`0ddc899`) built the S1 evidence projector and the quarantined negative-evidence row helper with
the closed Case-5 `MALFORMED_SCORE_INPUTS_SUMMARY` subvariants `MISSING` / `WRONG_ARITY` /
`NON_TEXT_ELEMENT` (per `045caea` §6). That subvariant set is **incomplete** with respect to the
**source-proven** context-shape contract: `phase6_1/passive_shadow_input.py` validates each context scalar
via `_require_str_field`, which rejects not only non-`str` values (`TypeError`) but also **empty and
whitespace-only** strings (`value.strip() == ""` ⇒ `ValueError`). The audited `score_inputs_summary` root
context therefore can **never** legitimately carry an empty or whitespace-only `source_venue`/`source_pair`,
yet the current closed subvariant set provides **no poison fixture** to prove the projector rejects such a
value. This charter closes that gap by authorizing **exactly two** additional fixed-shape subvariants and
pinning the source-proven non-empty / non-whitespace invariant — **nothing else**. The seven-case partition,
the absolute single-fault rule, the relevance/harness-scoped poison invariant, and the real-`sqlite3.Row`
mechanism are all preserved.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Evidence-First Verification (source-proven)

- **Context shape.** `phase6_1/b4_passive_scoring.py` sets
  `family_payload["score_inputs_summary"] = (pass_handoff.source_venue, pass_handoff.source_pair)` — exactly
  two ordered scalars, `source_venue` then `source_pair`.
- **Per-scalar lexis (the binding new invariant).** `phase6_1/passive_shadow_input.py`:
  `_CALLER_SUPPLIED_STR_FIELDS = ("source_venue", "source_pair")`; `_require_str_field(name, value)` raises
  `TypeError` unless `type(value) is str`, **and** raises `ValueError` when `value.strip() == ""` — i.e. an
  **empty** string and a **whitespace-only** string are both rejected at the S1 boundary. Construction wires
  these via `_require_str_field("source_venue", …)` / `_require_str_field("source_pair", …)`.
- **Consequence.** A faithfully-audited SCORE can never carry an empty or whitespace-only context element;
  such a value is **malformed evidence** that the Slice-C projector must reject — but the adapter, deriving
  every column from one validated record, can **never emit** it (the `5211652` §8 / `b4368fd` blocker).
  Therefore proving the rejection requires the quarantined negative-evidence mechanism, extended here by
  exactly two fixed subvariants.

This charter introduces **no** new field, path, or generic scraping; it reads the **already-whitelisted**
`family_payload.score_inputs_summary` only.

---

## 3. Exact Supersession Map (binding)

| Charter / § | Quoted clause | Precise replacement |
|---|---|---|
| `045caea` §6 (Closed Context Subvariants) | "`MALFORMED_SCORE_INPUTS_SUMMARY` (Case 5) has **exactly** these closed subvariants … `MISSING_SCORE_INPUTS_SUMMARY` … `WRONG_ARITY_SCORE_INPUTS_SUMMARY` … `NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT`" | "`MALFORMED_SCORE_INPUTS_SUMMARY` (Case 5) has **exactly** these **five** closed subvariants: `MISSING_SCORE_INPUTS_SUMMARY`, `WRONG_ARITY_SCORE_INPUTS_SUMMARY`, `NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT`, **`EMPTY_TEXT_ELEMENT`**, **`WHITESPACE_ONLY_TEXT_ELEMENT`** — each with one fixed malformed shape (§4)." |
| `045caea` §9 (Exact Fixed Constructions, context bullet) | "**context / decimal / timestamp cases (5/6/7):** **only the selected named invariant** (the chosen subvariant) is malformed; everything else valid and canonical." | **Preserved**, and extended so the two new Case-5 subvariants likewise malform **only** the named context element while every other field stays valid and canonical enough to reach exactly `MALFORMED_SCORE_INPUTS_SUMMARY` (§4–§5). |
| `045caea` §14 (Closed Builder API) | "a **subvariant selector required only for Cases 5, 6, and 7**" | **Preserved**; the Case-5 subvariant selector now ranges over the **five** members of §6 (this charter), with exact type/membership validation and no default/omitted/random subvariant. |
| `b4368fd` §7 / §11 (`MALFORMED_SCORE_INPUTS_SUMMARY` description) | "uses a **valid JSON** payload whose `score_inputs_summary` is **missing, wrong-arity, or contains a non-text scalar**" | "uses a **valid JSON** payload whose `score_inputs_summary` is **missing, wrong-arity, contains a non-text scalar, contains an empty-text scalar, or contains a whitespace-only-text scalar**" — all under the single-fault rule. |

**No other clause is superseded.** The **seven top-level cases stay exactly seven** (no eighth case); the
strict partition, Case-3-owns-timestamp-disagreement / Case-7-consistent-invalids-only non-overlap, the
decimal (`INVALID_S1_DECIMAL_LEXIS`) and timestamp (`INVALID_PROVENANCE_TIMESTAMP`) subvariant sets, the
real-`sqlite3.Row` representation, tests-only location + import isolation, adapter-only successful evidence,
no-production-fixture-awareness, and deferred Slice-C-RED implementation are all **unchanged**.

---

## 4. Pinned Context Shape & Fixed Poison Subvariants (binding)

**Context-shape invariant (source-proven, §2):** `score_inputs_summary` is **exactly**
`[source_venue, source_pair]` — two ordered elements, each an **exact `str`** that is **non-empty and
contains at least one non-whitespace character**. **No trimming, normalization, replacement, coercion, case
conversion, or stripping** is performed by the projector — the value is consumed verbatim; an empty or
whitespace-only element is **rejected**, never repaired.

**The two newly authorized fixed subvariants** (each a single fixed shape; the caller selects only the
closed subvariant name and supplies nothing else):

- **`EMPTY_TEXT_ELEMENT`** — `score_inputs_summary` is a two-element list whose **first element is one fixed
  valid text scalar** and whose **second element is exactly the empty string `""`**.
- **`WHITESPACE_ONLY_TEXT_ELEMENT`** — `score_inputs_summary` is a two-element list whose **first element is
  one fixed valid text scalar** and whose **second element is a fixed ASCII-whitespace-only string** (e.g. a
  single space or a fixed run of ASCII spaces/tabs — a fixed literal, never caller-chosen).

For **both** subvariants: the list arity is exactly two, both elements are JSON strings (so neither the
`WRONG_ARITY` nor the `NON_TEXT_ELEMENT` branch is reached first), and **every other row/payload field
remains valid and canonical** (row/payload kinds agree on `SCORE`; family descriptors agree on
`passive_net_edge_diagnostic`; `provenance_timestamp` is a consistent canonical non-negative integer;
`passive_score_magnitude` is valid Phase-5 lexis; `score_unit_context` is valid text) so the projector
reaches **exactly** the `MALFORMED_SCORE_INPUTS_SUMMARY` rejection branch.

**Forbidden (preserved):** no caller-selected value, no caller-selected position/index, no callback, no raw
SQL input, no arbitrary payload-mutation function, no generic fixture factory, no arbitrary list/arity, and
no caller-supplied malformed text. The helper remains a **closed case + subvariant selector**.

---

## 5. Absolute Single-Fault Isolation (preserved)

- Each new fixture **violates exactly one named invariant** — the context-shape non-empty / non-whitespace
  rule on a single element — while **every other field/invariant remains valid and canonical** enough to
  reach that exact rejection branch.
- **No incidental second defect** is permitted.
- A test that reaches a **different or earlier** failure (e.g. `WRONG_ARITY`, `NON_TEXT_ELEMENT`, a timestamp
  or magnitude branch, or a structural/JSON branch) **does not prove** the case and **MUST fail**; the test
  asserts the **exact** `MALFORMED_SCORE_INPUTS_SUMMARY` category, never merely "some failure."

---

## 6. Final Closed Case-5 Subvariant Vocabulary (binding)

`MALFORMED_SCORE_INPUTS_SUMMARY` (Case 5) has **exactly** these **five** subvariants — no sixth:

1. `MISSING_SCORE_INPUTS_SUMMARY`
2. `WRONG_ARITY_SCORE_INPUTS_SUMMARY`
3. `NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT`
4. `EMPTY_TEXT_ELEMENT`
5. `WHITESPACE_ONLY_TEXT_ELEMENT`

The seven **top-level** cases remain exactly seven (`ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT`,
`ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT`, `ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT`,
`MALFORMED_CANONICAL_JSON`, `MALFORMED_SCORE_INPUTS_SUMMARY`, `INVALID_S1_DECIMAL_LEXIS`,
`INVALID_PROVENANCE_TIMESTAMP`).

---

## 7. Preserved Prohibitions & Semantics (affirmed)

- **Relevance-scoped / harness-scoped poison invariant (`045caea` §10–§13) stands:** the two new fixtures
  expect the exact `MALFORMED_SCORE_INPUTS_SUMMARY` rejection **only inside an authorized harness** that
  actually demands the context projection/validation operation (Slice C direct boundary op; Slice E/F
  targeted-root or established-non-terminal-context-equal slot that forces context classification). They
  **must not** override terminal relevance, context inequality, expiry-before-unit/magnitude precedence, or
  lazy field evaluation; outside such a harness, relevance-scoped no-op/terminal behavior remains valid and
  is **not** a fixture failure. Fixtures may not smuggle an inspection that production legitimately skips.
- **Real tests-only `sqlite3.Row` mechanism preserved:** one parameterized in-memory `SELECT` over the six
  aliases, fresh connection per call, exactly one Row returned, connection closed, no connection/cursor
  leak; **no** table/DDL/DML, temp/production DB, adapter mutation/private-connection access,
  monkeypatch/mock/**fake**-Row/dict substitution, private SQL-constant import, or network/persistent state.
- **Adapter-only successful evidence preserved:** all successful S1/reconstruction evidence comes
  **exclusively** from `S1DurableSqliteSink.record_observation` + the ratified replay; **synthetic
  successful rows / fabricated intent state / alternate observed-event sources remain forbidden**.
- **Import isolation preserved:** the helper lives only at `tests/fixtures/phase6_2_negative_evidence_rows.py`;
  production never imports tests/fixtures/pytest/mocks; the static import-direction lock stands; the runtime
  carries **no** test-only flag/branch/parser/fixture awareness.
- **No** wall clock, S4 fallback, mutation/write-back, global state/registry/cache/singleton, actionability,
  capacity, or integration is introduced. **Capacity stays deferred at exactly 0 emit sites.**

---

## 8. Current Runtime Mismatch (recorded)

- **`0ddc899` is BUILT but UNRATIFIED** with respect to this amendment and the corrections named in §9.
- **P1 (architecture):** the Slice-C projector performs a **monolithic eager** SCORE projection — it
  validates all whitelisted fields up front, **before** the ratified relevance/expiry precedence (Slice
  D/E/F) would permit those fields to be inspected. The later predicate/replay layers require **separately
  invocable lazy** projection/validation operations so that expiry-before-unit/magnitude and context
  relevance govern **which** field is demanded **when**.
- **P1 (hardening):** the exported projection carriers (`ScoreEvidenceProjection`,
  `NonScoreEnvelopeProjection`) are plain frozen/slotted dataclasses and currently permit a
  **direct-constructor bypass** of the projector's validation (a caller can construct a projection without
  going through `project_s1_evidence`).
- **P2 (binding, this charter):** **empty / whitespace-only context elements are currently accepted** — the
  projector's `_validate_score_inputs_summary` checks only `type is str` and arity, not the source-proven
  non-empty / non-whitespace lexis. It must reject them as `MALFORMED_SCORE_INPUTS_SUMMARY`, and the two new
  fixtures (§4) must exist to prove it.
- **Slice D remains BLOCKED** until the §9 correction is ratified.

---

## 9. Next Eligible Correction (named, NOT opened)

The **only** next eligible gate is a separately-authorized **"Phase 6.2 Slice C Lazy Projection,
Constructor-Hardening & Context-Shape Targeted TDD Correction"**, which must:

1. Provide **separately invoked lazy projection/validation operations** (so a field is validated only when
   that exact operation is demanded), replacing the monolithic eager projection while preserving the
   ratified **expiry-before-unit/magnitude** precedence and **context relevance** (it must not force
   inspection of fields production legitimately skips).
2. **Harden every exported projection construction path** so the carriers cannot be constructed in an
   unvalidated state via a direct constructor (factory-only / self-validating, like the Slice-A DTOs).
3. **Defensively revalidate at trust boundaries** (re-assert invariants where a projection is consumed, not
   only where first produced).
4. **Implement the two newly authorized fixture subvariants** (`EMPTY_TEXT_ELEMENT`,
   `WHITESPACE_ONLY_TEXT_ELEMENT`) and enforce the source-proven non-empty / non-whitespace context-shape
   invariant (§4) in the projector — `0`/valid-text accepted, empty/whitespace-only rejected as
   `MALFORMED_SCORE_INPUTS_SUMMARY` — with no trimming/normalization/repair.

**This charter does NOT implement any of those corrections** — it only pins the context-shape invariant,
authorizes the two subvariants, records the mismatch, and names the correction. **It is not opened here.**

---

## 10. Status & Post-Charter State (ratified)

- **Phase 6.2 remains INCOMPLETE and NOT runtime-ready.** This amendment pins **only** the context-shape
  invariant and the two new Case-5 subvariants; it authorizes **no** executable work.
- **`0ddc899` BUILT but UNRATIFIED** pending the §9 correction; **Slice D blocked.**
- **Phase 6.1** remains **COMPLETE + RATIFIED** in its narrow passive-audit scope. **Capacity** deferred at
  **0 emit sites**. **Production / live / paper / canary / execution / routing / actionability:** forbidden.

**Conclusion:** the closed Case-5 `MALFORMED_SCORE_INPUTS_SUMMARY` subvariant set is narrowly extended from
three to **exactly five** members — adding **`EMPTY_TEXT_ELEMENT`** (second element exactly `""`) and
**`WHITESPACE_ONLY_TEXT_ELEMENT`** (second element a fixed ASCII-whitespace-only string), each a single
fixed shape with a valid fixed first element and all other fields valid/canonical so the projector reaches
**exactly** `MALFORMED_SCORE_INPUTS_SUMMARY` — and the **source-proven** context-shape invariant is pinned:
`score_inputs_summary` is exactly `[source_venue, source_pair]`, both exact `str`, **non-empty and
containing at least one non-whitespace character** (proven by `phase6_1/passive_shadow_input.py`
`_require_str_field`'s `value.strip() == ""` rejection), with **no trimming / normalization / replacement /
coercion / case conversion**. The **seven top-level cases stay exactly seven** (no eighth); the strict
partition, absolute single-fault rule, relevance/harness-scoped poison invariant, real-`sqlite3.Row`
mechanism, adapter-only successful evidence, import isolation, and the ban on synthetic successful rows are
**all preserved**. The recorded mismatch — **P1** monolithic eager projection ahead of relevance/expiry
precedence, **P1** direct-constructor-bypassable exported carriers, and **binding P2** empty/whitespace
context elements currently accepted — leaves **`0ddc899` BUILT but UNRATIFIED** and **Slice D BLOCKED**; the
**only** next eligible gate is the separately-authorized **"Phase 6.2 Slice C Lazy Projection,
Constructor-Hardening & Context-Shape Targeted TDD Correction"** (lazy separately-invoked validation
preserving expiry-before-unit/magnitude + context relevance, hardened exported construction paths,
trust-boundary revalidation, and implementation of the two new subvariants), **not opened here**. **Phase
6.2 remains INCOMPLETE and NOT runtime-ready; capacity stays deferred at 0 emit sites; Phase 6.1 stays
COMPLETE + RATIFIED in its narrow passive-audit scope. No executable work is authorized.**
