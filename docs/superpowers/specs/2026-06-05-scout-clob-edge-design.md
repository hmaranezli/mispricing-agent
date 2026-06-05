# Scout CLOB Edge Entegrasyonu — Design

**Goal:** Scout, edge hesabını market API (stale) yerine CLOB gerçek zamanlı fiyatıyla yapar. Council gecikmesi 10-20s → 2-4s'ye düşer.

**Problem:** Scout market API `bestAsk` kullanıyor (10-30s gecikmeli). Verifier CLOB'u kontrol ediyor → edge_gone → 0 trade. Tüm fırsat penceresi kaçıyor.

**Çözüm (A):**

### Scout değişikliği (`council/scout.py`)
- `_analyse_market()` içinde: market API'den `yes_token_id`, `no_token_id`, `seconds_remaining`, `ref_price` alınır (bu kısım aynı kalır)
- `window["best_ask"]` yerine: `await get_clob_price(yes_token_id)` çağrısı → gerçek CLOB ask fiyatı
- NO frame: `1 - await get_clob_price(no_token_id)` → YES bid
- CLOB None dönerse → market atlanır (likidite yok)
- Edge: `fair_yes - clob_ask` (YES) veya `clob_bid - fair_yes` (NO)
- Bulgu: `best_ask = clob_ask`, `best_bid = clob_bid` (taze, doğru)

### Verifier değişikliği (`council/verifier.py`)
- CLOB kontrolü kaldırılır (scout zaten yaptı)
- Sadece HL drift kontrolü kalır: `abs(fresh_hl - scout_hl) / scout_hl > 2%` → veto
- Diğer her şey kaldırılır (fresh_ask hesabı, CLOB çağrısı, seconds check)

### Config
- `MIN_EDGE_PCT = 0.05` ✅ (zaten yapıldı)

### Test
- Scout testleri: `get_clob_price` mock → CLOB fiyatıyla edge hesabı doğru
- Verifier testleri: CLOB kontrolü yok, sadece HL drift veto testi
- Entegrasyon: 0 trade → gerçek trade akışı

**Değişmeyen:** RedTeam, Risk, Gate, main_loop, clob_executor
