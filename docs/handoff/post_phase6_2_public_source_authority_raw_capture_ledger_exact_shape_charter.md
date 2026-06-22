# Post-Phase 6.2 — Public Source-Authority & Raw-Capture-Ledger Exact-Shape Charter

> **This is a docs-only exact-shape charter** (corrective revision over base `fa12d4a`, created as a normal
> follow-up commit — no amend/rebase/squash/force-push). It pins the closed public-source authority allowlist, the
> exact one-shot transport contract, the isolated raw-ledger medium, **complete executable SQLite DDL with enforced
> invariants and append-only triggers**, the **docs-only future runtime API shape**, the **idempotent
> initialization + schema-fingerprint law**, the **request grammar + header-ownership law**, the **forensic clock
> law**, and the **journal-coherence law**. It **builds nothing and authorizes nothing executable**: no runtime
> code, no collector, no tests, no fixtures, no adapter, no config, no locks, no package exports, no tracking files,
> no generated files, no pytest, no graphify, and **no network call**. Committing it performs **no data
> acquisition** and builds **no collector**. It is the single next docs-only gate named by
> `docs/handoff/post_phase6_2_read_only_real_world_evidence_acquisition_boundary_charter.md`. **This is not a Phase
> 6.3 work item and bears no Phase 6.3 label.**

**Base:** `fa12d4a6f99e964ad1a9e9ba43c66680c7f959b3`

---

## 0. Enforcement Model & SQLite-Limit Disclosures

Every invariant below is enforced by **executable schema** (CHECK / FOREIGN KEY / partial UNIQUE index / predecessor
trigger) **except** the following, which **SQLite cannot enforce** and are therefore **assigned to fail-fast runtime
validation** (named here, never silently assumed):

- **RV-1** `response_body_sha256` equals the actual SHA-256 of `response_body` (SQLite has no `sha256()`); DDL checks
  only shape.
- **RV-2** `response_headers_payload` internal length-prefixed binary structure (§4.2) is well-formed (SQLite cannot
  parse BLOB structure).
- **RV-3** exact `slug` / `token_id` full-match grammar and percent/Unicode/oversize rejection (§5) — DDL applies
  only a coarse target-prefix check.
- **RV-4** `retrieval_elapsed_monotonic_ns` is the exact `time.monotonic_ns()` completed−started delta sampled at the
  §8.1/§8.2 hooks (genuine monotonic source; a negative delta is a fail-fast defect that writes no row); DDL checks
  only non-negativity.
- **RV-5** `clock_anomaly_evidence` is the exact §8.3 derivation (`1` iff `retrieval_completed_epoch_ms <
  retrieval_started_epoch_ms`, else `0`) from the §8.1/§8.2 epoch samples — beyond the stored §4 epoch coupling.
- **RV-6** `failure_payload` exact UTF-8 JSON encoding law (§5.3): parse-then-re-encode byte-for-byte equality
  before INSERT; SQLite cannot validate the JSON shape/redaction.
- **RV-7** — a **deferred downstream validation boundary** (§9): inter-ordinal retry authorization / gapless
  progression is **not implemented or claimed here**; it is owned by the future projection/S1 charter. DDL checks only
  `attempt_ordinal >= 1` and per-triple uniqueness/transition order.
- **RV-8** TLS/cert verification, redirect refusal, decompression-disabled, timeouts, ≤16 MiB cap, one-request-per-call
  (§2) — transport-layer, not schema.
- **RV-9** exact reference-catalog comparison + PRAGMA + S1 path-isolation preflight (§4B/§4B.1) — runtime-computed
  before any network I/O.
- **RV-10** **capture/attempt commit reconciliation** (§10): SQLite cannot enforce the reverse "every capture row has
  exactly one provenance-matching `RAW_COMMITTED` attempt at commit" under an append-only insertion model. After both
  inserts and **before `COMMIT`**, the conforming runtime must query **inside the same transaction** and prove
  **exactly one** `raw_capture_log` row and **exactly one** provenance-matching `RAW_COMMITTED` `raw_fetch_attempt_log`
  row; **any mismatch rolls back and raises `RawLedgerCommitError`**, **no RAW_CAPTURED is claimed**, and **the
  conforming runtime accepts no silent orphan**. A **privileged direct SQL writer is NOT prevented from bypassing
  RV-10** (this is a conforming-runtime obligation, not a schema guarantee).

No prose invariant is claimed that the DDL silently accepts in violation **unless** it appears in RV-1…RV-10 with an
explicit runtime owner.

---

## 1. Closed Public-Source Authority (exactly three variants)

Exactly **three** closed source-authority variants; no fourth; no free-form URI/host/path/method/query-name/body.

| Token | Method | Scheme | Host | Path | Query / Body |
|---|---|---|---|---|---|
| `POLYMARKET_GAMMA_MARKET_BY_SLUG_V1` | GET | https | `gamma-api.polymarket.com` | `/markets` | exactly one caller-supplied `slug`; empty body |
| `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1` | GET | https | `clob.polymarket.com` | `/book` | exactly one caller-supplied `token_id`; empty body |
| `HYPERLIQUID_META_AND_ASSET_CTXS_V1` | POST | https | `api.hyperliquid.xyz` | `/info` | body bytes exactly `b'{"type":"metaAndAssetCtxs"}'` (`X'7b2274797065223a226d657461416e64417373657443747873227d'`, 27 bytes) |

- `POLYMARKET_GAMMA_MARKET_BY_SLUG_V1` carries **no closed-market / resolution authority** (deferred to a later
  HYPOTHETICAL_OUTCOME source amendment, §11). No wall-clock slug generation.
- HTTPS + certificate verification mandatory; redirects forbidden; credential/auth/signing/cookie/session/private/
  account/order headers forbidden (§5). GET allows only `Accept: application/json`; POST additionally requires
  `Content-Type: application/json`.
- No Data API, WebSocket, Chainlink, account endpoint, exchange (trading) endpoint, or authenticated CLOB surface.
- **No import or reuse of legacy `data/` modules** in the first runtime.
- Bytes-only capture: **no** JSON parsing, normalization, field mapping, event-time extraction, gross-edge
  calculation, Option-B construction, or S1 writing.

---

## 2. Exact Transport Contract (runtime-owned, RV-8)

- **One callable execution = at most one HTTP request.**
- Connect timeout **3000 ms**; total timeout **10000 ms**; max response entity **16 MiB** (`16777216` bytes;
  exceeding ⇒ `RESPONSE_TOO_LARGE`, never partial-body success).
- TLS verification **enabled**; automatic content decompression **disabled**.
- **No** retry, fallback, cache, stale substitution, alternate endpoint, or partial-body success.
- Stored body = exact response entity bytes after HTTP transfer-framing removal but **before** content decoding,
  decompression, JSON/Unicode decoding, or normalization.
- **Every completed HTTP response, including non-2xx**, may become **RAW_CAPTURED** *iff* its raw-ledger transaction
  commits. **RAW_CAPTURED means only "exact response evidence durably committed"** — not HTTP success, valid JSON,
  usable data, or downstream eligibility.
- Transport failure before a completed response creates **no** `raw_capture_log` row. Ledger-commit failure creates
  **no** RAW_CAPTURED claim (§7).

---

## 3. Isolated Storage Medium

A **separate caller-owned SQLite database path**, distinct from S1:

- Must **not equal, alias, canonical-path-collide with, attach, replace, or share** the S1 database path. The S1 path
  is supplied by the caller as the mandatory `s1_ledger_path` argument (§7) **only** for disjointness checking; raw
  acquisition **never opens, reads, imports, attaches, queries, mutates, or initializes S1**, and uses no global
  state, hidden config, environment lookup, or S1-package import (§4B step 1 enforces, before network I/O).
- `PRAGMA journal_mode=WAL`; `PRAGMA synchronous=FULL`; `PRAGMA foreign_keys=ON`.
- **No** `ATTACH DATABASE`; **no** `UPDATE`/`DELETE`/`REPLACE`/UPSERT/destructive DDL/vacuum-rewrite/mutation of
  committed evidence (§2-trigger enforced + §0 bans).
- All connections/resources owned and closed by the one-shot acquisition boundary.
- **S1 remains frozen and untouched.**

---

## 4. Exact Executable DDL

All objects are created with `IF NOT EXISTS` (idempotent init, §4.3). `PRAGMA foreign_keys=ON` is required for the
foreign keys below to be enforced (verified in preflight, RV-9).

### 4.1 `raw_capture_log`

```sql
CREATE TABLE IF NOT EXISTS raw_capture_log (
    capture_sequence             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_authority             TEXT    NOT NULL,
    http_method                  TEXT    NOT NULL,
    request_scheme               TEXT    NOT NULL,
    request_host                 TEXT    NOT NULL,
    request_target               TEXT    NOT NULL,
    request_body                 BLOB    NOT NULL,
    retrieval_started_epoch_ms   INTEGER NOT NULL,
    retrieval_completed_epoch_ms INTEGER NOT NULL,
    retrieval_elapsed_monotonic_ns INTEGER NOT NULL,
    clock_anomaly_evidence       INTEGER NOT NULL,
    http_status                  INTEGER NOT NULL,
    response_headers_payload     BLOB    NOT NULL,
    response_body                BLOB    NOT NULL,
    response_body_sha256         TEXT    NOT NULL,
    collector_commit_sha         TEXT    NOT NULL,

    CHECK (typeof(request_body) = 'blob'),
    CHECK (typeof(response_headers_payload) = 'blob'),
    CHECK (typeof(response_body) = 'blob'),
    CHECK (request_scheme = 'https'),
    CHECK (http_method IN ('GET','POST')),
    CHECK (retrieval_started_epoch_ms >= 0),
    CHECK (retrieval_completed_epoch_ms >= 0),
    CHECK (retrieval_elapsed_monotonic_ns >= 0),
    CHECK (clock_anomaly_evidence IN (0,1)),
    CHECK (http_status BETWEEN 100 AND 599),
    -- forensic clock law (§8): never reject a backward wall-clock; record it as anomaly evidence instead.
    CHECK (
        (retrieval_completed_epoch_ms >= retrieval_started_epoch_ms AND clock_anomaly_evidence = 0)
        OR (retrieval_completed_epoch_ms <  retrieval_started_epoch_ms AND clock_anomaly_evidence = 1)
    ),
    -- SHA shape only (actual digest equality is RV-1):
    CHECK (length(response_body_sha256) = 64 AND response_body_sha256 NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(collector_commit_sha) = 40 AND collector_commit_sha NOT GLOB '*[^0-9a-f]*'),
    -- closed source-authority <-> method/host/target/body coupling (exact GET/POST body compatibility):
    CHECK (
        (source_authority = 'POLYMARKET_GAMMA_MARKET_BY_SLUG_V1'
            AND http_method = 'GET'  AND request_host = 'gamma-api.polymarket.com'
            AND substr(request_target,1,14) = '/markets?slug=' AND length(request_target) > 14
            AND length(request_body) = 0)
        OR (source_authority = 'POLYMARKET_CLOB_BOOK_BY_TOKEN_V1'
            AND http_method = 'GET'  AND request_host = 'clob.polymarket.com'
            AND substr(request_target,1,15) = '/book?token_id=' AND length(request_target) > 15
            AND length(request_body) = 0)
        OR (source_authority = 'HYPERLIQUID_META_AND_ASSET_CTXS_V1'
            AND http_method = 'POST' AND request_host = 'api.hyperliquid.xyz'
            AND request_target = '/info'
            AND request_body = X'7b2274797065223a226d657461416e64417373657443747873227d')
    ),
    -- §3 parent key for the composite provenance FK from raw_fetch_attempt_log (trivially unique because
    -- capture_sequence is already the primary key; declared so the composite FK has a valid parent target):
    UNIQUE (capture_sequence, source_authority, request_target, collector_commit_sha)
);
```

`capture_sequence` is `AUTOINCREMENT` medium-local append order / reference **only** — never market/domain identity,
never a deduplication key.

### 4.2 `response_headers_payload` exact binary encoding (RV-2 validated at runtime)

- unsigned 32-bit **big-endian** header-pair **count**;
- then, per header in **received order**: u32-BE name length, exact name bytes, u32-BE value length, exact value
  bytes;
- duplicate headers and original order **preserved**; **no** Unicode decoding, case-folding, sorting, dict
  conversion, or comma-joining.

### 4.3 `raw_fetch_attempt_log`

```sql
CREATE TABLE IF NOT EXISTS raw_fetch_attempt_log (
    attempt_sequence             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_authority             TEXT    NOT NULL,
    request_target               TEXT    NOT NULL,
    retrieval_started_epoch_ms   INTEGER NOT NULL,
    retrieval_completed_epoch_ms INTEGER NOT NULL,
    retrieval_elapsed_monotonic_ns INTEGER NOT NULL,
    clock_anomaly_evidence       INTEGER NOT NULL,
    outcome                      TEXT    NOT NULL,
    capture_sequence             INTEGER,
    failure_code                 TEXT,
    failure_payload              TEXT,
    collector_commit_sha         TEXT    NOT NULL,

    CHECK (source_authority IN (
        'POLYMARKET_GAMMA_MARKET_BY_SLUG_V1',
        'POLYMARKET_CLOB_BOOK_BY_TOKEN_V1',
        'HYPERLIQUID_META_AND_ASSET_CTXS_V1')),
    CHECK (outcome IN (
        'RAW_COMMITTED','TRANSPORT_FAILED','TIMEOUT','RESPONSE_TOO_LARGE','HTTP_PROTOCOL_FAILED')),
    CHECK (retrieval_started_epoch_ms >= 0),
    CHECK (retrieval_completed_epoch_ms >= 0),
    CHECK (retrieval_elapsed_monotonic_ns >= 0),
    CHECK (clock_anomaly_evidence IN (0,1)),
    CHECK (
        (retrieval_completed_epoch_ms >= retrieval_started_epoch_ms AND clock_anomaly_evidence = 0)
        OR (retrieval_completed_epoch_ms <  retrieval_started_epoch_ms AND clock_anomaly_evidence = 1)
    ),
    CHECK (length(collector_commit_sha) = 40 AND collector_commit_sha NOT GLOB '*[^0-9a-f]*'),
    -- outcome-conditional nullability of capture_sequence / failure_code / failure_payload:
    CHECK (
        (outcome = 'RAW_COMMITTED'
            AND capture_sequence IS NOT NULL AND failure_code IS NULL AND failure_payload IS NULL)
        OR (outcome IN ('TRANSPORT_FAILED','TIMEOUT','RESPONSE_TOO_LARGE','HTTP_PROTOCOL_FAILED')
            AND capture_sequence IS NULL AND failure_code IS NOT NULL AND failure_payload IS NOT NULL)
    ),
    -- closed outcome -> failure_code mapping (RAW_COMMITTED has NULL failure_code; failures map 1:1):
    CHECK (
        (outcome = 'RAW_COMMITTED'        AND failure_code IS NULL)
        OR (outcome = 'TRANSPORT_FAILED'     AND failure_code = 'RAW_TRANSPORT_ERROR')
        OR (outcome = 'TIMEOUT'              AND failure_code = 'RAW_TIMEOUT')
        OR (outcome = 'RESPONSE_TOO_LARGE'   AND failure_code = 'RAW_RESPONSE_TOO_LARGE')
        OR (outcome = 'HTTP_PROTOCOL_FAILED' AND failure_code = 'RAW_HTTP_PROTOCOL_ERROR')
    ),
    -- composite provenance FK: a RAW_COMMITTED attempt must reference the SAME-provenance capture row.
    -- Failure attempts carry capture_sequence NULL; under MATCH SIMPLE a composite FK with any NULL
    -- referencing column is not enforced, so failure attempts remain allowed.
    FOREIGN KEY (capture_sequence, source_authority, request_target, collector_commit_sha)
        REFERENCES raw_capture_log (capture_sequence, source_authority, request_target, collector_commit_sha)
);

-- exactly one RAW_COMMITTED attempt per captured response:
CREATE UNIQUE INDEX IF NOT EXISTS ux_attempt_committed_capture
    ON raw_fetch_attempt_log (capture_sequence)
    WHERE outcome = 'RAW_COMMITTED';
```

`attempt_sequence` is ledger-local only — never market/domain identity. (A completed non-2xx response that commits is
`RAW_COMMITTED`, **not** `TRANSPORT_FAILED`.)

### 4.4 `raw_processing_journal`

```sql
CREATE TABLE IF NOT EXISTS raw_processing_journal (
    journal_sequence     INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_sequence     INTEGER NOT NULL,
    stage                TEXT    NOT NULL,
    attempt_ordinal      INTEGER NOT NULL,
    event_kind           TEXT    NOT NULL,
    recorded_at_epoch_ms INTEGER NOT NULL,
    failure_code         TEXT,
    failure_payload      TEXT,

    CHECK (stage IN ('OPTION_B_PROJECTION','S1_INGESTION')),
    CHECK (event_kind IN (
        'STARTED','SUCCEEDED','FAILED',
        'RECONCILIATION_REQUIRED','RECONCILED_SUCCEEDED','RECONCILED_FAILED')),
    CHECK (attempt_ordinal >= 1),
    CHECK (recorded_at_epoch_ms >= 0),
    CHECK (
        (event_kind IN ('FAILED','RECONCILED_FAILED')
            AND failure_code IS NOT NULL AND failure_payload IS NOT NULL)
        OR (event_kind IN ('STARTED','SUCCEEDED','RECONCILIATION_REQUIRED','RECONCILED_SUCCEEDED')
            AND failure_code IS NULL AND failure_payload IS NULL)
    ),
    FOREIGN KEY (capture_sequence) REFERENCES raw_capture_log (capture_sequence)
);

-- journal cardinality (§9): partial UNIQUE indexes per (capture, stage, attempt):
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_started
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind = 'STARTED';
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_ordinary_terminal
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind IN ('SUCCEEDED','FAILED');
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_reconciliation_required
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind = 'RECONCILIATION_REQUIRED';
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_reconciled_terminal
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind IN ('RECONCILED_SUCCEEDED','RECONCILED_FAILED');
```

### 4.5 Journal transition-order triggers (predecessor validation — CHECK/UNIQUE cannot enforce order)

```sql
-- any terminal or reconciliation requires a prior STARTED for the same (capture, stage, attempt):
CREATE TRIGGER IF NOT EXISTS trg_journal_requires_started
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind IN
    ('SUCCEEDED','FAILED','RECONCILIATION_REQUIRED','RECONCILED_SUCCEEDED','RECONCILED_FAILED')
 AND NOT EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind = 'STARTED')
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: event requires a prior STARTED');
END;

-- RECONCILIATION_REQUIRED only on an unresolved STARTED (no ordinary terminal present):
CREATE TRIGGER IF NOT EXISTS trg_journal_reconreq_requires_unresolved
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind = 'RECONCILIATION_REQUIRED'
 AND EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind IN ('SUCCEEDED','FAILED'))
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: RECONCILIATION_REQUIRED forbidden after an ordinary terminal');
END;

-- reconciled terminal only after RECONCILIATION_REQUIRED:
CREATE TRIGGER IF NOT EXISTS trg_journal_reconciled_requires_reconreq
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind IN ('RECONCILED_SUCCEEDED','RECONCILED_FAILED')
 AND NOT EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind = 'RECONCILIATION_REQUIRED')
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: reconciled terminal requires prior RECONCILIATION_REQUIRED');
END;

-- nothing may follow a final reconciled terminal:
CREATE TRIGGER IF NOT EXISTS trg_journal_no_event_after_reconciled_terminal
BEFORE INSERT ON raw_processing_journal
WHEN EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal
      AND event_kind IN ('RECONCILED_SUCCEEDED','RECONCILED_FAILED'))
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: no event may follow a reconciled terminal');
END;

-- once reconciliation has begun, only a reconciled terminal may close the ordinal: an ordinary
-- SUCCEEDED/FAILED is forbidden after RECONCILIATION_REQUIRED (closes the transition hole):
CREATE TRIGGER IF NOT EXISTS trg_journal_no_ordinary_terminal_after_reconreq
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind IN ('SUCCEEDED','FAILED')
 AND EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind = 'RECONCILIATION_REQUIRED')
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: ordinary terminal forbidden after RECONCILIATION_REQUIRED');
END;
```

`OUTCOME_UNKNOWN` is a **derived read-time status** for a `STARTED` with no terminal after restart; it is **never
stored** (a crashed process cannot observe its own crash).

---

## 4A. Append-Only Enforcement Triggers (§2)

```sql
CREATE TRIGGER IF NOT EXISTS trg_raw_capture_log_no_update
BEFORE UPDATE ON raw_capture_log
BEGIN SELECT RAISE(ABORT, 'raw_capture_log is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_raw_capture_log_no_delete
BEFORE DELETE ON raw_capture_log
BEGIN SELECT RAISE(ABORT, 'raw_capture_log is append-only: DELETE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS trg_raw_fetch_attempt_log_no_update
BEFORE UPDATE ON raw_fetch_attempt_log
BEGIN SELECT RAISE(ABORT, 'raw_fetch_attempt_log is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_raw_fetch_attempt_log_no_delete
BEFORE DELETE ON raw_fetch_attempt_log
BEGIN SELECT RAISE(ABORT, 'raw_fetch_attempt_log is append-only: DELETE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS trg_raw_processing_journal_no_update
BEFORE UPDATE ON raw_processing_journal
BEGIN SELECT RAISE(ABORT, 'raw_processing_journal is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_raw_processing_journal_no_delete
BEFORE DELETE ON raw_processing_journal
BEGIN SELECT RAISE(ABORT, 'raw_processing_journal is append-only: DELETE forbidden'); END;
```

`REPLACE`, UPSERT, `ATTACH`, destructive migration, and silent rewriting remain banned (§0/§3).

**These triggers are NOT tamper-proof and NOT tamper-evident against a privileged database owner.** They are
**fail-closed enforcement inside the conforming, ratified schema only**: any writer using the ratified schema with
`foreign_keys=ON` is prevented from mutating committed evidence. A privileged owner who drops triggers, opens a raw
connection, rewrites the file, or bypasses the schema is **outside this guarantee**; external privileged modification
is not defended against here.

---

## 5. Request Grammar & Header Ownership

### 5.1 Bounded full-match grammars (RV-3; rejected **before** network I/O)

- **`slug`** — full match `^[0-9a-z][0-9a-z-]{0,254}$` (1–255 bytes, lowercase ASCII alnum + hyphen, leading
  alphanumeric).
- **`token_id`** — full match `^[0-9]{1,80}$` (1–80 ASCII decimal digits).

Both must **reject** empty values, any Unicode/non-ASCII byte, whitespace, control bytes, the reserved delimiters
`/ ? & = # %`, **any** percent-encoding, and oversized input, **before** the request is constructed. (These charter
grammars are conservative bounded forms; the runtime full-match is authoritative and runs pre-network.)

### 5.2 Header ownership (no false "only application headers" claim)

- **Application-owned request headers:** `Accept: application/json` (GET and POST); `Content-Type: application/json`
  (POST only). These are the **only** headers the application sets.
- **Protocol-required, transport-generated headers** — e.g. `Host` and, for POST, `Content-Length` (and any
  framing/`Connection` header the HTTP client library emits) — are produced by the transport layer and appear on the
  wire. **The complete wire request is NOT only application-owned headers**; this charter does not claim otherwise.
- **Forbidden everywhere:** credentials, `Authorization`, `Cookie`, session state, authenticated CLOB, redirects,
  decompression, retry, fallback, and cache substitution. No credential/auth/signing/cookie header is ever set by the
  application or required by the allowlisted endpoints.

### 5.3 `failure_payload` Exact Encoding Law (RV-6 — the single, exact encoding)

`failure_payload` (the `raw_fetch_attempt_log` failure column) is **exactly** the deterministic UTF-8 JSON document
below. This is the **only** `failure_payload` encoding law in this charter. The raw-only runtime owns **only**
raw-fetch failure payloads; the future processing-journal failure taxonomy remains **separately blocked**.

**Logical payload:**

```json
{
  "exception_type": "<exact type(exc).__name__>",
  "args": [
    {"kind": "STRING", "value": "<sanitized exact string arg>"},
    {"kind": "NON_STRING", "type": "<exact type(arg).__name__>"}
  ]
}
```

**Rules:**

- `exception_type` is exactly `type(exc).__name__` — **never** module repr, object repr, traceback, cause (`__cause__`),
  context (`__context__`), `__dict__`, `id`, or memory address.
- Preserve exact **exception argument order**.
- For each arg, if `type(arg) is str`, emit exactly `{"kind":"STRING","value":sanitized_arg}`; **otherwise** emit
  **only** `{"kind":"NON_STRING","type":type(arg).__name__}`.
- **Never call `str()` or `repr()` on non-string args** (only `type(arg).__name__` is read).
- **Sanitize string args with one pinned substitution only** — the case-insensitive regex
  `(?<=\bat )0x[0-9a-f]{6,}(?=>)` replaced with `<memory-address-redacted>`. This redacts Python object-repr forms
  such as `object at 0xABCDEF>` **without** broadly deleting legitimate standalone hexadecimal evidence.
  **Do not redact arbitrary `0x…` values outside that exact object-repr context.**
- Serialize with exactly
  `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`; store the resulting
  **exact JSON text** directly in `failure_payload`, with **no trailing newline and no surrounding whitespace**.
- The serialization is **deterministic across repeated construction** from equal exception type/args.
- **RV-6 runtime validation** must, before INSERT, **parse the stored text, re-encode it under this exact law, and
  require byte-for-byte UTF-8 equality** — otherwise fail-fast (no attempt row).

---

## 6. `collector_commit_sha` — Caller-Supplied Opaque Provenance

- Defined **only** as **caller-supplied opaque provenance**: it satisfies the exact **lowercase-40-hex** shape (§4
  CHECK), is **stored verbatim**, and carries **no** cryptographic trust, code-authenticity, deployment-authenticity,
  or self-verification claim.
- It is **not** sourced from environment variables, Git subprocesses, network metadata, or self-referential runtime
  discovery; the caller passes it in as an argument (§7 API).
- **Independent artifact / build attestation is outside this charter.**

---

## 7. Future Runtime API Shape (docs-only; implements nothing)

Pinned **shape only** of the future one-shot runtime (built only after independent ratification, §10):

- **Module path (future):** `raw_acquisition/public_raw_capture.py` (new quarantined package; no Phase 6.3 label).
- **One public async acquisition callable (future):**

  ```python
  async def acquire_public_raw_capture(
      *,
      request: PublicSourceRequest,
      raw_ledger_path: str,
      s1_ledger_path: str,
      collector_commit_sha: str,
  ) -> RawCaptureCommitted:
      ...
  ```

  `s1_ledger_path` is a **mandatory exact-`str`** argument that exists **solely for caller-injected path-isolation
  checking**. Raw acquisition **never** opens, reads, imports, attaches, queries, mutates, or initializes S1; there is
  **no** global state, hidden config, environment lookup, or S1-package import. The preflight (§4B step 1) uses both
  paths only to **prove disjointness** before any network I/O: reject empty/NUL paths; canonicalize each path and its
  resolved parent / final-component target; when **both** paths exist, additionally apply same-file / device+inode
  equivalence; and reject equality, symlink alias, canonical collision, or same-file identity. S1 is never opened — it
  is only compared as a path.

- **Frozen, slotted, keyword-only request variants** (the three allowlisted authorities; closed sum
  `PublicSourceRequest`):

  ```python
  @dataclass(frozen=True, slots=True, kw_only=True)
  class PolymarketGammaMarketBySlugV1Request:   # GET gamma-api.polymarket.com/markets?slug=<slug>
      slug: str

  @dataclass(frozen=True, slots=True, kw_only=True)
  class PolymarketClobBookByTokenV1Request:      # GET clob.polymarket.com/book?token_id=<token_id>
      token_id: str

  @dataclass(frozen=True, slots=True, kw_only=True)
  class HyperliquidMetaAndAssetCtxsV1Request:    # POST api.hyperliquid.xyz/info  (fixed body)
      pass
  ```

- **Exact frozen result carrier** (RAW_CAPTURED handle; available **only after** successful local ledger commit):

  ```python
  @dataclass(frozen=True, slots=True, kw_only=True)
  class RawCaptureCommitted:
      capture_sequence: int
      attempt_sequence: int
      source_authority: str
      http_status: int
      response_body_sha256: str
  ```

- **Exact argument types:** `request` is exactly one of the three frozen variant types; `raw_ledger_path`,
  `s1_ledger_path`, and `collector_commit_sha` are each exact `str`.
- **Exact guard order (all guards run before any network I/O):**
  1. `type(request)` is one of the three exact variant classes — else
     `TypeError("request must be an exact PublicSourceRequest variant")`.
  2. `type(raw_ledger_path) is str` and `type(s1_ledger_path) is str` and `type(collector_commit_sha) is str` — else
     `TypeError("raw_ledger_path, s1_ledger_path, and collector_commit_sha must be exact str")`.
  3. `raw_ledger_path` and `s1_ledger_path` are non-empty and contain no NUL byte — else
     `ValueError("raw_ledger_path and s1_ledger_path must be non-empty NUL-free paths")`.
  4. `collector_commit_sha` matches `^[0-9a-f]{40}$` — else
     `ValueError("collector_commit_sha must be exactly 40 lowercase hex characters")`.
  5. variant payload grammar (§5.1): `slug` / `token_id` full-match — else
     `ValueError("slug must match ^[0-9a-z][0-9a-z-]{0,254}$")` /
     `ValueError("token_id must match ^[0-9]{1,80}$")`.
  6. ledger preflight (§4 / §4B): **S1 path-isolation** (`raw_ledger_path` vs `s1_ledger_path`: equality / symlink
     alias / canonical collision / same-file identity) + open + PRAGMA + init + fingerprint + FK +
     transaction-readiness — else a `RawLedgerPreflightError`.
- **Closed acquisition/ledger exception hierarchy:**

  ```
  RawAcquisitionError                      (base)
  ├── RawLedgerPreflightError              (pre-network; NO attempt row; NO result; fail-fast)
  │     ├── RawLedgerPathError             (path missing/invalid OR S1 alias/canonical collision)
  │     ├── RawLedgerPragmaError           (WAL/FULL/foreign_keys mismatch)
  │     ├── RawLedgerSchemaFingerprintError(stale / extra / missing column/index/trigger)
  │     └── RawLedgerReadinessError        (FK off / not transaction-ready)
  ├── RawTransportError                    (attempt began; commits a TRANSPORT_FAILED attempt row; NO result)
  ├── RawTimeoutError                      (commits a TIMEOUT attempt row; NO result)
  ├── RawResponseTooLargeError             (commits a RESPONSE_TOO_LARGE attempt row; NO result)
  ├── RawHttpProtocolError                 (commits an HTTP_PROTOCOL_FAILED attempt row; NO result)
  └── RawLedgerCommitError                 (a ledger transaction could not commit; NO durable row; NO result; fail-fast)
  ```

- **`RawLedgerCommitError` covers BOTH** (a) the **successful-response** capture/RAW_COMMITTED transaction failing to
  commit (§10 / RV-10) **and** (b) a **failure-attempt** transaction failing to commit: if committing a failure
  attempt row fails, **no failure row is claimed durable**, `RawLedgerCommitError` is raised, **no acquisition
  result** is returned, and **no retry occurs inside this callable**.
- **Which failures append a durable `raw_fetch_attempt_log` row:** `RawTransportError` / `RawTimeoutError` /
  `RawResponseTooLargeError` / `RawHttpProtocolError` — **iff** their single failure-attempt transaction commits (one
  failure row, exact mapped `failure_code`, `capture_sequence` NULL).
- **Which failures append no durable row:** all `RawLedgerPreflightError` subtypes and the input-guard
  `TypeError`/`ValueError` (raised before any network attempt); and `RawLedgerCommitError` (any ledger transaction —
  success or failure-attempt — that could not commit, so nothing is durable).
- **Which failures return no result:** **all** of them — `RawCaptureCommitted` is returned **only** after a
  successful local ledger commit (RAW_CAPTURED).
- The callable exposes **no** custom URL, arbitrary headers, retry count, timeout override, projection, S1 write,
  parser, scheduler, or authenticated input. **One invocation = at most one network request.**

---

## 4B. Idempotent Initialization & Schema Fingerprint (RV-9; runs before any network I/O)

Before **every** request, the runtime must, in order, **fail before network I/O** on any mismatch. **There is no
universal "run `CREATE … IF NOT EXISTS` then fingerprint" step**: the candidate is probed **empty-vs-existing first**,
and DDL executes **only** on a proven-empty candidate.

1. **path validation + S1 isolation** (caller-injected `raw_ledger_path` and `s1_ledger_path`): reject empty/NUL
   paths; canonicalize each path **and** its resolved parent / final-component target; when **both** paths exist,
   additionally apply **same-file / device+inode** equivalence; **reject** equality, symlink alias, canonical
   collision, or same-file identity ⇒ `RawLedgerPathError`. **S1 is never opened — only compared as a path.**
   (`raw_ledger_path` must also be creatable for the raw ledger itself.)
2. **database open**.
3. **candidate-catalog probe — BEFORE executing any schema DDL.** Run the exact closed catalog query (§4B.1 step 2)
   against the candidate to count its non-internal objects.
4. **empty-vs-existing decision:**
   - **`FIRST_INITIALIZATION`** (candidate has **zero** non-internal objects): apply the required **new-ledger
     PRAGMAs**; **in one local transaction** execute the **complete pinned DDL once** (the immutable `CREATE … IF NOT
     EXISTS` constants of §4 / §4A / §4.5); run the exact §4B.1 catalog + structural-PRAGMA + FK verification and the
     connection-state PRAGMA check (§4B.1 step 5); **commit initialization only if everything matches**, otherwise
     **roll back and claim no valid ledger** (`RawLedgerSchemaFingerprintError`).
   - **`EXISTING_LEDGER`** (candidate contains **any** non-internal object): execute **NO** `CREATE TABLE` / `CREATE
     INDEX` / `CREATE TRIGGER` statement; compare its **existing** exact catalog and structural-PRAGMA outputs against
     the fresh reference DB (§4B.1); **exact match may proceed**; **partial / stale / extra / missing / text-different
     ⇒ `RawLedgerSchemaFingerprintError` immediately** (the existing partial schema is **never completed or repaired
     by `IF NOT EXISTS`**).
5. **connection-state PRAGMA verification** (§4B.1 step 5): `journal_mode=wal`, `synchronous=2`, `foreign_keys=1`, and
   `PRAGMA foreign_key_check` returns no rows — checked against **literal required values**, not the reference DB.
6. **transaction-readiness preflight** (a no-op `BEGIN IMMEDIATE` / `ROLLBACK` succeeds, confirming writability).

`IF NOT EXISTS` may remain in the immutable DDL constants as **defensive syntax**, but those constants **execute only
in the proven-empty `FIRST_INITIALIZATION` branch**. A failed first initialization **rolls back without claiming a
valid ledger**.

### 4B.0 Path-isolation threat model (forensic limitation — binding)

The `s1_ledger_path` dependency injection and all stable-path checks (§4B step 1) are preserved. Their guarantee is
**explicitly scoped**:

- The path-isolation proof **assumes caller-owned, stable paths in the intended offline, single-tenant execution
  context**.
- A **privileged actor concurrently replacing path components, symlinks, mounts, files, or inodes between validation
  and the SQLite open** is **outside this charter's threat model** (a classic TOCTOU window).
- **No atomic OS-level lock, sandbox, anti-TOCTOU mechanism, or privileged-attacker resistance is claimed.** This is
  **not** described as protection against hostile concurrent filesystem mutation, and is **consistent** with the
  existing statement (§4A) that privileged raw-file / schema manipulation is outside the tamper guarantee.
- **Under stable paths**, equality, `realpath` alias, existing same-file / device+inode identity, and resolved-parent
  / final-component collision remain **fail-closed before network I/O**.

### 4B.1 Exact reference-catalog comparison algorithm (binding)

There is **no** "normalized schema set." The comparison is exact and text-literal:

1. Build a **private in-memory reference SQLite database** by executing the **exact pinned DDL constants** of §4 / §4A
   (and §4.5) under the **same `sqlite3` runtime** as the candidate ledger. The reference catalog is generated
   **fresh from the immutable DDL constants, never from the candidate database**.
2. Query **both** the reference and the candidate with the **exact same closed catalog query**:
   `SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name, tbl_name`.
3. Compare the resulting **exact ordered tuples `(type, name, tbl_name, sql)`** for every non-internal
   table/index/trigger/view, ordered by `(type, name, tbl_name)`. Exclude **only** names beginning with `sqlite_`.
4. Perform **no** whitespace, case, SQL-text, token, or AST normalization. **Reject** every **extra, missing,
   NULL-different, or text-different** tuple ⇒ `RawLedgerSchemaFingerprintError`.
5. **Structural reference comparison vs the in-memory reference DB** applies **only** to: the closed `sqlite_master`
   catalog tuples (step 2–3) and, per pinned table, the **exact ordered outputs** of `PRAGMA table_xinfo(<table>)`,
   `PRAGMA foreign_key_list(<table>)`, and `PRAGMA index_list(<table>)` + `PRAGMA index_xinfo(<index>)` — any
   difference ⇒ `RawLedgerSchemaFingerprintError`.
6. **Connection / database-state PRAGMAs are NOT compared against the private in-memory reference database.** The
   candidate is checked **directly against literal required values**: `journal_mode = wal`, `synchronous = 2`,
   `foreign_keys = 1`, and `PRAGMA foreign_key_check` returns **zero rows** — any difference ⇒ `RawLedgerPragmaError`
   (or, for `foreign_key_check` rows, `RawLedgerReadinessError`). **The private in-memory reference DB may report
   `journal_mode=memory`; that is irrelevant and is NEVER used as the expected-WAL authority.** For a **new empty**
   ledger, WAL is established during `FIRST_INITIALIZATION`; for an **existing** ledger, a **non-WAL durable mode is
   rejected**, never silently converted as schema repair. Connection-local `synchronous` and `foreign_keys` must be
   applied and verified **for the active connection**.
7. **Reject unknown views or any other non-internal object** present in the candidate but absent from the reference.

A semantically equivalent but **text-different** external schema is **intentionally rejected** — this is an
**exact-shape contract**, not a semantic-equivalence contract.

**No automatic migration, repair, downgrade, or permissive compatibility mode is allowed.** Exact behaviors:

| Situation | Pinned behavior |
|---|---|
| First initialization (probe finds **zero** non-internal objects) | `FIRST_INITIALIZATION`: new-ledger PRAGMAs + complete pinned DDL once **in one transaction**; §4B.1 verification; commit only if all matches, else roll back with **no valid-ledger claim**. |
| Repeated initialization (candidate already exact) | `EXISTING_LEDGER`: **no DDL executed**; §4B.1 exact comparison matches; proceed. |
| Partially initialized schema | `EXISTING_LEDGER` (non-empty): **no DDL executed**, **never completed/repaired by `IF NOT EXISTS`**; §4B.1 mismatch ⇒ `RawLedgerSchemaFingerprintError`; **fail before network**. |
| Stale schema (older/different ratified shape) | `EXISTING_LEDGER`: comparison mismatch ⇒ `RawLedgerSchemaFingerprintError`; **no migration**. |
| Extra / missing / text-different column, index, or trigger | `EXISTING_LEDGER`: comparison mismatch ⇒ `RawLedgerSchemaFingerprintError`. |
| Existing non-WAL durable journal mode | `RawLedgerPragmaError`; **rejected**, never silently converted as repair. |
| Failed first initialization | Roll back; **no valid ledger claimed**; `RawLedgerSchemaFingerprintError`. |
| S1-schema collision (path resolves to / aliases the S1 DB) | `RawLedgerPathError`; **fail before network**; never write into S1. |
| Path alias / canonical-path collision | `RawLedgerPathError`; **fail before network**. |

---

## 8. Forensic Clock Law & Exact Sampling Hooks

**Purpose:** deterministic forensic **cross-execution comparability** of the network-operation interval (this is **not**
"inter-ordinal timing consistency" — the raw-only runtime writes **no** processing-journal ordinal).

- **UTC wall-clock epoch** values (`retrieval_started_epoch_ms`, `retrieval_completed_epoch_ms`) carry **retrieval
  provenance only**.
- **Monotonic time** is the **sole** authority for elapsed-duration measurement; only the derived
  `retrieval_elapsed_monotonic_ns` is stored (the start/completed monotonic samples are runtime-internal).

### 8.1 Measured interval (binding)

**Preconditions (all complete before sampling begins):** all input guards complete; path isolation, ledger
initialization/fingerprint, and transaction-readiness preflight complete; the per-call transport/session object is
successfully constructed; **no network request has yet been invoked.**

**Start samples — in exact order, immediately before the single transport request invocation:**

1. `retrieval_started_epoch_ms = time.time_ns() // 1_000_000`
2. `retrieval_started_monotonic_ns = time.monotonic_ns()`
3. invoke the single request.

The measured interval **includes** DNS resolution, connect, TLS handshake, request transmission, response headers, and
response-body streaming. It **excludes** input/ledger preflight, session construction, hashing, header serialization,
and ledger writes.

### 8.2 Completion samples (binding)

**Successful / completed HTTP response** — after EOF confirms the final response entity byte has been read into the
bounded in-memory body, and **before** hashing, header-payload encoding, response-context cleanup, or ledger work,
sample in exact order:

1. `retrieval_completed_monotonic_ns = time.monotonic_ns()`
2. `retrieval_completed_epoch_ms = time.time_ns() // 1_000_000`

**Mapped transport / timeout / protocol failure** — sample the **same** completion pair (monotonic then epoch)
immediately upon entering the **first** mapped exception handler, **before** `failure_payload` construction or
failure-attempt ledger writing.

**`RESPONSE_TOO_LARGE`** — detection occurs when accepting the next chunk would make cumulative entity bytes exceed
**exactly 16 MiB**; **retain no partial body as RAW_CAPTURED**; sample the completion pair **immediately at that
detection point**, before discard/close/failure serialization.

### 8.3 Exact derivations (binding)

```
retrieval_elapsed_monotonic_ns = retrieval_completed_monotonic_ns - retrieval_started_monotonic_ns
clock_anomaly_evidence         = 1 if retrieval_completed_epoch_ms < retrieval_started_epoch_ms else 0
```

### 8.4 Rules (binding)

- **No** clamp, `max()`, substitution, wall-clock duration, fabricated completion, or timestamp reordering. Both
  original epoch readings are preserved **verbatim** (the §4 CHECK couples `clock_anomaly_evidence` to them; the schema
  does **NOT** require `retrieval_completed_epoch_ms >= retrieval_started_epoch_ms`).
- A **negative monotonic delta** is an unexpected **fail-fast runtime defect** and produces **no fabricated attempt
  row**.
- **Ledger / hash / header-encoding duration is NOT included** in the measured interval.
- The total **10000 ms** transport timeout **starts at the single request invocation** and applies to the measured
  network operation.
- **Preflight / input failures occur before this interval and write no attempt row.**
- An **unexpected session-construction failure before start sampling** remains **fail-fast and writes no invented
  attempt evidence**.
- The sampling law applies **consistently** to successful captures (`raw_capture_log`) **and** to recorded failed
  attempts (`raw_fetch_attempt_log`), both of which carry started/completed-epoch + derived elapsed + anomaly fields.

---

## 9. Journal Coherence & Retry Law

Enforced by §4.4 partial UNIQUE indexes + §4.5 predecessor triggers:

- exactly one `STARTED` per `(capture_sequence, stage, attempt_ordinal)`;
- at most one ordinary terminal (`SUCCEEDED`|`FAILED`); at most one `RECONCILIATION_REQUIRED`; at most one reconciled
  terminal (`RECONCILED_SUCCEEDED`|`RECONCILED_FAILED`);
- no terminal/reconciliation before `STARTED`; no `RECONCILIATION_REQUIRED` once an ordinary terminal exists; no
  reconciled terminal before `RECONCILIATION_REQUIRED`; no event after a reconciled terminal.
- `attempt_ordinal` begins at **1** (CHECK `>= 1`) and every per-ordinal uniqueness/transition rule above holds
  within each `(capture_sequence, stage, attempt_ordinal)`.

**No inter-ordinal retry policy is defined or claimed here.** Specifically:

- The **raw-only acquisition runtime authorized by this charter never writes `raw_processing_journal`** — that table
  is written only by the **future, separately-authorized projection / S1-ingestion runtime**.
- This charter enforces coherence **only within one `(capture, stage, attempt_ordinal)`**; it makes **no** claim about
  when or whether ordinal *N+1* may open.
- **Inter-ordinal retry authorization, known-`FAILED` retryability, S1-commit-uncertainty handling, and
  stage-specific failure taxonomy remain BLOCKED** for a separate projection / S1 charter.
- **No automatic or manual downstream retry is authorized here.**
- **RV-7 is redefined as a deferred downstream validation boundary** (owned by the future projection/S1 charter),
  **not** an implemented "gapless progression" claim.

Preserved: raw-evidence immutability; **no** distributed raw-to-S1 transaction; **no** automatic retry under S1-commit
uncertainty (S1 is frozen, no exactly-once key); projection / S1 / HYPOTHETICAL_OUTCOME runtime remains
**unauthorized** (the journal pins shape only).

---

## 10. Exact Raw-Capture Transaction Law & Pre-Commit Loss Window

For a **completed HTTP response** (status `100..599`):

1. capture exact headers/body (§4.1/§4.2);
2. compute the body integrity digest (`response_body_sha256` over the exact stored bytes; RV-1);
3. **begin one local raw-ledger transaction**;
4. append exactly one `raw_capture_log` row; retain its `current_capture_sequence` (= `lastrowid`);
5. append exactly one `RAW_COMMITTED` `raw_fetch_attempt_log` row referencing it (composite provenance FK, §4.3);
   retain its `current_attempt_sequence` (= `lastrowid`);
6. **RV-10 in-transaction reconciliation** — **inside the same transaction**, execute these **exact scoped
   parameterized** queries (no database-wide unscoped `COUNT` is permitted):

   ```sql
   SELECT COUNT(*)
   FROM raw_capture_log
   WHERE capture_sequence = ?
     AND source_authority = ?
     AND request_target = ?
     AND collector_commit_sha = ?;
   -- params (exact): (current_capture_sequence, current_source_authority,
   --                   current_request_target, current_collector_commit_sha)

   SELECT COUNT(*)
   FROM raw_fetch_attempt_log
   WHERE attempt_sequence = ?
     AND capture_sequence = ?
     AND source_authority = ?
     AND request_target = ?
     AND collector_commit_sha = ?
     AND outcome = 'RAW_COMMITTED'
     AND failure_code IS NULL
     AND failure_payload IS NULL;
   -- params (exact): (current_attempt_sequence, current_capture_sequence, current_source_authority,
   --                  current_request_target, current_collector_commit_sha)
   ```

   **Both scalar results must equal the exact integer `1`.** Anything else ⇒ **roll back**, raise
   `RawLedgerCommitError`, **no durable claim**, **no `RawCaptureCommitted` result**, **no retry** (no silent orphan
   accepted by the conforming runtime; a privileged direct SQL writer bypassing RV-10 is out of scope).
7. **commit**;
8. **only after successful commit** may the result be called **RAW_CAPTURED** and `RawCaptureCommitted` returned.

**This is NOT exactly-once acquisition.** Precisely:

- The ledger is initialized, fingerprint-verified, path-isolated from S1, writable, and transaction-ready **before**
  network I/O (§4B), **but** network response receipt and ledger commit are **not one atomic operation**.
- A process/OS failure **after response receipt but before commit** can leave **no durable `raw_capture_log` row and
  no durable `raw_fetch_attempt_log` row**.
- **No RAW_CAPTURED claim exists without commit.** This **unobservable pre-commit loss window is acknowledged**; the
  system makes **no exhaustive-capture and no exactly-once claim**.
- A later refetch **must never be represented as the lost original response** (it is a new observation with its own
  capture row).
- **Reconciliation (§9) applies only where durable evidence exists.** An entirely uncommitted response **cannot** be
  reconciled — there is nothing durable to reconcile.
- Raw capture, once committed, is **permanent** and is never rolled back because any future projection, S1, outcome,
  calibration, or paper step fails. **No raw↔S1 distributed transaction or exactly-once claim exists.**

---

## 11. Explicit Unresolved Boundaries (preserved as BLOCKED)

- **B-1** `gross_magnitude` / `unit` authority; **B-2** event-time authority; **B-3** `venue` / `pair` canonical
  mapping; **B-4** real fee/cost/slippage authority.
- **Polymarket resolved-market / outcome source authority** (later HYPOTHETICAL_OUTCOME source amendment).
- **Cross-ledger S1 idempotency / exactly-once.**
- **Automated scheduler / poller / daemon.**
- **Chainlink / source-basis alignment.**

---

## 12. Status, Scope & Post-State

This docs charter builds no collector and performs no network call. After commit, before external review:

- **Charter:** BUILT / RATIFIABLE / **UNRATIFIED**, pending independent Gemini and Codex review.
- **Raw acquisition runtime:** **BLOCKED.**
- **Data collection:** **NOT STARTED.**
- **Option-B projection / S1 ingestion:** **BLOCKED.**
- **HYPOTHETICAL_OUTCOME:** **UNBUILT + BLOCKED.**
- **Calibration:** **BLOCKED.** **Phase 7.1 / 7.2 / 8.1:** **BLOCKED.**
- **Capacity:** **0.**

**Only after independent Gemini + Codex ratification** may **one** raw-only, one-shot acquisition runtime/TDD slice
become **ELIGIBLE**, implementing only `public request → exact raw bytes → isolated raw ledger`. The system and data
collection are **not** called ready. This charter modifies **only** the single existing docs file
`docs/handoff/post_phase6_2_public_source_authority_raw_capture_ledger_exact_shape_charter.md`; it changes no
`phase6_1/`, `phase6_1_s1_storage/`, `phase6_2_shadow_intent/`, S1/S5, frozen DTOs, `config.py`, `data/`, other
charter, or lock test.

**Conclusion:** the public source authority is the closed three-variant allowlist with HTTPS/cert-verified,
redirect-free, credential-free, bytes-only one-shot transport; the raw ledger is an S1-isolated WAL/FULL/foreign_keys
SQLite medium whose **executable DDL** enforces (via CHECK/FK/partial-UNIQUE/predecessor-trigger) the closed
source-authority/method/host/target/body coupling and exact Hyperliquid body bytes, GET-empty-body, `http_status`
`100..599`, lowercase-64/40 SHA shapes, BLOB storage classes, outcome-conditional `capture_sequence`/`failure_*`
nullability, both capture/attempt foreign keys, non-negative sequences/ordinals/timestamps/durations, and the full
journal cardinality + transition order — with the residue (digest equality, header-blob structure, exact slug/token
grammar, monotonic-source genuineness, anomaly-derivation, the §5.3 exact `failure_payload` JSON encoding law,
gapless ordinals, transport limits,
and the schema-fingerprint/PRAGMA/path-isolation preflight) explicitly assigned to **fail-fast runtime validation
(RV-1…RV-9)**; append-only `BEFORE UPDATE`/`BEFORE DELETE` triggers fail-closed **inside the conforming schema only
(not tamper-proof, not tamper-evident against a privileged owner)**; the future runtime API is a docs-only one-shot
async callable over three frozen kw-only request variants returning a frozen `RawCaptureCommitted` only after local
commit, with a closed exception hierarchy distinguishing pre-network preflight (no row), committed failure attempts
(one failure row), and commit failure (no durable claim); the forensic clock law records backward wall-clocks as
anomaly evidence without rejection while monotonic ns measures duration; `collector_commit_sha` is caller-supplied
opaque lowercase-40-hex provenance with no authenticity claim and no env/subprocess/network sourcing (build
attestation out of scope); and the law explicitly **disclaims exactly-once**, acknowledges the unobservable
pre-commit loss window, forbids refetch-as-original, and confines reconciliation to durable evidence. **Charter BUILT
/ RATIFIABLE / UNRATIFIED; raw acquisition, projection, S1 ingestion, HYPOTHETICAL_OUTCOME, calibration, and Phases
7.1/7.2/8.1 all BLOCKED; data collection NOT STARTED; capacity 0; only independent ratification makes one raw-only
one-shot slice eligible — the system is not ready.**
