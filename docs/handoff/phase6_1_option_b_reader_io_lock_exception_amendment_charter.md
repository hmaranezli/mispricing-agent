# Phase 6.1 Option-B Reader IO-Lock Exception Amendment Charter

> **This is a planning/charter document only.** It formally authorizes, **at docs level only**, a single,
> surgical, module-scoped exception to the package-wide Phase 6.1 forbidden-token locks: the `json` token, for
> **exactly one** future module basename (the Option-B event-stream reader). It **designs and builds nothing**,
> and it **commits or authorizes nothing executable**. It authorizes NO runtime commit, NO tests commit, NO
> lock-test edit, NO staging/committing of the already-created reader/runtime/test files, NO Python/schema/
> runtime/interface edits, NO B1/B2/B3/Phase 5/passive-producer changes, NO pytest, NO graphify, NO network/API
> call. It is subordinate to
> `docs/handoff/phase6_1_option_b_reader_io_design_charter.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`,
> `docs/handoff/phase6_1_option_b_event_level_replay_artifact_contract_amendment_charter.md`,
> `docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `7e311125bac1ff87ab86e705f88fad2f7490520e`

---

## 1. Purpose — A Surgical Token Exception, Not a Relaxation of Posture

The Phase 6.1 runtime package is under a **package-wide no-IO / closed-token posture**: two package-wide
structural lock tests sweep **every** `phase6_1/*.py` and reject, among other things, the **`json` token**:

- `tests/test_phase6_1_forbidden_token_locks.py::test_runtime_source_is_free_of_forbidden_tokens`
- `tests/test_phase6_1_diagnostic_ev_non_actionability.py::test_slice0d_forbidden_token_lock_still_holds`

Both currently allow the `json` token for **exactly one** allowlisted basename
(`b1_replay_depth_artifact_reader.py`, authorized by
`docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`).

The ratified Option-B charters selected a **JSONL-style line-oriented** event-artifact family and an Option-B
reader that is a **dumb physical parser** of caller-injected text streams. To distinguish a structurally-valid
JSON line from a malformed one (and to surface malformed lines as a local IO-halt rather than dropping or
crashing), that reader must use `json` — which the package-wide token scans currently forbid for any basename
other than the one existing reader.

This charter defines a **surgical exception**: a closed, **token-only**, module-scoped carve-out for **exactly
one future module basename**, leaving the package-wide posture as the default for **every other** module and
keeping all other guarantees global and unweakened. It does **not** apply the exception; it specifies its exact
shape so a later separately-authorized slice can apply it without expanding it.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Strict Module Pinning — The One Allowlisted Basename

- The future `json`-token exception applies to **exactly one** module basename:
  **`option_b_event_stream_reader.py`**.
- No other basename is covered. No wildcard, prefix, directory-level, or package-wide allowance is granted.
- The allowlist is **by exact basename**, evaluated per-file inside the existing package-wide token scans.
- This is **NOT** a blanket Phase 6.1 JSON authorization. Every other `phase6_1/*.py` module remains fully
  under the `json`-token ban, unchanged.
- If the Option-B reader module is ever removed or renamed, the exception lapses; no other module inherits it.

---

## 3. IO-Dependency Justification — Structural Parsing, Not Business Logic

- The exception is required **because** the ratified Option-B field-shape charter selected a **JSONL-style
  line-oriented** artifact family (one physical line = one logical event).
- `json` use in the Option-B reader is **structural IO parsing only** — turning one physical line into a payload
  object and detecting a malformed line. It is **not** business logic, **not** scoring, **not** normalization,
  **not** semantic validation, **not** mapping/coercion/calibration.
- The `json` token is therefore an **IO-parsing dependency**, justified on the same structural grounds the
  existing single-artifact reader's exception was justified — and is the **narrowest possible** carve-out (a
  single token for a single basename).

---

## 4. Anti-File-System Seal — Stream-Only, No Filesystem Mechanics

Reaffirmed and **unweakened**, including inside `option_b_event_stream_reader.py`:

- **No `open()`** — the Option-B reader opens nothing. (Unlike the single-artifact reader's exception, this
  exception grants **no** `open()` carve-out at all.)
- **No `os`, `sys`, `pathlib`, `io`, `tempfile`, `shutil`, `pickle`, `shelve`** imports.
- **No absolute path derivation, directory crawling, globbing, walking, or implicit path lookup.**
- The reader parses **caller-injected text streams only** (e.g. an in-memory `io.StringIO` supplied by the
  caller); it performs **no** filesystem access of any kind.

This exception is strictly a **token** carve-out for `json`; it grants **no** IO/path/`open` capability.

---

## 5. Narrow Lock-Test Future Scope

A later, separately-authorized runtime/TDD slice may amend **only** the two package-wide **token-scan** lock
tests, and **only** to add `option_b_event_stream_reader.py` to the existing single-basename `json`-token
allowlist:

- `tests/test_phase6_1_forbidden_token_locks.py::test_runtime_source_is_free_of_forbidden_tokens`
- `tests/test_phase6_1_diagnostic_ev_non_actionability.py::test_slice0d_forbidden_token_lock_still_holds`

Scope limits on that future amendment:

- **Token-only.** Only the `json` token is allowlisted for the new basename. **No other token** (e.g. `serialize`,
  `serialization`, `to_json`, `to_dict`, `order`, `routing`, `sizing`, …) is allowlisted.
- **No import, IO, path, or `open` capability** is granted to the new basename. (The reader already passes the
  package-wide import and IO/dynamic-exec scans because `json`/`dataclasses` are not forbidden imports and the
  reader uses no `open`/`eval`/`exec`/`compile`/`__import__`/`input`; those scans therefore need **no**
  amendment.)
- **No package-wide relaxation.** The amendment must be expressed **per-file, keyed on the exact basename**,
  leaving every other module's bans intact and every §6 guarantee global.
- **No other lock test, no single-file scanner, and no runtime file** is in scope for that future amendment.

This charter authorizes **none** of those edits now.

---

## 6. Existing Guardrails Remain Global and Unweakened

The following remain **banned for the Option-B reader** (and everywhere), unchanged by this exception:

- **No `enumerate`** and **no global/application/persisted/cross-file counters** — `physical_record_position`
  must come only from the active stream's own position mechanics.
- **No `uuid` / `hashlib` / `random` / `secrets` / `time` / `datetime` / `calendar`** imports — no identity
  minting, no clock.
- **No `B1` / `B2` / `B3` / `Phase 5` / `passive_producer` imports** — the reader is a standalone physical
  parser; it constructs/calls none of those carriers.
- **No semantic validation** — no price/sign/unit/venue/cost/freshness/scoring judgement; no mapping/coercion/
  calibration; structural parse only.
- **No identity in payload / no payload-authored identity trust** — `artifact_locator` and
  `physical_record_position` are medium metadata, never read from or written into the payload.
- **No actionability surface** — no `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/
  order content.
- **No `open` / network / env / secrets / subprocess / dynamic exec** anywhere.
- **No S4 materialization, no B4 scoring, no S5 runner, no Cell-3 route, no Phase 6.2 work.**

The exception weakens none of these. The malformed-line behavior remains a **local** IO-halt only — it designs
**no** S4 global halt schema and **no** shadow-log materialization.

---

## 7. Pending Uncommitted Files — Explicitly Unauthorized by This Charter

- A green-in-isolation Option-B reader and its test currently sit **uncommitted** in the working tree:
  - `phase6_1/option_b_event_stream_reader.py`
  - `tests/test_phase6_1_option_b_event_stream_reader.py`
- These files are **NOT** authorized, staged, or committed by this docs-only charter. They **remain uncommitted**
  and unauthorized.
- This charter commits **only** itself (this one docs file). It does **not** stage, commit, or push the reader/
  test files, and it does **not** amend any lock test.
- The next executable step — applying the §5 token-only lock-test amendment **and** committing the reader/test —
  must be **separately authorized** after this charter lands.

---

## 8. Any Future Amendment Must Be Module-Scoped by Basename

- A future amendment must carve the exception **per-file, keyed on the exact basename**
  `option_b_event_stream_reader.py`.
- It must **not** be expressed package-wide (no global removal of the `json` token ban, no blanket relaxation).
- The allowed surface for that one module is the **single `json` token** and nothing else; every other token,
  import, IO/path capability, and §6 ban stays in force for it.
- The amendment must keep every other module's token assertions intact and must keep all §6 bans global.

---

## 9. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 10. Still-Blocked Work

- **No** lock-test edit is authorized (the §5 token allowlist amendment is specified, not applied).
- **No** staging/commit/push of the uncommitted reader/test files is authorized.
- **No** runtime/schema/interface change; **no** B1/B2/B3/Phase 5/passive-producer change.
- **No** `open`/IO/path capability for the Option-B reader; **no** network/env/secrets/subprocess/dynamic exec.
- **No** S4 materialization, **no** B4 scoring, **no** S5 runner, **no** Cell-3 route, **no** Phase 6.2 work.
- **No** S2 identity fill; **no** Slice-0B field-level schema. S2 identity remains BLOCKED and Slice-0B remains
  BLOCKED; Phase 6.1 remains incomplete; Phase 6.2 not ready.

---

## 11. Next Safe Step

- After this docs-only charter, the next step is a **separately-authorized single combined slice** that (a)
  applies the narrow, **token-only**, single-basename lock-test amendment per §5/§8 to the two named token-scan
  tests, **and** (b) commits the already-green Option-B reader and its test — or a decision to split those into
  two separately-gated steps.
- That future work, **if authorized**, must keep the exception **token-only** (`json`), **stream-only** (no
  `open`/path/IO), and must leave every §6 guarantee global and every other module's bans intact.
- **No implementation, no lock-test edit, and no reader/test commit is authorized by this charter.** The lock-test
  amendment, the reader/test commit, S2 identity, the Slice-0B schema, S4 materialization, B4 scoring, the S5
  runner, the Cell-3 route, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** this charter authorizes — **at docs level only** — a single, surgical, **token-only** exception
granting the `json` token to **exactly one** future basename (`option_b_event_stream_reader.py`), justified by the
ratified JSONL-style Option-B artifact family, with **no** `open`/IO/path capability, the anti-filesystem seal and
all §6 guardrails intact, and the lock-test amendment **specified but not applied**. The already-created reader and
test files **remain uncommitted and unauthorized**; the next executable step is **separately gated**. **No
executable work is authorized.**
