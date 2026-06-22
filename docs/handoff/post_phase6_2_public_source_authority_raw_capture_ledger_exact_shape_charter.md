# Post-Phase 6.2 — Public Source-Authority & Raw-Capture-Ledger Exact-Shape Charter

> **This is a docs-only exact-shape charter.** It pins the closed public-source authority allowlist, the exact
> one-shot transport contract, the isolated raw-ledger storage medium, and the exact append-only ledger/journal
> schemas + recovery law for the **future, separately-authorized** raw-only one-shot acquisition runtime. It **builds
> nothing and authorizes nothing executable**: no runtime code, no collector, no tests, no fixtures, no adapter, no
> config, no locks, no package exports, no tracking files, no generated files, no pytest, no graphify, and **no
> network call**. Committing it performs **no data acquisition** and builds **no collector**. It is the single next
> docs-only gate named by
> `docs/handoff/post_phase6_2_read_only_real_world_evidence_acquisition_boundary_charter.md` (§8 step 2) and is
> subordinate to that charter, the Phase 6.2 Slice-G closeout charter, the Phase 6.1 / Phase 5 chain, and
> `CLAUDE.md`; where any conflict arises, those govern. **This is not a Phase 6.3 work item and bears no Phase 6.3
> label.**

**Base:** `2617852fefbce64a0576f36730a828c426c6bc13`

---

## 1. Closed Public-Source Authority (exactly three variants)

The acquisition runtime may issue requests to **exactly three** closed source-authority variants. No fourth variant,
no free-form URI/host/path/method/query-name/request-body, ever.

### `POLYMARKET_GAMMA_MARKET_BY_SLUG_V1`
- **Method:** `GET`
- **Scheme:** `https`
- **Host:** `gamma-api.polymarket.com`
- **Path:** `/markets`
- **Query:** exactly one caller-supplied `slug` parameter.
- **No wall-clock slug generation.**
- **No closed-market / resolution authority** — that requires a later HYPOTHETICAL_OUTCOME source amendment (§9).

### `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1`
- **Method:** `GET`
- **Scheme:** `https`
- **Host:** `clob.polymarket.com`
- **Path:** `/book`
- **Query:** exactly one caller-supplied `token_id` parameter.

### `HYPERLIQUID_META_AND_ASSET_CTXS_V1`
- **Method:** `POST`
- **Scheme:** `https`
- **Host:** `api.hyperliquid.xyz`
- **Path:** `/info`
- **Request body bytes (exact):** `b'{"type":"metaAndAssetCtxs"}'`

### Closed rules (binding)
- **No** free-form URI, host, path, method, query name, or request body — each request is exactly one of the three
  variants above.
- Caller-supplied `slug` / `token_id` values must be **non-empty bounded ASCII** and must **reject** `/`, `?`, `&`,
  `=`, `#`, `%`, control bytes, whitespace, and any Unicode (non-ASCII) byte.
- **HTTPS and certificate verification are mandatory.**
- **Redirects are forbidden** (no automatic following; a redirect status is a completed HTTP response, §2).
- **Credential / auth / signing / cookie / session / private / account / order headers are forbidden.**
- For **GET**, only `Accept: application/json` is allowed.
- For **POST**, `Content-Type: application/json` is additionally required (with `Accept: application/json`).
- **No** Data API, WebSocket, Chainlink, account endpoint, exchange (trading) endpoint, or authenticated CLOB
  surface.
- **No import or reuse of legacy `data/` modules** in the first runtime.
- The runtime **captures response bytes only** — **no** JSON parsing, normalization, field mapping, event-time
  extraction, gross-edge calculation, Option-B construction, or S1 writing.

---

## 2. Exact Transport Contract

- **One callable execution equals exactly one HTTP request.**
- **Connect timeout:** `3000 ms`.
- **Total timeout:** `10000 ms`.
- **Maximum response entity:** `16 MiB` (16 × 1024 × 1024 = 16777216 bytes); exceeding it is `RESPONSE_TOO_LARGE`
  (§5), not a partial-body success.
- **TLS verification enabled.**
- **Automatic content decompression disabled.**
- **No** retry, fallback, cache, stale substitution, alternate endpoint, or partial-body success.
- **Stored body** is the **exact response entity bytes after HTTP transfer framing removal but before** content
  decoding, decompression, JSON decoding, Unicode decoding, or normalization.
- **Every completed HTTP response, including non-2xx, may become RAW_CAPTURED** if its raw-ledger transaction commits.
- **RAW_CAPTURED means only "exact response evidence durably committed"** — it does **not** mean HTTP success, valid
  JSON, usable market data, or downstream eligibility.
- **Transport failure before a completed response creates no raw-capture row.**
- **Ledger-commit failure creates no RAW_CAPTURED claim.**

---

## 3. Isolated Storage Medium

The raw ledger is a **separate caller-owned SQLite database path**, distinct from S1:

- It **must not equal, alias, attach, replace, or share** the S1 database path.
- `PRAGMA journal_mode=WAL`.
- `PRAGMA synchronous=FULL`.
- `PRAGMA foreign_keys=ON`.
- **No** `ATTACH DATABASE`.
- **No** `UPDATE`, `DELETE`, `REPLACE`, UPSERT, destructive DDL, vacuum-based rewriting, or any mutation of committed
  evidence.
- All connections / resources are **owned and closed by the one-shot acquisition boundary**.
- **S1 remains frozen and untouched** (no field, schema, pragma, or path change to the S1 durable medium).

---

## 4. Exact `raw_capture_log` Schema

```sql
CREATE TABLE raw_capture_log (
    capture_sequence            INTEGER PRIMARY KEY,
    source_authority            TEXT    NOT NULL,
    http_method                 TEXT    NOT NULL,
    request_scheme              TEXT    NOT NULL,
    request_host                TEXT    NOT NULL,
    request_target              TEXT    NOT NULL,
    request_body                BLOB    NOT NULL,
    retrieval_started_epoch_ms  INTEGER NOT NULL,
    retrieval_completed_epoch_ms INTEGER NOT NULL,
    http_status                 INTEGER NOT NULL,
    response_headers_payload    BLOB    NOT NULL,
    response_body               BLOB    NOT NULL,
    response_body_sha256        TEXT    NOT NULL,
    collector_commit_sha        TEXT    NOT NULL
);
```

Columns are in **exactly** this order.

### Required invariants
- `source_authority` is **exactly one** of the three closed tokens (`POLYMARKET_GAMMA_MARKET_BY_SLUG_V1`,
  `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1`, `HYPERLIQUID_META_AND_ASSET_CTXS_V1`).
- `http_method` / `request_scheme` / `request_host` / `request_target` (path + any query) / `request_body` **must
  match** the variant pinned in §1 for that `source_authority`.
- For a **GET** variant, `request_body` is **exact empty bytes** (`b''`).
- `retrieval_started_epoch_ms` and `retrieval_completed_epoch_ms` are **exact non-negative integers**, with
  `retrieval_completed_epoch_ms >= retrieval_started_epoch_ms`.
- `http_status` is an integer in **`100..599`** inclusive.
- `response_body` **may be empty** but is always **exact bytes** (no NULL).
- `response_body_sha256` is the **lowercase 64-character SHA-256 hex** over the **exact stored `response_body`**.
- `collector_commit_sha` is **lowercase 40-character Git SHA text**.
- `capture_sequence` is **medium-local append order / reference only** — **never** market/domain identity and
  **never** a deduplication key.

### `response_headers_payload` exact encoding
A length-prefixed, order-preserving binary blob:
- **unsigned 32-bit big-endian** header-pair **count**;
- then, for **each** header in **received order**:
  - **unsigned 32-bit big-endian** name-byte **length**, then the **exact name bytes**;
  - **unsigned 32-bit big-endian** value-byte **length**, then the **exact value bytes**;
- **duplicate headers and original order are preserved**;
- **no** Unicode decoding, case folding, sorting, dictionary conversion, or comma joining.

---

## 5. Separate Fetch-Attempt Ledger (`raw_fetch_attempt_log`)

Downstream processing state is **not** overloaded into fetch attempts. Exact append-only table:

```sql
CREATE TABLE raw_fetch_attempt_log (
    attempt_sequence            INTEGER PRIMARY KEY,
    source_authority            TEXT    NOT NULL,
    request_target              TEXT    NOT NULL,
    retrieval_started_epoch_ms  INTEGER NOT NULL,
    retrieval_completed_epoch_ms INTEGER NOT NULL,
    outcome                     TEXT    NOT NULL,
    capture_sequence            INTEGER,
    failure_code                TEXT,
    failure_payload             TEXT,
    collector_commit_sha        TEXT    NOT NULL
);
```

### Closed `outcome` vocabulary
`RAW_COMMITTED`, `TRANSPORT_FAILED`, `TIMEOUT`, `RESPONSE_TOO_LARGE`, `HTTP_PROTOCOL_FAILED`.

### Rules
- `RAW_COMMITTED` requires a **non-null `capture_sequence`** referencing `raw_capture_log`.
- **Every failure outcome** (`TRANSPORT_FAILED`, `TIMEOUT`, `RESPONSE_TOO_LARGE`, `HTTP_PROTOCOL_FAILED`) requires
  **`capture_sequence` NULL**.
- A completed HTTP response with **non-2xx** status is **`RAW_COMMITTED`** if its bytes commit — it is **not**
  `TRANSPORT_FAILED`.
- The successful `raw_capture_log` row and its `RAW_COMMITTED` `raw_fetch_attempt_log` row are written in **one local
  SQLite transaction** (§7).
- If the SQLite transaction itself **cannot commit**, **no durable attempt/capture claim is made**; the exception
  **propagates fail-fast**.
- `failure_payload` is a **canonical, address-free** representation of the **exact exception type plus its string
  args** — **no** `repr`, traceback, memory address, secret, request header, or fabricated explanation.
- `attempt_sequence` is **ledger-local only** — never market/domain identity.

---

## 6. Separate Downstream Processing Journal (`raw_processing_journal`)

Exact append-only table (shape only — **authorizes no projection or S1 runtime**):

```sql
CREATE TABLE raw_processing_journal (
    journal_sequence     INTEGER PRIMARY KEY,
    capture_sequence     INTEGER NOT NULL,
    stage                TEXT    NOT NULL,
    attempt_ordinal      INTEGER NOT NULL,
    event_kind           TEXT    NOT NULL,
    recorded_at_epoch_ms INTEGER NOT NULL,
    failure_code         TEXT,
    failure_payload      TEXT,
    FOREIGN KEY (capture_sequence) REFERENCES raw_capture_log (capture_sequence)
);
```

### Closed `stage` vocabulary
`OPTION_B_PROJECTION`, `S1_INGESTION`.

### Stored `event_kind` vocabulary
`STARTED`, `SUCCEEDED`, `FAILED`, `RECONCILIATION_REQUIRED`, `RECONCILED_SUCCEEDED`, `RECONCILED_FAILED`.

### Rules
- `capture_sequence` is a **foreign key** to `raw_capture_log` and remains **ledger-local** (never domain identity).
- `attempt_ordinal` is an integer **`>= 1`**.
- Every stage attempt **begins with exactly one `STARTED` event**.
- **At most one** ordinary terminal `SUCCEEDED` **or** `FAILED` event exists per `(capture_sequence, stage,
  attempt_ordinal)`.
- A `STARTED` without a terminal event **after restart** is evaluated as the **derived** status `OUTCOME_UNKNOWN`.
- **`OUTCOME_UNKNOWN` is never written** as if the crashed process observed its own crash (it is a derived read-time
  status, not a stored event).
- Recovery appends **`RECONCILIATION_REQUIRED`**.
- **Automatic retry is forbidden while reconciliation is unresolved.**
- Projection retry must **consume the same stored `response_body` bytes** — **no network refetch substitution**.
- **S1-commit uncertainty cannot be automatically retried** because S1 is frozen and **no distributed transaction /
  exactly-once key exists**.
- Reconciliation outcome is appended as **`RECONCILED_SUCCEEDED`** or **`RECONCILED_FAILED`**.
- **No row is updated or deleted.**
- This charter defines the **journal shape only**; it **does not authorize** projection or S1 runtime.

---

## 7. Exact Raw-Capture Transaction Law

For a **completed HTTP response** (any status `100..599`):

1. capture the **exact headers / body** (§2/§4 encodings);
2. compute the **body integrity digest** (`response_body_sha256` over the exact stored `response_body`);
3. **begin one local raw-ledger transaction**;
4. append **exactly one** `raw_capture_log` row;
5. append **exactly one** `RAW_COMMITTED` `raw_fetch_attempt_log` row referencing it (`capture_sequence` non-null);
6. **commit**;
7. **only after successful commit** may the result be called **RAW_CAPTURED**.

- **Raw capture is permanent and is never rolled back** because any future projection, S1, outcome, calibration, or
  paper step fails.
- **No raw↔S1 distributed transaction and no exactly-once claim exists.**
- A **transport failure before a completed response** or a **failed ledger commit** yields **no RAW_CAPTURED** (a
  failure attempt row with `capture_sequence` NULL on a committed transaction, or a fail-fast propagated exception if
  the transaction itself cannot commit).

---

## 8. Runtime & Roadmap Status

**This docs charter builds no collector and performs no network call.**

After commit, before external review:

- **Charter:** BUILT / RATIFIABLE / **UNRATIFIED**.
- **Raw acquisition runtime:** **BLOCKED.**
- **Data collection:** **NOT STARTED.**
- **Option-B projection / S1 ingestion:** **BLOCKED.**
- **HYPOTHETICAL_OUTCOME:** **BLOCKED.**
- **Calibration:** **BLOCKED.**
- **Phase 7.1 / 7.2 / 8.1:** **BLOCKED.**
- **Capacity:** **0.**

**Only after independent Gemini + Codex ratification** may **one** raw-only, one-shot acquisition runtime/TDD slice
become **ELIGIBLE**. That future runtime may implement **only**:

```
public request -> exact raw bytes -> isolated raw ledger
```

It **may not** implement projection, S1, outcomes, calibration, paper, execution, routing, wallet, orders, or
capacity.

---

## 9. Explicit Unresolved Boundaries (preserved as BLOCKED)

- **B-1** — `gross_magnitude` / `unit` authority.
- **B-2** — event-time authority.
- **B-3** — `venue` / `pair` canonical mapping.
- **B-4** — real fee / cost / slippage authority.
- **Polymarket resolved-market / outcome source authority** (the later HYPOTHETICAL_OUTCOME source amendment).
- **Cross-ledger S1 idempotency / exactly-once.**
- **Automated scheduler / poller / daemon.**
- **Chainlink / source-basis alignment.**

---

## 10. Frozen / Unchanged Surfaces

This charter changes **none** of: `phase6_1/`; `phase6_1_s1_storage/` and the S1 medium; `phase6_2_shadow_intent/`;
S1 / S5; the frozen DTOs; `config.py`; any `data/` module; existing charters; lock tests; capacity boundaries;
analytics/export boundaries. It adds **only** the single new docs file
`docs/handoff/post_phase6_2_public_source_authority_raw_capture_ledger_exact_shape_charter.md`.

---

**Conclusion:** the public source authority is a **closed allowlist of exactly three variants**
(`POLYMARKET_GAMMA_MARKET_BY_SLUG_V1` GET `https://gamma-api.polymarket.com/markets?slug=…`;
`POLYMARKET_CLOB_BOOK_BY_TOKEN_V1` GET `https://clob.polymarket.com/book?token_id=…`;
`HYPERLIQUID_META_AND_ASSET_CTXS_V1` POST `https://api.hyperliquid.xyz/info` with body
`b'{"type":"metaAndAssetCtxs"}'`), HTTPS+cert-verified, redirect-free, credential-free, JSON-`Accept`-only (POST adds
`Content-Type: application/json`), with bounded-ASCII slug/token rejection of `/ ? & = # %`, control, whitespace, and
Unicode — and **no** legacy `data/` reuse, **no** parsing, and **bytes-only** capture. One callable execution is one
HTTP request (connect 3000 ms, total 10000 ms, ≤16 MiB, TLS on, auto-decompress off, no retry/fallback/cache);
**every completed response including non-2xx may become RAW_CAPTURED only on raw-ledger commit**, where RAW_CAPTURED
means only durably-committed exact-byte evidence. Storage is an **isolated WAL/FULL/foreign_keys SQLite medium**
disjoint from S1, with **no** UPDATE/DELETE/REPLACE/UPSERT/ATTACH/vacuum mutation. The exact append-only schemas are
`raw_capture_log` (14 ordered columns incl. length-prefixed order-preserving `response_headers_payload`,
lowercase-64 `response_body_sha256`, lowercase-40 `collector_commit_sha`, `capture_sequence` append-order-only),
`raw_fetch_attempt_log` (closed outcomes `RAW_COMMITTED` / `TRANSPORT_FAILED` / `TIMEOUT` / `RESPONSE_TOO_LARGE` /
`HTTP_PROTOCOL_FAILED`; `RAW_COMMITTED`⇒non-null `capture_sequence`, failures⇒NULL; non-2xx-on-commit is
`RAW_COMMITTED`; address-free `failure_payload`), and `raw_processing_journal` (closed stages `OPTION_B_PROJECTION` /
`S1_INGESTION`; event kinds `STARTED` / `SUCCEEDED` / `FAILED` / `RECONCILIATION_REQUIRED` / `RECONCILED_SUCCEEDED` /
`RECONCILED_FAILED`; derived-only `OUTCOME_UNKNOWN`; no-auto-retry-while-unreconciled; same-bytes replay; no S1
auto-retry; append-only). The raw-capture transaction law writes one capture row + one `RAW_COMMITTED` attempt row in
one local transaction, names RAW_CAPTURED only post-commit, keeps raw evidence permanent, and claims **no** raw↔S1
distributed transaction or exactly-once. **Charter BUILT / RATIFIABLE / UNRATIFIED; raw acquisition runtime, Option-B
projection, S1 ingestion, HYPOTHETICAL_OUTCOME, calibration, and Phases 7.1/7.2/8.1 all BLOCKED; data collection NOT
STARTED; capacity 0. Committing this charter builds no collector and acquires no data; only independent Gemini +
Codex ratification makes one raw-only one-shot acquisition slice eligible.**
