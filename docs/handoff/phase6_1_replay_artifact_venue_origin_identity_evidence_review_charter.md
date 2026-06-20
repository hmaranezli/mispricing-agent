# Phase 6.1 — Replay Artifact / Venue-Origin Identity Evidence Review Charter

> **This is a docs-only, read-only evidence review.** It inspects existing repo contracts, the replay reader, and
> any available sample/replay artifacts — **bounded, read-only, small samples only** — to classify whether an
> authoritative **event-level** identity source is currently carried. Finding none, it returns **BLOCKED/DEFERRED**
> and **invents no source**. It **designs and builds nothing**. It modifies, normalizes, regenerates, or rewrites
> **no data file**. It authorizes NO runtime, NO tests, NO lock-test edits, NO pytest, NO graphify, NO Python, NO
> imports, NO schema/runtime/interface edits, NO B1 runtime implementation, NO replay-reader implementation, NO
> log field-level schema, NO persistence/storage/serialization design, NO B4 scoring, NO S4 materialization, NO S5
> runner, NO Cell-3 route, NO Phase 6.2 work. It is subordinate to
> `docs/handoff/phase6_1_b1_replay_artifact_identity_source_decision_charter.md`,
> `docs/handoff/phase6_1_s2_identity_source_definition_charter.md`,
> `docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`,
> `docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `ce81078089cab90f27eb0d1e33304b30913fdb99`

**External review note:** Gemini Quant/Red-Team verdict — `ce81078` **BLOCKED/DEFERRED** is **APPROVED**;
event-level authoritative identity is still absent; the next step is a **bounded read-only evidence review** of
venue-origin and replay-artifact sources before any S2/0B schema work. This charter is that review.

---

## 1. Base / Dependency Chain

**Base commit:** `ce81078089cab90f27eb0d1e33304b30913fdb99`.

References:

- `…_b1_replay_artifact_identity_source_decision_charter.md` — decided the authoritative event-level identity
  must live at the **source contract boundary** (replay artifact contract or venue/B1 origin contract); **B1
  runtime is a blind courier**; per evidence, none carried → **BLOCKED/DEFERRED**.
- `…_s2_identity_source_definition_charter.md` — classified candidate sources; venue/replay classes ABSENT;
  snapshot-level `raw_snapshot_identity` DEFERRED.
- `…_replay_depth_artifact_reader_charter.md` / `…_replay_depth_reader_io_lock_exception_amendment_charter.md` —
  bound the single allowlisted IO module (`phase6_1/b1_replay_depth_artifact_reader.py`) to a read-only,
  single-artifact, decide-nothing, verbatim-carry reader.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Evidence Locations Inspected (read-only, bounded)

All inspection was **read-only**; **no data file was modified, normalized, regenerated, or rewritten.**

| Location | What was inspected | Relevant finding |
|---|---|---|
| `phase6_1/b1_replay_depth_artifact_reader.py` | The replay reader's artifact contract and read shape | Reads **ONE** caller-supplied artifact via `json.load` → **one** `PublicDepthSourceRecord`; **closed 8-field** artifact contract; unknown keys **fail fast**; carries every field verbatim; **decides nothing** |
| `phase6_1/b1_depth_source_contract.py` | B1 origin record fields | Carries `depth_*` provenance + **`depth_snapshot_identity`** (snapshot-level); **no** sequence/message/offset/row/event/record id |
| `phase6_1/b2_normalization_contract.py` | B2 normalized record fields | Carries `source_*`, `venue`, `pair`, timestamps + **`raw_snapshot_identity`** (snapshot-level); **no** event-level id |
| `phase6_1/b2_replay_normalization.py` | B2 replay normalization | Adds **no** event-level id (no `row_offset`/`read_index`/`sequence`/`enumerate`/`index`) |
| `tests/test_phase6_1_b1_replay_depth_artifact_reader.py` | How replay artifacts are sourced for tests | Fixtures are **built in-test** in `tmp_path` (`_write_artifact` → `json.dumps`); the only identity-adjacent value is `depth_snapshot_identity` (e.g. `"replay-depth-0001"`, a label) |
| `git ls-files` (tracked data) | Any committed replay artifact / sample | **Zero** tracked `.jsonl`; **no** committed replay/sample artifact. (`data/output/*.jsonl` are **untracked** legacy phase3/4 outputs — not phase6 replay artifacts, not in scope) |
| Repo-wide grep (`sequence_number`/`message_id`/`row_offset`/`read_index`/`record_id`/`event_id`) | Any event-level id anywhere in the passive pipeline | All hits are in legacy `main_loop.py` (position/order `seq_no`) and `graphify-out/` graph artifacts — **none** in the Phase 6.1 passive contracts |

**Closed-contract note.** The replay artifact contract is the frozen 8-field set
`{observed_size, size_unit, depth_source_field, depth_source_artifact, depth_source_contract,
depth_snapshot_identity, depth_observed_at_epoch_ms, depth_retrieval_epoch_ms}`. It carries **no** event-level
origin identity, and — because unknown fields fail fast — it **cannot** carry one without a **separately-authorized
contract change**. The reader is **single-artifact** (`json.load` of one object), so it tracks **no physical read
position**, exposes **no row order**, and provides **no I/O-intrinsic ordinal** that could even be a Silver
candidate today.

---

## 3. Gold / Silver Source Hierarchy (governing standard)

- **Gold** — venue/exchange-provided **event-level** `sequence_number` / `message_id`, present in a raw venue
  payload or the B1 origin contract.
- **Silver** — replay artifact `row_offset` / `read_index`, **only if** it is **artifact-origin / I/O-intrinsic**
  evidence (physical replay-artifact order or reader-provided position defined by the artifact/IO contract).
- **Disqualified as sole event identity** — snapshot-level `raw_snapshot_identity` / `depth_snapshot_identity`.

---

## 4. Physical I/O Evidence Standard

A `row_offset` / `read_index` may be considered **only** if it is tied to **physical replay-artifact order** or a
**reader-provided position** that the **artifact/IO contract** authoritatively defines. **Runtime-invented
counters are forbidden** (§5). This charter **classifies evidence only**; it designs **no** extraction mechanics,
reader change, parsing, or position-tracking.

---

## 5. Anti-Counter Firewall (explicit)

In-memory stateful counters used to *simulate* identity — `i = 0; … i += 1`, an enumeration index, a read-loop
ordinal, a computed "row number" — are **banned** as the identity source. A loop counter is **not** authoritative
provenance **unless a future source contract explicitly defines it as the replay artifact's row order** (an
artifact-origin fact), **not** runtime state. No such contract definition exists today.

---

## 6. No Mutation / No Casting (binding)

Whatever identity is ever borrowed must be carried **exactly as inherited**. Forbidden: string formatting, string
concatenation, int↔str normalization, prefixing/suffixing, hashing, UUID, random, timestamp-as-ID, payload
fingerprint, or any `event_id`/`log_id` formula.

---

## 7. Blind Courier (binding)

- **B1 may only carry** an inherited identity once a contract defines one.
- **B1 / B2 / B3 / Producer / Phase 5 / B4 / S1 must not** branch on, inspect, derive, reinterpret, mutate, or
  apply fallback to identity. Carriage is opaque and by reference.

---

## 8. Source Classification (evidence verdicts)

- **Gold — venue `sequence_number` / `message_id`: ABSENT.** No raw venue payload is carried in the repo, and the
  B1 origin contract defines no venue event-level identifier. (Not BLOCKED-by-policy but **ABSENT-in-evidence**:
  nothing to borrow.)
- **Silver — replay `row_offset` / `read_index`: ABSENT.** The closed replay artifact contract carries no offset/
  index; the single-artifact reader exposes no physical row order or I/O-intrinsic position. Any future Silver
  source would require a **separately-authorized replay-artifact/IO contract change** that defines the position as
  an **artifact-origin fact** (never a runtime counter). **ABSENT today; not invented.**
- **Snapshot-level `raw_snapshot_identity` / `depth_snapshot_identity`: DISQUALIFIED as sole event identity.**
  Carried, but snapshot-level (one snapshot ⇒ potentially many shadow events) and of unproven external authority
  (fixtures use labels like `"replay-depth-0001"`). May **only** remain a **candidate tuple component** **if**
  later proven authoritative **and** completed by an event-level Gold/Silver discriminator — **never sufficient
  alone**. No transformation/concatenation/hashing of it is performed or authorized.
- **Committed sample / replay artifact: ABSENT.** No replay/sample artifact is git-tracked; test fixtures are
  built in-process in `tmp_path`. Nothing is invented to stand in for one.

---

## 9. Minimum Evidence Standard for Accepting Any Source

A source may be accepted as authoritative event-level identity **only if all** hold:

1. **External origin.** It is supplied by the venue raw payload **or** defined by the replay-artifact/IO contract
   as an artifact-origin fact — **not** computed downstream.
2. **Event-level granularity.** It distinguishes each individual replay/log event or message (not merely each
   snapshot).
3. **Immutable & deterministic.** Stable and reproducible across replays; **not** a process-local runtime counter,
   timestamp, `id()`, hash, or random value.
4. **Carried verbatim.** Inheritable and carriable without mutation/casting/formatting (§6), opaque to all
   downstream boundaries (§7).
5. **Contract-anchored.** Owned by a source contract (venue origin or replay artifact), so its authority is
   provable, not assumed.

Snapshot-level labels fail criterion 2; runtime counters fail criteria 1 and 3.

---

## 10. Verdict — S2 Identity & Slice-0B Schema

- **Gold: ABSENT. Silver: ABSENT. Snapshot-level: DISQUALIFIED (deferred tuple-component only). Committed
  artifact: ABSENT.** No authoritative event-level identity source is currently carried → **BLOCKED/DEFERRED**.
  Nothing minted; nothing invented.
- **S2 identity: BLOCKED.** The opaque S2-owned identity slot stays **unfilled**; no authoritative borrowed source
  exists to fill it.
- **Slice-0B field-level schema: BLOCKED.** It may not define an event-identity field while the source is ABSENT
  (doing so would force minting). **No 0B schema authorized.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged. **This review authorizes nothing executable.**

---

## 11. Still-Forbidden Work

- **No** minting of identity (generate/calculate/hash/concatenate/increment/count/randomize/fingerprint); **no**
  `event_id`/`log_id` formula; **no** filling of the opaque S2 slot.
- **No** loop counter / enumeration index / read-ordinal as identity (Anti-Counter Firewall, §5).
- **No** mutation/casting/formatting/concatenation of any identity value (§6); **no** promotion of snapshot-level
  labels to sole event identity.
- **No** timestamp-as-identity; **no** `id()`/memory identity as durable identity.
- **No** modification/normalization/regeneration/rewrite of any data/fixture/artifact file.
- **No** B1 runtime implementation; **no** replay-reader/extraction/parsing/position-tracking design; **no** replay
  artifact / IO contract change.
- **No** log field-level schema; **no** persistence/storage/serialization/database/file design.
- **No** S4 materialization; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** downstream inspection/derivation/mutation/reinterpretation/fallback of carried identity (blind courier,
  §7).
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Slice-0B authorization; **no** S2 runtime/schema; **no** Phase 6.1 completion claim; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 12. Readiness Verdict

- **Authoritative event-level identity source: ABSENT (Gold ABSENT, Silver ABSENT, snapshot-level DISQUALIFIED,
  no committed artifact) → BLOCKED/DEFERRED.** Location already decided (source contract boundary; never B1
  runtime), but no such source is carried.
- **S2 identity: BLOCKED.** **Slice-0B field-level schema: BLOCKED.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.**

---

## 13. Next Safe Step (recommendation only)

- A **separately-authorized docs-only decision** on whether to **author a replay-artifact / IO contract amendment**
  that carries a deterministic, immutable, **artifact-origin** event-level identity (e.g. a contract-defined
  `row_offset`/`read_index` as a Silver source, or a venue `sequence_number`/`message_id` as a Gold source if a
  raw venue payload is ever ingested) — meeting the §9 minimum evidence standard, **borrowed not minted**, and
  carried verbatim. Only such a contract amendment can move Silver/Gold from ABSENT to AVAILABLE; absent it, the
  source stays **BLOCKED/DEFERRED**.
- Only after an authoritative **borrowed** source is **carried and ratified** may the **S2 identity slice** fill
  the opaque slot, and only then may a **Slice-0B field-level schema** charter be authorized (under the S1 boundary
  and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The contract amendment, the S2 identity fill, the 0B
  schema, S4 materialization, B4 scoring, S5 runner, durable persistence, the Cell-3 route, the Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** read-only evidence confirms **no authoritative event-level identity source is currently carried** —
**Gold ABSENT**, **Silver ABSENT** (closed single-artifact replay contract exposes no artifact-origin row order),
**snapshot-level DISQUALIFIED** as sole identity, **no committed replay/sample artifact** → **BLOCKED/DEFERRED**
(nothing minted, nothing invented). **S2 identity remains BLOCKED**; **Slice-0B schema remains BLOCKED**; Phase 6.1
remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
