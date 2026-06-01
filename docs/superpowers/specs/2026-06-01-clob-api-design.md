# Polymarket CLOB API Entegrasyonu — Design Spec

**Tarih:** 2026-06-01  
**Karar:** Yaklaşım B — Temiz Split + Aşamalı Geçiş  
**Durum:** APPROVED

---

## Hedef

DRY_RUN botu kanıtladı: 73.4% win rate, 124 trade, Z-score > 6. Sıradaki adım gerçek
Polymarket CLOB API ile order göndermek. Bu spec, mevcut sistemi kırmadan gerçek order
execution katmanını ekler.

**Tasarım prensibi:** `executor.py` dokunulmaz. Yeni `clob_executor.py` aynı interface'i
uygular. `main_loop.py` sadece route eder.

---

## Mimari

### Yeni Dosyalar

```
execution/
├── executor.py           DOKUNULMAZ — DRY_RUN logger
├── clob_client.py        YENİ — py-clob-client singleton + credential yönetimi
├── clob_executor.py      YENİ — gerçek BUY order placement
└── position_store.py     YENİ — kaç token tuttuğumuzu DB'de saklar (sell için)
```

### Değişen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `data/shortterm.py` | `fetch_by_slug()` → `clobTokenIds` extract eder; `yes_token_id` + `no_token_id` finding dict'e eklenir |
| `main_loop.py` | execute router + sell_position çağrısı + BANKROLL_USD config'den |
| `db/schema.py` | `positions` tablosuna `shares REAL` kolonu (ALTER TABLE migration) |
| `db/logger.py` | `log_position_open()` → `shares` alanı yazar |
| `.env` | 5 yeni credential satırı (kullanıcı yönetir) |

### Değişmeyen Dosyalar

`council/`, `monitor/`, `position/manager.py`, `config.py` — hiçbirine dokunulmaz.

---

## Interface Sözleşmesi

`clob_executor.py` imzası `executor.py` ile birebir aynı olmalı:

```python
async def execute(
    finding:        dict,
    gate_result:    dict,
    risk_result:    dict,
    open_positions: list[dict],
) -> dict | None:
    ...
```

Döndürdüğü `position` dict'i `executor.py`'nin döndürdüğüyle aynı şekilde — ek olarak:
- `shares: float` — satın alınan token miktarı (fill'den)
- `order_id: str` — CLOB order ID (monitoring için)
- `fill_price: float` — gerçek fill fiyatı (slippage ölçümü)

`main_loop.py` tek satır router:
```python
from execution.executor      import execute as _dry_execute
from execution.clob_executor import execute as _clob_execute
_execute = _dry_execute if config.DRY_RUN else _clob_execute
```

---

## Veri Katmanı: clobTokenIds

`data/shortterm.py` → `fetch_by_slug()` zaten Polymarket Gamma API'sini çağırıyor.
API yanıtı `clobTokenIds: ["yes_token_id", "no_token_id"]` içeriyor — sadece çıkarmıyorduk.

**Değişiklik:** `parse_market_window()` veya `fetch_by_slug()` sonucuna eklenir:
```python
result["yes_token_id"] = raw.get("clobTokenIds", [None, None])[0]
result["no_token_id"]  = raw.get("clobTokenIds", [None, None])[1]
```

`scan_edges()` bu alanları finding'e kopyalar. Executor token ID'yi finding'den alır.

---

## clob_client.py

```python
# execution/clob_client.py
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
import os

_client: ClobClient | None = None

def get_client() -> ClobClient:
    global _client
    if _client is None:
        _client = ClobClient(
            host="https://clob.polymarket.com",
            key=os.environ["POLY_PRIVATE_KEY"],
            chain_id=POLYGON,
            creds=ApiCreds(
                api_key        = os.environ["POLY_API_KEY"],
                api_secret     = os.environ["POLY_API_SECRET"],
                api_passphrase = os.environ["POLY_API_PASSPHRASE"],
            ),
        )
    return _client
```

Lazy init: import sırasında crash etmez. `POLY_*` env değişkenleri yoksa sadece
`clob_execute()` çağrıldığında hata verir.

---

## clob_executor.py — Entry (BUY)

```python
async def execute(finding, gate_result, risk_result, open_positions) -> dict | None:
    client = get_client()
    action = finding["action"]   # "YES" veya "NO"
    token_id = finding["yes_token_id"] if action == "YES" else finding["no_token_id"]

    position_usd = risk_result["position_usd"]
    entry_price  = finding["best_ask"]
    shares       = round(position_usd / entry_price, 4)

    order = client.create_and_post_order(OrderArgs(
        token_id = token_id,
        price    = entry_price,
        size     = shares,
        side     = BUY,
        time_in_force = GTD,   # Good Till Day
    ))

    if not order or order.status != "MATCHED":
        return None  # fill olmadı, pozisyon açılmaz

    fill_price = float(order.price)
    fill_size  = float(order.size_matched)

    return {
        "position_id":  str(uuid4()),
        "asset":        finding["asset"],
        "action":       action,
        "slug":         finding["slug"],
        "pm_entry_price": fill_price,
        "fair_value":   finding["fair_value"],
        "ref_price":    finding["ref_price"],
        "edge":         finding["edge"],
        "position_usd": fill_price * fill_size,
        "kelly_f":      risk_result["kelly_f"],
        "confidence_score": gate_result["confidence_score"],
        "shares":       fill_size,
        "order_id":     order.order_id,
        "fill_price":   fill_price,
        "requires_human_approval": False,
        "dry_run":      False,
        "status":       "open",
        "opened_at":    datetime.now(timezone.utc).isoformat(),
        "yes_token_id": finding["yes_token_id"],
        "no_token_id":  finding["no_token_id"],
    }
```

---

## position_store.py — SELL için Token Takibi

Token ID'leri ve shares DB'ye kaydedilir. Sell sırasında position'dan okunur.

```python
async def sell_position(pos: dict, client: ClobClient) -> float:
    """Pos'taki shares kadar token sat, fill fiyatını döndür."""
    action   = pos["action"]
    token_id = pos["yes_token_id"] if action == "YES" else pos["no_token_id"]
    shares   = pos["shares"]

    order = client.create_and_post_order(OrderArgs(
        token_id      = token_id,
        price         = pos.get("current_bid", 0),
        size          = shares,
        side          = SELL,
        time_in_force = GTD,
    ))
    return float(order.price) if order else pos.get("pm_exit_price", 0)
```

---

## Exit Flow Değişimi (main_loop.py)

`_monitor_positions` içindeki exit path:

```python
# Mevcut (DRY_RUN)
pm_exit = window["best_ask"]   # modelled fiyat

# Yeni (DRY_RUN=False)
if not config.DRY_RUN:
    pm_exit = await sell_position(pos, get_client())
else:
    pm_exit = round(1 - window["best_ask"], 4) if pos["action"] == "NO" else window["best_ask"]
```

---

## DB Schema Değişimi

`db/schema.py` → `CREATE TABLE positions` sorgusuna `shares REAL` eklenir:

```sql
-- Mevcut DB için migration (schema.py init_schema içinde):
ALTER TABLE positions ADD COLUMN shares REAL;
ALTER TABLE positions ADD COLUMN order_id TEXT;
ALTER TABLE positions ADD COLUMN yes_token_id TEXT;
ALTER TABLE positions ADD COLUMN no_token_id TEXT;
```

DRY_RUN pozisyonları için bu alanlar NULL — geriye dönük uyumlu.

---

## Credentials Yapısı

`.env` dosyasına kullanıcı ekler (CLAUDE dokunmaz):

```bash
POLY_PRIVATE_KEY=0x...          # Metamask: export private key
POLY_WALLET_ADDRESS=0x...       # Wallet adresi
POLY_API_KEY=...                # polymarket.com → profil → API → Create Key
POLY_API_SECRET=...
POLY_API_PASSPHRASE=...
```

**USDC gereksinimi:** Polygon ağında USDC bakiyesi. Aşama 2 için $50 yeterli.

---

## Fee Muhasebesi

| Kalem | Oran |
|-------|------|
| Polymarket CLOB taker fee | %2 / order |
| Round-trip (buy + sell) | ~%4 |
| Mevcut MIN_EDGE_PCT | %8 |
| Net minimum edge | ~%4 |

73.4% win rate, ortalama edge ~%20 → fee sonrası net beklenti değeri pozitif.

**Kalibrasyon:** `council/redteam.py` içindeki `fee_adj_edge` hesabı %2 Polymarket taker
fee ile kalibre edilecek (mevcut değer kontrol + gerekirse güncelleme).

---

## 3 Aşamalı Rollout

### Aşama 1 — API Bağlantı Testi (DRY_RUN=True)
- Credentials yükle, `get_client()` auth doğrula
- Wallet USDC bakiyesini oku
- Bilinen bir market için `clobTokenIds` doğrula
- Hiç order gönderilmez

### Aşama 2 — Mikro Canlı (DRY_RUN=False, BANKROLL_USD=50)
- MAX_TRADE_PCT=5% × $50 = max $2.50/trade
- Kelly doğal olarak $1-3 üretir — minimum order $1 ✅
- İlk 5 trade: `fill_price` vs `best_ask` farkını logla (slippage ölçümü)
- Telegram: "filled at X, expected Y, slippage ±Z%" bildirimi

### Aşama 3 — Tam Deployment
- BANKROLL_USD kullanıcı belirler
- **CONSTITUTION:** `DRY_RUN=False` yalnızca yazılı insan komutuyla
- Telegram kill switch aktif

---

## Hata Yönetimi

| Senaryo | Davranış |
|---------|----------|
| Order MATCH olmadı | `execute()` → None döner, pozisyon açılmaz |
| API timeout | 3 retry, sonra skip (bu scan'de bu market atlanır) |
| Partial fill | `size_matched < size` → gerçek fill ile pozisyon aç, kalan iptal |
| Sell order dolmadı | GTD: günün sonunda otomatik iptal, bir sonraki scan'de tekrar dene |
| USDC yetersiz | Risk katmanı position_usd'i zaten wallet'tan düşük tutar (bakiye kontrolü eklenecek) |
| Credentials eksik | clob_client.py → clear error at first use, DRY_RUN koruması devrede |

---

## Test Stratejisi

**Unit testler** (py-clob-client mock edilir):
- `tests/test_clob_client.py` — credential loading, lazy init, conn=None guard
- `tests/test_clob_executor.py` — execute() order placement, fill → position dict, partial fill
- `tests/test_position_store.py` — sell_position(), token ID routing (YES vs NO)

**Integration test** (gerçek API, sıfır order):
- Auth doğrulama testi
- USDC bakiye okuma
- clobTokenIds fetch (bilinen BTC market)

**Slippage ölçümü** (Aşama 2):
- `analysis/slippage_report.py` — fill_price vs best_ask farkını özetle

---

## Bağımlılık

```bash
pip install py-clob-client
```

`requirements.txt`'e eklenir.

---

## Sıralama (Implementation Plan için)

1. `db/schema.py` — shares + order_id + token ID kolonları (migration)
2. `data/shortterm.py` — clobTokenIds extract
3. `execution/clob_client.py` — singleton + auth
4. `execution/clob_executor.py` — execute() BUY order
5. `execution/position_store.py` — sell_position()
6. `main_loop.py` — router + exit path
7. `council/redteam.py` — fee kalibrasyon kontrolü
8. `requirements.txt` — py-clob-client
9. Aşama 1 doğrulama (bağlantı testi)
