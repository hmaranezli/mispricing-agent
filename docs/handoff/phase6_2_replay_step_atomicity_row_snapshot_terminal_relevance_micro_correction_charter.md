# Phase 6.2 — Replay-Step Atomicity, Row-Start Snapshot & Terminal-Relevance Micro-Correction Charter

> **This is a docs-only targeted micro-amendment charter.** It pins **behavioral invariants only** — replay-step
> atomicity, the row-start slot snapshot, and terminal/relevance scoping — correcting the remaining
> sequential-mutation and over-broad fail-fast contradictions in `44791ce`. It **selects no concrete runtime class,
> container, exception, or library**, and it **implements nothing and authorizes nothing executable**: no runtime
> code, no tests, no DTO, no loader, no state machine, no Phase 6.1 edits, no S1-adapter edits, no Gate A/B edits,
> no frozen-component edits, no prior-charter file edits, no Phase 6.2 runtime, no pytest, no graphify. It corrects
> prior charters **only** through the exact supersession map in §2. It makes **no** Phase 6.2 runtime/paper/live/
> production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_duplicate_root_guard_context_first_precedence_micro_correction_charter.md`,
> `docs/handoff/phase6_2_predicate_precedence_decimal_evidence_consistency_targeted_correction_charter.md`,
> `docs/handoff/phase6_2_evidence_intersection_classification_predicate_charter.md`, the Gate A/B charters
> (`5dc757c`, `1071067`, `474cc6f`), the source-boundary + amendment charters (`07135be`, `abd1b41`), the lifecycle
> charters (`e9995e7`, `999a109`), the S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises,
> those govern **except** for the narrow, explicitly-mapped supersessions in §2.

**Base:** `44791ce30dc60f12db67655c865bab621611f1aa`

---

## 1. Base / Purpose

**Base commit:** `44791ce30dc60f12db67655c865bab621611f1aa`.

`44791ce` pinned the duplicate-root guard, root non-establishment, and context-first precedence, but left two
behavioral gaps: (1) its §5 D/E per-slot evaluation reads as **immediate, sequential, per-intent mutation**, which
admits externally-visible **partial** state and **iteration-order**-dependent results; and (2) its §6
"malformed context **while established intents exist**" fails too broadly — it would fail-fast even when the only
established slots are **terminal** or **permanently non-established** and thus have **no relevance** to context. This
charter pins a **formal atomic replay-step law** (classify-all then apply-all, no partial state), a **row-start slot
snapshot**, and **terminal/relevance scoping** so malformed context only matters when a row-start **established
non-terminal** slot actually requires relevance classification.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Exact Supersession Map (binding)

| Charter / § | Quoted/identified clause | Precise replacement |
|---|---|---|
| `44791ce` §5 D/E | "**D. Evaluate the row against previously established intent slots.** … **E. For each previously established slot:** [1–12]" — read as immediate sequential mutation | Superseded by the **§3 atomic Step law** + **§4 classify-all/apply-all**: per-slot results are computed as **inert proposals without mutation**; all proposals commit **atomically** into one immutable `NextShadowSnapshot`, or the whole row hard-fails with **no** partial state. The 1–12 per-slot predicate **content** is unchanged; only its **mutation timing** is corrected (propose, don't mutate). |
| `44791ce` §6 | "Malformed / missing / not-exactly-two-text `score_inputs_summary` **while established intents exist** remains hard fail-fast" | Superseded by **§7 terminal relevance**: malformed context is hard fail-fast **only when at least one row-start slot is established AND non-terminal** (`INTENT_RECORDED` or `HYPOTHETICAL_CONDITION_MET`). Terminal or permanently-non-established slots do **not** trigger context parsing or its failure. |
| `44791ce` conclusion | every clause implying per-intent immediate mutation or "malformed context fails merely because established intents exist" | Re-stated under the atomic Step law and terminal-relevance scoping (§3–§7). |

All other `44791ce` provisions (duplicate-root guard primacy, permanent root unit-mismatch non-establishment,
context-first family validation, expiry-before-unit/magnitude, decimal/timestamp contracts) stand intact.

---

## 3. Formal Replay-Step Law (binding)

Each replay step is a **pure function**:

```
Step(
  RowStartShadowSnapshot,
  RowStartSeenTargetPairs,
  CurrentS1Row,
  FrozenManifestProjection
)
  → HardFailure
    OR
    (NextShadowSnapshot, NextSeenTargetPairs)
```

- **All four inputs are immutable for the duration of the step.**
- **No externally visible intermediate state exists** during the step.
- **`HardFailure` produces no successful next snapshot** — there is no "next state" on failure.

The step consumes the row-start state + the current row + the frozen manifest projection and yields **either** one
complete next state pair **or** a hard failure — never anything in between.

---

## 4. Classify-All / Apply-All (binding)

- Every **root-guard result** and every **affected per-intent lifecycle result** is **first computed as an inert
  proposal**.
- **Proposal computation MUST NOT mutate** any slot, the guard set, the manifest projection, any S1 record, or any
  shared container.
- **If any proposal hard-fails, every proposal from that row is discarded.**
- **No partial `ShadowState` may be published, returned, exposed, or persisted.** The caller receives **failure**,
  never a partially-updated or apparently-successful snapshot.
- **Only if every required classification succeeds** may all proposals be **applied together** to produce **one
  immutable `NextShadowSnapshot`**.

This makes the row the unit of atomicity: classify the whole row, then either apply the whole row or fail the whole
row.

---

## 5. Guard-State Atomicity (binding)

- `RowStartSeenTargetPairs` is **caller-owned, replay-local, instance-scoped structural state** — **never** global,
  module-level, shared, or cached (consistent with `07135be` §8 / `999a109` §3 / `44791ce`).
- **Duplicate detection reads only `RowStartSeenTargetPairs`** (the immutable row-start guard set), never a
  mid-row-mutated set.
- A **successful first targeted occurrence proposes adding its pair to `NextSeenTargetPairs`**; this addition is
  **committed atomically with all shadow-state proposals** (§4) — never independently.
- A **valid root unit-mismatch still commits the pair as seen** (so a later occurrence is correctly a duplicate
  hard-failure) **while leaving its slot permanently `AUDIT_REPLAYED` / non-established** (`44791ce` §4).
- A **hard failure commits neither** guard-state nor shadow-state proposals.
- **Hard failure terminates replay**; the prior snapshot **must not be returned as a successful reconstruction
  result** (failure is failure, not a silent revert-to-prior).

---

## 6. Row-Start Slot Snapshot (binding)

- **"Previously established slots" means exactly the immutable set present at the START of the current replay row**
  (`RowStartShadowSnapshot`).
- A slot **proposed for establishment by the current row is EXCLUDED from all crossing/expiry predicates for that
  same row** (the root observation never transitions its own slot on its establishing step — `d7204d6` §7 /
  `44791ce` §8).
- It becomes eligible **only from the next append-ordered row**.
- The current row **may still classify proposals for other slots that were established at row start** (a single
  SCORE may establish its own slot **and** propose updates to other row-start slots, §9).

---

## 7. Terminal Relevance (binding)

After the global targeted-pair guard / root path (§8 A–C):

- **Terminal slots** (`INTENT_EXPIRED`, `INTENT_RETIRED`) **self-loop without reading** context, family, timestamp,
  unit, or magnitude.
- **Permanently non-established `AUDIT_REPLAYED` slots** (root unit-mismatch, `44791ce` §4) **track nothing** and
  **require no later context parsing**.
- **Context classification is required only when at least one row-start slot is both established AND non-terminal**
  — i.e. `INTENT_RECORDED` or `HYPOTHETICAL_CONDITION_MET`.
- **If no such slot exists and the row is not a first targeted root, the row is an irrelevant no-op after the global
  guard** (no context/family/timestamp/unit/magnitude evaluation).
- **Therefore malformed context does NOT fail merely because terminal or permanently-non-established slots exist.**
- **If at least one established non-terminal slot requires relevance classification, malformed / missing /
  not-exactly-two-text context remains hard fail-fast** (relevance cannot be determined — `44791ce` §6 as narrowed).

---

## 8. Per-Row Ordering (binding)

The **only** legal per-row sequence:

- **A.** Global manifest-target occurrence guard against `RowStartSeenTargetPairs` (§5).
- **B.** Duplicate target → **immediate `HardFailure`** (regardless of kind/state; terminals never absorb it —
  `44791ce` §3/§5).
- **C.** First target → **compute root-establishment proposal** (`d7204d6` §4 / `44791ce` §4/§7 root validation;
  HALT/non-SCORE/malformed root → `HardFailure`; valid directional unit-mismatch → permanent non-establishment
  proposal that still commits the seen-pair, §5).
- **D.** Freeze the **row-start established + non-terminal slot set** (§6, §7).
- **E.** If that set is **empty**, **skip later-observation predicates**.
- **F.** Otherwise validate **context shape once** (§7; malformed → `HardFailure`).
- **G.** Determine **context-equal row-start slots**.
- **H.** **Classify every affected slot WITHOUT mutation** (inert proposals; per-slot predicates per `44791ce` §5
  E.1–E.12 content).
- **I.** **Any hard failure → discard all row proposals** (§4).
- **J.** **All classifications successful → atomically produce both next snapshots** (`NextShadowSnapshot`,
  `NextSeenTargetPairs`).

**No other ordering is legal.**

---

## 9. Multi-Intent Consistency (binding)

- **Proposal results must be independent of iteration order.** **No "for each intent: mutate immediately"
  interpretation is legal.**
- One intent may propose **expiry** while another proposes **crossing**; **both commit together only if the whole
  row succeeds**.
- If **any** affected intent yields a hard failure, **none** of the row's proposed establishment, expiry, crossing,
  self-loop bookkeeping, or seen-pair additions becomes externally visible (§4).
- **Concrete error-aggregation / exception types are NOT pinned here**; the planning charter (§12) must preserve
  **deterministic failure reporting** (same fixed inputs ⇒ same failure outcome).

---

## 10. Relevance-Scoped Validation (binding)

- **Shadow reconstruction is NOT a general S1 repair or validation engine.**
- **Context-unequal SCORE family / timestamp / unit / magnitude defects remain OUTSIDE that intent's predicate and
  are not inspected** (only a context-equal SCORE undergoes full family/timestamp/unit/magnitude validation —
  `44791ce` §6).
- **Global targeted-root validation and the duplicate-root guard remain MANDATORY regardless of active-slot state**
  (§8 A–C run for every row, even when the row-start non-terminal set is empty).

---

## 11. Preserve (affirmed)

- **Duplicate-root guard precedes terminal handling** (§8 A/B before any per-slot terminal self-loop).
- **Permanent root unit-mismatch non-establishment** (`44791ce` §4).
- **Context-first family validation** (`44791ce` §6).
- **Expiry before unit/magnitude** (`f57d116` §4 / `44791ce` §5 E.9 before E.11/E.12).
- **Separate S1 / Gate B decimal contracts** and **timestamp authority** (`f57d116` §6/§7).
- **`INTENT_RETIRED` reserved / unreachable**; **equality-only fallback unactivated**.
- **No** wall clock, S4 fallback, mutation/write-back, global state/registry/cache/singleton, actionability,
  capacity, or integration. **Capacity stays deferred at exactly 0 emit sites.** Phase 6.1 frozen, COMPLETE +
  RATIFIED. Crossing inequalities, `delta > duration` expiry, negative-delta non-comparability, and the terminal
  invariant (at most one terminal; open frozen at replay EOF valid) all stand.

---

## 12. Next Gate (ratified)

- **`44791ce` alone did NOT make planning complete** — replay-step atomicity (no partial state, order-independence,
  terminal relevance) was still unpinned. This charter closes it.
- **After this correction, the ONLY next eligible gate is the separately-authorized docs-only "Phase 6.2
  Reconstruction Runtime TDD Planning & Slice Charter."** **No direct runtime implementation is authorized.**
- **This charter does NOT open, draft, or perform that planning charter** (or any runtime). **Phase 6.2 remains
  UNBUILT and NOT runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED; capacity deferred (0 emit sites);
  production / live / paper / canary / execution / routing / actionability forbidden.

**Conclusion:** replay-step behavior is corrected to a **pure, atomic Step law** —
`Step(RowStartShadowSnapshot, RowStartSeenTargetPairs, CurrentS1Row, FrozenManifestProjection) → HardFailure |
(NextShadowSnapshot, NextSeenTargetPairs)` with **immutable inputs, no externally visible intermediate state, and no
successful snapshot on failure** — superseding `44791ce` §5 D/E's implied sequential mutation and §6's over-broad
malformed-context fail-fast. Each row is **classify-all then apply-all**: every root-guard and per-intent result is
computed as an **inert proposal with zero mutation** of any slot / guard set / manifest / S1 record / shared
container; **any** proposal hard-failure **discards the whole row** and the caller receives **failure, never a
partial or apparently-successful `ShadowState`**; only when **every** required classification succeeds are all
proposals **applied atomically** into one immutable `NextShadowSnapshot`. **Guard state** (`RowStartSeenTargetPairs`,
caller-owned/replay-local/instance-scoped, never global) is read only at row start, a successful first occurrence
**proposes** its pair into `NextSeenTargetPairs` committed atomically with shadow proposals, a **valid root
unit-mismatch still commits the pair as seen** while staying permanently non-established, and a **hard failure
commits neither** and terminates replay (the prior snapshot is **not** returned as success). **"Previously
established slots" = the immutable row-start set**; a slot established by the current row is **excluded from
crossing/expiry that same row** and eligible only from the next append-ordered row. **Terminal relevance**: terminal
and permanently-non-established slots **self-loop / track nothing without reading context/family/timestamp/unit/
magnitude**, context classification is required **only** when a row-start slot is **established and non-terminal**
(`INTENT_RECORDED`/`HYPOTHETICAL_CONDITION_MET`), so **malformed context does not fail merely because terminal or
non-established slots exist** — but **does** hard fail-fast when an established non-terminal slot needs relevance
classification. The **per-row ordering A–J** (target guard → duplicate `HardFailure` → first-target root proposal →
freeze row-start non-terminal set → skip-if-empty → validate context shape once → context-equal slots →
no-mutation classification → discard-all-on-failure → atomic dual-snapshot) is the **only legal ordering**, results
are **iteration-order-independent**, and one intent's expiry + another's crossing **commit together or not at all**
(concrete error-aggregation/exception types deferred to planning, deterministic failure reporting required). Shadow
reconstruction stays **relevance-scoped** (context-unequal SCORE defects uninspected) while the **global root and
duplicate guards stay mandatory** for every row. The duplicate-root primacy, permanent unit-mismatch
non-establishment, context-first family validation, expiry-before-unit/magnitude, separate decimal/timestamp
contracts, **reserved-unreachable `INTENT_RETIRED`**, **unactivated equality-only fallback**, and all no-wall-clock /
no-S4 / no-mutation / no-global-state / no-actionability / no-capacity / no-integration provisions are **preserved**.
**`44791ce` alone did not complete planning**; the only next eligible gate is the separately-authorized docs-only
**"Phase 6.2 Reconstruction Runtime TDD Planning & Slice Charter,"** **not opened here**. **Phase 6.2 remains UNBUILT
and NOT runtime-ready. No executable work is authorized.**
