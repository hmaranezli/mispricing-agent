# Phase 6.2 — Predicate Precedence, Decimal-Source & Evidence-Consistency Targeted Correction Charter

> **This is a docs-only targeted amendment charter.** It corrects **only** the predicate-precedence,
> decimal-source, evidence-consistency, duplicate-root, and HALT-distinction contradictions in the predicate charter
> (`d7204d6`) and the narrowly-affected upstream clauses — it does **NOT** redesign the predicate model. It
> **implements nothing and authorizes nothing executable**: no runtime code, no tests, no DTO, no loader, no state
> machine, no Gate A/B edits, no Phase 6.1 edits, no S1-adapter edits, no frozen-component edits, no prior-charter
> file edits, no Phase 6.2 runtime, no pytest, no graphify. It corrects prior charters **only** through the exact
> supersession map in §3. It makes **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate
> to `docs/handoff/phase6_2_evidence_intersection_classification_predicate_charter.md`, the Gate A/B charters
> (`5dc757c`, `1071067`, `474cc6f`), the source-boundary + amendment charters (`07135be`, `abd1b41`), the lifecycle
> charters (`e9995e7`, `999a109`), the S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises,
> those govern **except** for the narrow, explicitly-mapped supersessions in §3.

**Base:** `d7204d6d1473260e28f8d6379371088ff3674adc`

---

## 1. Base / Purpose

**Base commit:** `d7204d6d1473260e28f8d6379371088ff3674adc`.

The predicate charter (`d7204d6`) left five contradictions that block runtime eligibility: (1) a **broad** "unit
mismatch causes no lifecycle transition" that wrongly implies a unit mismatch could suppress a `TIMESTAMP_DELTA`
**expiry** (expiry must be independent of magnitude unit); (2) an under-specified evaluation **precedence**;
(3) a conflation of the **Phase 5 S1 decimal acceptance contract** with **Gate B's stricter artifact grammar**;
(4) an "idempotent replay … never creates a duplicate intent" gloss that hides an **in-stream duplicate-root**
hazard (the Silver pair is **not** a database key); and (5) an unbounded "HALT = no-op" that ignores the
**targeted-HALT hard fail-fast**. This charter repairs exactly those, adds the minimal whitelist paths for
SCORE-family consistency, and pins the closed evaluation precedence — nothing else.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Evidence-First Verification (the corrected facts, proven from source)

- **(a) Silver pair is NOT a uniqueness key.** `phase6_1_s1_storage/s1_durable_sqlite_sink.py` DDL declares
  **`append_sequence INTEGER PRIMARY KEY`** and **no `UNIQUE` constraint and no index** on `(artifact_locator,
  physical_record_position)` (a source scan finds zero `UNIQUE`/`INDEX` statements). Therefore the **exact targeted
  Silver pair can physically recur** within one stored/replayed sequence — an in-stream duplicate is possible and
  must be handled (§8), not assumed away.
- **(b) Timestamp ≠ insertion order.** `phase6_1/b4_passive_scoring.py` sets `provenance_timestamp =
  pass_handoff.observed_at_epoch_ms` (audited **observed** epoch-ms), while the adapter assigns `append_sequence` as
  "the monotonic append order" and replays `ORDER BY append_sequence`. So **`provenance_timestamp` is the audited
  observed time; append order alone is the processing order** — the two are distinct, and timestamps need not be
  monotonic.
- **(c) Phase 5 S1 decimal contract ≠ Gate B grammar.** `phase5/net_edge_calculator_boundary.py` accepts S1
  magnitudes under **`_CANONICAL_DECIMAL = re.compile(r"-?\d+(\.\d+)?")`** (anchored `.fullmatch`) and serializes via
  `_to_canonical_decimal_string` (`"0"` for zero; else `format(dec, "f")`). This acceptance lexis is **looser** than
  Gate B's artifact grammar (`474cc6f` §11 forbids leading zeros, trailing fractional zeros, `-0`, trailing point).
  The two decimal-source contracts are therefore **separate** (§7), and Gate B's grammar must **never** be applied
  to historical S1 evidence.

---

## 3. Exact Supersession Map (binding)

Each row supersedes **only** the quoted clause; everything else stands. The substituted principle is **(U)**: *unit
comparability gates `PASSIVE_EVIDENCE_CROSSING` only; after exact context equality and valid timestamps,
`TIMESTAMP_DELTA` expiry is independent of magnitude unit; `delta > duration` ⇒ `INTENT_EXPIRED` is classified
before any unit or magnitude evaluation; for `0 ≤ delta ≤ duration`, a directional unit mismatch is passive
not-comparable and causes no **crossing** transition; root establishment for a directional definition still requires
unit comparability.*

| Charter / § | Exact quoted clause | Precise replacement |
|---|---|---|
| `07135be` §10 | "**In-flight unit non-comparability** … a **passive not-comparable result** — **no lifecycle transition**, no mutation, NOT fail-fast, and NOT a Phase 6.1 halt" | "In-flight unit non-comparability produces **no `PASSIVE_EVIDENCE_CROSSING` transition** (a passive not-comparable no-op) — it does **not** suppress a `TIMESTAMP_DELTA` expiry; no mutation, not fail-fast, not a Phase 6.1 halt. (U)" |
| `5dc757c` §8 | "**Unit mismatch remains passive not-comparable** — **no transition**, NOT fail-fast, and NOT a Phase 6.1 halt" | "Unit mismatch remains passive not-comparable — **no crossing transition** (expiry remains independent of unit, §3 (U)); not fail-fast, not a halt." |
| `1071067` §9 | "**unit exact-equality** for `boundary_unit_context` vs `score_unit_context` (no normalization)" | "unit exact-equality **gates `PASSIVE_EVIDENCE_CROSSING` and directional root establishment only** (no normalization); it does **not** gate expiry. (U)" |
| `d7204d6` §6 | "**Unit inequality is passive not-comparable and causes no transition** (no-op; not fail-fast, not a halt)." | "Unit inequality is passive not-comparable and causes **no crossing transition** (no-op); it does **not** block expiry; not fail-fast, not a halt. (U)" |
| `d7204d6` §8 | (expiry table — correct, but precedence relative to unit/magnitude was implicit) | **Reaffirmed and made explicit**: `delta > duration` ⇒ `INTENT_EXPIRED` is classified **before** any unit or magnitude evaluation (§4 steps g vs i/j). |
| `d7204d6` §10 | "**HALT, irrelevant, non-comparable, and unit-mismatch records are passive no-ops** (not errors, not fail-fast, not halts)" | "**Non-targeted** HALT, irrelevant, non-comparable, and in-window unit-mismatch records are passive no-ops. A **targeted** HALT/non-SCORE at an unestablished manifest key is a **hard fail-fast** (§9); a later repetition of the established target key is a **duplicate-root hard fail-fast** (§8)." |
| `d7204d6` §4 / §11 | "re-encountering the establishing key (**idempotent replay**) **never** creates a duplicate intent" | "A **second in-stream occurrence** of the exact targeted Silver pair is an **ambiguous duplicate-root → hard fail-fast** (§8); it never re-anchors, never creates a second slot, and never acts as a later comparison. Determinism/idempotency refers **only** to re-running the **whole fixed input pair in a fresh replay context** — distinct from an in-stream duplicate." |
| `d7204d6` conclusion | "a directional unit mismatch is a passive no-op" | "a directional unit mismatch blocks **crossing only** (and blocks directional **root establishment**); it never blocks expiry. (U)" |

The broad "unit mismatch causes no lifecycle transition" reading is superseded **everywhere** above; **directional
root establishment still requires unit comparability** (`d7204d6` §4 line 95 preserved, now explicitly
establishment-scoped).

---

## 4. Closed Evaluation Precedence for Later Records (binding)

For each **strictly later append-ordered** S1 record evaluated against an established intent, the **only** legal
ordering is:

- **a.** Absorbing terminal (`INTENT_EXPIRED` / `INTENT_RETIRED`) → **self-loop** (no further evaluation).
- **b.** Non-SCORE / non-targeted HALT → **irrelevant no-op**.
- **c.** **Exact SCORE-family structural consistency validation** (§5) — inconsistency on an evaluated SCORE is
  **hard fail-fast**.
- **d.** **Context-shape validation and exact context equality** (§5, §10) — malformed/missing/not-exactly-two-text
  `score_inputs_summary` on an evaluated SCORE is **hard fail-fast**; well-formed context inequality is an
  **irrelevant no-op**.
- **e.** **Timestamp validation and `TIMESTAMP_DELTA`** (§6): `delta = comparison_timestamp − anchor_timestamp`
  (exact integers).
- **f.** `delta < 0` → **passive timestamp non-comparability** (no-op; never expiry).
- **g.** `delta > duration` → **`INTENT_EXPIRED`** (classified **here**, before any unit or magnitude evaluation).
- **h.** In-window (`0 ≤ delta ≤ duration`) **`INERT_STATE`** → **no-op**.
- **i.** In-window **directional unit inequality** → **passive no-op** (no crossing).
- **j.** In-window **directional magnitude validation and crossing predicate** (§7 of `d7204d6`): magnitude malformed
  → hard fail-fast; else `POSITIVE_EXPOSURE: evidence ≥ boundary` / `NEGATIVE_EXPOSURE: evidence ≤ boundary` →
  `INTENT_RECORDED → HYPOTHETICAL_CONDITION_MET` (or sustaining/no-op).

**No other ordering is legal.** In particular, unit (i) and magnitude (j) are evaluated **only after** expiry (g) has
been ruled out.

---

## 5. SCORE-Family Consistency (binding)

A qualifying **root or later** SCORE that is **evaluated** must satisfy **all** of:

- replay-row `observation_kind == "SCORE"`;
- `canonical_text_payload.observation_kind == "SCORE"`;
- replay-row `family_descriptor == "passive_net_edge_diagnostic"`;
- `family_payload.score_family_descriptor == "passive_net_edge_diagnostic"`;
- the row and payload descriptors/kinds **agree exactly** (row kind == payload kind; row descriptor == payload
  descriptor).

**Any inconsistency required by an evaluated SCORE is hard fail-fast** (§9 firewall; never an S4 halt). The literal
`"passive_net_edge_diagnostic"` is the ratified B4 `_FAMILY_DESCRIPTOR` (`phase6_1/b4_passive_scoring.py`), surfaced
by the adapter's `_family_descriptor()` into the replay-row `family_descriptor` column.

**Whitelist additions (exact canonical paths only):** `canonical_text_payload.observation_kind` and
`canonical_text_payload.provenance_timestamp` are added to the `d7204d6` §3 whitelist **solely** for these
consistency and timestamp-authority checks. **Generic dict/JSON scraping, key-name guessing, and all other unlisted
fields remain banned.**

---

## 6. Timestamp Authority (binding)

- `provenance_timestamp` means the **audited `observed_at_epoch_ms`**, **NOT** insertion/append time.
- **Append order determines processing order** (replay `ORDER BY append_sequence`); the anchor/comparison roles are
  by append order, not by timestamp value.
- An evaluated SCORE must satisfy: `canonical_text_payload.provenance_timestamp` is an **exact non-negative
  integer**, **and** the replay-row `provenance_timestamp` equals its **canonical decimal text**
  (`str(int)` form). **Any disagreement is hard fail-fast.**
- **Timestamp values need not be monotonic** across append order (`abd1b41` §9). `TIMESTAMP_DELTA` uses exact
  integer arithmetic; a negative delta is passive non-comparability (§4 f), never expiry.

---

## 7. Separate Decimal-Source Contracts (binding)

- **S1 `passive_score_magnitude`** must be validated under the **exact ratified Phase 5 lexical contract**
  (`_CANONICAL_DECIMAL = ^-?\d+(\.\d+)?$`, anchored), **NOT** Gate B's stricter artifact grammar.
- **Artifact `passive_boundary_magnitude`** remains **pre-verified under Gate B** (`474cc6f` §11) before replay.
- Each accepted lexical value is converted **independently** to **exact base-10 `Decimal` semantics**, and **only
  `Decimal` values are compared**.
- **Ban** float/double, rounding, quantization, lexical rewriting, and **applying Gate B normalization to historical
  S1 evidence**.
- **S1 lexical distinctions remain preserved in audit evidence** even when `Decimal` values compare equal (e.g.
  `"1.50"` and `"1.5"` are equal as `Decimal` but stay distinct verbatim text in the immutable S1 trail — never
  rewritten to satisfy Gate B's canonical form).

---

## 8. Duplicate Targeted Silver Pair (binding)

- The Silver pair is **not** a database primary key (§2 a) — `append_sequence` is.
- **A second occurrence of the exact targeted Silver pair within one ordered S1 replay is an ambiguous
  duplicate-root occurrence and MUST hard fail-fast.** It must **not** create another lifecycle slot, must **not**
  re-anchor the intent, and must **not** act as a later comparison observation.
- **Re-running the entire fixed input pair** (same sealed artifact + same ordered S1 records) **in a fresh replay
  context** remains **deterministic / idempotent** and is **distinct** from an in-stream duplicate. Idempotency is a
  property of whole-replay re-execution, not of intra-stream key repetition.

---

## 9. HALT Distinction (binding)

- **Targeted HALT / non-SCORE at an unestablished manifest key** → **reconstruction hard fail-fast**; no lifecycle
  transition and no synthetic terminal.
- **Any later repetition of the established target key** → **duplicate-root hard fail-fast** (§8).
- **Non-targeted HALT** (a HALT whose Silver pair is not a manifest key, or which is irrelevant to every active
  intent) → **irrelevant no-op**.
- The unbounded `d7204d6` §10 "HALT … are passive no-ops" wording is **qualified accordingly** (§3): only the
  **non-targeted** HALT is a no-op.

---

## 10. Malformed Context (binding)

- For an **evaluated later SCORE** while active intents exist, a `score_inputs_summary` that is **malformed,
  missing, or not exactly two text scalars** **prevents context classification and MUST hard fail-fast** (§4 d).
- **Context inequality after successful structural validation** (well-formed two-scalar `score_inputs_summary` whose
  `(source_venue, source_pair)` simply differs from the root) **remains an irrelevant no-op** — not an error.

---

## 11. Preserved Unchanged (affirmed)

- `POSITIVE_EXPOSURE: evidence ≥ boundary`; `NEGATIVE_EXPOSURE: evidence ≤ boundary`; `INERT_STATE` has no crossing.
- Expiry inequality: `delta > duration` ⇒ `INTENT_EXPIRED`.
- Negative `delta` is passive non-comparability (never expiry).
- `INTENT_RETIRED` remains **reserved and unreachable** (no S1 retirement vocabulary; never synthesized).
- The **equality-only fallback remains UNACTIVATED**.
- **No** wall clock, S4 fallback, mutation/write-back, global state/registry/cache/singleton, actionability,
  capacity, or integration. **Capacity stays deferred at exactly 0 emit sites.** Phase 6.1 stays frozen, COMPLETE +
  RATIFIED. Terminal invariant unchanged (at most one terminal; open frozen at replay EOF is valid audit state).

---

## 12. Status & Remaining Gates (ratified)

- **`d7204d6` alone did NOT make runtime TDD eligible** — the predicate-precedence, decimal-source,
  evidence-consistency, duplicate-root, and HALT contradictions above had to be corrected first. This charter closes
  them.
- **After this corrective charter is ratified, the separately-authorized Phase 6.2 reconstruction runtime /
  verifier / state-machine / container TDD gate MAY be named eligible — but it MUST NOT be opened, drafted,
  implemented, or authorized here**, and any frozen-component / lock-touching slice requires its own human
  authorization under `CLAUDE.md`.
- **Phase 6.2 remains UNBUILT and NOT runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED; capacity deferred (0
  emit sites); production / live / paper / canary / execution / routing / actionability forbidden.

**Conclusion:** the predicate contradictions are corrected through a targeted, quote-anchored supersession map (§3)
and nothing else. The substituted principle **(U)** narrows every broad "unit mismatch ⇒ no lifecycle transition"
clause (`07135be` §10, `5dc757c` §8, `1071067` §9, `d7204d6` §6/§8/§10/conclusion) so that **unit comparability gates
`PASSIVE_EVIDENCE_CROSSING` only**: after exact context equality and valid timestamps, **`TIMESTAMP_DELTA` expiry is
independent of magnitude unit**, **`delta > duration` ⇒ `INTENT_EXPIRED` is classified before any unit or magnitude
evaluation**, in-window directional unit mismatch yields **no crossing** (passive no-op), and **directional root
establishment still requires unit comparability**. The **closed evaluation precedence** is pinned (a→j: absorbing
self-loop; non-SCORE/non-targeted-HALT no-op; SCORE-family consistency; context shape + equality; timestamp +
`TIMESTAMP_DELTA`; `delta<0` non-comparability; `delta>duration` expiry; in-window inert no-op; in-window directional
unit no-op; in-window directional magnitude + crossing), **no other ordering legal**. **SCORE-family consistency**
requires row/payload `observation_kind == "SCORE"` and `family_descriptor`/`score_family_descriptor ==
"passive_net_edge_diagnostic"` to **agree exactly** (else hard fail-fast), adding **only**
`canonical_text_payload.observation_kind` and `canonical_text_payload.provenance_timestamp` to the whitelist (generic
scraping still banned). **Timestamp authority**: `provenance_timestamp` is the audited `observed_at_epoch_ms`,
append order is processing order, the payload integer must equal the row's canonical decimal text (else fail-fast),
and timestamps need not be monotonic. **Separate decimal contracts**: S1 magnitude under the **Phase 5 lexis**
(`-?\d+(\.\d+)?`), boundary under **Gate B**, both to exact base-10 `Decimal`, compared as `Decimal` only, with
**Gate B normalization never applied to historical S1 evidence** and S1 lexical distinctions preserved even when
values are `Decimal`-equal. The **Silver pair is not a DB key**, so a **second in-stream occurrence of the targeted
pair is a duplicate-root hard fail-fast** (no second slot / re-anchor / comparison), distinct from idempotent
whole-replay re-execution. **Targeted HALT/non-SCORE at an unestablished key and any later repetition of the
established key are hard fail-fast**; only **non-targeted HALT** is a no-op. **Malformed/not-two-scalar context on an
evaluated SCORE is hard fail-fast**, while well-formed context inequality is an irrelevant no-op. The crossing
inequalities, expiry inequality, negative-delta non-comparability, **reserved-unreachable `INTENT_RETIRED`**,
**unactivated equality-only fallback**, and all no-wall-clock / no-S4 / no-mutation / no-global-state /
no-actionability / no-capacity / no-integration provisions are **preserved**. **`d7204d6` alone did not confer
runtime eligibility**; after this charter the runtime TDD gate **may be named eligible but is not opened here**.
**Phase 6.2 remains UNBUILT and NOT runtime-ready. No executable work is authorized.**
