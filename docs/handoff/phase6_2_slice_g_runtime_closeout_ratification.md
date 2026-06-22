# Phase 6.2 — Slice-G Runtime Closeout & Ratification Charter

> **This is a docs-only exact-scope closeout charter.** It **proposes** the closeout and ratification of the
> **already-built** Phase 6.2 deterministic, replay-only, quarantined shadow-intent reconstruction runtime in its
> exact offline audit-reconstruction scope; the proposed closeout becomes **effective only upon independent external
> Gemini and Codex ratification of this committed charter** — never merely by existing or being committed. It
> **builds nothing and authorizes nothing executable**: no runtime code, no new
> module, no integration/façade/orchestrator/service/adapter/registry/resolver/export layer, no new callable, no
> new result carrier, no tests, no fixtures, no `__init__.py` / package-export change, no prior-doc edit, no lock
> edit, no config, no generated files, no pytest, and no graphify. It is subordinate to the full Phase 6.2 charter
> chain — the reconstruction-runtime TDD planning charter (`457d279`), the Slice-A logical-model field-shape chain
> (`85de568`→`01331ec`), the Slice-B Gate-A/Gate-B artifact charters (`5dc757c`, `1071067`, `474cc6f`), the Slice-C
> evidence-projection chain, the Slice-D classification-predicate chain, the Slice-E atomic-replay-step exact-shape
> charter (`cf73e3c`), the Slice-F reconstruction-loop exact-shape charter (`04a20eb`), the negative-evidence
> fixture-boundary charter, and `CLAUDE.md` — and where any conflict arises, those govern. It **selects no next
> executable component** and **grants no adjacent authorization**.

**Base:** `452e37a0eb3f83ec11b8f43e961184750d64f047`

---

## 1. Exact Evidence Base (recorded, not re-run)

**Base commit:** `452e37a0eb3f83ec11b8f43e961184750d64f047`.

Sealed slice evidence:

| Slice | Module | Status |
|---|---|---|
| A — Logical Model | `phase6_2_shadow_intent/logical_model.py` | BUILT + RATIFIED/SEALED |
| B — Artifact Verification | `phase6_2_shadow_intent/artifact_verifier.py` | BUILT + RATIFIED/SEALED |
| C — S1 Evidence Projection | `phase6_2_shadow_intent/s1_evidence_projection.py` | BUILT + RATIFIED/SEALED |
| D — Classification Predicates | `phase6_2_shadow_intent/classification_predicates.py` | BUILT + RATIFIED/SEALED |
| E — Atomic Replay Step | `phase6_2_shadow_intent/atomic_replay_step.py` | BUILT + RATIFIED/SEALED |

Slice-F commit lineage (verbatim, exact):

- **Slice-F docs base:** `04a20eb9e6b9b5f298cd268972e462fa2c9a6f20`
- **Slice-F runtime build:** `14e490e81d0d2b8580f829b90fd6a6498658663d`
- **Slice-F proof hardening:** `67359e28835c23b9d571080e749306195a0251b8`
- **Slice-F final identical-input proof:** `452e37a0eb3f83ec11b8f43e961184750d64f047`

Reported verification evidence (recorded as reported by the authorized build/hardening tasks; **not re-run by this
charter**):

- Focused Slice-F suite (`tests/test_phase6_2_reconstruction.py`): **51 passed**.
- Combined Phase 6.2 A–F suites: **380 passed**.
- S1 durable regression (`tests/test_phase6_1_s1_durable_sqlite_sink.py`): **16 passed**.
- `git diff --check`: clean.
- `phase6_2_shadow_intent/reconstruction.py` **byte-for-byte unchanged** across the two tests-only proof-hardening
  commits (`14e490e` → `67359e2` → `452e37a`).

**No additional SHA, test count, or evidence is invented or approximated here.**

---

## 2. Exact Built Module Inventory (ratified)

Phase 6.2 is exactly **six behavior-bearing runtime modules** under `phase6_2_shadow_intent/`:

1. `phase6_2_shadow_intent/logical_model.py`
2. `phase6_2_shadow_intent/artifact_verifier.py`
3. `phase6_2_shadow_intent/s1_evidence_projection.py`
4. `phase6_2_shadow_intent/classification_predicates.py`
5. `phase6_2_shadow_intent/atomic_replay_step.py`
6. `phase6_2_shadow_intent/reconstruction.py`

**Plus one inert / exportless package initializer** (physically present, not behavior-bearing):

- `phase6_2_shadow_intent/__init__.py`

Pinned (`__init__.py` tombstone — documentary only):

- `__init__.py` **physically exists** but is **not a seventh behavior-bearing runtime component**.
- It **exports no** Phase 6.2 façade, callable, carrier, coordinator, or integration API.
- Its historical orientation wording — that the predicates, the atomic replay step, and the reconstruction fold are
  "later, separately-authorized slices" — is now **stale** (Slices A–F are all built and sealed).
- That stale orientation wording is **formally superseded / tombstoned by this Slice-G closeout charter**; the
  initializer carries **no current-state or architectural authority** where it conflicts with this charter.
- This tombstone is **documentary only**: **no physical `__init__.py` edit, package export, or API change is
  authorized.**

**No seventh behavior-bearing runtime module is added** — no integration module, façade, orchestrator, service,
adapter, registry, resolver, or export layer. The behavior-bearing inventory is closed at these six; the package
initializer remains inert.

---

## 3. Final Dependency DAG (pinned as built)

```
logical_model              (leaf — no intra-package deps)

s1_evidence_projection     (leaf — no intra-package deps)

artifact_verifier
    -> logical_model

classification_predicates
    -> logical_model
    -> s1_evidence_projection

atomic_replay_step
    -> classification_predicates
    -> logical_model
    -> s1_evidence_projection

reconstruction
    -> atomic_replay_step
    -> logical_model
```

Explicitly:

- The **earlier planning-time** `reconstruction` dependency shape (`457d279` §4, which also listed
  `artifact_verifier` and `s1_evidence_projection`) was **superseded** by the ratified Slice-F boundary
  (`04a20eb` §10).
- `reconstruction` **does not import** `artifact_verifier` **or** `s1_evidence_projection`. Its runtime imports are
  exactly `atomic_replay_step` and `logical_model`.
- **Artifact verification is an external, caller-owned precondition** (Slice B runs before reconstruction; Slice F
  never re-verifies).
- **S1 replay acquisition is external, caller-owned input supply** (the caller obtains the ordered replay tuple and
  hands it in).
- **No circular dependency and no shared mutable state** exists; the DAG is one-way and acyclic.
- **No Phase 6.1 module imports Phase 6.2** — the quarantine is one-directional.

---

## 4. Public API Surface (ratified — no new Slice-G callable)

**Slice G defines no new callable.** The existing two-stage trust-boundary workflow is ratified.

**Stage 1 — artifact verification (Slice B) — exact live, unannotated signature:**

```python
def verify_artifact(*, reference, binary_stream):
    ...
```

On successful verification, `verify_artifact` returns an exact `ShadowIntentDefinitionArtifact`. (The live runtime
definition carries **no** Python parameter or return annotations; the successful return object is a **behavioral
contract** — canonical bytes + detached SHA-256 digest under one-read discipline yielding the exact
`ShadowIntentDefinitionArtifact` — **not** a Python annotation.)

**Stage 2 — deterministic reconstruction (Slice F):**

```python
reconstruct_shadow_intent_state(
    *,
    ordered_replay_rows: tuple[object, ...],
    verified_manifest_artifact: ShadowIntentDefinitionArtifact,
) -> AtomicReplayStepResult
```

Pinned:

- `reconstruct_shadow_intent_state` is the **final reconstruction entrypoint**.
- `verify_artifact` remains a **separate artifact trust boundary** (canonical bytes + detached SHA-256; one-read
  discipline), upstream of and independent from reconstruction.
- `ordered_replay_rows` is **caller-supplied S1 append-order replay evidence**.
- **Phase 6.2 does not open or read the S1 database itself** — it consumes a caller-materialized tuple.
- **No combined verify-and-reconstruct façade exists or is authorized.**
- **No package-level re-export and no `__init__.py` API change is authorized.**

---

## 5. Return-Carrier Seal

The final return type remains exactly **`AtomicReplayStepResult`** (the Slice-E-owned frozen/slotted/kw-only
two-field carrier: `next_lifecycle_snapshot`, `next_seen_target_pairs`).

Pinned:

- **Empty replay** returns the **fresh empty `AtomicReplayStepResult`** constructed by Slice F (fresh factory-built
  empty `ShadowLifecycleSnapshot` / `SeenTargetPairsSnapshot`).
- **Non-empty replay** returns the **exact final Slice-E `AtomicReplayStepResult` unwrapped** (`is`-identical to the
  last step's carrier).
- **No `Phase6_2Result`, closeout carrier, wrapper, envelope, tuple, sentinel, export DTO, or alternate result type
  exists or is authorized.**

---

## 6. Orchestration Boundary

**Slice G performs no runtime orchestration.** Only the existing caller-level flow is ratified:

```
SealedArtifactReference + binary_stream
    -> verify_artifact
    -> ShadowIntentDefinitionArtifact

S1DurableSqliteSink.replay()
    -> ordered replay tuple

verified artifact + ordered replay tuple
    -> reconstruct_shadow_intent_state
    -> AtomicReplayStepResult
```

Pinned:

- **The caller owns sequencing** between these already-built boundaries.
- Slice G introduces **no** call site, coordinator, driver, runner, callback, sink, or integration hook.
- Slice G introduces **no** `try`/`except`, retry, recovery, timeout, scheduler, polling, thread, async task, or
  background worker.
- Slice G **does not inspect** snapshots, seen pairs, manifests, rows, or lifecycle state.

---

## 7. Integration and Lock Evidence (already present)

The planned Slice-G integration/lock evidence is **already present in the sealed A–F test chain**, especially
`tests/test_phase6_2_reconstruction.py`, which proves:

- genuine S5-produced records;
- `S1DurableSqliteSink.record_observation` → `replay()` evidence;
- genuine Slice-B `verify_artifact` output;
- targeted non-empty state growth;
- changed-snapshot threading (next-step inputs `is` the prior result's changed snapshots);
- same-input referential transparency (one rows object + one manifest object drive both executions);
- cross-execution output freshness and content equality (distinct objects, `==` content);
- the exact **two-module** reconstruction dependency (`atomic_replay_step`, `logical_model`);
- AST negative-space locks (no comprehensions / growing mutation / subscript-assign / aug-assign / rematerialization
  / module-global state; single public function; no error class; no `try`/`except`);
- raw-row opacity (the strict single-`Load` whitelist for `raw_evidence_row`);
- no rematerialization / no global state;
- exact error surface (`AtomicReplayStepError` propagation) and result surface (`AtomicReplayStepResult`).

**Slice G adds no duplicate integration test and no new lock test.**

---

## 8. Absence-Lock Resolution

Pinned lock state:

- There is **no remaining Slice-G-specific target-not-created or integration absence lock**.
- **Slice G relaxes no existing lock.**
- The **two `reconstruction.py` absence assertions** (`test_slice_f_target_not_created` in
  `tests/test_phase6_2_s1_evidence_projection.py` and `tests/test_phase6_2_classification_predicates.py`) were
  **already retired during the authorized Slice-F implementation** (`14e490e`).
- **No previously-retired lock is reopened.**
- **Every remaining negative architecture lock remains binding.**
- **No** capacity, execution, routing, paper, canary, live, package-export, analytics, persistence, or
  external-integration lock is weakened.

**No lock name or target is invented here.**

---

## 9. Memory, Identity, and Failure Seals

**Memory (Slice-F model, ratified):**

- **O(N)** caller-materialized replay tuple.
- **O(K)** evolving reconstruction payload, **worst-case O(N)**.
- **O(1)** Slice-F loop / reference / carrier overhead.
- **No streaming and no globally bounded-memory claim.**

**Identity:**

- The **same** rows and manifest objects may drive repeated executions.
- Outputs are **content-equal** and **cross-execution fresh** (distinct objects per execution).
- **Within-execution** row/artifact pass-through identity and changed/unchanged snapshot identity contracts remain
  sealed (Slice-E §5; Slice-F `04a20eb` §5).
- **No `id(...)`, cache, singleton, or hidden state.**

**Failure:**

- The **closed domain surface** remains distinct from open factory/system/unexpected fault propagation.
- **`AtomicReplayStepError` propagates unchanged** (same object, same `.reason`, same message).
- **No** wrapping, swallowing, retry, partial result, S4 conversion, or recovery behavior; the first failing row
  terminates the fold with no partial publication.

---

## 10. Proposed Completion Claim (conditional on external ratification)

This charter **proposes** the following exact, narrow completion claim — it is **not** self-effective and is **not**
asserted as already-ratified:

> **Phase 6.2 deterministic, replay-only, quarantined shadow-intent reconstruction runtime becomes COMPLETE +
> RATIFIED in its exact offline audit-reconstruction scope only upon independent external ratification of this
> Slice-G charter.**

Until that independent external Gemini and Codex review succeeds, this aggregate claim is **PENDING**. The existing
Slice A–F ratified/sealed statuses (§1) remain **historical evidence and are NOT downgraded**, and the existing
Slice-F ratification remains valid; **only** this new Slice-G closeout and the Phase 6.2 aggregate completion claim
are **conditional**.

That proposed completion is defined **narrowly** as:

- sealed artifact verification;
- deterministic append-order evidence projection / classification;
- atomic replay steps;
- sequential reconstruction fold;
- immutable, replay-local output state;
- evidence-first tests and structural negative locks.

Completion **MUST NOT** be interpreted as any of: production-ready; live-ready; paper-ready; canary-ready;
execution-ready; routing-ready; actionability-ready; capacity-validated; strategy/alpha validated; calibrated;
analytics/reporting/export ready; operationally deployed; or feature-complete beyond the exact Phase 6.2
reconstruction scope.

The generic phrase **"runtime-ready" is avoided**; where any readiness is asserted it is **only** the **sealed
offline audit-reconstruction scope**.

---

## 11. Capacity and Actionability Seal

Pinned:

- **Capacity remains deferred at exactly 0 emit sites.**
- **No capacity pass or validation exists.**
- **No** order, trade, buy, sell, submit, execute, route, fill, cancel, sizing, allocation, signal, recommendation,
  wallet, balance, PnL, portfolio, broker, exchange, market-data API, paper, canary, or live surface exists.
- **Historical S1 evidence is read verbatim.**
- **`HYPOTHETICAL_OUTCOME` remains counterfactual bookkeeping only** (firewalled; transition-non-driving).

---

## 12. Frozen / Unchanged Surfaces

Slice G changes **none** of:

- `phase6_2_shadow_intent` runtime files;
- tests or fixtures;
- `phase6_2_shadow_intent/__init__.py`;
- Phase 6.1 (all modules);
- `phase6_1_s1_storage`;
- S1 / S5;
- the frozen DTOs;
- `config.py`;
- existing charters;
- lock tests;
- capacity boundaries;
- analytics / export boundaries.

This charter adds **only** the single new docs file `docs/handoff/phase6_2_slice_g_runtime_closeout_ratification.md`.

---

## 13. Next-State Discipline

After Phase 6.2 closeout:

- **Do not automatically open** Phase 6.3, analytics, calibration, offline research, paper, canary, live, capacity,
  or integration work.
- **No next executable component is selected by this charter.**
- Any later boundary requires **separate evidence, review, Gemini assessment, Codex judgment, and explicit user
  authorization**.
- **Phase 6.2 completion alone grants no adjacent authorization.**

---

## 14. Exclusions / Precise Post-Charter State

- Docs-only: no runtime / tests / fixtures / package-export / `__init__.py` / prior-doc / lock / config edits; no
  seventh module; no new callable / carrier / façade; no generated files; no pytest; no graphify.
- **Slice-G docs-only closeout charter:** BUILT / RATIFIABLE / **UNRATIFIED**, **pending independent Gemini and Codex
  review of this committed charter**. It does **not** become effective merely by existing or being committed.
- The **Phase 6.2 aggregate COMPLETE + RATIFIED closeout claim** (§10) is **PENDING** — it becomes effective **only
  upon** that independent external ratification, and is **proposed** here, not asserted as already-ratified.
- **Capacity remains 0.** **No next executable scope is authorized.** Phase 6.1 frozen, COMPLETE + RATIFIED.

**Conclusion:** the Phase 6.2 shadow-intent reconstruction runtime is exactly **six behavior-bearing quarantined
modules** (`logical_model`, `artifact_verifier`, `s1_evidence_projection`, `classification_predicates`,
`atomic_replay_step`, `reconstruction`) **plus one inert / exportless `phase6_2_shadow_intent/__init__.py`** (whose
stale "later slices" orientation wording is tombstoned by this charter, documentary-only), under a one-way acyclic
DAG whose `reconstruction` boundary imports **only** `atomic_replay_step` and `logical_model`; the public surface is
the two-stage caller-owned workflow — Stage 1 the exact live, **unannotated** `def verify_artifact(*, reference,
binary_stream):` which **on success returns an exact `ShadowIntentDefinitionArtifact`** (a behavioral contract, not a
Python annotation), then Stage 2 **`reconstruct_shadow_intent_state(*, ordered_replay_rows: tuple[object, ...],
verified_manifest_artifact: ShadowIntentDefinitionArtifact) -> AtomicReplayStepResult`** — with the caller owning
sequencing and S1 replay acquisition, no façade, no re-export, and the direct **`AtomicReplayStepResult`** return
(fresh empty on empty replay, final Slice-E carrier unwrapped otherwise). The planned Slice-G integration/lock
evidence already lives in the sealed A–F chain (notably `tests/test_phase6_2_reconstruction.py`); no duplicate test
or new lock is added, no lock is relaxed, and the two `reconstruction.py` absence assertions were already retired in
`14e490e`. Memory (O(N) input, O(K)≤O(N) payload, O(1) overhead), identity (content-equal + cross-execution fresh;
no `id`/cache/singleton), and failure (`AtomicReplayStepError` propagates unchanged; no partial result) seals stand.
**Phase 6.2 deterministic, replay-only, quarantined shadow-intent reconstruction runtime becomes COMPLETE + RATIFIED
in its exact offline audit-reconstruction scope only upon independent external ratification of this Slice-G charter**
— and, even then, **not** production / live / paper / canary / execution / routing / actionability / capacity /
strategy / calibration / analytics / deployment ready, nor feature-complete outside the exact reconstruction scope.
**Capacity stays 0; no adjacent or next-phase scope is authorized; Slice A–F remain RATIFIED + SEALED; this Slice-G
closeout charter is BUILT / RATIFIABLE / UNRATIFIED, pending independent Gemini and Codex review of the committed
charter.**
