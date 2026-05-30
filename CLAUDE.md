# CLAUDE.md — Mispricing Bot Anayasası

> Bu dosya projenin anayasasıdır. Claude Code her oturumda bunu okur ve bu kuralların DIŞINA ÇIKAMAZ. Bu kurallar kullanıcının (insanın) açık izni olmadan değiştirilemez.

## PROJE
Polymarket kısa vadeli crypto "Up/Down" marketleri ile Hyperliquid perp gerçek fiyat hareketini karşılaştıran mispricing botu. Hyperliquid net yön gösterip Polymarket o yönü fiyatlamadığında = aday işlem. Ortalama tutuş ~14 dakika. Hedef ~%71 kazanma oranı. Bu RİSKSİZ ARBİTRAJ DEĞİLDİR — kayıplar olur, risk yönetimi bu yüzden vardır.

## DEĞİŞMEZ KURALLAR (anayasa)

### 1. Sormadan değişiklik yok
- `config.py` içindeki guardrail sabitlerini (DRY_RUN, limitler, eşikler) ASLA değiştirme.
- Mimaride, risk parametrelerinde veya işlem mantığında değişiklik gerekiyorsa ÖNCE insana söyle, onay al. Onaysız değiştirme.

### 2. DRY_RUN varsayılan
- `DRY_RUN=True` iken hiçbir gerçek order gönderilmez, sadece "şunu yapardım" loglanır.
- Canlıya (`DRY_RUN=False`) geçiş YALNIZCA insanın açık, yazılı komutuyla olur. Claude bunu kendiliğinden yapamaz.

### 3. Verisiz/uydurma işlem yok (anti-hallucination)
- Hiçbir fiyat, funding, olasılık veya hareket hafızadan ya da tahminden YAZILMAZ.
- Her sayı, kullanıldığı anda gerçek API'den taze çekilir.
- Bir karar verilecekse, o kararın dayandığı veri loglanır (kaynak + zaman damgası).
- API verisi ile hesaplanan değer çelişirse → işlem DURUR (`HALT_ON_API_MISMATCH`).

### 4. Konsey onayı zorunlu
- Hiçbir işlem tek bir kontrolden geçerek açılamaz.
- 5 katman (Scout → Verifier → RedTeam → Risk → Gate) sırayla onaylamalı.
- Bir katman bile "hayır/veto" derse işlem açılmaz.

### 5. Risk limitleri kutsaldır
- Tek işlem max sermayenin %5'i.
- Aynı anda max 5 açık pozisyon.
- Günlük kayıp %10'a ulaşınca TÜM SİSTEM DURUR.
- `HUMAN_APPROVAL_USD` üstü pozisyon insan onayı ister.

### 6. Test-önce (TDD)
- Para hareket ettiren veya karar veren her modül, önce testiyle yazılır.
- Test geçmeden o modül "bitti" sayılmaz.

### 7. Her şey loglanır
- Her aday, her veto, her işlem gerekçesiyle PostgreSQL'e yazılır.
- "Neden açtın / neden açmadın / neden kapattın" sorusunun cevabı her zaman kayıtta olmalı.

## ÇALIŞMA TARZI
- Koda atlamadan önce sor, tasarımı netleştir.
- Her adımdan sonra dur, özetle, onay bekle.
- Emin olmadığın bir şeyi uydurma — sor.
- Mevcut elle yazılmış dosyalar TASLAKTIR; mantık referansı olarak kullan ama testli yeniden yaz.

## DOSYA YAPISI
```
mispricing_agent/
├── config.py          # ANAYASA sabitleri (dokunma)
├── data/              # veri katmanı (Polymarket + Hyperliquid)
├── council/           # 5 katman: scout, verifier, redteam, risk, gate
├── execution/         # order mantığı (DRY_RUN'da)
├── position/          # pozisyon yönetimi (14 dk / sinyal dönüşü)
├── monitor/           # Telegram bildirim + kill switch
└── db/                # PostgreSQL log
```

## BUILD TALİMATI (yeni oturum başlangıcı)

Bir kripto mispricing trading botu inşa ediyoruz. Aşağıdaki kurallara KESİNLİKLE uy. CLAUDE.md dosyasındaki anayasa kuralları her şeyin üstündedir; onlara aykırı tek satır yazma.

### Ne yapıyoruz
Polymarket'in kısa vadeli "Up or Down" crypto marketleri (BTC, ETH, SOL, XRP — 5dk/15dk/saatlik) ile Hyperliquid'in gerçek perp fiyat hareketini karşılaştıran bir bot. Hyperliquid'de gerçek bir yön hareketi varken Polymarket o yönü henüz fiyatlamamışsa = mispricing = aday işlem. Ortalama tutuş ~14 dakika.

### Çalışma yöntemi (zorunlu)
1. ÖNCE bana soru sor, tasarımı netleştir. Koda hemen atlama (Superpowers brainstorm akışını kullan).
2. Her modül için ÖNCE test yaz, sonra kod (TDD — kırmızı/yeşil).
3. Her adımdan sonra dur, ne yaptığını özetle, onayımı bekle.
4. config.py'deki guardrail sabitlerini ASLA değiştirme. Değişiklik istersen bana söyle, ben elle yaparım.
5. Hiçbir sayıyı uydurma. Her fiyat/funding/hareket gerçek API'den taze çekilecek.

### Mevcut durum
Şu dosyalar elle yazıldı, TASLAK kabul et — mantığı doğru ama testsiz, düzgün yeniden yaz:
- `data/polymarket.py` — Polymarket genel market çekme
- `data/shortterm.py` — kısa vadeli Up/Down market bulucu (slug'dan)
- `data/hyperliquid.py` — anlık perp durumu
- `data/hl_candles.py` — gerçek geçmiş fiyat (candle)
- `council/scout.py` — Katman 1: edge tarama
- `config.py` — ANAYASA (dokunma)

### 5 katmanlı konsey (sırayla inşa edilecek)
1. **Scout** — 80+ marketi tarar, gerçek mispricing arar (var, sağlamlaştırılacak)
2. **Verifier** — Scout'un bulduğu fiyatı tekrar API'den teyit eder. Uyuşmazsa işlem durur.
3. **RedTeam** — işlemin aleyhine argüman üretir (likidite ince mi? market kapanıyor mu? satılamayan kontrat mı?). İkna olmazsa veto.
4. **Risk** — Kelly sizing + config limitleri + margin kontrolü. Fee sonrası edge pozitif mi?
5. **Gate** — 4 katman geçtiyse + güven eşiği üstündeyse işlem. Büyük pozisyon insan onayı ister.

### İlk görev (yeni oturumda)
1. Mevcut taslak dosyaları oku ve anla.
2. Bana mimariyi özetle, sorularını sor.
3. Onayımı alınca Scout'u TDD ile düzgün yeniden yaz + 80+ markete genişlet (BTC/ETH/SOL/XRP × 5dk/15dk/saatlik × son birkaç pencere).
4. Her şey DRY_RUN modunda, hiçbir gerçek order yok.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
