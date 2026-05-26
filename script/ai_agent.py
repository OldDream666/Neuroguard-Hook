#!/usr/bin/env python3
"""
NeuroGuard Hook — Off-Chain AI Sentiment Agent (Real Data)
===========================================================
Fetches real market data from CoinGecko (free, no API key),
computes a risk score 0-10, and calls setRiskLevel() on the
deployed NeuroGuardHook contract via X Layer testnet.

Usage:
    cp .env.example .env   # fill in your keys
    pip install -r requirements.txt
    python ai_agent.py              # run once
    python ai_agent.py --loop 60    # loop every 60 seconds
    python ai_agent.py --dry-run    # score only, no tx
    python ai_agent.py --score 7    # manual override
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests
from web3 import Web3
from dotenv import load_dotenv

# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("NeuroGuard-Agent")

# ──────────────────────────────────────────────
#  Environment
# ──────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

RPC_URL = os.getenv("RPC_URL", "https://testrpc.xlayer.tech")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
HOOK_ADDRESS = os.getenv("HOOK_ADDRESS", "")
CHAIN_ID = int(os.getenv("CHAIN_ID", "1952"))

# Token to monitor (CoinGecko ID)
# Common: ethereum, bitcoin, solana, dogecoin, pepe, shiba-inu
TOKEN_ID = os.getenv("TOKEN_ID", "ethereum")

# ──────────────────────────────────────────────
#  Minimal ABI (only what we need)
# ──────────────────────────────────────────────
HOOK_ABI = [
    {
        "inputs": [{"internalType": "uint8", "name": "_riskScore", "type": "uint8"}],
        "name": "setRiskLevel",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "riskScore",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "aiAgent",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]


# ═══════════════════════════════════════════════
#  Real Market Data — CoinGecko (Free, No API Key)
# ═══════════════════════════════════════════════

SENTIMENT_LABELS = {
    range(0, 3):  "🟢 CALM — Normal trading conditions",
    range(3, 5):  "🟡 CAUTIOUS — Mild concern detected",
    range(5, 8):  "🟠 FEAR — Significant negative sentiment",
    range(8, 11): "🔴 PANIC — Extreme FUD, activating sell-side defense",
}


def fetch_market_data(token_id: str) -> dict | None:
    """
    Fetch real market data from CoinGecko free API.
    Returns dict with: price, 24h_change, 24h_volume, market_cap.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": token_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if token_id not in data:
            log.error("Token '%s' not found in CoinGecko response", token_id)
            return None

        token_data = data[token_id]
        return {
            "price_usd": token_data.get("usd", 0),
            "change_24h": token_data.get("usd_24h_change", 0),  # percentage
            "volume_24h": token_data.get("usd_24h_vol", 0),
            "market_cap": token_data.get("usd_market_cap", 0),
        }
    except requests.RequestException as e:
        log.error("Failed to fetch CoinGecko data: %s", e)
        return None


def fetch_historical_volume(token_id: str) -> float:
    """
    Fetch 7-day average volume to compare against current volume.
    Returns average daily volume in USD.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart"
    params = {"vs_currency": "usd", "days": "7", "interval": "daily"}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        volumes = [v[1] for v in data.get("total_volumes", [])]
        if volumes:
            return sum(volumes) / len(volumes)
        return 0
    except requests.RequestException:
        return 0


def compute_risk_score(market: dict, avg_volume: float) -> int:
    """
    Compute risk score 0-10 from real market signals.

    Signals:
      1. 24h price change (negative = bearish)  — weight 70%
      2. Volume spike (high volume + drop = panic selling) — weight 30%

    Scoring:
      price_change  → risk contribution
      -3% ~ 0%      → 0-2   (calm)
      -7% ~ -3%     → 2-4   (cautious)
      -15% ~ -7%    → 4-7   (fear)
      < -15%         → 7-10  (panic)
      positive       → 0-2   (bullish, low risk)
    """
    change = market["change_24h"]  # e.g. -5.2 means -5.2%

    # ── Signal 1: Price change → risk ──
    if change >= 0:
        price_risk = 0  # bullish, no risk
    elif change >= -2:
        price_risk = abs(change) / 2 * 2        # 0-2
    elif change >= -5:
        price_risk = 2 + (abs(change) - 2) / 3 * 2  # 2-4
    elif change >= -10:
        price_risk = 4 + (abs(change) - 5) / 5 * 3  # 4-7
    else:
        price_risk = min(10, 7 + (abs(change) - 10) / 10 * 3)  # 7-10

    # ── Signal 2: Volume spike multiplier ──
    volume_multiplier = 1.0
    if avg_volume > 0 and market["volume_24h"] > 0:
        ratio = market["volume_24h"] / avg_volume
        if ratio > 3.0:
            volume_multiplier = 1.5   # massive volume spike during dump
        elif ratio > 2.0:
            volume_multiplier = 1.3
        elif ratio > 1.5:
            volume_multiplier = 1.1
        # Low volume dump is less concerning
        elif ratio < 0.5:
            volume_multiplier = 0.8

    # ── Final score ──
    raw_score = price_risk * volume_multiplier
    risk_score = min(10, max(0, round(raw_score)))

    return risk_score


def analyze_market() -> int:
    """
    Full pipeline: fetch real data → compute risk → return score.
    This replaces the old simulate_ai_sentiment() with real market analysis.
    """
    log.info("📡 Fetching market data for '%s' from CoinGecko...", TOKEN_ID)

    market = fetch_market_data(TOKEN_ID)
    if market is None:
        log.warning("⚠️  Could not fetch market data, defaulting to risk=0")
        return 0

    # Fetch 7-day average volume for comparison
    avg_vol = fetch_historical_volume(TOKEN_ID)

    # Log the real data
    log.info("💰 Price: $%s", f"{market['price_usd']:,.2f}")
    log.info("📊 24h Change: %s%%", f"{market['change_24h']:+.2f}")
    log.info("📈 24h Volume: $%s", f"{market['volume_24h']:,.0f}")
    if avg_vol > 0:
        vol_ratio = market['volume_24h'] / avg_vol
        log.info("📉 7d Avg Volume: $%s (current/avg = %.2fx)", f"{avg_vol:,.0f}", vol_ratio)

    # Compute risk
    risk_score = compute_risk_score(market, avg_vol)

    # Label
    label = "UNKNOWN"
    for r, lbl in SENTIMENT_LABELS.items():
        if risk_score in r:
            label = lbl
            break
    log.info("🧠 AI Risk Score: %d/10  →  %s", risk_score, label)

    return risk_score


# ═══════════════════════════════════════════════
#  On-Chain Interaction
# ═══════════════════════════════════════════════

def init_web3() -> Web3:
    """Initialize Web3 connection."""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        log.error("❌ Failed to connect to RPC: %s", RPC_URL)
        sys.exit(1)
    log.info("✅ Connected to X Layer (chain %d) via %s", CHAIN_ID, RPC_URL)
    return w3


def get_hook_contract(w3: Web3):
    """Return contract instance."""
    if not HOOK_ADDRESS:
        log.error("❌ HOOK_ADDRESS not set in .env")
        sys.exit(1)
    return w3.eth.contract(
        address=Web3.to_checksum_address(HOOK_ADDRESS),
        abi=HOOK_ABI,
    )


def verify_agent(w3: Web3, contract, account: str):
    """Verify that the private key matches the contract's aiAgent."""
    on_chain_agent = contract.functions.aiAgent().call()
    if on_chain_agent.lower() != account.lower():
        log.error(
            "❌ Wallet mismatch!\n"
            "   Your address:  %s\n"
            "   Contract aiAgent: %s\n"
            "   Only the aiAgent can call setRiskLevel.",
            account,
            on_chain_agent,
        )
        sys.exit(1)
    log.info("🔐 Agent verification passed: %s", account)


def get_current_risk(contract) -> int:
    """Read current risk score from chain."""
    score = contract.functions.riskScore().call()
    log.info("📊 Current on-chain risk score: %d", score)
    return score


def send_risk_update(w3: Web3, contract, new_score: int) -> str:
    """
    Build, sign, and send setRiskLevel transaction.
    Returns tx hash.
    """
    account = w3.eth.account.from_key(PRIVATE_KEY)
    current = get_current_risk(contract)

    if current == new_score:
        log.info("⏭️  Risk score unchanged (%d), skipping tx.", new_score)
        return ""

    # Build transaction
    tx = contract.functions.setRiskLevel(new_score).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": CHAIN_ID,
    })

    # Sign and send
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    log.info("📤 TX sent: %s", tx_hash.hex())

    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status == 1:
        log.info("✅ TX confirmed in block %d — risk score: %d → %d",
                 receipt.blockNumber, current, new_score)
    else:
        log.error("❌ TX reverted! Check on explorer.")

    return tx_hash.hex()


# ═══════════════════════════════════════════════
#  Main Loop
# ═══════════════════════════════════════════════

def run_once(w3, contract):
    """Single iteration: fetch real data → score → send if changed."""
    log.info("─" * 50)
    score = analyze_market()
    tx_hash = send_risk_update(w3, contract, score)
    return tx_hash


def main():
    parser = argparse.ArgumentParser(description="NeuroGuard AI Sentiment Agent")
    parser.add_argument("--loop", type=int, default=0,
                        help="Run in loop mode with N-second interval (0 = run once)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score sentiment but don't send transactions")
    parser.add_argument("--score", type=int, default=None,
                        help="Override: manually set risk score (0-10), skip AI")
    args = parser.parse_args()

    # Dry run — only analyze market, no chain interaction needed
    if args.dry_run:
        log.info("🧪 DRY RUN mode — no transactions will be sent")
        log.info("   Monitoring: %s", os.getenv("TOKEN_ID", "ethereum"))
        analyze_market()
        return

    if not PRIVATE_KEY:
        log.error("❌ PRIVATE_KEY not set. Copy .env.example → .env and fill in.")
        sys.exit(1)

    w3 = init_web3()
    contract = get_hook_contract(w3)
    account = w3.eth.account.from_key(PRIVATE_KEY)

    log.info("🤖 NeuroGuard AI Agent starting")
    log.info("   Wallet:     %s", account.address)
    log.info("   Hook:       %s", HOOK_ADDRESS)
    log.info("   Monitoring: %s", TOKEN_ID)

    verify_agent(w3, contract, account.address)

    if args.score is not None:
        if not 0 <= args.score <= 10:
            log.error("Score must be 0-10")
            sys.exit(1)
        log.info("🎯 Manual mode: setting risk score to %d", args.score)
        send_risk_update(w3, contract, args.score)
        return

    if args.loop > 0:
        log.info("🔄 Loop mode: checking every %d seconds (Ctrl+C to stop)", args.loop)
        try:
            while True:
                run_once(w3, contract)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            log.info("\n👋 Agent stopped by user.")
    else:
        run_once(w3, contract)


if __name__ == "__main__":
    main()
