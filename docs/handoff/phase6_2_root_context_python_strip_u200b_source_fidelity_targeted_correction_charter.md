# Phase 6.2 — Root-Context Python-`strip` / U+200B Source-Fidelity Targeted Correction Charter

> **This is a docs-only single-contradiction correction charter.** It marks the prior exactness correction charter
> (`38eccce`) **UNRATIFIED** for **exactly one** technical contradiction — the false claim that the zero-width space
> `U+200B` is removed by Python `str.strip()` / is a whitespace-only blank — and corrects **only** that. It
> **implements nothing and authorizes nothing executable**: no runtime code, no tests, no fixtures, no package
> files, no prior-charter file edits, no generated files, no DTO instance, no loader, no state machine, no `Step`
> algorithm, no replay loop, no SQLite, no artifact read, no persistence, no emission, no Phase 6.1 edits, no
> S1-adapter edits, no Gate A/B edits, no frozen-component edits, no pytest, no graphify, and no commit beyond this
> single docs file. It does **not** amend, edit, delete, rebase, or force-push `38eccce`. It corrects `38eccce`
> **only** through the one-clause supersession map in §2. It makes **no** Phase 6.2 runtime/paper/live/production
> readiness claim. It is subordinate to the full Phase 6.2 charter chain — Gate A (`5dc757c`, `1071067`), Gate B
> (`474cc6f`), conceptual field-shape (`ef26f59`), lifecycle (`e9995e7`), multi-event context (`999a109`),
> predicate-precedence / decimal-source (`d7204d6`→`457d279`-chain), replay-step atomicity (`44791ce`→`457d279`),
> reconstruction-runtime planning (`457d279`), the prior field-shape amendment (`85de568`, already UNRATIFIED) and
> exactness correction (`38eccce`), the S1 durable-storage charters, and `CLAUDE.md` — and where any conflict
> arises, those govern **except** for the narrow, explicitly-mapped correction in §2.

**Base:** `38eccce136898762d2f25476652aa69190826d6b`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `38eccce136898762d2f25476652aa69190826d6b`.

`38eccce` pinned the corrected blank-context rule (`type(value) is str` and `value.strip() != ""`) but then
**misdescribed** the rule's extent: in its §3 prose, §9 construction matrix, and §10 RED test #1 it asserted that
the zero-width space `U+200B` is among the "whitespace-only Unicode" strings that `str.strip()` reduces to `""` and
is therefore invalid. **That is technically false** (§3 proof). The normative rule `value.strip() != ""` is correct
and unchanged; only the **claim about how that rule classifies `U+200B`** is wrong. Under the actual contract,
`U+200B` is **non-blank** and **accepted**.

**`38eccce` is hereby marked UNRATIFIED for exactly this one contradiction.** Every other `38eccce` decision stands
intact (§5). `38eccce` itself is **not** edited, deleted, amended, rebased, or force-pushed — it remains in history;
this charter governs the corrected classification going forward. (`85de568` remains UNRATIFIED per `38eccce`.)

**No capacity validation and no capacity pass is claimed by this charter** (see §7).

---

## 2. Source / Runtime Proof (binding)

Verified against the project interpreter (`./venv/bin/python`):

| Expression | Result |
|---|---|
| `"​".strip() == "​"` | **`True`** — `str.strip()` does **not** remove `U+200B` |
| `"​".isspace()` | **`False`** — `U+200B` is **not** Unicode whitespace |
| `"​".strip() == ""` | **`False`** — so `value.strip() != ""` is **True** ⇒ **accepted** |

Contrast (each reduces to `""` under `str.strip()`, hence invalid):

| Expression | `str.strip()` result |
|---|---|
| `"".strip()` | `""` |
| `" ".strip()` / `"\t".strip()` / `"\n".strip()` (ASCII whitespace) | `""` |
| `" ".strip()` (NBSP) | `""` |
| `" ".strip()` (EM SPACE) | `""` |
| `"　".strip()` (IDEOGRAPHIC SPACE) | `""` |

`U+200B` is a zero-width **format** character (general category `Cf`), not a `Zs`/whitespace character; Python's
`str.strip()` (which strips by the Unicode whitespace property) leaves it intact.

---

## 3. Exact One-Clause Supersession Map to `38eccce` (binding)

Each row supersedes **only** the quoted/identified clause; everything else in `38eccce` stands.

| `38eccce` § | Quoted/identified clause | Precise replacement |
|---|---|---|
| §3 blank rule prose | "every whitespace-only Unicode string (any string whose `.strip()` yields `""` — including ASCII space/tab/newline and Unicode whitespace such as `U+00A0`, `U+2003`, `U+3000`, **`U+200B`-class blanks** as Python `str.strip()` treats them) are **invalid**" | "every string whose Python `str.strip()` yields `""` is invalid (empty, ASCII space/tab/newline, and Unicode **whitespace** such as `U+00A0`, `U+2003`, `U+3000`). **`U+200B` is NOT among them**: `"​".strip() == "​" != ""`, so `U+200B`(-containing) text is **non-blank and accepted**, preserved verbatim." |
| §9 matrix row | `EstablishedRootContext` with "whitespace-only (`" "`, `"\t"`, `" "`, `"　"`, …) scalar → ❌ `LogicalModelError`" insofar as it implied `U+200B` is rejected | The whitespace-only rejection row stands for genuine `str.strip()=="">` blanks (ASCII, `U+00A0`, `U+2003`, `U+3000`); a **new accept row** is added (§6 truth table): a `U+200B`-only or `U+200B`-containing non-blank scalar → ✅ accept (verbatim). |
| §10 RED test #1 | "rejects … each whitespace-only Unicode blank (`" "`, `"\t"`, `"\n"`, `" "`, `" "`, `"　"`)" insofar as any listed item denoted `U+200B` | Corrected per §8: `U+200B` is moved to an **accepted/verbatim** RED/GREEN case, **not** an invalid-blank case; the invalid-blank cases remain `""`, ASCII whitespace, `U+00A0`, `U+2003`, `U+3000`. |

This is the **only** supersession. The normative rule itself (`type(value) is str` and `value.strip() != ""`) is
**unchanged** — only its misstated classification of `U+200B` is corrected.

---

## 4. Preserved Sole Normative Context Rule (affirmed, verbatim)

The single normative blank-context rule, unchanged from `85de568`/`38eccce`, is exactly:

- `type(value) is str`, **and**
- `value.strip() != ""`.

No additional predicate is introduced.

---

## 5. Operational, Exclusive Definition of Invalidity (binding)

- **A context scalar is blank — and therefore invalid — if and only if Python `str.strip()` returns `""`.**
- **No broader Unicode whitespace / invisible-character / zero-width / format-character category is invented or
  applied.** Validity is decided **solely** by `str.strip() != ""` (after the `type(value) is str` gate). The
  validator does not consult `unicodedata`, `isspace()`, category `Cf`/`Zs`, or any curated invisible-character set.

---

## 6. Explicit Pins & Corrected Truth Table (binding)

**Pins:**

- **`U+200B` alone is accepted as non-blank** under the existing source contract (`"​".strip() != ""`).
- **Accepted `U+200B`-containing text is preserved verbatim** — no trim, normalization, repair, stripping of the
  zero-width character, or coercion.
- **Empty string, ASCII whitespace, NBSP `U+00A0`, EM SPACE `U+2003`, and IDEOGRAPHIC SPACE `U+3000` remain
  invalid** precisely where `str.strip()` returns `""`.

**Corrected truth table for an `EstablishedRootContext` scalar `value`:**

| `value` | `type(value) is str` | `value.strip()` | `value.strip() != ""` | Outcome |
|---|---|---|---|---|
| `"hyperliquid"` | True | `"hyperliquid"` | True | ✅ accept (verbatim) |
| `"​"` (U+200B only) | True | `"​"` | True | ✅ **accept (verbatim)** |
| `"​BTC"` / `"BTC​"` | True | `"​BTC"` / `"BTC​"` | True | ✅ **accept (verbatim)** |
| `""` | True | `""` | False | ❌ `LogicalModelError` |
| `" "` / `"\t"` / `"\n"` (ASCII ws) | True | `""` | False | ❌ `LogicalModelError` |
| `" "` (NBSP) | True | `""` | False | ❌ `LogicalModelError` |
| `" "` (EM SPACE) | True | `""` | False | ❌ `LogicalModelError` |
| `"　"` (IDEOGRAPHIC SPACE) | True | `""` | False | ❌ `LogicalModelError` |
| `b"x"` / `None` / non-`str` | False | — | — | ❌ `LogicalModelError` |

---

## 7. Future Zero-Width / Invisible-Character Ban (deferred — NOT opened here)

Any future policy that bans `U+200B` (or other zero-width / invisible / format characters) from context scalars
would be a **semantic content policy, not a `strip`-blank fact**, and would require a **separate, end-to-end
context-character-policy amendment** spanning, consistently:

- the **source validator** (the S1/score-context producer boundary),
- **historical S1 compatibility** (the append-only trail is immutable and read verbatim — already-recorded payloads
  must not be retroactively invalidated or censored),
- **Slice C** (`s1_evidence_projection` context projection / non-blank shape),
- **Slice D** (`classification_predicates` consumer-boundary context revalidation),
- **Slice A** (`logical_model` `EstablishedRootContext`).

Such a cross-cutting policy is **explicitly not opened, drafted, or authorized here.** Until it is separately
ratified, the operational rule of §5 (`str.strip() != ""`) governs and `U+200B` is accepted.

---

## 8. Corrected Future RED → GREEN Matrix Delta (for the LATER Slice-A runtime extension only)

These belong to a **future** human-authorized Slice-A runtime extension TDD task; **none is authorized or written
here.** This delta amends `38eccce` §10 row #1:

| # | Corrected RED (must fail before impl) | GREEN (minimal impl satisfies) | Maps to |
|---|---|---|---|
| 1a | `EstablishedRootContext` rejects `""` and each genuine `str.strip()=="">` blank: ASCII space/tab/newline, `U+00A0`, `U+2003`, `U+3000` | `type(value) is str and value.strip() != ""` | §4/§5/§6 |
| 1b | `EstablishedRootContext` **accepts** `U+200B`-only (`"​"`) and `U+200B`-containing (`"​BTC"`) scalars and stores them **verbatim** (proves `str.strip()` is the sole operator and no zero-width ban exists) | same single rule (no extra predicate) | §6 |

All other `38eccce` §10 / `85de568` §8 RED/GREEN rows (ASCII timestamp grammar incl. Unicode-digit rejection,
snapshot fields/representations/factories, duplicate rejection, alias resistance, exact signatures, dependency/
absence locks) are **unchanged**.

---

## 9. Preserved Unchanged from `38eccce` (affirmed)

Every other `38eccce` decision stands intact:

- **ASCII timestamp grammar** `"0" | [1-9][0-9]*` (ASCII digits only; `\d`/Unicode-digit/sign/fraction/exponent/
  whitespace/leading-zero banned; lexical, no `int()` requirement).
- **`ShadowLifecycleSnapshot`** — exact field `slots_by_identity`; `MappingProxyType` over a non-retained local
  dict; factory `make_shadow_lifecycle_snapshot(*, slot_entries)` (exact tuple of exact 2-tuples); key ==
  `slot.shadow_intent_identity_reference`; empty valid; content-based order-independent equality.
- **`SeenTargetPairsSnapshot`** — exact field `seen_target_pairs`; `frozenset` of exact `OpaqueSilverPairKey`;
  factory `make_seen_target_pairs_snapshot(*, members)` (exact tuple); duplicate members rejected **before**
  frozenset (no silent dedup); set-content order-independent equality.
- **Duplicate rejection** and **alias resistance** for both containers.
- **Root-evidence option-sum** `NoRootEvidence | EstablishedRootEvidence`.
- **Lifecycle / root compatibility matrix** (`AUDIT_REPLAYED ⟺ NoRootEvidence`; established/forward/terminal `⟺
  EstablishedRootEvidence`; permanent unit-mismatch = `AUDIT_REPLAYED` + `NoRootEvidence` distinguished by the
  seen-pair snapshot).
- **Manifest-resident `exposure_orientation`** and **firewalled-deferred `hypothetical_outcome_reference`**.
- **Slice-A ownership** and the **`logical_model` intra-package leaf** import direction.
- **Complete `object.__new__` defensive revalidation** through the single closed `LogicalModelError` surface.
- **No `Step` algorithm, no lifecycle application/mutation, no replay loop, no Slice E behavior**, and the
  "no alternative class/field/representation/factory name is legal" ambiguity ban (`38eccce` §7).

---

## 10. Unresolved Items

- **None.** The single contradiction is corrected against a verified runtime proof; the normative rule is
  unchanged; the future zero-width policy is explicitly deferred (§7), not left open as a blocker for these types.

---

## 11. Exclusions / Precise Post-Charter State (ratified)

- **`38eccce` is UNRATIFIED for exactly one contradiction;** this charter corrects only the `U+200B`/`strip`
  misclassification (§2) and preserves all else (§9). `38eccce` is not edited/deleted/amended/rebased/force-pushed.
  `85de568` remains UNRATIFIED.
- **No `Step` algorithm, inert proposals, classify/apply ordering, lifecycle application/mutation, replay loop,
  SQLite, artifact read, persistence, emission, execution, routing, or actionability** is defined here.
- **The Slice-A runtime extension remains BLOCKED pending independent review.** **Slice E / F / G remain blocked.**
  **Capacity remains DEFERRED at exactly 0 emit sites.** **Phase 6.2 remains INCOMPLETE and NOT runtime-ready.**
  Phase 6.1 frozen, COMPLETE + RATIFIED. Production / live / paper / canary / execution / routing / actionability
  forbidden. Historical S1 evidence read verbatim, never censored.

**Conclusion:** `38eccce` is marked **UNRATIFIED for exactly one technical contradiction** — its claim that the
zero-width space `U+200B` is stripped by Python `str.strip()` / is a whitespace-only blank. The runtime proof is
recorded: `"​".strip() == "​"` and `"​".isspace() is False`, so `value.strip() != ""` is **True** for
`U+200B` and it is **accepted**. The **sole normative context rule is preserved unchanged** (`type(value) is str`
and `value.strip() != ""`), invalidity is defined **operationally and exclusively** as "blank iff Python
`str.strip()` returns `""`" with **no invented broader Unicode whitespace / zero-width / invisible-character
category**. Every `38eccce` statement asserting `U+200B` is removed by `strip` or invalid is **removed/superseded**.
It is **explicitly pinned** that `U+200B` alone is accepted as non-blank, `U+200B`-containing text is preserved
**verbatim**, while the empty string, ASCII whitespace, NBSP `U+00A0`, EM SPACE `U+2003`, and IDEOGRAPHIC SPACE
`U+3000` remain invalid (each `str.strip()=="">`). Any future zero-width/invisible-character ban requires a
**separate end-to-end context-character-policy amendment** across the source validator, historical S1 compatibility,
Slice C, Slice D, and Slice A — **not opened here.** The future RED/GREEN matrix is corrected so `U+200B` is an
**accepted/verbatim** case, not an invalid-blank case. **All other `38eccce` decisions** — ASCII timestamp grammar,
exact snapshot fields/representations/factories, duplicate rejection, alias resistance, root option-sum, lifecycle
matrix, ownership, leaf direction, `object.__new__` revalidation, and exclusions — are **preserved unchanged.** **No
unresolved items.** The **Slice-A runtime extension stays BLOCKED pending independent review; Slice E/F/G stay
blocked; capacity deferred at 0 emit sites; Phase 6.2 remains INCOMPLETE and NOT runtime-ready. No executable work
is authorized.**
