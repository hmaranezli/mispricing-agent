# Phase 6.2 — Hypothetical-Window Duration Signed-64 Range Targeted Amendment Charter

> **This is a docs-only targeted amendment charter.** It pins the exact inclusive integer range of
> `hypothetical_window_duration_ms` and narrows the previously-unbounded duration contract — it does **NOT** redesign
> any logical, encoding, predicate, timestamp, or lifecycle rule. It **implements nothing and authorizes nothing
> executable**: no runtime code, no tests, no fixtures, no package, no prior-charter file edits, no lock-test edits,
> no Phase 6.1 edits, no S1 edits, no config edits, no generated-file edits, no pytest, no graphify. It corrects the
> Gate A / Gate B / planning charters **only** through the explicit supersession map in §4. It makes **no** Phase
> 6.2 runtime/paper/live/production readiness claim. It is subordinate to the Gate A/B charters (`5dc757c`,
> `1071067`, `474cc6f`), the planning + fixture charters (`5211652`, `b4368fd`, `045caea`), the predicate chain, the
> S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises, those govern **except** for the narrow,
> explicitly-mapped supersessions in §4.

**Base:** `e712dba9f94c9771b647139d698b68d9c5c53d49`

---

## 1. Base / Purpose

**Base commit:** `e712dba9f94c9771b647139d698b68d9c5c53d49`.

Gate A (`5dc757c` §9) pinned `hypothetical_window_duration_ms` as an "exact non-negative integer" with **no upper
bound**, and Gate B (`474cc6f` §12) pinned its canonical string grammar `"0" | [1-9][0-9]*` with no numeric ceiling.
This is **contradictory with the runtime environment**: Python 3.11+ enforces a default **integer string-conversion
length limit** (`sys.set_int_max_str_digits`, default 4300 digits), so an arbitrarily long all-digit duration string
— while matching the Gate B grammar — would raise `ValueError` on `int(...)` conversion, an implementation-dependent
failure rather than a pinned contract. An unbounded duration is therefore neither faithfully encodable nor reliably
decodable.

This charter closes that contradiction by pinning an **exact, environment-independent inclusive logical range** for
the declared duration. It changes **only** the duration bound; every other rule stands.

**No capacity validation and no capacity pass is claimed by this charter** (see §7).

---

## 2. Exact Pinned Range (binding)

```
MIN_HYPOTHETICAL_WINDOW_DURATION_MS = 0
MAX_HYPOTHETICAL_WINDOW_DURATION_MS = 9223372036854775807   # 2^63 - 1
```

The declared `hypothetical_window_duration_ms` is an **exact non-negative integer within the inclusive interval
`[0, 2^63 − 1]`**.

---

## 3. Binding Rules

- **Both endpoints are valid:** `0` and `9223372036854775807` are accepted.
- **`MAX + 1` (`9223372036854775808`) is invalid.**
- **`bool` remains invalid** (`type(True) is bool`; a boolean is not an integer here).
- **Negative values, floats, `Decimal` values, JSON numbers, exponent forms, signs, whitespace, and alternate
  units remain invalid.**
- **Physical representation remains a canonical JSON string** (never a JSON number).
- **The Gate-B lexical grammar remains exactly** `"0" | [1-9][0-9]*`, **followed by the mandatory inclusive
  signed-64 range check** (`0 ≤ value ≤ 2^63 − 1`) applied to the decoded integer.
- **Do NOT** replace this rule with "18 digits," `uint64`, platform-native `int`, `sys.int_info`, Python's
  configurable digit limit, clamping, wrapping, saturation, modulo, or any implementation-dependent behavior. The
  bound is the **exact literal `2^63 − 1`**, independent of platform or interpreter configuration.
- **Scope of the bound:** it applies **only** to the **declared** duration. It does **NOT** reinterpret or bound the
  **opaque S1 `provenance_timestamp` text** (which stays verbatim opaque text, parsed to an exact integer for
  `TIMESTAMP_DELTA` per the predicate charters, but **not** subject to this artifact-side duration ceiling).
- **`TIMESTAMP_DELTA` remains exact signed arithmetic:** no overflow, no wrapping, no negative-delta
  reinterpretation. The signed-64 ceiling governs the **declared window magnitude only**, never the delta algebra.

---

## 4. Exact Supersession Map (binding)

| Charter / § | Superseded clause | Narrowed replacement |
|---|---|---|
| `5dc757c` §9 (and every repeated "exact non-negative integer duration" clause) | "`hypothetical_window_duration_ms` is an **exact non-negative integer** … in **milliseconds**" (no upper bound) | "an **exact non-negative integer within `[0, 2^63 − 1]`** (milliseconds)"; `bool` excluded, all other type/sign/float/exponent exclusions unchanged. |
| `5dc757c` artifact pre-flight (§11 validation set) | duration validated only as "exact non-negative integer" | pre-flight **must reject** any duration outside the inclusive `[0, 2^63 − 1]` range (in addition to the existing type checks). |
| `474cc6f` §12 (and repeated duration clauses) | canonical duration grammar `"0" | [1-9][0-9]*` decoding to "exact non-negative integer milliseconds" (no ceiling) | **preserve the canonical string grammar verbatim** and **add the mandatory numeric range check** (`0 ≤ value ≤ 2^63 − 1`) **before logical construction** — a grammar-valid but out-of-range string is rejected. |
| `5211652` planning / test matrix | the duration test surface (unbounded) | Slice A/B tests **must include** `0`, `MAX` (`2^63 − 1`), `MAX + 1`, and **overlong digit strings** (e.g. beyond the interpreter's int-string limit) — all rejected except `0` and `MAX`. |

**No unrelated logical, encoding, predicate, timestamp, or lifecycle rule is superseded.** The orientation
vocabulary, boundary decimal grammar, Silver-pair keying, predecessor option-sum, definition variants, canonical
member ordering, digest contract, lifecycle table, and all precedence/atomicity rules are unchanged.

---

## 5. Current-Runtime Impact (recorded)

- **`3954dc5` `phase6_2_shadow_intent/logical_model.py`** enforces `type(value) is int` + `value >= 0` (bool
  excluded) but **does NOT yet enforce the `2^63 − 1` maximum** — it would currently accept an out-of-range
  duration.
- **`e712dba` `phase6_2_shadow_intent/artifact_verifier.py`** enforces the Gate B duration **grammar** and converts
  via `int(...)`, but **does NOT yet enforce the numeric ceiling** and would surface an overlong digit string as a
  raw `ValueError` (interpreter int-string limit) rather than a pinned `ArtifactVerificationError`.
- Therefore **`e712dba` remains UNRATIFIED** with respect to this amendment: the Slice A logical model and the
  Slice B verifier require a targeted TDD correction (§6) before they conform.
- **Slice C remains BLOCKED** (it must not be opened until the duration-range correction is ratified).

---

## 6. Next Eligible Correction (named, not opened)

The **only** next eligible gate is a separately-authorized **Slice A/B Duration-Range, Reference-Self-Validation &
Read-Error-Surface Targeted TDD Correction**, which must:

1. **Enforce the `[0, 2^63 − 1]` inclusive duration range** in `logical_model.py` (Slice A) and as a numeric range
   check **after** the grammar match and **before** logical construction in `artifact_verifier.py` (Slice B), with
   `0`/`MAX` accepted and `MAX + 1`/overlong-digit strings rejected as the pinned error.
2. Close the **`SealedArtifactReference` direct-constructor bypass** (it must be factory-only / self-validating like
   the Slice-A DTOs, so direct construction cannot evade reference validation).
3. Add **defensive reference revalidation** (re-assert the locator/digest invariants inside `verify_artifact`, not
   only at the factory).
4. **Normalize a missing/raising `binary_stream.read()`** (a stream lacking `read`, or whose `read()` raises) into a
   deterministic `ArtifactVerificationError`, never a leaked `AttributeError`/arbitrary exception.
5. **Normalize parser `RecursionError`** (deeply-nested JSON) into a deterministic `ArtifactVerificationError`,
   never a leaked `RecursionError`.

**This charter does NOT implement those corrections** — it only pins the range and names the correction.

---

## 7. Precise Post-Charter State (ratified)

- **Phase 6.2 remains UNBUILT and NOT runtime-ready.** This amendment pins **only** the duration range and its
  supersession map; it authorizes **no** executable work.
- **`e712dba` UNRATIFIED** pending the §6 correction; **Slice C blocked.**
- **Phase 6.1:** frozen, COMPLETE + RATIFIED. **Capacity:** deferred at **0 emit sites**. **Production / live /
  paper / canary / execution / routing / actionability:** forbidden.

**Conclusion:** the unbounded `hypothetical_window_duration_ms` contract is contradictory with the runtime's integer
string-conversion limit, so the declared duration is pinned to the **exact inclusive logical range `[0, 2^63 − 1]`**
(`MIN = 0`, `MAX = 9223372036854775807`): both endpoints valid, `MAX + 1` invalid, `bool` invalid, and
negative/float/`Decimal`/JSON-number/exponent/sign/whitespace/alternate-unit forms invalid; the physical
representation stays a **canonical JSON string** and the **Gate B grammar `"0" | [1-9][0-9]*` is preserved verbatim**
with a **mandatory inclusive signed-64 numeric range check** added **before logical construction** — **never**
replaced by "18 digits"/`uint64`/platform-native-int/`sys.int_info`/configurable-digit-limit/clamp/wrap/saturate/
modulo behavior. The bound governs **only the declared duration**, never the opaque S1 `provenance_timestamp` text,
and **`TIMESTAMP_DELTA` stays exact signed arithmetic** (no overflow/wrap/negative-delta reinterpretation). The
supersession map narrows `5dc757c` §9 + its duration clauses and its pre-flight, preserves and augments `474cc6f`
§12, and extends the `5211652` test matrix to cover `0`/`MAX`/`MAX + 1`/overlong-digit cases — **nothing else**.
`3954dc5` `logical_model.py` and `e712dba` `artifact_verifier.py` do **not yet enforce** the maximum, so **`e712dba`
remains UNRATIFIED** and **Slice C is blocked**; the **only** next eligible gate is the separately-authorized **Slice
A/B Duration-Range, Reference-Self-Validation & Read-Error-Surface Targeted TDD Correction** (also closing the
`SealedArtifactReference` direct-constructor bypass, defensive reference revalidation, `binary_stream` missing/raising
read normalization, and parser `RecursionError` normalization), **not opened here**. **Phase 6.2 remains UNBUILT and
NOT runtime-ready; capacity stays deferred at 0 emit sites; Phase 6.1 stays frozen, COMPLETE + RATIFIED. No
executable work is authorized.**
