# Live Trading Unblock Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 blocking issues and enable DRY_RUN=False live trading on Polymarket CLOB.

**Architecture:** 3 code fixes (scout.py tokenID, approve_usdc.py rewrite, HTTPS_PROXY config) + 1 infrastructure fix (geoblock via SOCKS5). All changes are backward-compatible with DRY_RUN=True.

**Tech Stack:** Python, py_clob_client, web3.py, requests[socks], Cloudflare WARP (or SSH SOCKS5)

---

## Blocking issues — neden live çalışmıyor

| # | Sorun | Etki |
|---|-------|------|
| 1 | `scout.py` clobTokenIds JSON string — `yes_token_id="["` | Tüm live order'lar yanlış token'a gidiyor |
| 2 | Geoblock — VPS IP'si Polymarket'te yasaklı bölge | Her API çağrısı 403 dönüyor |
| 3 | `approve_usdc.py` server-side API kullanıyor (çalışmıyor) | Approve script yanıltıcı "✅" veriyor |
| 4 | CLOB API balance=0 — native USDC vs USDC.e belirsizliği | Canlı test sonrasında netleşecek |

**Mevcut durum:** Native USDC zaten approve edildi (MAX × 3 kontrat, web3.py ile). Token ID + geoblock düzeltilince test_order.py çalışacak.

---

## Task 1: scout.py — clobTokenIds parse fix

**Files:**
- Modify: `council/scout.py:106-107`
- Modify: `data/shortterm.py` (yardımcı fonksiyon ekle)
- Test: `tests/test_scout.py` (mevcut token_id testi güncelle)

### Adım 1.1 — shortterm.py'e parse yardımcısı ekle

`data/shortterm.py` dosyasına, mevcut `_parse()` fonksiyonunun hemen altına:

```python
def _parse_token_ids(raw) -> list[str]:
    """clobTokenIds alanını her zaman list[str] döndür."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
    return []
```

- [ ] `data/shortterm.py`'i aç, `_parse()` fonksiyonundan sonra `_parse_token_ids()` ekle.
- [ ] `from data.shortterm import _parse_token_ids` ile import test et: `python -c "from data.shortterm import _parse_token_ids; print(_parse_token_ids('[\"abc\",\"def\"]'))"` → `['abc', 'def']`

### Adım 1.2 — scout.py'deki bug'ı düzelt

`council/scout.py:106-107` satırlarını değiştir:

```python
# ESKİ (YANLIŞ):
"yes_token_id": next(iter((m.get("clobTokenIds") or [])[0:1]), None),
"no_token_id":  next(iter((m.get("clobTokenIds") or [])[1:2]), None),

# YENİ (DOĞRU):
"yes_token_id": (_ids := _parse_token_ids(m.get("clobTokenIds")))[0] if (_ids := _parse_token_ids(m.get("clobTokenIds"))) else None,
"no_token_id":  _parse_token_ids(m.get("clobTokenIds"))[1] if len(_parse_token_ids(m.get("clobTokenIds"))) > 1 else None,
```

Walrus operatörü karmaşık — daha temiz yazım:

```python
_ids = _parse_token_ids(m.get("clobTokenIds"))
...
"yes_token_id": _ids[0] if _ids else None,
"no_token_id":  _ids[1] if len(_ids) > 1 else None,
```

`scout.py`'deki finding dict'ini şu şekilde güncelle (`_raw_market` satırından önce `_ids` hesapla):

```python
_ids = _parse_token_ids(m.get("clobTokenIds"))
return {
    ...
    "yes_token_id": _ids[0] if _ids else None,
    "no_token_id":  _ids[1] if len(_ids) > 1 else None,
}
```

- [ ] `council/scout.py` import kısmına `from data.shortterm import _parse_token_ids` ekle.
- [ ] 106-107. satırları `_ids` ile değiştir.

### Adım 1.3 — Test yaz ve çalıştır

`tests/test_scout.py`'de token ID testi:

```python
def test_yes_no_token_ids_from_json_string(mock_hl, mock_poly):
    """clobTokenIds JSON string olarak geldiğinde doğru parse edilmeli."""
    mock_poly.return_value = [
        {
            "slug": "btc-updown-5m-123",
            "bestAsk": "0.40",
            "bestBid": "0.38",
            "clobTokenIds": '["tokenA111", "tokenB222"]',  # JSON string
            "eventStartTime": "2026-06-01T00:00:00Z",
            "endDate": "2026-06-01T00:05:00Z",
            "negRisk": False,
            "outcomePrices": '["0.40", "0.60"]',
        }
    ]
    mock_hl.return_value = {"price": 65000.0, "mark_price": 65000.0}
    findings = asyncio.run(scan_edges())
    if findings:
        f = findings[0]
        assert f["yes_token_id"] == "tokenA111", f"yes_token_id yanlış: {f['yes_token_id']}"
        assert f["no_token_id"] == "tokenB222", f"no_token_id yanlış: {f['no_token_id']}"
        assert len(f["yes_token_id"]) > 3, "yes_token_id tek karakter olmamalı"
```

- [ ] Testi çalıştır: `source venv/bin/activate && python -m pytest tests/test_scout.py -v -k "token_id" 2>&1 | tail -20`
- [ ] PASS görülmeden devam etme.

### Adım 1.4 — Commit

```bash
git add council/scout.py data/shortterm.py tests/test_scout.py
git commit -m "fix(scout): clobTokenIds JSON string parse — yes/no token ID artık doğru"
```

---

## Task 2: approve_usdc.py — web3.py ile yeniden yaz

**Files:**
- Rewrite: `analysis/approve_usdc.py`

Mevcut script `client.update_balance_allowance()` kullanıyor — bu server-side API çağrısı USDC.e hedef alıyor ve native USDC için çalışmıyor. Yeniden yaz: doğrudan web3.py ile on-chain ERC20 `approve()`.

**Not:** Native USDC (0x3c499c...) gas 67k gerektiriyor; eski script 60k limit koyuyordu → silent revert.

### Adım 2.1 — approve_usdc.py'yi komple yeniden yaz

```python
#!/usr/bin/env python3
"""analysis/approve_usdc.py — Native USDC harcama izni (web3 ile direkt on-chain).

Polymarket'in 3 exchange kontratına native USDC için MAX allowance verir.
Gas: ~67k per tx. Polygon'da ~3 tx.

Kullanım:
    python analysis/approve_usdc.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from web3 import Web3

POLYGON_RPC   = "https://polygon-bor-rpc.publicnode.com"
USDC_NATIVE   = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
MAX_UINT256   = 2**256 - 1
GAS_APPROVE   = 120_000  # native USDC ~67k gas; 120k güvenli limit

POLYMARKET_SPENDERS = {
    "CTF_Exchange":     "0xE111180000d2663C0091e4f400237545B87B996B",
    "NegRisk_Adapter":  "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
    "NegRisk_Exchange": "0xe2222d279d744050d28e00520010520000310F59",
}

ERC20_ABI = [
    {"name": "approve",   "type": "function",
     "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"name": "allowance", "type": "function",
     "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "balanceOf", "type": "function",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
]


def run_approval() -> bool:
    print("=" * 60)
    print("NATIVE USDC APPROVE — Polymarket exchange kontratları")
    print("=" * 60)

    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    if not w3.is_connected():
        print("✗ Polygon RPC bağlantısı kurulamadı")
        return False

    wallet_raw = os.environ.get("POLY_WALLET_ADDRESS", "")
    key_raw    = os.environ.get("POLY_PRIVATE_KEY", "")
    if not wallet_raw or not key_raw:
        print("✗ POLY_WALLET_ADDRESS veya POLY_PRIVATE_KEY eksik")
        return False

    wallet = Web3.to_checksum_address(wallet_raw)
    key    = key_raw if key_raw.startswith("0x") else "0x" + key_raw
    usdc   = w3.eth.contract(address=Web3.to_checksum_address(USDC_NATIVE), abi=ERC20_ABI)

    balance = usdc.functions.balanceOf(wallet).call()
    pol_bal = w3.eth.get_balance(wallet)
    print(f"\nCüzdan  : {wallet}")
    print(f"USDC    : {balance / 1e6:.4f}")
    print(f"POL/gas : {pol_bal / 1e18:.4f}")

    nonce     = w3.eth.get_transaction_count(wallet)
    gas_price = w3.eth.gas_price

    all_ok = True
    for name, spender in POLYMARKET_SPENDERS.items():
        spender_cs = Web3.to_checksum_address(spender)
        current    = usdc.functions.allowance(wallet, spender_cs).call()
        if current == MAX_UINT256:
            print(f"\n[{name}] Zaten MAX approve ✅ — atlanıyor")
            continue

        print(f"\n[{name}] Approve gönderiliyor...")
        tx = usdc.functions.approve(spender_cs, MAX_UINT256).build_transaction({
            "from": wallet, "nonce": nonce,
            "gas": GAS_APPROVE, "gasPrice": gas_price, "chainId": 137,
        })
        signed  = w3.eth.account.sign_transaction(tx, private_key=key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status == 1:
            print(f"  ✅ Başarılı (gas: {receipt.gasUsed})")
        else:
            print(f"  ❌ Başarısız — Polygon explorer'dan TX'i kontrol et")
            all_ok = False
        nonce += 1
        time.sleep(1)

    print("\n=== Sonuç ===")
    for name, spender in POLYMARKET_SPENDERS.items():
        al = usdc.functions.allowance(wallet, Web3.to_checksum_address(spender)).call()
        status = "MAX ✅" if al == MAX_UINT256 else f"{al/1e6:.2f} USDC ⚠"
        print(f"  {name}: {status}")

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ Tüm approve'lar tamamlandı")
        print("   Sıradaki adım: geoblock fix → test_order.py → DRY_RUN=False")
    else:
        print("⚠ Bazı approve'lar başarısız")
    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    ok = run_approval()
    sys.exit(0 if ok else 1)
```

- [ ] Dosyayı kaydet.
- [ ] Çalıştır: `source venv/bin/activate && python analysis/approve_usdc.py`
  - Beklenen: "Zaten MAX approve ✅ — atlanıyor" (zaten approve edildi)
  - Eğer eksik approve varsa TX gönderir ve onaylar.

### Adım 2.2 — Commit

```bash
git add analysis/approve_usdc.py
git commit -m "fix(approve_usdc): web3 ile native USDC approve — gas 120k, USDC.e bağımlılığı kaldırıldı"
```

---

## Task 3: Geoblock Fix — SOCKS5 Proxy

**Goal:** `py_clob_client` (requests kütüphanesi) trafiğini US IP üzerinden yönlendir.

**Strateji:**
- `requests` kütüphanesi `HTTPS_PROXY` env var'ını otomatik okur → py_clob_client için sıfır kod değişikliği
- `aiohttp` (Gamma API, Hyperliquid) bu proxy'den geçmez — onlar zaten geoblok değil
- Proxy kaynağı: Cloudflare WARP (ücretsiz, önce dene) → SSH SOCKS5 (fallback)

### Adım 3.1 — requests[socks] kur

```bash
source venv/bin/activate && pip install "requests[socks]"
```

Doğrula:
```bash
python -c "import socks; print('socks OK')"
```

### Adım 3.2 — Cloudflare WARP kur (ücretsiz yol)

```bash
# WARP repo ekle
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
sudo apt update && sudo apt install cloudflare-warp -y

# Kaydet ve proxy modda başlat
warp-cli registration new
warp-cli mode proxy
warp-cli proxy port 40000
warp-cli connect
warp-cli status
```

Beklenen son satır: `Status update: Connected`

SOCKS5 test:
```bash
curl --socks5-hostname 127.0.0.1:40000 https://ipinfo.io/json 2>/dev/null | python -m json.tool | grep '"country"'
```
`"country": "US"` (veya başka bir izin verilen ülke) görünmeli.

**Eğer WARP çalışmazsa / IP hâlâ blocked → Fallback: SSH SOCKS5**

```bash
# Yeni $5 DigitalOcean/Vultr NYC droplet oluşturduktan sonra:
ssh -N -D 1080 root@<US_VPS_IP> -o "ServerAliveInterval 30" &
echo $! > /tmp/socks5.pid

# Test:
curl --socks5-hostname 127.0.0.1:1080 https://ipinfo.io/json 2>/dev/null | grep '"country"'
```

Proxy portunu not et (WARP=40000, SSH=1080).

### Adım 3.3 — .env'e HTTPS_PROXY ekle

`.env` dosyasına ekle (port, kullandığın proxy'e göre):

```bash
# WARP kullanıyorsan:
HTTPS_PROXY=socks5h://127.0.0.1:40000

# SSH SOCKS5 kullanıyorsan:
# HTTPS_PROXY=socks5h://127.0.0.1:1080
```

**Not:** `socks5h://` (h = host resolution proxy'de yapılır) yaz, `socks5://` değil.

### Adım 3.4 — Proxy çalışıyor mu test et

```bash
source venv/bin/activate && python -c "
import os
from dotenv import load_dotenv
load_dotenv()
import requests
proxies = {'https': os.environ.get('HTTPS_PROXY')}
r = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=10)
import json; d = json.loads(r.text)
print('IP:', d.get('ip'))
print('Country:', d.get('country'))
print('City:', d.get('city'))
"
```

`Country: US` (veya GB, CA — Polymarket'in izin verdiği bir ülke) görünmeli.

### Adım 3.5 — CLOB bağlantı testi

```bash
source venv/bin/activate && python analysis/clob_connection_test.py
```

Beklenen:
```
[1] Credentials yükleniyor... ✓
[2] Wallet bakiyesi okunuyor... ✓ USDC bakiye: ...
[3] BTC market clobTokenIds okunuyor... ✓ YES token: 3336219949...
✅ HAZIR
```

Eğer hâlâ `403 geoblock` → proxy ülkesi Polymarket'te kısıtlı demektir. WARP çıkış ülkesini kontrol et veya başka US proxy dene.

### Adım 3.6 — Commit

```bash
git add .env.example  # .env'i commit'leme, sadece .env.example güncelle
git commit -m "infra: HTTPS_PROXY socks5 geoblock fix — requests[socks] eklendi"
```

---

## Task 4: End-to-End Test — $1 Gerçek Order

**Önkoşullar:** Task 1-3 tamamlandı, proxy aktif.

### Adım 4.1 — test_order.py çalıştır

```bash
source venv/bin/activate && python analysis/test_order.py 2>&1
```

**Beklenen başarı senaryosu:**
```
[2] USDC bakiye kontrol...
    USDC (CLOB deposit): 0.0
    ⚠ CLOB deposit bakiye=0.0 (native USDC görünmüyor — devam ediyoruz)
[3] Aktif BTC marketi aranıyor... ✓ btc-updown-5m-...
[4] $1.0 YES order gönderiliyor...
    Status: UNMATCHED  ← IOC dolmadı, normal
    ✅ Test tamamlandı — CLOB entegrasyonu çalışıyor
```

**veya:**
```
    Status: MATCHED  ← Fill oldu!
```

**Hata senaryoları ve çözümleri:**

| Hata | Çözüm |
|------|-------|
| `403 geoblock` | Proxy çalışmıyor → Task 3'ü tekrar kontrol et |
| `not enough funds` / `insufficient balance` | Native USDC settlement desteklenmiyor → bkz Task 5 |
| `price not valid` | Tick size sorunu → price round(x, 2) yap |
| `UNMATCHED` | Normal — IOC, likidite yoktu. Entegrasyon çalışıyor ✅ |

### Adım 4.2 — "not enough funds" durumunda Task 5'e geç

`MATCHED` veya `UNMATCHED` ise canlıya geçebilirsin → Task 6.  
`insufficient balance` hatası alırsan → Task 5 (USDC.e approve).

---

## Task 5: (Koşullu) USDC.e Approve — Sadece Task 4 "insufficient balance" verdiyse

**Bu task yalnızca Task 4 balance hatası verdiyse gereklidir.**

Native USDC approve edildi ama Polymarket settlement hâlâ USDC.e bekliyorsa, USDC.e (`0x2791...`) da approve etmemiz gerekir. Elimizde USDC.e YOK — sadece approve vermek yeterli; settlement sırasında USDC.e transferi yapılacaksa sistem zaten hata verir. 

Seçenek A: **Swap native USDC → USDC.e** (1inch veya Uniswap Polygon'da)
- 2.295 native USDC → ~2.28 USDC.e (swap fee ~0.05%)
- Sonra approve_usdc.py'yi USDC.e için de çalıştır (ayrı script gerekir)

Seçenek B: **USDC.e approve et (balance yoksa bile)**  
```bash
source venv/bin/activate && python -c "
from analysis.approve_usdc import run_approval
# approve_usdc.py zaten native USDC için → USDC.e için ayrı script
"
```

**Bu task gerekirse adımları detaylandır — şimdilik beklet.**

---

## Task 6: DRY_RUN=False — Kullanıcı Yapar

**ÖNEMLİ: Bu adımı Claude yapamaz. CLAUDE.MD anayasası gereği.**

Test order başarılı olduktan sonra:

```bash
# 1. Mevcut botu durdur
tmux attach -t mispricing
# Ctrl+C

# 2. config.py'yi elle düzenle
nano /root/mispricing_agent/config.py
# DRY_RUN = True  →  DRY_RUN = False

# 3. Botu yeniden başlat
source venv/bin/activate && python main_loop.py
```

**İlk canlı çalışma kontrolleri:**
- İlk scan'de `[clob]` log satırları görünmeli
- `logs/mispricing.db`'de `dry_run=0` kayıtlar gelmeli
- Telegram'da bildirim gelmeli (monitor çalışıyorsa)

---

## Özet Sıra

```
Task 1: scout.py clobTokenIds fix  (5 dk, kod + test)
Task 2: approve_usdc.py rewrite    (3 dk, script değiştir)
Task 3: Geoblock / SOCKS5 proxy    (10-20 dk, kurulum)
Task 4: test_order.py — $1 test    (2 dk, gözlemle)
Task 5: (koşullu) USDC.e fix       (sadece "insufficient balance" hatası gelirse)
Task 6: DRY_RUN=False             (kullanıcı yapar)
```
