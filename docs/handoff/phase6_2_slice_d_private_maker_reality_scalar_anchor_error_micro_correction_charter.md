# Phase 6.2 — Slice-D Private-Maker Reality / Scalar-Anchor Error Micro-Correction Charter

> **This is a docs-only two-contradiction micro-correction charter.** It marks the prior Slice-D root-operand
> reconciliation charter (`b874ec0`) **historical and UNRATIFIED** for **exactly two** contradictions — an absolute
> "only a real `sqlite3.Row` can construct the Slice-C carriers" claim that ignores the private Slice-C makers, and a
> scalar-anchor error-mapping that wrongly assigns `PREDICATE_WRONG_CARRIER_TYPE` to a non-`str` anchor — and
> supersedes **only** those clauses. Every other asymmetric-interface decision of `b874ec0` stands intact. It
> **implements nothing and authorizes nothing executable**: no runtime code, no tests, no fixtures, no
> `atomic_replay_step.py`, no `reconstruction.py`, no lock edits, no prior-charter edits, no generated files, no
> pytest, no graphify, and no commit beyond this single docs file. It does **not** edit, amend, rebase, delete, or
> rewrite history. It is subordinate to the full Phase 6.2 chain — the sealed Slice-A/B/C/D runtimes, the Slice-E
> exact-shape chain (`85d1ba6`→`ff92ad0`→`90bb5d3`), the Slice-D reconciliation charter (`b874ec0`, hereby
> UNRATIFIED), and `CLAUDE.md` — and where any conflict arises, those govern **except** for the two corrections in
> §2.

**Base:** `b874ec0a13f0c286eafda7bdbf9a77d2fca6178d`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `b874ec0a13f0c286eafda7bdbf9a77d2fca6178d`.

`b874ec0` reconciled the Slice-D root-operand interface but carried two exactness contradictions: (1) its line-29
prose asserts the Slice-C projection carriers are "built only from a real `sqlite3.Row`, never synthesizable from
stored scalars" — an **absolute** claim contradicted by the real Slice-C private makers `_make_score_context` /
`_make_score_timestamp`, which construct and validate those carriers internally without a row; and (2) its §8.2 / §10
matrices map the old symmetric `ScoreTimestampProjection` anchor to `PREDICATE_WRONG_CARRIER_TYPE`, contradicting the
corrected scalar-`anchor: str` contract (under which a non-`str` anchor is `type(anchor) is not str` and therefore
maps to `PREDICATE_INVALID_CANONICAL_TIMESTAMP`), and contradicting `b874ec0`'s own line-183 row.

**`b874ec0` is hereby marked historical and UNRATIFIED for exactly these two contradictions.** Every other `b874ec0`
clause stands intact (§7). `b874ec0` is **not** edited/deleted/amended/rebased/force-pushed.

**No capacity validation and no capacity pass is claimed by this charter.**

---

## 2. Two-Clause Quote-Anchored Supersession Map to `b874ec0` (binding)

| `b874ec0` site | Quoted clause | Precise replacement |
|---|---|---|
| §1 line 29 | "while Slice-C carriers are **factory-only** (built only from a real `sqlite3.Row`, **never synthesizable from stored scalars**, and never from the unavailable root row)." | The corrected private-maker statement in §3. Slice-C carriers are factory-only **for external/public consumption** (the public `project_*(*, replay_row)` path); internally they are also constructed by the **private** makers `_make_score_context` / `_make_score_timestamp`. The contradiction blocking Slice E is **not** "physically impossible to construct" but "**not sanctioned** for Slice-E consumption" — no public maker/bridge exists and the private makers are off-limits to Slice E. |
| §8.2 matrix line 182 **and** §10 future-test line 209 | "`ScoreTimestampProjection` (old symmetric anchor) … ❌ `PREDICATE_WRONG_CARRIER_TYPE`" / "`classify_timestamp_window(anchor=<ScoreTimestampProjection>, …)` → `PREDICATE_WRONG_CARRIER_TYPE`" | The closed scalar-anchor rule in §4: a `ScoreTimestampProjection` anchor (and **every** non-`str` anchor) → `PREDICATE_INVALID_CANONICAL_TIMESTAMP`. There is **no** special type check, ghost branch, compatibility branch, fallback, overload, or distinct reason for the old `ScoreTimestampProjection` anchor. |

All other `b874ec0` clauses remain in force.

---

## 3. Corrected Private-Maker Reality (binding)

- **Acknowledged:** Slice C contains the **private** functions `_make_score_context` and `_make_score_timestamp`
  (`s1_evidence_projection.py`), which construct and validate `ScoreContextProjection` / `ScoreTimestampProjection`
  carriers internally (via the closed `_seal` primitive) — **without** a `sqlite3.Row`.
- **Every absolute "only a real `sqlite3.Row` can construct these carriers" / "never synthesizable from stored
  scalars" claim is removed/superseded.** The accurate statement is: the carriers' **public/direct** `__init__` is
  forbidden (`_forbid_direct_construction`), and the only **sanctioned public** evidence-production path remains the
  reached Slice-C `project_*(*, replay_row)` operations under strict-lazy precedence.
- **These makers remain private Slice-C implementation details and Slice-C test surfaces.** **Slice E must never
  import, call, alias, expose, wrap, or depend on them.**
- **No public maker, bridge, adapter, inverse hydration, synthetic row, fabricated row, registry, or cache is
  authorized.**
- **Do not confuse "physically constructible by a private maker" with "sanctioned for Slice-E consumption."** The
  reason the Slice-A root operand could not feed the old symmetric predicates was the **sanctioning/ownership**
  boundary (no public way for Slice E to obtain a Slice-C root carrier), not a claim of physical impossibility. The
  §-`b874ec0` asymmetric fix (root operand = the Slice-A carrier the slot already stores) stands and is the correct
  resolution.

---

## 4. Corrected Scalar-Anchor Error Rule (binding)

For `classify_timestamp_window(*, anchor: str, comparison: ScoreTimestampProjection, duration_ms: int)`:

- `anchor` must satisfy **`type(anchor) is str`**.
- **Every value for which `type(anchor) is not str` maps to `PREDICATE_INVALID_CANONICAL_TIMESTAMP`** — this
  includes a `ScoreTimestampProjection` (the superseded symmetric anchor), `int`, `bool`, `None`, `Decimal`,
  `bytes`, containers, arbitrary objects, **and `str` subclasses** (`type(x) is str` is `False` for a subclass).
- **Every exact `str` that violates the ASCII canonical grammar `"0" | [1-9][0-9]*`** (leading zero, sign, fraction,
  exponent, whitespace, Unicode decimal digit, empty) **also maps to `PREDICATE_INVALID_CANONICAL_TIMESTAMP`.**
- **There is no special type check, ghost branch, compatibility branch, fallback, overload, or distinct reason for
  the old `ScoreTimestampProjection` anchor** — it is just one non-`str` value among many, all sharing the one reason.
- **`PREDICATE_WRONG_CARRIER_TYPE` is reserved** for the parameters whose current contract requires an exact carrier
  class: the **context** root operand (`EstablishedRootContext`), the **context** observed operand
  (`ScoreContextProjection`), and the **timestamp comparison** operand (`ScoreTimestampProjection`). It is **never**
  used for the scalar `anchor`.
- **Deterministic precedence preserved:** validate the scalar `anchor` first → then the exact
  `ScoreTimestampProjection` `comparison` (with full forgery/canonical validation) → then `duration_ms` → then the
  lexical arithmetic.

### 4.1 Closed scalar-anchor reason table

| `anchor` value | `type(anchor) is str`? | canonical `"0"\|[1-9][0-9]*`? | reason |
|---|---|---|---|
| `"0"`, `"1700000000000"`, ≥5000-digit `[1-9][0-9]*` | yes | yes | ✅ proceeds |
| `"00"` / `"007"` / `"-1"` / `"+1"` / `"1.0"` / `"1e3"` / `" 1"` / `"1 "` / `""` / Unicode-digit | yes | no | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| `ScoreTimestampProjection` (old symmetric anchor) | no | — | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| `int` / `bool` / `None` / `Decimal` / `bytes` / list / dict / arbitrary object | no | — | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| `str` subclass instance (even if its text is canonical) | no (`type(x) is str` False) | — | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |

---

## 5. Corrected Operand Matrix — `classify_timestamp_window` (binding, replaces `b874ec0` §8.2)

| `anchor` | `comparison` | `duration_ms` | Outcome |
|---|---|---|---|
| exact canonical `str` | exact `ScoreTimestampProjection`, canonical | exact int in range | ✅ `WINDOW_*` |
| **`ScoreTimestampProjection` (old symmetric anchor)** | any | any | ❌ **`PREDICATE_INVALID_CANONICAL_TIMESTAMP`** |
| any other non-`str` anchor (`int`/`bool`/`None`/`Decimal`/`bytes`/container/object/`str`-subclass) | any | any | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| exact `str` violating canonical grammar | any | any | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| valid anchor | non-`ScoreTimestampProjection` `comparison` | valid | ❌ `PREDICATE_WRONG_CARRIER_TYPE` |
| valid anchor | forged/missing-slot `ScoreTimestampProjection` | valid | ❌ `PREDICATE_FORGED_OR_MISSING_SLOT` |
| valid anchor | `ScoreTimestampProjection` with non-canonical `provenance_timestamp` | valid | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| valid anchor | valid comparison | non-int / bool / out-of-range | ❌ `PREDICATE_INVALID_DURATION` |

`PREDICATE_WRONG_CARRIER_TYPE` appears **only** for the `comparison` carrier (and, in `context_equals`, the root/
observed context carriers) — never for the scalar `anchor`.

---

## 6. Corrected Future Targeted Slice-D TDD / AST Requirements (binding; NOT opened here)

The separately-authorized Slice-D runtime correction must, in addition to `b874ec0` §10 (as corrected):

- prove old symmetric `classify_timestamp_window(anchor=<ScoreTimestampProjection>, …)` fails with
  **`PREDICATE_INVALID_CANONICAL_TIMESTAMP`** (not `PREDICATE_WRONG_CARRIER_TYPE`);
- prove **all** other non-`str` anchors (`int`/`bool`/`None`/`Decimal`/`bytes`/container/object/`str`-subclass) and
  all non-canonical `str` anchors produce the **same** `PREDICATE_INVALID_CANONICAL_TIMESTAMP`;
- **static AST proof** that the corrected predicate contains **no** branch that recognizes or special-cases
  `ScoreTimestampProjection` (or any Slice-C timestamp carrier) as a legal `anchor` — no `isinstance`/`type(...) is
  ScoreTimestampProjection` test on `anchor`, no attribute read of `anchor.provenance_timestamp`;
- the implementation passes `anchor` **directly** through the **single existing** canonical-timestamp validator
  (`_require_canonical_timestamp`) — **no** carrier conversion, no private-maker call, and **no** duplicated grammar.

---

## 7. Preserved Unchanged (affirmed)

- `context_equals(*, root_context: EstablishedRootContext, observed_context: ScoreContextProjection) -> bool`;
- `classify_timestamp_window(*, anchor: str, comparison: ScoreTimestampProjection, duration_ms: int)`;
- populated / missing-slot revalidation of the root (`EstablishedRootContext`) and observed (`ScoreContextProjection`
  / `ScoreTimestampProjection`) carriers;
- `U+200B` context blank semantics (Python `str.strip()`; `U+200B` accepted);
- timestamp lexical arithmetic and the `WINDOW_NON_COMPARABLE` / `WINDOW_IN_WINDOW` / `WINDOW_EXPIRED` truth table
  (≥5000-digit; inclusive `delta == duration`);
- the private-maker prohibition for Slice E (§3);
- all other Slice-D predicates (`silver_pair_intersects`, `unit_comparable`, `classify_directional_crossing`) and the
  Slice-E charter chain through `90bb5d3`.

---

## 8. Unresolved Items

- **None.** No "only a real `sqlite3.Row` can construct" / "never synthesizable from stored scalars" claim remains;
  the private makers are acknowledged as private and off-limits to Slice E. No old-`ScoreTimestampProjection`-anchor
  special-case reason or branch remains; every non-`str` anchor maps to the single
  `PREDICATE_INVALID_CANONICAL_TIMESTAMP`, and `PREDICATE_WRONG_CARRIER_TYPE` is reserved to the three exact-carrier
  operands.

---

## 9. Exclusions / Precise Post-Charter State (ratified)

- Docs-only: no runtime/tests/fixtures/prior-charter/lock edits; `atomic_replay_step.py` and `reconstruction.py`
  not created; Slice F/G not opened. `b874ec0` not edited/deleted/amended/rebased/force-pushed.
- **The Slice-D runtime correction remains BLOCKED pending independent review and ratification** (of `b874ec0` as
  corrected by this charter). **Slice E remains BLOCKED; Slice F/G remain blocked.** **Capacity remains 0.** **Phase
  6.2 remains INCOMPLETE and NOT runtime-ready;** execution / routing / actionability / live / paper / canary
  behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE + RATIFIED.

**Conclusion:** `b874ec0` is marked historical and **UNRATIFIED** for exactly two contradictions, corrected here.
**(1)** Its absolute "Slice-C carriers are built only from a real `sqlite3.Row`, never synthesizable from stored
scalars" claim is superseded: the real private Slice-C makers `_make_score_context` / `_make_score_timestamp`
construct/validate those carriers internally; they remain private Slice-C implementation/test surfaces that Slice E
must never import, call, alias, expose, wrap, or depend on; the only **sanctioned public** evidence-production path
stays the reached `project_*(*, replay_row)` operations; no public maker / bridge / adapter / inverse hydration /
synthetic-or-fabricated row / registry / cache is authorized; and "physically constructible by a private maker" is
**not** "sanctioned for Slice-E consumption." **(2)** The scalar-`anchor` error rule is corrected: `anchor` must be
`type(anchor) is str`, and **every** non-`str` anchor — `ScoreTimestampProjection` (the old symmetric anchor),
`int`/`bool`/`None`/`Decimal`/`bytes`/containers/arbitrary objects/`str`-subclasses — plus every non-canonical exact
`str` maps to **`PREDICATE_INVALID_CANONICAL_TIMESTAMP`**, with **no** special check / ghost / compatibility branch /
fallback / overload / distinct reason for the old anchor, `PREDICATE_WRONG_CARRIER_TYPE` reserved to the context
root/observed and timestamp comparison exact-carrier operands, deterministic precedence (scalar anchor → exact
comparison carrier → duration → arithmetic) preserved, and the anchor passed directly through the single existing
canonical-timestamp validator with no carrier conversion or duplicated grammar. All other `b874ec0` asymmetric-
interface decisions — the two corrected signatures, populated/missing-slot revalidation, `U+200B` semantics, lexical
arithmetic and the WINDOW truth table, the private-maker prohibition for Slice E, and the Slice-E charter chain
through `90bb5d3` — are **preserved**, **no unresolved items** remain, and **the Slice-D runtime correction stays
BLOCKED pending independent review; Slice E blocked; Slice F/G blocked; capacity 0; Phase 6.2 INCOMPLETE and NOT
runtime-ready. No executable work is authorized.**
