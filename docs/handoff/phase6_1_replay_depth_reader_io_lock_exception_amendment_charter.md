# Phase 6.1 Replay Depth-Reader IO-Lock Exception Amendment Charter

> **This is a planning/charter document only.** It defines a single, surgical, module-scoped exception to the
> package-wide Phase 6.1 no-IO structural locks, to be applied **only** by a later separately-authorized
> slice. It authorizes NO runtime, NO tests, NO lock-test edits, NO reader implementation, NO pytest, NO
> graphify update, NO network/API call. It is subordinate to
> `docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`,
> `docs/handoff/phase6_1_b1_depth_source_amendment_charter.md`,
> `docs/handoff/phase6_1_b2_schema_extension_charter.md`, and
> `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md`. Where any conflict arises,
> those govern.

**Base:** `c9125e55ee11b268d9c669a224ff390d70ed3061`

---

## 1. Purpose — A Surgical Exception, Not a Relaxation of Posture

The Phase 6.1 runtime package is under a **package-wide no-IO posture**: two package-wide structural lock
tests sweep **every** `phase6_1/*.py` and reject file IO (`open`), IO/OS imports (`os`, `sys`, `pathlib`,
`io`, `pickle`, `shelve`, `tempfile`, `shutil`), the `json` token, network roots, dynamic exec, and the
actionability surface.

A future replay depth-artifact reader (chartered in
`docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`) must read **one local replay artifact** to
construct a `PublicDepthSourceRecord`. That single read is structurally incompatible with the package-wide
`open`/`pathlib`/`json` bans.

This charter defines a **surgical exception**: a closed, read-only, module-scoped carve-out for **exactly one
future module basename**, leaving the package-wide no-IO posture as the default for **every other** module and
keeping all non-IO guarantees global and unweakened. It does not implement the exception; it specifies its
exact shape so a later slice can apply it without expanding it.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. The One Allowlisted Module Basename

- The exception applies to **exactly one** future module basename:
  **`b1_replay_depth_artifact_reader.py`**.
- No other basename is covered. No wildcard, prefix, or directory-level allowance is granted.
- The allowlist is **by exact basename**, evaluated per-file inside the existing package-wide scans.

---

## 3. All Other Modules Stay Under the Existing No-IO Posture

- Every `phase6_1/*.py` module **other than** `b1_replay_depth_artifact_reader.py` remains fully under the
  current no-IO locks — no `open`, no IO/OS imports, no `json` token, unchanged.
- The carve-out must be expressed as a single-basename allowance inside the scanners; it must **not** loosen,
  delete, or broaden any check for the rest of the package.
- If the reader module is ever removed or renamed, the exception lapses; no other module inherits it.

---

## 4. Future Allowed IO Surface — Reader Module Only

For `b1_replay_depth_artifact_reader.py` only, a later slice may permit:

- **Read-only** local artifact `open` only (read mode).
- **No** write mode.
- **No** append mode.
- **No** mutation of artifacts (the artifact is read, never modified).
- **No** directory discovery, globbing, walking, or implicit path lookup unless **separately authorized**.
- Only the **explicitly supplied** local artifact path/reference may be opened.

The reader opens one explicitly-named local artifact, reads it, and constructs `PublicDepthSourceRecord`. It
does nothing else with the filesystem.

---

## 5. Future Closed Import Allowlist — Reader Module Only

For `b1_replay_depth_artifact_reader.py` only, a later slice may permit a **closed** import allowlist:

- `pathlib`
- `json`
- `csv`

Explicitly **disallowed even inside the reader**:

- `os`, `sys`, `io`, `tempfile`, `shutil`, `pickle`, `shelve`
- `requests`, `urllib`, `socket`, `aiohttp`, `websocket`/`websockets`, `http`
- `subprocess`

The allowlist is **closed**: any import not in `{pathlib, json, csv}` stays banned in the reader module too.

---

## 6. Globally Banned and Unweakened — Including Inside the Reader

The following remain **banned for every module, including** `b1_replay_depth_artifact_reader.py`:

- **Network / live / API access** — no network clients, no live or public/private API reads, no network
  fallback from a missing artifact.
- **Env / secrets / private credentials** — no environment access, no secrets, no API keys (note: `os`/`sys`
  stay banned in the reader precisely so `os.environ`/`getenv` cannot appear).
- **Account / wallet / order / balance / trading endpoints** — none.
- **Dynamic exec** — no `eval`, `exec`, `compile`, `__import__`, `input`.
- **Subprocess / system / popen** — none.
- **Actionability / sizing / allocation / routing / verdict / score / threshold semantics** — none; the
  reader carries evidence and decides nothing.
- **B3 / Phase 5 wiring or bypass** — the reader does not call, import, or construct B3 or Phase 5 carriers.
- **Shadow Intent Envelope runtime/schema** — not introduced or referenced.

The exception is strictly an IO carve-out; it weakens none of these.

---

## 7. Exact Package-Wide Lock Tests a Later Slice May Amend

A later, separately-authorized slice may amend **only** these package-wide lock tests to encode the
single-basename exception:

- `tests/test_phase6_1_forbidden_token_locks.py`
  - `test_runtime_has_no_io_or_dynamic_exec_calls`
  - `test_runtime_has_no_forbidden_imports`
  - `test_runtime_source_is_free_of_forbidden_tokens`
- `tests/test_phase6_1_diagnostic_ev_non_actionability.py`
  - `test_slice0d_import_and_io_locks_still_hold`
  - `test_slice0d_forbidden_token_lock_still_holds`

No other lock test, no single-file B1/B2 scanner, and no runtime file is in scope for that future amendment.
This charter authorizes **none** of those edits now.

---

## 8. Any Future Amendment Must Be Module-Scoped by Basename

- A future amendment must carve the exception **per-file, keyed on the exact basename**
  `b1_replay_depth_artifact_reader.py`.
- It must **not** be expressed package-wide (no global removal of `open`, no global drop of `pathlib`/`json`,
  no blanket relaxation).
- The allowed IO surface (read-only `open`) and the import allowlist (`pathlib`, `json`, `csv`) must remain
  **closed and enumerated** for that one module; everything else stays banned for it.
- The amendment must keep every other module's no-IO assertions intact and must keep all §6 bans global.

---

## 9. Future Reader TDD Must Prove (Planning Notes Only — NOT Written Now)

When a reader slice is later authorized, its TDD must prove:

1. **Strict 8-field replay depth artifact contract** — all of `observed_size`, `size_unit`,
   `depth_source_field`, `depth_source_artifact`, `depth_source_contract`, `depth_snapshot_identity`,
   `depth_observed_at_epoch_ms`, `depth_retrieval_epoch_ms` supplied explicitly.
2. **No numeric parsing / coercion of `observed_size`** — never `int`/`float`/`Decimal`/`complex`.
3. **Missing / malformed fields fail fast** (and unknown semantic fields fail fast unless separately
   chartered).
4. **Exact string preservation** — `"100.00"` stays `"100.00"`; `"not-a-number"` carried verbatim.
5. **Timestamp isolation / no retrieval-timestamp substitution** — reject
   `depth_observed_at_epoch_ms == str(depth_retrieval_epoch_ms)`.
6. **Immutable artifact / provenance anchor** required before construction; no fabricated anchors.
7. **No live / network / env / secrets** — AST-scan rejects them in the reader.
8. **No B2 / B3 / Phase 5 runtime change** unless separately authorized; construct only
   `PublicDepthSourceRecord` via `make_public_depth_source_record`.

The reader module must also carry its **own** file-scoped lock tests proving the closed IO/import surface
(read-only `open`; imports ⊆ `{pathlib, json, csv}`; none of the §6 bans present).

---

## 10. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 11. Still-Blocked Work

- **No runtime reader implementation** is authorized.
- **No lock-test edits** are authorized.
- **No tests** are authorized.
- **No B2 threading**, **no B3 implementation**, **no Phase 5 runtime change** is authorized.
- **No live/network read** is authorized.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.

---

## 12. Next Safe Step

- After this docs-only charter, the next step is a **separate review** deciding whether to authorize a single
  combined slice that (a) applies the narrow, single-basename IO-lock test amendment per §7–§8 **and**
  (b) implements the replay depth-reader via TDD per §9 — or to split those into two separately-gated slices.
- That future work, **if authorized**, must be **replay-only**, **local-artifact-only**, **read-only**,
  **no network**, **no B2 threading**, and **no Phase 5 / B3** change.
- **No implementation is authorized by this charter.** Reader implementation, lock-test amendment, B2 depth
  threading, B3 mapping/wiring, Phase 5 runtime changes, Phase 6.2 calibration, and 7.x/8.x remain separately
  gated.
