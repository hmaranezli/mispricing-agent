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

POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
MAX_UINT256 = 2**256 - 1
GAS_APPROVE = 120_000  # native USDC ~67k gas; 120k güvenli limit

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
            print(f"  ❌ Başarısız")
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
    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    ok = run_approval()
    sys.exit(0 if ok else 1)
