# Phase 6.2 — Fixed-Whitespace Literal & Slice-C/D Trust-Ownership Micro-Correction Charter

> **This is a docs-only targeted micro-correction charter.** It corrects **only** two imprecisions in the
> score-context empty/whitespace subvariant charter (`04c88fc`): (a) the `WHITESPACE_ONLY_TEXT_ELEMENT`
> fixture must be a single fixed literal (no "e.g." latitude), and (b) the named Slice-C correction's
> trust-boundary ownership vs Slice D. It does **NOT** redesign the fixture architecture, the seven-case
> partition, the five Case-5 subvariants, the projector, or any predicate. It **implements nothing and
> authorizes nothing executable**: no runtime code, no tests, no fixture code, no package, no DTO, no
> adapter, no Phase 6.1 edits, no S1 edits, no Gate A/B edits, no prior-charter file edits, no lock-test
> edits, no config, no generated-file edits, no pytest, no graphify. It is exactly one docs file and
> corrects `04c88fc` **only** through the supersession map in §3. It makes **no** Phase 6.2
> runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_negative_evidence_score_context_empty_whitespace_subvariant_targeted_amendment_charter.md`
> (`04c88fc`),
> `docs/handoff/phase6_2_negative_evidence_case_isolation_relevance_harness_micro_correction_charter.md`
> (`045caea`), `docs/handoff/phase6_2_negative_evidence_fixture_boundary_charter.md` (`b4368fd`),
> `docs/handoff/phase6_2_reconstruction_runtime_tdd_planning_slice_charter.md` (`457d279`), the predicate +
> precedence/decimal-consistency charters (`474cc6f`, `d7204d6`), the full Phase 6.2 chain, the S1
> durable-storage charters, and `CLAUDE.md`; where any conflict arises, those govern **except** for the
> narrow, explicitly-mapped supersessions in §3.

**Base:** `04c88fc87723ced6183977fb9e02e6ed8832abd2`

---

## 1. Base / Purpose

**Base commit:** `04c88fc87723ced6183977fb9e02e6ed8832abd2`.

`04c88fc` correctly added the `EMPTY_TEXT_ELEMENT` and `WHITESPACE_ONLY_TEXT_ELEMENT` Case-5 subvariants and
pinned the source-proven non-empty / non-whitespace context-shape invariant. It left **two** imprecisions
that this charter closes:

1. **Non-deterministic whitespace literal.** `04c88fc` §4 described `WHITESPACE_ONLY_TEXT_ELEMENT` as "a
   fixed ASCII-whitespace-only string (**e.g.** a single space or a fixed run of ASCII spaces/tabs…)". The
   "e.g." and the alternative forms violate the **fixed single-shape** discipline (`045caea` §6/§9): a
   subvariant must be **one** fixed construction, not a family. The exact bytes must be pinned.
2. **Ambiguous Slice-C/D trust ownership.** `04c88fc` §9 item 3 ("**defensively revalidate at trust
   boundaries** … re-assert invariants where a projection is **consumed**") could be read as obligating the
   Slice-C correction to perform **consumer-side (Slice-D)** revalidation. That conflates ownership: Slice C
   owns its own producer/public-operation boundary; the **consumer-side** revalidation is a **Slice-D**
   obligation, to be discharged only when Slice D is separately authorized.

This charter pins the exact whitespace bytes and the exact Slice-C-vs-Slice-D trust ownership — **nothing
else**. Every preserved provision of `04c88fc` / `045caea` / `b4368fd` stands.

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Evidence-First Verification (unchanged contract)

- The source-proven context shape is unchanged: `phase6_1/b4_passive_scoring.py` sets
  `score_inputs_summary = (source_venue, source_pair)`; `phase6_1/passive_shadow_input.py`
  `_require_str_field` rejects non-`str` (`TypeError`) and empty/whitespace-only (`value.strip() == ""` ⇒
  `ValueError`). A single U+0020 SPACE satisfies `" ".strip() == ""`, so it is a **valid poison** whose only
  outcome is `MALFORMED_SCORE_INPUTS_SUMMARY` — it can never be legitimately audited.
- No new field, path, byte interpretation, or generic scraping is introduced. The fixture reads only the
  already-whitelisted `family_payload.score_inputs_summary`.

---

## 3. Exact Supersession Map (binding)

| Charter / § | Quoted clause | Precise replacement |
|---|---|---|
| `04c88fc` §4 (`WHITESPACE_ONLY_TEXT_ELEMENT` bullet) | "`score_inputs_summary` … whose **second element is a fixed ASCII-whitespace-only string** (**e.g.** a single space or a fixed run of ASCII spaces/tabs — a fixed literal, never caller-chosen)." | "`score_inputs_summary` is exactly `["hl", " "]` — first element exactly the two ASCII characters `hl`; **second element exactly one U+0020 ASCII SPACE** (UTF-8 exactly the single byte `0x20`). **No** `e.g.`, no alternative whitespace form (§4)." |
| `04c88fc` §4 (`EMPTY_TEXT_ELEMENT` bullet) | "second element is exactly the empty string `""`." | **Reaffirmed and pinned to the exact list:** `score_inputs_summary` is exactly `["hl", ""]` — first element exactly `hl`; second element exactly the empty string `""` (UTF-8 zero bytes). |
| `04c88fc` §9 item 3 ("**Defensively revalidate at trust boundaries** … re-assert invariants where a projection is **consumed**, not only where first produced.") | the Slice-C correction owns consumer-boundary revalidation | "the Slice-C correction owns **only producer/public-operation-boundary** validation/revalidation (§5); **consumer-side (Slice-D) revalidation is a Slice-D obligation**, recorded but not owned, implemented, or claimed by the Slice-C correction (§5)." |
| `04c88fc` conclusion (whitespace wording + "trust-boundary revalidation" phrase) | "a fixed ASCII-whitespace-only string"; "trust-boundary revalidation" read as consumer-side | restated under the **fixed `" "` (one `0x20` byte)** literal and the **Slice-C-producer-boundary-only** ownership, with the **Slice-D consumer-boundary revalidation** recorded as a separate future obligation (§4–§5). |

**No other clause is superseded.** The seven top-level cases, the five Case-5 subvariants, the strict
partition / non-overlap, the absolute single-fault rule, the relevance/harness-scoped poison invariant, the
real-`sqlite3.Row` mechanism, adapter-only successful evidence, import isolation, and the ban on synthetic
successful rows are all **unchanged**.

---

## 4. Pinned Fixed Fixture Byte Shapes (binding)

Both fixtures are **fixed single-fault Case-5 fixtures** whose **only** valid outcome is
`MALFORMED_SCORE_INPUTS_SUMMARY` when their context projection/validation operation is demanded:

- **`EMPTY_TEXT_ELEMENT`** — payload `score_inputs_summary` is **exactly** `["hl", ""]`.
  - First element: exactly the two ASCII characters `hl`.
  - Second element: exactly the empty string `""` (no bytes).
- **`WHITESPACE_ONLY_TEXT_ELEMENT`** — payload `score_inputs_summary` is **exactly** `["hl", " "]`.
  - First element: exactly the two ASCII characters `hl`.
  - Second element: **exactly one U+0020 ASCII SPACE** — its UTF-8 representation is **exactly the single
    byte `0x20`**.

**Forbidden for `WHITESPACE_ONLY_TEXT_ELEMENT` (binding):** tab (`0x09`), multiple spaces, carriage return
(`0x0D`), line feed (`0x0A`), form-feed (`0x0C`), vertical-tab (`0x0B`), no-break space (NBSP, U+00A0), any
other Unicode whitespace, the empty string, any caller-selected text, and any caller-selected position/index.
The second element is the **fixed literal single space**; the first element is the fixed literal `hl`.

For **both** subvariants: list arity is exactly two, both elements are JSON strings (so neither `WRONG_ARITY`
nor `NON_TEXT_ELEMENT` is reached first), and **every other row/payload field remains valid and canonical**
(row/payload kinds agree on `SCORE`; family descriptors agree on `passive_net_edge_diagnostic`;
`provenance_timestamp` is a consistent canonical non-negative integer; `passive_score_magnitude` is valid
Phase-5 lexis; `score_unit_context` is valid text) so the projector reaches **exactly**
`MALFORMED_SCORE_INPUTS_SUMMARY`. **Absolute single-fault isolation** holds: each violates exactly the named
context-shape invariant on the second element; reaching a different/earlier error does **not** prove the case
and **MUST fail**.

---

## 5. Exact Slice-C vs Slice-D Trust Ownership (binding)

**The named Slice-C correction owns ONLY:**

- hardening the Slice-C **exported carriers** (`ScoreEvidenceProjection`, `NonScoreEnvelopeProjection`) and
  their **construction paths** (factory-only / self-validating; no unvalidated state);
- validating / revalidating **inputs to Slice-C's own public lazy projection operations** (its producer /
  public-operation boundary);
- **preventing direct-constructor bypass inside Slice C**;
- **implementing the two authorized Case-5 fixture subvariants** (`EMPTY_TEXT_ELEMENT`,
  `WHITESPACE_ONLY_TEXT_ELEMENT`, §4) and enforcing the source-proven non-empty / non-whitespace
  context-shape invariant in the projector (no trimming / normalization / repair).

**The named Slice-C correction MUST NOT:**

- create, edit, import, or implement `classification_predicates.py`;
- implement Slice D;
- claim consumer-side **Slice-D** validation;
- modify Slice D / E / F behavior or containers.

**Slice D remains separately BLOCKED.** When Slice D is **separately authorized later**, it **must
defensively revalidate projection inputs at its own consumer boundary** (re-assert the Slice-C invariants
where it consumes a projection). **That future Slice-D obligation is recorded here but is NOT implemented,
owned by Slice C, or opened by this charter.**

---

## 6. Preserved Prohibitions & Semantics (affirmed)

- **Exactly seven** top-level negative cases (no eighth).
- **Exactly five** Case-5 subvariants (`MISSING_SCORE_INPUTS_SUMMARY`, `WRONG_ARITY_SCORE_INPUTS_SUMMARY`,
  `NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT`, `EMPTY_TEXT_ELEMENT`, `WHITESPACE_ONLY_TEXT_ELEMENT`).
- **Absolute single-fault isolation** (exactly one named invariant violated; no incidental second defect; a
  different/earlier failure must fail the test).
- **Relevance-scoped / harness-scoped poison semantics** (`045caea` §10–§13): these fixtures fail **only**
  inside an authorized harness that actually demands the context projection/validation operation; they must
  **not** override **terminal relevance, context inequality, expiry-before-unit/magnitude precedence, or
  lazy field evaluation**, and may not smuggle an inspection production legitimately skips.
- **Real tests-only `sqlite3.Row` mechanism** (one parameterized in-memory `SELECT` over the six aliases,
  fresh connection, one Row, connection closed, no leak; no DDL/DML/temp-DB, adapter mutation,
  monkeypatch/mock/**fake**-Row/dict substitution, private SQL-constant import, or network/persistent state).
- **Adapter-only successful evidence** (`S1DurableSqliteSink.record_observation` + ratified replay);
  **synthetic successful rows / fabricated intent state / alternate observed-event sources remain
  forbidden**.
- **Import isolation** (helper only at `tests/fixtures/phase6_2_negative_evidence_rows.py`; production never
  imports tests/fixtures/pytest/mocks; static import-direction lock; runtime carries no test-only
  flag/branch/parser/fixture awareness).
- **No** caller-selected value/position/callback/raw-SQL/payload-mutation-function/generic factory; **no**
  trimming/normalization/coercion/case-conversion.
- **No** wall clock, S4 fallback, mutation/write-back, global state/registry/cache/singleton, actionability,
  capacity, or integration. **Capacity stays deferred at exactly 0 emit sites.**

---

## 7. Status (recorded)

- **`04c88fc` is directionally correct but required this precision correction** (fixed whitespace literal +
  Slice-C/D trust ownership).
- **`0ddc899` Slice C remains BUILT but UNRATIFIED** (the §8 correction below is still required: monolithic
  eager projection ahead of relevance/expiry precedence; direct-constructor-bypassable carriers;
  empty/whitespace context currently accepted).
- **Slice D remains BLOCKED.**

---

## 8. Next Eligible Gate (named, NOT opened)

After this docs correction, the **only** next eligible gate is the separately-authorized **"Phase 6.2 Slice
C Lazy Projection, Constructor-Hardening & Context-Shape Targeted TDD Correction"**, which must (within the
Slice-C ownership boundary of §5):

1. provide **separately invoked lazy projection/validation operations** preserving the ratified
   **expiry-before-unit/magnitude** precedence and **context relevance** (no forced inspection of fields
   production legitimately skips);
2. **harden every exported projection construction path** (factory-only / self-validating; no
   direct-constructor bypass);
3. **revalidate at Slice-C's own producer/public-operation boundary** (consumer-side Slice-D revalidation is
   a separate, future Slice-D obligation, §5);
4. **implement** `EMPTY_TEXT_ELEMENT` (`["hl", ""]`) and `WHITESPACE_ONLY_TEXT_ELEMENT` (`["hl", " "]`, one
   `0x20` byte) and enforce the non-empty / non-whitespace context-shape invariant (reject empty/whitespace
   as `MALFORMED_SCORE_INPUTS_SUMMARY`, no trimming/normalization/repair).

**This charter does NOT open, draft, implement, or authorize that runtime correction** — it only pins the
fixed bytes and the trust ownership and names the gate.

**Conclusion:** `WHITESPACE_ONLY_TEXT_ELEMENT` is pinned to the exact fixed payload `["hl", " "]` — first
element exactly `hl`, second element **exactly one U+0020 ASCII SPACE (UTF-8 byte `0x20`)** — with **"e.g."
and every alternative form (tab, multiple spaces, CR, LF, form-feed, vertical-tab, NBSP, other Unicode
whitespace, empty text, caller-selected text/position) forbidden**; `EMPTY_TEXT_ELEMENT` is pinned to exactly
`["hl", ""]`; both remain **fixed single-fault Case-5 fixtures** yielding **exactly**
`MALFORMED_SCORE_INPUTS_SUMMARY` when their context operation is demanded. The named **Slice-C correction
owns only** Slice-C carrier/construction hardening, its **own** public lazy-operation input
validation/revalidation, direct-constructor-bypass prevention, and the two new fixture subvariants — and
**must not** create/edit/import/implement `classification_predicates.py`, implement Slice D, claim
consumer-side Slice-D validation, or modify Slice D/E/F; **Slice D stays separately blocked** and, when later
authorized, **must defensively revalidate projection inputs at its own consumer boundary** (recorded, not
opened). The **seven top-level cases**, **five Case-5 subvariants**, **absolute single-fault isolation**,
**relevance/harness-scoped poison**, **terminal/context relevance and expiry-before-unit/magnitude**,
**real-`sqlite3.Row` mechanism**, **adapter-only successful evidence**, **import isolation / no synthetic
successful rows**, and **all capacity/actionability prohibitions** are **preserved**. **`04c88fc`
directionally correct but corrected; `0ddc899` Slice C BUILT but UNRATIFIED; Slice D BLOCKED**; the only next
eligible gate is the separately-authorized **"Phase 6.2 Slice C Lazy Projection, Constructor-Hardening &
Context-Shape Targeted TDD Correction"**, **not opened here**. **Phase 6.2 remains INCOMPLETE and NOT
runtime-ready; capacity stays deferred at 0 emit sites; Phase 6.1 stays COMPLETE + RATIFIED in its narrow
passive-audit scope; production / live / paper / canary / execution / routing / actionability remain
forbidden. No executable work is authorized.**
