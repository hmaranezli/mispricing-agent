# Graph Report - mispricing_agent  (2026-05-31)

## Corpus Check
- 57 files · ~35,992 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 755 nodes · 1211 edges · 41 communities (39 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `66ce1259`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]

## God Nodes (most connected - your core abstractions)
1. `scan_edges()` - 36 edges
2. `verify()` - 30 edges
3. `fair_yes()` - 25 edges
4. `risk()` - 24 edges
5. `redteam()` - 22 edges
6. `current_price()` - 18 edges
7. `parse_market_window()` - 18 edges
8. `execute()` - 17 edges
9. `check_exit()` - 16 edges
10. `_monitor_positions()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_scan_edges_returns_list()` --calls--> `scan_edges()`  [EXTRACTED]
  tests/test_scout.py → council/scout.py
- `_run_council()` --calls--> `gate()`  [EXTRACTED]
  main_loop.py → council/gate.py
- `_run_council()` --calls--> `redteam()`  [EXTRACTED]
  main_loop.py → council/redteam.py
- `_run_council()` --calls--> `risk()`  [EXTRACTED]
  main_loop.py → council/risk.py
- `_run_council()` --calls--> `verify()`  [EXTRACTED]
  main_loop.py → council/verifier.py

## Communities (41 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (47): _asset_of(), _edge_signal(), float, str, fair: fair_yes değeri [0,1]     best_ask: YES almak için ödeyeceğimiz fiyat, tests/test_scout.py — council/scout.py testleri. Unit testler (_asset_of, _edge_, Her bulgu zorunlu alanları içeriyor., Dönen tüm bulgular MIN_EDGE_PCT eşiği üstünde. (+39 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (34): bool, bool, float, str, _result(), _fake_finding(), council/verifier.py testleri. Gerçek API kullanılır — mock yok., Scout cur_price=1.0 (imkansız) iken HL taze fiyat ~73k → drift devasa → api_mism (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (36): fair_yes(), float, str, data/fair_value.py — Binary option fair value hesaplayıcı. Model: log-normal GBM, P(asset_price > p_ref at resolution | current_price = p_now)      Args:, tests/test_fair_value.py — data/fair_value.py unit testleri Gerçek API çağrısı y, Takip edilen tüm varlıklar ASSET_VOL sözlüğünde var ve pozitif., ETH daha yüksek vol kullandığı için aynı sapmayla daha geniş dağılım. (+28 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (33): main(), _process_market(), council/scout.py — KATMAN 1: Keşif Ajanı.  Edge tanımı (matematiksel):   fair_ye, Tek marketi değerlendirir. Edge yoksa veya veri eksikse None., current_price(), fetch_candles(), fetch_candles_range(), main() (+25 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (51): fetch_resolved(), _fetch_slug(), find_shortterm(), main(), _parse(), _parse_resolution(), str, data/shortterm.py — Kisa vadeli BTC/ETH Up/Down market bulucu. Slug'i o anki UTC (+43 more)

### Community 5 - "Community 5"
Cohesion: 0.43
Nodes (6): fetch_market_state(), main(), _post(), data/hyperliquid.py — Hyperliquid veri katmani (public, key gerekmez). BTC/ETH i, Basit yon gostergesi: mark vs oracle + gunluk degisim + funding., _signal()

### Community 6 - "Community 6"
Cohesion: 0.53
Nodes (5): fetch_crypto_markets(), _fmt(), main(), _parse(), data/polymarket.py — Polymarket veri katmani (ADIM 1: canli fiyat cekme) Gamma A

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (23): 1. Sormadan değişiklik yok, 2. DRY_RUN varsayılan, 3. Verisiz/uydurma işlem yok (anti-hallucination), 4. Konsey onayı zorunlu, 5 katmanlı konsey (sırayla inşa edilecek), 5. Risk limitleri kutsaldır, 6. Test-önce (TDD), 7. Her şey loglanır (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (70): main(), council/gate.py — KATMAN 5: Kapı.  Son karar ve uygulama katmanı. 4 katmandan ge, Manuel test: Scout→Verifier→RedTeam→Risk→Gate tam zinciri., _fee_adjusted_edge(), main(), _parse_taker_fee(), bool, float (+62 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (68): parse_market_window(), Ham Gamma market dict'inden scout'un ihtiyacı olan alanları çıkarır.     Returns, get_connection(), load_closed_today(), log_candidate(), log_position_close(), log_position_open(), bool (+60 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (35): check_exit(), close_position(), _log(), float, int, Path, str, position/manager.py — Açık pozisyon takibi ve çıkış kararı. (+27 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (34): execute(), _log(), Path, str, execution/executor.py — DRY_RUN order logger., Gate onaylı bulguyu DRY_RUN'da loglar, pozisyon kaydı döndürür., _finding(), _gate() (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (29): init_schema(), db/schema.py — SQLite şeması ve başlatma., conn(), tests/test_db.py — db/ birim testleri. aiosqlite in-memory, sıfır sunucu., positions tablosu ref_price ve edge sütunlarına sahip olmalı., log_position_open ref_price ve edge değerlerini DB'ye yazar., positions tablosu realized_pnl sütununa sahip olmalı., Kapanan pozisyonda realized_pnl hesaplanıp DB'ye yazılır.     entry=0.40, exit=0 (+21 more)

### Community 20 - "Community 20"
Cohesion: 0.21
Nodes (27): _kelly(), bool, float, int, str, Ham Kelly fraksiyonu. Bölme sıfırı (payda < 0.01) → 0.0., Pozisyon boyutlandırması ve sistem limiti kontrolü.      Args:         finding:, _result() (+19 more)

### Community 21 - "Community 21"
Cohesion: 0.23
Nodes (24): _confidence_score(), gate(), _gate_decide(), _log(), float, 0-100 güven skoru. 4 bileşen ağırlıklı toplam., Güven skoru hesapla, CONFIDENCE_THRESHOLD kontrolü yap., Kararı LOG_FILE'a yaz. Dizin yoksa oluşturur. (+16 more)

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (23): tests/test_monitor.py — monitor/ birim testleri. Sıfır gerçek HTTP/dosya., pm_exit_price yoksa P&L satırı olmaz., logs/KILL dosyası varsa check() True döner., logs/KILL dosyası yoksa check() False döner., Token + chat_id varsa requests.post çağrılır., Token yoksa requests.post hiç çağrılmaz., DRY_RUN=True iken mesaj '[DRY RUN]' ile başlar., notify_open mesajı asset ve action içerir. (+15 more)

### Community 23 - "Community 23"
Cohesion: 0.11
Nodes (17): 1. Günlük Kayıp Limiti (HALT), 2. Açık Pozisyon Limiti, 3. Edge Geçerlilik Kontrolü (çift emniyet), 4. Kelly Hesabı ve Minimum Pozisyon, 5. İnsan Onayı Bayrağı (VETO DEĞİL), Amaç, Bağımlılıklar, Dosya Yapısı (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (13): Akış, Amaç, Bağımlılıklar, Dosya Yapısı, Gelecek: DB Entegrasyonu, Güven Skoru Formülü, Input / Output, Kalibrasyon (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (12): Dosya Yapısı, Doğrulama, Risk Katmanı (Katman 4) Implementation Plan, Sabit Referanslar (config.py'den, değiştirme), Task 1: Skeleton + Output Şeması Testi, Task 2: `_kelly()` — YES ve NO Kolları, Task 3: Günlük Kayıp Limiti (Halt), Task 4: Açık Pozisyon Limiti (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (11): 10. Bağımlılıklar, 1. Amaç, 2. Arayüz, 3. Finding Yapısı (scout çıktısı — referans), 4. Guard Sırası, 5. Giriş Fiyatı Hesabı, 6. Pozisyon Kaydı (dönüş değeri), 7. JSONL Log (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (10): 1. `data/shortterm.py` — `fetch_resolved(slug)`, 2. `main_loop._monitor_positions` güncelleme, 3. P&L hesabı, 4. `monitor/notifier.notify_close` güncelleme, API Kanıtı, Değişmeyen Şeyler, P&L Resolution Design, Problem (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (8): Dosya Haritası, Matematiksel temel, Scout Fair Value Rewrite — Implementation Plan, Sıradaki Aşama (Bu Plandan Sonra), Task A1: data/fair_value.py — Binary Option Fair Value Modeli, Task A3: data/shortterm.py — parse_market_window() ekle, Task B1: council/scout.py — Tam Rewrite (Fair Value Modeli), Verification Checklist (Tamamlama Öncesi)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (9): 6 Kontrol, Amaç, Dosya Değişiklikleri, Eşik Sabitleri (redteam.py içinde), Fee Hesabı, RedTeam (Katman 3) — Tasarım Dokümanı, Sorumluluk Sınırı, Test Stratejisi (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (9): Amaç, Dosya Değişiklikleri, Doğrulama Akışı, İki Başarısızlık Türü, Output Formatı, Re-fetch Edilenler, Test Stratejisi, Tolerans Eşikleri (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (8): Dosya Yapısı, Doğrulama, Gate Katmanı (Katman 5) Implementation Plan, Sabit Referanslar (config.py'den, değiştirme), Task 1: Skeleton + `_confidence_score()` + 4 Test, Task 2: `_gate_decide()` + 3 Test, Task 3: `_log()` + `gate()` + 3 Async Test, Task 4: `main()` + Tam Test Koşusu

### Community 32 - "Community 32"
Cohesion: 0.25
Nodes (7): Dosya Haritası, Fonksiyon İmzaları (referans), main_loop Implementation Plan, Self-Review, Task 1: `main_loop.py` iskeleti + `_run_council()`, Task 2: `_scan_and_execute()`, Task 3: `_monitor_positions()`

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (7): Dosya Haritası, position/ Implementation Plan, Referans: Test Sabitleri, Self-Review, Task 1: `_log()` + `close_position()`, Task 2: `check_exit()` — zaman ve expiry kontrolleri, Task 3: `check_exit()` — thesis ve kâr hedefi

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (7): Dosya Haritası, Realized P&L + Daily Loss Restart Recovery Implementation Plan, Task 1: Schema Migration — `realized_pnl` Kolonu, Task 2: `log_position_close` — P&L Hesapla ve Yaz, Task 3: `load_closed_today` — Restart Recovery Sorgusu, Task 4: Main Loop Startup Recovery, Task 5: Tam Suite + Bot Restart

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (6): Dosya Haritası, execution/ Implementation Plan, Self-Review Notları, Task 1: `_log()` yardımcı fonksiyon, Task 2: Guard — gate fail ve max pozisyon, Task 3: execute() happy path — pozisyon kaydı

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (6): Dosya Haritası, P&L Resolution Implementation Plan, Task 1: `_parse_resolution` + `fetch_resolved` — shortterm.py, Task 2: `_monitor_positions` güncelleme, Task 3: `notify_close` P&L satırı, Task 4: Tam suite + bot restart

### Community 37 - "Community 37"
Cohesion: 0.33
Nodes (5): Dosya Haritası, monitor/ Implementation Plan, Task 1: monitor/notifier.py — 6 test, Task 2: monitor/kill_switch.py — 2 test, Task 3: main_loop.py entegrasyonu — mevcut 6 test kırılmaz

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (5): Dosya Haritası, Task 1: Scout'a slug ekle, Task 2: council/verifier.py — Bağımsız Doğrulayıcı, Verification Checklist (Tamamlama Öncesi), Verifier (Katman 2) Implementation Plan

### Community 39 - "Community 39"
Cohesion: 0.40
Nodes (4): Dosya Haritası, RedTeam (Katman 3) Implementation Plan, Task 1: council/redteam.py — Şeytan Avukatı, Verification Checklist

## Knowledge Gaps
- **164 isolated node(s):** `int`, `str`, `int`, `PreToolUse`, `allow` (+159 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `scan_edges()` connect `Community 15` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 16`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `verify()` connect `Community 15` to `Community 16`, `Community 1`, `Community 2`, `Community 3`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `fair_yes()` connect `Community 2` to `Community 17`, `Community 3`, `Community 15`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **What connects `int`, `main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü.`, `DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru` to the rest of the system?**
  _376 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0549645390070922 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06756756756756757 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.07396870554765292 - nodes in this community are weakly interconnected._