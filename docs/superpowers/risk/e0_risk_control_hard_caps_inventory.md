# E0 Risk-Control Hard Caps Inventory

> Yalnız ENVANTER — implementasyon/davranış değişikliği YOK. **E protects survival probability**
> (iflas/execution riski), F'ten (model/edge riski) AYRIDIR. **F parked until exact Streams data**;
> E bağımsız survival/ruin koruması. **offline data only · no live API.** Tarih: 2026-06-14.

## 1. Verdict

- **E0 inventory complete, but Risk-Control Hard Caps NOT complete.**
- E0 tek başına **F, Paper Soak, canary, D#2 veya D#7'yi UNLOCK ETMEZ.** **Paper Soak blocked until hard caps are verified.**
- Amaç: edge belirsizken bile **ruin probability**'yi sınırlayan guardrail'lerin var olup olmadığını
  saymak.

## 2. config-based hard caps (MEVCUT — config.py)

- `MAX_TRADE_PCT = 0.05` — tek trade max sermaye %5 (≈ **MAX_CAPITAL_PER_TRADE**'in yaklaşık karşılığı).
- **MAX_OPEN_POSITIONS** `= 5` — aynı anda max açık pozisyon.
- `BUST_PROTECTION_PCT = 0.50` — bankroll %50 altına düşünce HARD STOP.
- `STREAK_WARN_COUNT = 6` — N ardışık kayıp → SOFT STOP.
- `HUMAN_APPROVAL_USD = 50` — üstü pozisyon insan onayı.
- `MAX_SLIPPAGE_CAP = 0.03` — taker limit; aşımda intent REJECTED (sessiz clamp yok).
- `MAX_HOLD_MINUTES = 20`, `NEW_ENTRIES_ENABLED = False`, `HALT_ON_API_MISMATCH = True`.

## 3. logic-based execution breakers (MEVCUT)

- `monitor/circuit_breaker.py` — bust hard_stop (@%50) + streak soft_stop (@6).
- `council/risk.py` — MAX_OPEN_POSITIONS enforce + Kelly sizing (çeyrek Kelly, MIN_POSITION_USD floor).
- `execution/emergency_pause.py` — DB kill-switch, fail-closed; **emergency/manual pause** mevcut.
- `monitor/kill_switch.py` — dosya `logs/KILL`; `monitor/shutdown.py` — SIGTERM/SIGINT graceful.
- Slippage-cap REJECT (network call yok).

## 4. missing or implied controls (BLOCKER / GAP)

- **DAILY_LOSS_LIMIT — EKSİK (anayasa ihlali).** CLAUDE.md §5 "Günlük kayıp %10'a ulaşınca TÜM SİSTEM
  DURUR" diyor; `council/risk.py` yorumu "gunluk kayip limiti circuit_breaker'a tasindi" — ama
  circuit_breaker'da yalnız bust %50 + streak 6 var, **günlük %10 cap YOK.** → **kritik gap.**
- **SESSION_LOSS_LIMIT** — yok.
- **MAX_TRADES_FIRST_SESSION** — yok (ilk canlı oturumda işlem-sayısı capı yok).
- **cancel/timeout burst breaker** — yok (grep boş).
- **fill-to-submit breaker** — yok.
- **exit-only mode** — yalnız `NEW_ENTRIES_ENABLED=False` ile KISMEN/İMA edilmiş; koşul-tetikli resmi
  breaker değil.
- **MAX_OPEN_POSITIONS = 5** ama Master TODO hard-cap/canary güvenliği için **MAX_OPEN_POSITIONS=1**
  istiyor → mevcut 5 bir **gap** (canary öncesi 1'e indirilmeli).
- **MAX_CAPITAL_PER_TRADE** yalnız yaklaşık olarak `MAX_TRADE_PCT=0.05` ile var; explicit USD / min-lot
  cap doğrulanmadı → **gap**.

## 5. Why E0 does not unblock anything

- E0 yalnız envanter (kod/davranış değişmedi). Eksik cap'ler (özellikle DAILY_LOSS_LIMIT,
  MAX_OPEN_POSITIONS=1, burst/fill-to-submit breaker'lar) TDD ile uygulanmadan survival guardrail'i
  tam değil. F ayrıca Streams confounder'ına bağlı (parked). Bu yüzden **Paper Soak / canary BLOCKED.**

## 6. NO-GO confirmation

- **no live API**, no Chainlink/HL/Polymarket fetch, no DB/Telegram/CLOB/auth/D#7/restart/kill.
  **no production trading code changed.** Canlıya/canary'e geçiş yalnız insanın açık yazılı komutuyla.
