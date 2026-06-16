# Council Inventory and LLM Decision De-Risk Audit Gate

<!-- FRAMING-START -->
## 1. Current status

- This is an **inventory / audit only** pass. It enumerates the council / multi-agent / decision
  layer and classifies its connection to deterministic trade/risk/order paths.
- **No code removal** is authorized by this gate.
- **No refactor** of council code is authorized by this gate.
- **No Phase 5 implementation** is authorized.
- **No trading, paper, or live** authorization is granted.
- This audit **reduces ambiguity before Phase 5 but authorizes nothing**. Deterministic
  risk/verification plus the operator gate (and `config.DRY_RUN` default) remain the intended
  authority model; the evidence verifier checks scoped invariants only.
<!-- FRAMING-END -->

## 2. Council inventory

Evidence gathered via read-only search at commit `a790333` (no files modified).

**Council files/directories found** (`council/`, deterministic Python package):

- `council/__init__.py`
- `council/scout.py` — edge scanning / signal generation (`scan_edges`, `scan_shadow_edges`)
- `council/verifier.py` — verification veto layer (`verify`)
- `council/redteam.py` — adversarial veto + fee-adjusted edge (`redteam`)
- `council/risk.py` — deterministic Kelly sizing + risk veto (`risk`)
- `council/gate.py` — final pass/veto + `confidence_score` (`gate`)

**Imports / call sites found:**

- The only non-test importer is `main_loop.py`:
  `from council.scout import scan_edges`, `from council.verifier import verify`,
  `from council.redteam import redteam`, `from council.risk import risk`,
  `from council.gate import gate`.
- `main_loop._run_council(...)` runs the layers in order scout → verifier → redteam → risk → gate,
  logging a VETO at each layer; on pass it logs `GEÇTİ → execute` and calls `execute(...)`.
- `execute(...)` selects `execution/executor.py:_dry_execute` when `config.DRY_RUN` is true, else
  `execution/clob_executor.py:_clob_execute` (live). Order construction lives in
  `execution/order_intent.py`.

**Connection to core paths:**

- Connected to **main_loop**: yes (imported and executed each scan).
- Connected to **analysis / edge**: yes (scout generates edge findings).
- Connected to **risk**: yes (deterministic risk layer participates in the veto chain).
- Connected to **execution / order intent**: yes (gate pass → `execute()` → order intent /
  executor; live path gated by `config.DRY_RUN`).
- Connected to **reporting**: yes (veto/pass logged to DB via the logger).

**Active / dead / legacy / docs-only / unclear:**

- The `council/` package appears **active** (imported and invoked by `main_loop.py`); the live
  execution branch is gated by `config.DRY_RUN`.
- The council is **deterministic Python**: no `llm` / `claude` / `gemini` / `openai` / `anthropic`
  / `requests` / `http` / `api_key` references were found in `council/*.py`.
- **LLM presence is audit/review-only and offline**: a Gemini-attributed code *comment* in
  `main_loop.py` (~line 1043) and the offline artifact `docs/superpowers/evidence/
  gemini_adversarial_review_d11.md` with `tests/test_gemini_adversarial_review_artifact.py`. No
  runtime LLM decision call was found in any decision path.

## 3. Decision-authority classification

| Component | Classification |
|---|---|
| `council/scout.py` | `trade_path_connected` (edge / signal generation feeds candidates) |
| `council/verifier.py` | `trade_path_connected` (veto in the chain) |
| `council/redteam.py` | `trade_path_connected` (adversarial veto in the chain) |
| `council/risk.py` | `risk_override_connected` / `trade_path_connected` (deterministic sizing + veto) |
| `council/gate.py` | `trade_path_connected` + `order_intent_connected` (pass → execute → order intent) |
| `main_loop._run_council` / `execute` | `order_intent_connected` (live branch gated by `DRY_RUN`) |
| Gemini adversarial-review artifact + its test | `audit_or_review_only` / `docs_or_legacy_only` (offline) |
| `tools/phase45_evidence_verifier.py` | `read_only_reporting` / `audit_or_review_only` |

Net: a (deterministic) council/multi-agent layer **is connected** to the edge/trade/risk/
order-intent/execution path. No runtime **LLM** decision authority was found; LLM usage is
audit/review-only.

<!-- RED-LINES-START -->
## 4. Required red lines

LLM and/or council components **must not**:

- **cannot approve trades**;
- **cannot approve edge**;
- **cannot generate signals** that directly authorize execution;
- **cannot create order intent** (cannot create order intents);
- **cannot override** deterministic risk;
- **cannot authorize execution**;
- **cannot authorize paper/live readiness**;
- **cannot authorize Phase 5 implementation**;
- must make **no profitability / alpha / edge / readiness** claims.

LLM/council must not have decision authority over edge, risk, order, execution, paper/live
readiness, or Phase 5 authorization.
<!-- RED-LINES-END -->

## 5. Allowed future role

Council/LLM may be allowed **only** as, and **only outside deterministic trade/execution/risk
paths**:

- read-only report summarizer;
- audit note generator;
- missing-evidence reviewer;
- adversarial review assistant;
- operator checklist assistant.

Any such role must remain outside the deterministic risk/verification/order/execution paths.

## 6. De-risk recommendation

**FOLLOW_UP_REMOVE_OR_BYPASS.**

> Update: the bypass has since been implemented — see
> `docs/protocols/council_decision_authority_bypass.md`. Council decision authority is now
> disconnected from execution authority by default (`config.COUNCIL_DECISION_AUTHORITY_ENABLED`,
> default disabled).

Rationale: a council/multi-agent decision layer is connected to the trade / edge / risk /
order-intent / execution path (via `main_loop._run_council` → `execute`). Per this gate's rules,
trade-path / order / risk / readiness connections require a separate TDD remove-or-bypass task. This
recommendation does **not** assert that the existence of the current deterministic council is itself
a failure, and read-only/docs-only remnants (e.g. the offline Gemini review artifact) can be
documented without immediate removal. The follow-up exists to enforce the red lines — in particular
that no LLM or non-deterministic element can ever gain decision authority in these paths.

## 7. Future removal/bypass gate

If connected or unclear (here: connected), a future **separate TDD remove-or-bypass task** must
enforce, with failing tests first and offline:

- the LLM council **cannot approve trades**;
- the LLM council **cannot approve edge**;
- the LLM council **cannot create order intent**;
- the LLM council **cannot override** risk;
- the LLM council **cannot authorize paper/live readiness**;
- deterministic verifier/risk contracts (plus the operator gate and `DRY_RUN` default) remain the
  only allowed gates before any future implementation.

That separate task — not this audit — would perform any removal or bypass; this gate only
determines that the follow-up is needed.

<!-- NO-CLAIMS-START -->
## No-claims statement

This audit makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no system-ready, no ready-to-fly, and no
ready claim**. It does not prove the absence of LLM risk and does not guarantee Phase 5 safety; it
reduces ambiguity within its read-only scope and authorizes nothing. Deterministic risk/verification
plus the operator gate remain the intended authority model.
<!-- NO-CLAIMS-END -->

## Safety note

This file is docs/tests only. No council code was removed, refactored, or executed; no production
path was changed; generated `data/output` artifacts remain untracked and are never staged.
