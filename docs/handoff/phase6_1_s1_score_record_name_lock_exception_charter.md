# Phase 6.1 — S1 `ObservationScoreRecord` Name-Lock Exception Amendment Charter

> **This is a planning/charter document only.** It formally authorizes, **at docs level only**, a single,
> surgical, **basename-pinned, exact-name** exception to the package-wide Phase 6.1 name-surface locks: the exact
> defined name `ObservationScoreRecord`, for **exactly one** future module basename
> (`s1_in_memory_observation_sink.py`). It **designs and builds nothing**, and it **commits or authorizes nothing
> executable**. It authorizes NO runtime code, NO tests, NO lock-test edit (the amendment is **specified, not
> applied**), NO DTO rename, NO schema/runtime/interface edits, NO score arithmetic, NO scoring/ranking function,
> NO B4 logic, NO B1/B2/B3/Phase 5/producer changes, NO S4 materialization, NO S5 runner, NO Cell-3 route, NO
> Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s1_runtime_sink_tdd_planning_charter.md`,
> `docs/handoff/phase6_1_option_b_reader_io_lock_exception_amendment_charter.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `7fcabdbbce846214c9ecbe774b592e89c3cc424c`

---

## 1. Purpose — A Surgical Exact-Name Exception, Not a Relaxation of Posture

The Phase 6.1 runtime package is under a package-wide **no-calculation/actionability name-surface** posture: two
package-wide lock tests sweep **every** `phase6_1/*.py` and reject any **defined name** whose lowercase contains a
banned substring, where `_BANNED_NAME_SUBSTRINGS` includes **`"score"`** (alongside `calculate`, `compute`,
`derive`, `readiness`, `actionability`, `actionable`, `recommendation`, `verdict`):

- `tests/test_phase6_1_forbidden_token_locks.py::test_runtime_has_no_calculation_or_actionability_surface`
- `tests/test_phase6_1_diagnostic_ev_non_actionability.py::test_runtime_has_no_actionability_or_ranking_surface`

The ratified Slice-0B record model (`4e65f93`) named the two equal-peer passive families **`ObservationScoreRecord`**
and `ObservationHaltRecord`. The substring `"score"` in `ObservationScoreRecord` trips both name-surface locks —
even though the family is a **passive DTO carrying opaque score *content*, with zero scoring logic**. This is a
collision between a **ratified docs-model name** and a **ratified runtime guardrail**, and (unlike the `json`
*token* allowlist) the name-surface locks currently have **no per-basename name allowlist**.

This charter defines a **surgical exception**: a closed, **exact-name**, **basename-pinned** carve-out for
**exactly one** future module basename and **exactly one** defined name, leaving the package-wide name-surface
posture the default for every other module and every other name. It does **not** apply the exception; it specifies
its exact shape so a later separately-authorized slice can apply it without expanding it.

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Why an Exception (Not a Rename) — Reconciling the Sealed Precedent

The S2-wiring closeout (`1e63c4f`) sealed: *locks do not bend for prose, convenience, or naming comfort; an
**avoidable** collision must be fixed by conforming the code.* That precedent governs **avoidable** collisions
(e.g. the scrubbed `route`/`candidate` docstring prose).

This collision is **not avoidable by the runtime author**: the name `ObservationScoreRecord` is **mandated** by the
ratified `4e65f93` logical record model and by the authorizing slice instruction. Renaming it would diverge from a
**ratified** artifact. It is therefore the **`json`-class** of collision — a structurally-required identifier — and
is handled the same way: a **narrow, chartered, basename-pinned, exact-name** exception, not a broad weakening and
not a unilateral rename.

---

## 3. Strict Pinning — One Basename, One Exact Name

- The future name-surface exception applies to **exactly one** module basename:
  **`s1_in_memory_observation_sink.py`**.
- Within that basename, it permits **exactly one** defined name: **`ObservationScoreRecord`** (exact string match).
- It does **NOT** allowlist the **substring** `"score"` globally, nor for any other name, nor for any other
  basename. `ObservationScoreRecord` is permitted **only as that exact, whole defined name**; any other name
  containing `"score"` (e.g. `score_threshold`, `compute_score`, `ScoreEngine`) remains **banned everywhere**,
  including in this same module.
- If the module basename is renamed/removed, or the exact name is changed, the exception lapses; no other module
  or name inherits it.

---

## 4. The Exception Is Name-Only — No Behavioral Permission

This exception grants a **name**, nothing more. It confers **no** permission for, and explicitly does **NOT**
authorize:

- score **arithmetic**, score **computation**, EV/ranking math, thresholding, or any calculation;
- any **scoring/ranking function**, `compute_*`/`calculate_*`/`derive_*`/`score_*` surface, or readiness/verdict
  surface;
- **B4 logic** of any kind (B4 remains unbuilt and separately gated);
- any actionability, routing, sizing, execution, or decision surface.

`ObservationScoreRecord` is a **passive, frozen DTO** that **carries** opaque score *content* in an opaque
`family_payload`; it performs **no** scoring. The other banned name substrings (`calculate`, `compute`, `derive`,
`readiness`, `actionability`, `actionable`, `recommendation`, `verdict`) remain **fully banned**, including in this
module — the exception does **not** touch them.

---

## 5. Narrow Lock-Test Future Scope

A later, separately-authorized runtime/TDD slice may amend **only** the two named package-wide **name-surface**
lock tests, and **only** to add the exact name `ObservationScoreRecord` to a **per-basename name allowlist** keyed
on `s1_in_memory_observation_sink.py`:

- `tests/test_phase6_1_forbidden_token_locks.py::test_runtime_has_no_calculation_or_actionability_surface`
- `tests/test_phase6_1_diagnostic_ev_non_actionability.py::test_runtime_has_no_actionability_or_ranking_surface`

Scope limits on that future amendment:

- **Name-only, exact-name.** Only the exact defined name `ObservationScoreRecord` is allowlisted, for the one
  basename. The substring `"score"` is **not** globally allowlisted; no other banned substring is touched.
- **Two tests only.** No other lock test, scanner, token list, import list, or IO list is in scope.
- **No package-wide relaxation.** The amendment must be expressed **per-file, per-exact-name**, leaving every other
  module's and name's bans intact.
- **No new behavioral permission.** The amendment changes a **name** allowlist only; it grants no scoring/ranking/
  calculation capability.

This charter authorizes **none** of those edits now.

---

## 6. Existing Guardrails Remain Global and Unweakened

Unchanged by this exception, for the S1 sink module and everywhere:

- **No-IO / import bans** — no `sqlite3`/`pandas`/`numpy`/`io`/`os`/`pathlib`/`sys`/`json`/`csv`/`open`/`tempfile`/
  `pickle`/`shelve`/`hashlib`/`uuid`/`random`/`time`/`datetime`; no filesystem/DB/serialization/clock/randomness.
- **No-`isinstance`** exact-type discipline; **no** identity minting (UUID/hash/counter/concat/timestamp-as-ID/
  fingerprint/synthetic key); `observed_at_epoch_ms`/`provenance_timestamp` stay **timestamp-only**.
- **All other name-surface bans** (`calculate`/`compute`/`derive`/`readiness`/`actionability`/`actionable`/
  `recommendation`/`verdict`) remain in force, including in the S1 sink module.
- **Forbidden-token source scan** (json/serialize/order/routing/route/execution/sizing/candidate/trade/…) remains
  in force for the S1 sink module — this charter touches **only** the name-surface locks, **not** the token scan.
- **Absolute passivity** — the sink scores/ranks/filters/decides/routes nothing; cost context stays opaque; Cell-3
  deferred.

---

## 7. Pending Work — Explicitly Unauthorized by This Charter

- **No runtime** S1 sink module or DTOs are authorized, created, or committed by this docs-only charter.
- **No lock-test edit** is authorized (the §5 name allowlist is **specified, not applied**).
- The next executable step — applying the §5 exact-name, per-basename name-allowlist amendment to the two named
  lock tests **and** implementing/committing the S1 in-memory sink + DTOs (under the Slice-0B model and the sink
  TDD plan) — must be **separately authorized** after this charter lands.

---

## 8. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read
as "capacity validated."

---

## 9. Still-Blocked Work

- **No** lock-test edit (the name allowlist is specified, not applied); **no** broadening beyond one basename + one
  exact name.
- **No** DTO rename; the ratified `4e65f93` name `ObservationScoreRecord` is preserved.
- **No** score arithmetic/computation/ranking/threshold; **no** scoring/calculation function; **no** B4 logic.
- **No** S1 runtime/DTO implementation or commit; **no** storage/persistence/serialization.
- **No** weakening of the IO/import/token/`isinstance`/identity locks or the other name-surface substrings.
- **No** S4 materialization; **no** S5 runner; **no** Cell-3 route; **no** B1/B2/B3/Phase 5/producer change.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 10. Next Safe Step

- A **separately-authorized S1 in-memory reference sink TDD slice** that (a) applies the §5 **exact-name,
  per-basename** name-allowlist amendment to the two named name-surface lock tests, and (b) implements + commits
  the pure-Python, instance-bound, append-only S1 sink with the frozen `ObservationScoreRecord` /
  `ObservationHaltRecord` DTOs (under the Slice-0B record model and the sink TDD plan) — test-first, existing
  modules frozen, designing **no** storage medium, **no** score arithmetic, **no** S4/B4.
- Independently/subsequently: the **S1 storage-medium** charter; the **S4 exception-routing** decision; a **B4
  passive scoring** slice; and the **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The lock-test amendment, the S1 sink slice, the storage
  medium, S4 materialization, B4 scoring, the S5 runner, durable persistence, the Cell-3 route, the Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** this charter authorizes — **at docs level only** — a single, surgical, **exact-name, basename-pinned**
exception permitting the exact defined name **`ObservationScoreRecord`** in the future basename
**`s1_in_memory_observation_sink.py`**, justified because that name is **mandated** by the ratified `4e65f93`
record model (a structurally-required identifier, handled like the `json` precedent — narrow chartered exception,
not a rename, not a broad weakening). It allowlists **the exact name only**, **never** the substring `"score"`
globally, grants **no** scoring/calculation/ranking/B4 behavioral permission, leaves all IO/import/token/
`isinstance`/identity locks and every other name-surface substring **fully intact**, and **specifies but does not
apply** the lock-test amendment (limited to the two named name-surface tests). The S1 sink runtime/DTOs **remain
unauthorized and uncreated**; the next executable step is **separately gated**. **No executable work is
authorized.**
