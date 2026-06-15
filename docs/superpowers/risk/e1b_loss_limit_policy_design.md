# E1b Loss Limit Policy Design

> Risk-kontrol **state machine** tasarımı. Policy-first: bu artifact YALNIZ politikayı tanımlar; kod /
> config sabiti / main_loop wiring SONRAKİ ayrı RED/GREEN adımlarıdır. **do not hardcode 0.10 yet** —
> eşik değeri implementasyon adımına bırakılır (anayasa: config guardrail sabitini insan ekler).
> **no live API · no production trading code changed.** Tarih: 2026-06-14.

## 1. Core formula

- **`mode = max_priority(active_blockers)`** — efektif risk modu, o an aktif olan blocker'ların en
  yüksek öncelikli olanıdır. Modlar bağımsız boolean değil; `active_blockers` kümesinden türetilir.
- **hierarchy: Halted > Exit-Only > Cooldown > Operational.** Çakışmada en yüksek kazanır.

## 2. Modlar (state machine)

- **Operational** — normal; yeni giriş açık. Tek streak izleme burada (§5).
- **Cooldown** — kısa soğuma; yeni giriş kapalı, exit/risk yönetimi aktif (§5).
- **Exit-Only** — graceful degradation; **Exit-Only disables new entries**, **exit/risk management remains active** (§6). **Exit-Only is graceful degradation.**
- **Halted** — mantıksal en üst risk modu (§7). **Halted is logical risk mode, not process restart.**

## 3. Transition matrix

| Tetik | Hedef blocker | Çıkış |
|---|---|---|
| 6 ardışık realized loss (Operational'da) | Cooldown | deterministik zaman aşımı VEYA manuel reset |
| günlük realized kayıp ≥ limit | Exit-Only (daily) | UTC 00:00 reset (yüksek blocker yoksa) |
| %50 bankroll drawdown | Halted | insan review / manuel reset |
| kill-switch (acil) | (politika dışı, §8) | manuel |

`active_blockers` = yukarıdaki tetiklerden o an doğru olanların kümesi; efektif mod
`max_priority(active_blockers)`.

## 4. Kill-Switch ayrımı

- **Kill-Switch is separate from Halted policy state.** **Kill-Switch is emergency last resort, outside normal policy mode transitions** — `execution/emergency_pause.py` (DB, fail-closed) +
  `monitor/kill_switch.py` (dosya). Politika state machine'inin bir modu DEĞİL; her şeyin üstünde
  acil durdurma katmanı. Graceful shutdown (`monitor/shutdown.py`, SIGTERM) da ayrı.

## 5. Cooldown semantiği (deadlock çözümü)

- **consecutive loss streak tracked only in Operational** (pause/exit-only'de yeni trade kapanmaz →
  streak orada artmaz/azalmaz). **consecutive loss streak resets on win.**
- **6 consecutive realized losses triggers Cooldown.** **Cooldown disables new entries.**
- **Cooldown must not wait for a new win while entries are disabled** — aksi halde deadlock (giriş
  kapalıyken win gelemez). **Cooldown exit is deterministic time expiry or manual reset.**
- **Cooldown exit resets the consecutive-loss trigger without requiring a win** — çıkışta streak
  sayacı sıfırlanır (win beklenmez), Operational'a temiz dönülür.

## 6. Daily breaker semantiği

- **daily realized loss breaker** — `daily_loss_pct = max(0, -realized_pnl_today/start_of_day_equity)`;
  eşik aşılınca **daily breaker enters Exit-Only**. Sayı (0.10) burada sabitlenmez (do not hardcode
  0.10 yet); değer config/implementation adımında, insan onayıyla.

## 7. Catastrophic stop / Halted

- **catastrophic bankroll stop** — **50 percent bankroll drawdown enters Halted.**
- **Halted requires human review/manual reset.** Otomatik temizlenmez; UTC reset Halted'ı temizlemez.

## 8. UTC daily reset semantiği (kesin)

- **UTC 00:00 start-of-day boundary.** **UTC 00:00 resets daily counters, not all risk state.**
- **UTC reset refreshes start_of_day_equity** + **UTC reset zeroes realized_pnl_today**.
- **next-day reset for daily limits.**
- **UTC reset may clear daily Exit-Only only if no higher-priority blocker remains.**
- **UTC reset must not clear Halted.** **UTC reset must not clear kill-switch/manual-review state.**
- **after any reset, effective mode is recomputed from active blockers** (`mode =
  max_priority(active_blockers)`).

## 9. Persistence / restart semantiği

- **no process restart required** — mod geçişleri runtime'da olur (restart şart değil).
- **restart must not reset risk state** — `start_of_day_equity`, `realized_pnl_today`, ve risk modu
  restart'tan sağ çıkmalı. **risk mode persistence** zorunlu; **state persistence must not be process-memory only** (DB/disk; process-memory tek başına yetmez, aksi halde restart guardrail'i sıfırlar).

## 10. Canary hard caps (bu policy ile birlikte zorunlu)

- **MAX_OPEN_POSITIONS=1 for canary** (mevcut 5; canary öncesi 1'e).
- **MAX_TRADES_FIRST_SESSION required** (ilk seans işlem-sayısı capı).
- **trade-size USD cap required** (explicit USD/min-lot; MAX_TRADE_PCT yaklaşık yeterli değil).
- **volatility-adjusted thresholds future consideration** (sabit eşikler v1; vol-ayarlı sonra).

## 11. NO-GO

- **no live API**, no Chainlink/HL/Polymarket fetch, no DB/Telegram/CLOB/auth/D#7/restart/kill.
  **no production trading code changed.** **Paper Soak blocked until policy and wiring are verified.**
  Canlıya/canary'e geçiş yalnız insanın açık yazılı komutuyla.

## 12. Micro-Canary Policy Deviation (E7)

Yalnız POLİTİKA revizyonu — config/kod/runtime değişikliği YOK. Aşağıdaki config sabitleri SONRADAN
**operatör (insan) eliyle** eklenecek (anayasa madde 1; bu doküman config.py'ye dokunmaz).

### 12.1 DAILY_LOSS_LIMIT = NET realized PnL tabanlıdır (gross losing trades DEĞİL)
- Ölçüm start-of-day equity'den **net realized** kayıptır, brüt kaybeden işlemler değil.
- **Formül:** `loss_pct = max(0.0, -realized_pnl_today / start_of_day_equity)`.
- **Yukarı volatilite CEZALANDIRILMAZ.** Kârlı bir günün bir kısmını geri vermesi, start-of-day
  equity'nin ALTINA düşmekle AYNI şey değildir.

### 12.2 Örnek: +1000 sonra −50 → HALT YOK
- `start_of_day_equity = $25`; gün içi `realized_pnl_today` +$1000'a ulaşır, sonra $50 geri verir.
- Net `realized_pnl_today = +$950` → `loss_pct = max(0, -950/25) = 0` → **daily_loss_halt TETİKLENMEZ**
  (No Halt, çünkü net PnL pozitif kalır).

### 12.3 Profit giveback ≠ daily loss (ayrı gelecek özellik)
- Pozitif gün-içi tepeden kâr geri verme, DAILY_LOSS_LIMIT'in işi DEĞİLDİR. Bu ayrı bir gelecek
  özelliktir: **High-Water Mark / Intraday Profit Lock / trailing drawdown guard.** Bu policy
  revizyonu onu KAPSAMAZ.

### 12.4 Micro-canary için trade-budget tabanlı eşik (10% neden yetersiz)
- $25 micro-canary bankroll, ~$1.25 trade size → bir tam kaybeden işlem ≈ bankroll'un **%5'i**.
- Legacy **%10** günlük limit yalnızca ~**2 tam kayba** izin verir → 6-loss streak/cooldown breaker
  pratikte **ULAŞILAMAZ** (gün limiti streak'ten önce vurur).
- Bu yüzden, **yalnız micro-canary için**, DAILY_LOSS_LIMIT trade-budget tabanlı olmalı:
  `risk_per_trade_pct * streak_threshold = 0.05 * 6 = 0.30`.
- Fee/slippage/yuvarlama için execution buffer eklenir → **önerilen micro-canary DAILY_LOSS_LIMIT = 0.35**.
- **0.35 vs 0.10 gerekçesi:** 0.10 streak breaker'ı gözlemlenemez kılar; 0.35 (=0.05×6 + buffer) en az
  6-loss streak'in gözlemlenmesine izin verir → cooldown/risk-state geçişleri gerçekten test edilebilir.

### 12.5 0.35 = veri-edinme bütçesi, üretim risk iştahı DEĞİL
- Bu 0.35 limiti küçük bankroll üzerinde slippage, fill davranışı, streak breaker davranışı ve
  risk-state geçişlerini GÖZLEMLEMEK için bir **data-acquisition budget**'tır. Production-scale risk
  appetite DEĞİLDİR. Ölçek büyüdüğünde yeniden değerlendirilir (Pre-F / üretim risk parametreleri).

### 12.6 Anti-burst cap
- **MAX_OPEN_POSITIONS = 1** canary anti-burst cap olarak KALIR (mevcut 5; canary için 1).

### 12.7 Explicit config sabitleri ve human-in-the-loop politikası (bu task EKLEMEZ)
```
DAILY_LOSS_LIMIT = 0.35
MAX_OPEN_POSITIONS = 1
```
- **`DAILY_LOSS_LIMIT` ve `MAX_OPEN_POSITIONS` insan-sahipli (human-owned) risk-iştahı sabitleridir.**
- Bunlar YALNIZCA (a) operatör tarafından elle, VEYA (b) explicit, dar kapsamlı, operatör-yetkili
  config-only bir task ile değiştirilebilir.
- **Claude bu değerleri icat edemez, çıkaramaz (infer), genişletemez veya sessizce değiştiremez.**
- Herhangi bir config task'i: yalnız `config.py`'yi düzenler, yalnız operatörün istediği sabit(ler)i
  değiştirir, diff'i gösterir, doğrulamayı koşar ve — ayrıca onaylanmadıkça — commit/push ÖNCESİ DURUR.
- `daily_loss_halt` şu an `getattr(config, "DAILY_LOSS_LIMIT", 0.10)` fallback'i kullanıyor; explicit
  0.35 sabiti eklenince micro-canary eşiği yürürlüğe girer.
