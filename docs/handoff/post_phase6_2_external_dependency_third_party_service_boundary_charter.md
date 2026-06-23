# Post-Phase 6.2 External Dependency / Third-Party Service Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements for future external dependencies and
  third-party services (exchanges, market-data APIs, news feeds, model providers, cloud providers,
  GitHub, messaging / notification services, and any future dependency). It **calls no external
  service**, **adds no dependency**, **implements nothing**, and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It **does not inspect** secrets, env vars, credentials, tokens, cookies, API keys, or account
  balances, and **calls no external service**.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, calibration / trading /
  actionability, paper / canary / live, routing, orders, fills, cancels, sizing, allocation,
  capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Secrets / Credentials / Access Authority Boundary Charter: RATIFIED at `bc145f5`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Halt / restart / rollback / recovery: BLOCKED.**
- **Secrets / credentials / wallet / signing / capital authority: BLOCKED.**
- **External dependency / third-party service authority: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `bc145f52ff130bfc35aa84ee87ba3bf60138541b`.
- Parent chain:
  - `bc145f52ff130bfc35aa84ee87ba3bf60138541b` = **RATIFIED** Secrets / Credentials / Access
    Authority Boundary Charter.
  - `89fed1fdb88676b7d7bd5533e4c7571ce7ef5526` = **RATIFIED** Halt / Restart / Rollback / Recovery
    Boundary Charter.
  - `1a35aeafc256811c4849b5b6b46a51508f65461d` = **RATIFIED** Operator Authorization / Human
    Command Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **external dependency / third-party service** boundary. It
  does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **dependency boundary**: **reachability or availability of a third-party
  service must never imply authority, actionability, or capacity**.
- It exists to make **"HTTP 200 ⇒ clean data", "API key ⇒ trade authority", "news ⇒ signal", and
  "provider uptime ⇒ activation" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only External Dependency Boundary

1. This charter defines **requirements only**.
2. It **does not call** external services.
3. It **does not add** dependencies.
4. It **does not authorize** runtime, S1 append, trading, paper / canary / live, routing, or
   capacity.

### Gate B — Preconditions Before Any Future Third-Party Integration Work

Future third-party integration work requires:

1. Secrets / Credentials / Access Authority boundary **ratified**;
2. Operator Authorization / Human Command boundary **ratified**;
3. Paper / Canary / Live firewall **ratified**;
4. an **exact future operator command**;
5. the **exact service name and endpoint class**;
6. the **exact intended access mode** — offline-docs, read-only, write, signing, notification, or
   trading-capable;
7. the **exact allowed data classes**;
8. the **exact forbidden actions**;
9. the **explicit S1 append state**;
10. the **explicit capacity state**;
11. the **explicit paper / canary / live state**;
12. **DIRTY state blocks implementation** unless the task is **documentation-only**.

### Gate C — Service Class Taxonomy

Future classification must define a closed taxonomy covering at least:

- **exchange / CLOB APIs**;
- **market-data APIs**;
- **news feeds**;
- **model providers**;
- **cloud / hosting providers**;
- **GitHub / source-control providers**;
- **notification providers**;
- **observability providers**;
- **payment / billing providers**;
- **wallet / signing providers**;
- **operator-control interfaces**;
- **local-only mock / stub services**.

Each service must map to exactly one class; an unclassifiable service is treated as the most
restrictive applicable class and **fails closed**.

### Gate D — Reachability Is Not Authority

Future systems must prove:

- **HTTP 200 does not imply data validity.**
- **API availability does not imply authorization.**
- **API key presence does not imply trading authority.**
- **Model response does not imply operator command.**
- **News feed access does not imply signal / actionability.**
- **Cloud availability does not imply runtime authorization.**
- **GitHub availability does not imply deploy authority.**
- **Notification delivery does not imply incident resolution.**
- **Market-data availability does not imply capacity.**

### Gate E — Third-Party Data Provenance Rules

Future external data must be:

- **source-authority-bound**;
- **timestamped with explicit authority** (source event time, not retrieval time, where the
  distinction matters);
- **commit / base-SHA-bound** when used in validation or replay;
- **artifact-hash-bound** when persisted;
- **deterministic where replayed**;
- **non-secret-preserving**;
- **separated by service class**;
- **never identified by SQLite `rowid` / `append_sequence`** as a domain identity (identity derives
  from content / provenance hashes only);
- **rejected or quarantined if provenance is missing or ambiguous**.

### Gate F — News / Model / Inference Firewall

1. **News feeds require a separate future charter** before use.
2. **Model-provider outputs require a separate future charter** before use.
3. **Inference outputs must not create** signal, ranking, advice, trading, routing, or capacity.
4. **Latency-arbitrage / news-reaction systems are out of scope here and BLOCKED.**
5. Any future news / model integration must be **offline / read-only until separately authorized**.
6. **No agent / model / scheduler / background process may convert news or inference into
   actionability.**

### Gate G — External Failure and Degradation Doctrine

Future systems must **fail closed** for:

- non-2xx response;
- timeout;
- rate limit;
- schema drift;
- stale data;
- timestamp ambiguity;
- provider mismatch;
- authentication ambiguity;
- partial response;
- provider outage;
- inconsistent duplicate provider data;
- undocumented endpoint behavior.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Forbidden Paths

The following automatic transitions are **explicitly forbidden**:

- `HTTP 200 ⇒ clean data`
- `API key presence ⇒ service authority`
- `news feed ⇒ signal`
- `model output ⇒ trade`
- `market-data availability ⇒ capacity`
- `GitHub push ⇒ deploy / runtime activation`
- `cloud availability ⇒ production runtime`
- `notification success ⇒ incident resolution`
- `provider uptime ⇒ S1 append`
- `external service success ⇒ paper / canary / live`
- `third-party score ⇒ routing / order / capital action`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** dependency installation.
3. **No** external calls.
4. **No** service credentials.
5. **No** endpoint probing.
6. **No** monitoring integration.
7. **No** alerting integration.
8. **No** S1 append.
9. **No** production stream.
10. **No** signal / trade / order / routing / capital output.
11. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. Future third-party service **TDD** requires a separate explicit operator command.
2. Future third-party service **implementation** requires a separate explicit operator command.
3. Future **news / model / exchange / cloud integration** requires a separate explicit charter and
   command.
4. Ratifying this charter **does not** make implementation eligible by itself.
5. **Clean state does not auto-advance.**
6. **Capacity remains 0.**

---

## Section 4 — Service Class Authority Ledger (template, to be completed later)

No service is asserted now. A future third-party-service charter / implementation must map each
class into this structure (documentation-only here):

| Service class | Access mode | Implies (none unless chartered) | Operator-gated | Status |
|---------------|-------------|---------------------------------|----------------|--------|
| exchange_clob_api | PENDING | nothing | PENDING | read-only ratified for raw collection only |
| market_data_api | PENDING | nothing | PENDING | read-only ratified for raw collection only |
| news_feed | PENDING | nothing | PENDING | BLOCKED |
| model_provider | PENDING | nothing | PENDING | BLOCKED |
| cloud_hosting | PENDING | nothing | PENDING | PENDING |
| github_scm | PENDING | nothing | PENDING | PENDING |
| notification | PENDING | nothing | PENDING | PENDING |
| observability | PENDING | nothing | PENDING | PENDING |
| payment_billing | PENDING | nothing | PENDING | BLOCKED |
| wallet_signing | PENDING | nothing | PENDING | BLOCKED |
| operator_control | PENDING | nothing | PENDING | PENDING |
| local_mock_stub | offline | nothing | n/a | PENDING |

The only currently-ratified external reachability is the **read-only raw collection** of the two
ratified public endpoints (Hyperliquid l2Book BTC, Polymarket CLOB YES-token) under the active
bounded run; all other service authority remains **BLOCKED** until separately chartered.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this external dependency / third-party service boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command: a separate third-party-service TDD charter, then a
   RED→GREEN implementation.
4. News / model / exchange-write / cloud-deploy integration each remain behind their **own**
   separate charters and operator commands.

## Post-state

- External Dependency / Third-Party Service Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Secrets / credentials / wallet / signing / capital authority: **BLOCKED**.
- External dependency / third-party service authority: **BLOCKED**.
- Capacity: **0**.
