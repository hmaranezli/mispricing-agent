# Performance Analysis Script — Design Spec

**Tarih:** 2026-05-31  
**Kapsam:** Dry-run strateji performansını analiz eden tek dosya terminal script

---

## Amaç

`analysis/performance.py` — botun dry-run pozisyonlarından strateji performansını ölçer.  
Her çalıştırmada terminal'e formatlanmış tablo basar. Bağımsız script, bot çalışırken de çalışır.

---

## Veri Kaynağı

SQLite: `logs/mispricing.db`  
Tablolar:
- `positions` — açık/kapalı tüm pozisyonlar
- `candidates` — konsey veto istatistikleri

**Önemli:** DB 2026-05-31 akşamı temizlendi. Eski (hatalı sistemden) kayıtlar silindi. Tüm veriler clean.

---

## Çıktı Bölümleri

### 1. Genel Bakış
```
GENEL BAKIŞ (tüm zamanlar)
Toplam trade  : 15
Kazanan       : 5  (Win rate: 33.3%)
Kaybeden      : 7
Belirsiz      : 3  (market_expired — P&L bilinmiyor)
Net P&L       : +$12.45
Ortalama P&L  : +$1.78 / trade
```

### 2. Exit Reason Dağılımı
```
EXIT REASON         | Adet | Oran  | Ort P&L | Toplam P&L
market_resolved     |    5 |  33%  |  +$14.94 |  +$74.70
thesis_invalidated  |    7 |  47%  |  -$15.06 | -$105.44
market_expired      |    3 |  20%  |     N/A  |     N/A
```

### 3. Asset Bazında Performans
```
ASSET | Trade | Kazanan | Win% | Net P&L
BTC   |     6 |       2 |  33% |  +$32.76
ETH   |     5 |       1 |  20% |  -$72.85
SOL   |     3 |       2 |  67% |  +$55.43
XRP   |     1 |       0 |   0% |  -$46.08
```

### 4. Konsey Veto Dağılımı
```
KONSEY VETO (bugün / tüm zamanlar)
Toplam aday  : 3,985
verifier     : 2,531  (63.6%)
risk         : 415    (10.4%)
redteam      : 240    ( 6.0%)
gate         : 73     ( 1.8%)
PASS         : 12     ( 0.3%)
```

### 5. En İyi / En Kötü 3 Trade
```
TOP 3 KAZANAN
SOL NO | +$43.62 (+87.2%) | thesis_invalidated
...

TOP 3 KAYBEDEN
ETH YES | -$50.00 (-100%) | market_resolved
...
```

---

## Parametreler

- `--days N` — Son N günün verisi (default: tüm zaman)
- `--asset BTC` — Tek asset filtresi (opsiyonel)

---

## Dosya Yapısı

```
analysis/
└── performance.py   # tek dosya, standalone
```

---

## Teknik Detaylar

- DB bağlantısı: `from db.logger import get_connection` (async)
- Çalıştırma: `python analysis/performance.py [--days N]`
- Dependency: yok (stdlib + mevcut db module)
- Test: yok — saf okuma/display, business logic yok
- Async: asyncio.run() wrapper ile

---

## Kapsam Dışı

- Grafik/chart (sonraya)
- Web dashboard (sonraya)
- Otomatik Telegram raporu (sonraya)
