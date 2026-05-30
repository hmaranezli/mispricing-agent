# Katman 4: Risk — Tasarım Dokümanı

Tarih: 2026-05-30  
Durum: Onaylandı  
Bağlam: 5 katmanlı konseyin 4. katmanı. Scout → Verifier → RedTeam geçmiş bulgu için pozisyon boyutlandırması ve son güvenlik kontrolleri.

---

## Amaç

Risk katmanı **ne kadar** sorusunu cevaplar. Geçen bir işlemin kaç dolarlık açılacağını belirler; sistemi durduracak koşulları (günlük kayıp limiti) ve insan onayı gerektiren koşulları (büyük pozisyon) tespit eder.

Risk katmanı hiçbir zaman bloklamaz. Bayrakları kaldırır, kararı Gate'e bırakır.

---

## Mimari Karar: Pure Function

Risk katmanı **tamamen saf fonksiyondur** — API çağrısı yok, DB bağlantısı yok, global state yok.

Tüm dış durum (bankroll, açık pozisyon sayısı, günlük kayıp) **parametre olarak enjekte edilir**.

```python
def risk(
    finding:       dict,   # Scout scan_edges() çıktısı
    verification:  dict,   # Verifier verify() çıktısı → fresh fiyatlar buradan
    redteam:       dict,   # RedTeam redteam() çıktısı → fee_adj_edge buradan
    bankroll_usd:  float,  # Çağıranın sağladığı sermaye
    open_positions: int,   # Şu an açık pozisyon sayısı
    daily_loss_usd: float, # Bugünkü gerçekleşmiş kayıp (USD)
) -> dict
```

Risk senkron fonksiyondur — API/DB çağrısı yok, `await` yok. Async pipeline içinden direkt çağrılabilir.

### Çağıran kimdir, değerleri nereden sağlar?

| Ortam | bankroll_usd | open_positions | daily_loss_usd |
|-------|-------------|----------------|----------------|
| **Test (şimdi)** | `1000.0` (sabit) | `0` | `0.0` |
| **DRY_RUN entegrasyon** | `config.STARTING_CAPITAL_USD`* | in-memory sayaç | in-memory toplam |
| **Canlı (ileride)** | HL API bakiyesi | DB sorgusu | DB sorgusu |

\* `STARTING_CAPITAL_USD` kullanıcı tarafından `config.py`'e eklenecek (ajan ekleyemez).

---

## Modül Sabitleri (risk.py içinde, config.py değil)

```python
KELLY_FRACTION  = 0.25   # Çeyrek Kelly — tam Kelly'nin 1/4'ü, variance düşük
MIN_POSITION_USD = 5.0   # Bu altı → fee'ye değmez → veto
```

Neden çeyrek Kelly: Tam Kelly teorik optimum ama gerçek variance çok yüksek. %25 fraksiyon, beklenen getirinin ~%50'sini korurken drawdown'ı dramatik düşürür. Başlangıç için güvenli seçim.

---

## Veto Zinciri (sırayla — ilk fail'de dur)

### 1. Günlük Kayıp Limiti (HALT)
```python
if daily_loss_usd / bankroll_usd >= config.DAILY_LOSS_LIMIT_PCT:
    return _result(pass_=False, halt=True, reason="daily_loss_limit_hit")
```
Anayasa: günlük kayıp %10'a ulaşınca TÜM SİSTEM DURUR. `halt=True` Gate'e iletilir, Gate tüm taramayı durdurur.

### 2. Açık Pozisyon Limiti
```python
if open_positions >= config.MAX_OPEN_POSITIONS:
    return _result(pass_=False, reason="max_open_positions_reached")
```
Anayasa: aynı anda max 5 açık pozisyon.

### 3. Edge Geçerlilik Kontrolü (çift emniyet)
```python
if redteam["fee_adj_edge"] < config.MIN_EDGE_PCT:
    return _result(pass_=False, reason="edge_below_minimum")
```
RedTeam zaten yakalamış olmalı. Ama paranoya iyi mühendisliktir.

### 4. Kelly Hesabı ve Minimum Pozisyon
```python
kelly_f    = _kelly(finding, redteam)
capped_f   = min(kelly_f * KELLY_FRACTION, config.MAX_TRADE_PCT)
position   = capped_f * bankroll_usd

if position < MIN_POSITION_USD:
    return _result(pass_=False, reason="position_too_small")
```

### 5. İnsan Onayı Bayrağı (VETO DEĞİL)
```python
requires_human_approval = position > config.HUMAN_APPROVAL_USD
```
Risk buradan geçer. Gate bu bayrağı görünce:
- DRY_RUN: logla, devam et.
- Canlı: Telegram'a bildir, 5 dakika bekle. Cevap gelmezse → o işlemi atla. Sistem durmaz.

---

## Kelly Formülü — Polymarket Binary

Polymarket kontratı binary: YES/NO, kazanırsa $1 öder.

```python
def _kelly(action: str, fee_adj_edge: float,
           fresh_ask: float, fresh_bid: float) -> float:
    """
    Ham Kelly fraksiyonu (0-1 arası, bankroll oranı).
    fresh_ask/bid: verification["fresh_best_ask/bid"] — RedTeam ile aynı kaynak.
    Bölme sıfırı koruması: payda < 0.01 → 0.0 döner (position_too_small vetosu tetikler).
    """
    if action == "YES":
        denom = 1.0 - fresh_ask
        return fee_adj_edge / denom if denom >= 0.01 else 0.0
    else:  # NO
        denom = fresh_bid
        return fee_adj_edge / denom if denom >= 0.01 else 0.0
```

Çağrı: `_kelly(finding["action"], redteam["fee_adj_edge"], verification["fresh_best_ask"], verification["fresh_best_bid"])`

**Neden verification'dan?** RedTeam `fee_adj_edge`'i `fresh_best_ask/bid` ile hesapladı. Kelly paydası da aynı taze fiyatı kullanmalı — tutarlılık.

**YES:** `kelly_f = fee_adj_edge / (1 - fresh_ask)`
- Kazanç: $1 − ask, Kayıp: ask. Oran = (1−ask)/ask. Kelly = edge/(1−ask).

**NO:** `kelly_f = fee_adj_edge / fresh_bid`
- Eşdeğer: NO'yu (1−bid) fiyatına alıyoruz. Kelly = edge_no/bid.

Sonra: `position_usd = min(kelly_f × 0.25, 0.05) × bankroll_usd`

---

## Output Şeması

```python
{
    "pass":                    bool,   # True → Gate'e ilet
    "position_usd":            float,  # Önerilen pozisyon büyüklüğü (USD)
    "kelly_f":                 float,  # Ham Kelly oranı (fraksiyonsuz)
    "kelly_fraction_applied":  float,  # 0.25 (KELLY_FRACTION)
    "requires_human_approval": bool,   # position_usd > HUMAN_APPROVAL_USD?
    "halt":                    bool,   # Günlük kayıp limiti → tüm sistemi durdur
    "reason":                  str,    # Veto/halt sebebi ("" → pass)
}
```

---

## Test Stratejisi

Tüm testler **senkron, saf unit test** — mock/API yok.

| Test | Ne kontrol eder |
|------|----------------|
| `test_result_has_required_fields` | Çıktı şeması tam |
| `test_halt_on_daily_loss_limit` | %10 kayıp → halt=True, pass=False |
| `test_no_halt_below_limit` | %9 kayıp → halt=False |
| `test_veto_max_open_positions` | 5 pozisyon → veto |
| `test_pass_below_max_positions` | 4 pozisyon → geçer |
| `test_veto_edge_below_minimum` | fee_adj_edge < MIN_EDGE_PCT → veto |
| `test_veto_position_too_small` | Çok küçük Kelly → position < 5$ → veto |
| `test_kelly_yes_calculation` | YES için doğru Kelly formülü |
| `test_kelly_no_calculation` | NO için doğru Kelly formülü |
| `test_kelly_capped_at_max_trade_pct` | Yüksek Kelly → %5 cap |
| `test_human_approval_flag_set` | position > HUMAN_APPROVAL_USD → bayrak |
| `test_human_approval_does_not_veto` | Bayrak kalksa da pass=True |
| `test_pass_normal_case` | Sağlıklı finding → pass, geçerli position |
| `test_kelly_zero_denom_vetoes` | best_ask=1.0 → bölme koruması → veto |

**Hedef:** ≥12 test, 0 skip, 0 API çağrısı.

---

## İnsan Onayı — Uzun Vade Notu

`HUMAN_APPROVAL_USD = 50$`, `STARTING_CAPITAL_USD = 1000$`, `MAX_TRADE_PCT = 5%` ile maks pozisyon = 50$. Çeyrek Kelly ile çoğu gerçek işlem 20-40$ bandında → bayrak nadiren kalkar.

Sistem olgunlaştıkça (yeterli track record + DB P&L doğrulaması sonrası) bu eşik kaldırılabilir. Karar kullanıcıya ait, config.py'den bir satır değişiklikle.

---

## Bağımlılıklar

- `config.py` — MAX_OPEN_POSITIONS, MAX_TRADE_PCT, DAILY_LOSS_LIMIT_PCT, MIN_EDGE_PCT, HUMAN_APPROVAL_USD
- `council/redteam.py` — fee_adj_edge, fresh_best_ask, fresh_best_bid buradan gelir (verification üzerinden)
- Dış bağımlılık yok (aiohttp, DB, HL API — hiçbiri)

---

## Dosya Yapısı

```
council/risk.py          # Ana modül (~120-150 satır)
tests/test_risk.py       # ≥12 unit test
```
