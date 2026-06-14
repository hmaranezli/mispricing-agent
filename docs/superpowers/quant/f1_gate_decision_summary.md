# F1 Gate Decision Summary

> **F1 Gate Decision** — F-fazı quant denetimlerinin tek-karar özeti. **Yeni ölçüm mantığı EKLEMEZ**;
> mevcut artifact'leri tek gate kararına indirger. **offline data only · no live API.** Tarih: 2026-06-14.

## 1. Verdict

- **F remains BLOCKED.** **production canary NOT approved.**
- **no production trading code changed** — bu gate yalnız karar/kanıt özetidir; trading path'e dokunmaz.

## 2. Özetlenen kanıt zinciri (mevcut artifact'ler)

- `pre_f_money_making_audit.md` → FAIL/BLOCKED on edge correctness (code/logic vs statistical edge vs data fidelity 3 eksen).
- `poly_api_data_fidelity_audit.md` → BLOCKED-UNTIL-DOCS / DATA FIDELITY NOT VERIFIED.
- `pm_up_down_resolution_rule_source.md` → SOURCE-RESOLVED: PM Up/Down **Chainlink BTC/USD Data Streams** ile resolve; **HL≠Chainlink confounder confirmed**.
- `f1b_chainlink_stream_blocker.md` → **F1b Measurement BLOCKED**.

## 3. Korunan matematik (özet, yeni mantık yok)

- **HL≠Chainlink confounder confirmed:** bot `fair_value` Hyperliquid mark/mid kullanıyor; PM Chainlink
  Data Streams ile resolve ediyor. Sistematik kaynak basis'i → recorded Brier 0.39 / fair-67-vs-win-14
  model overconfidence DEĞİL kaynak uyuşmazlığı olabilir.
- **F1b Measurement BLOCKED:** gerçek ölçüm için **exact Chainlink Data Streams required**.
- **Feed-proxy cannot clear F1b:** Data Feed heartbeat/deviation örneklemesi 0s/30s/60s shift
  ölçeğinde **Time Resolution Mismatch** + stale price confounder yaratır → Feed-proxy gerçek
  HL↔Stream kaynak basis'ini değil, temporal heartbeat noise'u ölçer. Feed-proxy yalnız **açıkça
  etiketli smoke test** olabilir ve **F'i UNLOCK ETMEZ**.

## 4. Calibration durumu

- **calibration metrics blocked until source-aligned data:** Brier/reliability vb. ancak HL↔Chainlink
  source-aligned veri üzerinde anlamlı; confounder ayrıştırılmadan kalibrasyon yanıltıcı.

## 5. Allowed unlock paths

- **allowed unlock paths: Streams auth or manual Streams CSV/JSON**
  1. Chainlink Data **Streams** read-only authenticated erişim (ayrı, açık insan onayı + scope).
  2. Manuel Streams **CSV/JSON paste** (offline, fetch'siz — en temiz).
  - Feed-proxy bu listede DEĞİL (yalnız etiketli smoke; F'i açmaz).

## 6. Next action

- **next action: obtain exact Streams data, then recompute calibration.** Sıra: exact Streams verisini
  edin (auth read-only veya manuel CSV/JSON) → `analysis/source_basis.py` ile source-aligned ölç
  (directional disagreement + bps + shift) → source-aligned calibration metrics → ancak sonra F
  değerlendirilebilir. Bu olana dek **F BLOCKED / canary NOT approved**.

## 7. Live/code NO-GO confirmation

- **no live API**, no Chainlink/HL fetch, no DB/Telegram/CLOB/auth/D#7/restart/kill. **no production
  trading code changed.** Canlıya/exact-Streams-auth'a geçiş yalnız insanın açık yazılı komutuyla.
