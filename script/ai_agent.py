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

# Token to monitor (OKX instrument ID)
# Common: ETH-USDT, BTC-USDT, SOL-USDT, DOGE-USDT, PEPE-USDT, SHIB-USDT
TOKEN_ID = os.getenv("TOKEN_ID", "ETH-USDT")

# ──────────────────────────────────────────────
#  LLM Enhancement (Optional)
# ──────────────────────────────────────────────
# Set LLM_API_KEY to enable LLM-based sentiment analysis.
# Supports any OpenAI-compatible API (OpenAI, Anthropic via proxy, local LLM, etc.)
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

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
#  Real Market Data — OKX Public API (No API Key)
# ═══════════════════════════════════════════════

SENTIMENT_LABELS = {
    range(0, 3):  "🟢 CALM — Normal trading conditions",
    range(3, 5):  "🟡 CAUTIOUS — Mild concern detected",
    range(5, 8):  "🟠 FEAR — Significant negative sentiment",
    range(8, 11): "🔴 PANIC — Extreme FUD, activating sell-side defense",
}


def fetch_market_data(inst_id: str) -> dict | None:
    """
    Fetch real market data from OKX public API (no API key needed).
    Returns dict with: price, change_24h, volume_24h, high_24h, low_24h.

    API: https://www.okx.com/api/v5/market/ticker?instId=ETH-USDT
    """
    url = "https://www.okx.com/api/v5/market/ticker"
    params = {"instId": inst_id}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "0" or not data.get("data"):
            log.error("OKX API error: %s", data.get("msg", "unknown"))
            return None

        ticker = data["data"][0]

        last = float(ticker["last"])
        open_24h = float(ticker["open24h"])
        vol_24h = float(ticker["volCcy24h"])  # volume in USDT
        high_24h = float(ticker["high24h"])
        low_24h = float(ticker["low24h"])

        # Calculate 24h change percentage
        change_24h = ((last - open_24h) / open_24h) * 100 if open_24h > 0 else 0

        return {
            "price_usd": last,
            "change_24h": change_24h,
            "volume_24h": vol_24h,
            "high_24h": high_24h,
            "low_24h": low_24h,
        }
    except requests.RequestException as e:
        log.error("Failed to fetch OKX data: %s", e)
        return None


def compute_risk_score(market: dict) -> int:
    """
    Compute risk score 0-10 from real market data.

    Signal: 24h price change (negative = bearish)

    Scoring:
      positive       → 0     (bullish, no risk)
      0% ~ -2%       → 0-2   (calm)
      -2% ~ -5%      → 2-4   (cautious)
      -5% ~ -10%     → 4-7   (fear)
      < -10%         → 7-10  (panic)
    """
    change = market["change_24h"]

    if change >= 0:
        price_risk = 0  # bullish, no risk
    elif change >= -2:
        price_risk = abs(change) / 2 * 2            # 0-2
    elif change >= -5:
        price_risk = 2 + (abs(change) - 2) / 3 * 2  # 2-4
    elif change >= -10:
        price_risk = 4 + (abs(change) - 5) / 5 * 3  # 4-7
    else:
        price_risk = min(10, 7 + (abs(change) - 10) / 10 * 3)  # 7-10

    risk_score = min(10, max(0, round(price_risk)))
    return risk_score


# ═══════════════════════════════════════════════
#  LLM-Enhanced Analysis (Optional)
# ═══════════════════════════════════════════════

def analyze_with_llm(market: dict) -> int | None:
    """
    Use an LLM to assess market risk. Returns risk score 0-10, or None if disabled/failed.

    Supports any OpenAI-compatible chat API:
      - OpenAI:       https://api.openai.com/v1/chat/completions
      - Anthropic:    https://api.anthropic.com/v1/messages (via proxy)
      - Local LLM:    http://localhost:11434/v1/chat/completions (Ollama)
      - DeepSeek:     https://api.deepseek.com/v1/chat/completions
      - Groq:         https://api.groq.com/openai/v1/chat/completions
    """
    if not LLM_API_KEY:
        return None

    log.info("🤖 Calling LLM (%s @ %s)...", LLM_MODEL, LLM_API_URL.split("/v1")[0])

    prompt = f"""Analyze the following crypto market data and assess the risk level.

Market Data:
- Token: {TOKEN_ID}
- Current Price: ${market['price_usd']:,.2f}
- 24h Change: {market['change_24h']:+.2f}%
- 24h Volume: ${market['volume_24h']:,.0f}
- 24h High: ${market['high_24h']:,.2f}
- 24h Low: ${market['low_24h']:,.2f}

Based on this data, assess the risk of a sudden price crash or panic selling in the next few hours.

Return ONLY a JSON object with this exact format:
{{"risk_score": <integer 0-10>, "reason": "<brief explanation>"}}

Scoring guide:
- 0-2: Calm, normal trading conditions
- 3-4: Cautious, mild concern
- 5-7: Fear, significant negative momentum
- 8-10: Panic, extreme FUD, high crash risk"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        resp = requests.post(LLM_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        msg = data["choices"][0]["message"]
        # Handle reasoning models (MiMo, DeepSeek R1, etc.)
        # reasoning_content = thinking process, content = final answer
        content = msg.get("content") or msg.get("reasoning_content") or ""
        if not content:
            log.warning("⚠️  LLM returned empty response")
            return None

        # Extract JSON from response (handle markdown code blocks)
        import re
        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', content)
        if not json_match:
            # Try reasoning_content for reasoning models
            reasoning = msg.get("reasoning_content", "")
            json_match = re.search(r'\{[^}]+\}', reasoning)

        if json_match:
            result = json.loads(json_match.group())
            score = min(10, max(0, int(result.get("risk_score", 5))))
            reason = result.get("reason", "no reason provided")
            log.info("🤖 LLM Assessment: %d/10 — %s", score, reason)
            return score
        else:
            log.warning("⚠️  LLM response not parseable: %s", content[:100])
            return None

    except Exception as e:
        log.warning("⚠️  LLM call failed: %s", e)
        return None


def analyze_market() -> int:
    """
    Full pipeline: fetch OKX data → compute risk → return score.
    If LLM_API_KEY is set, uses LLM for assessment; otherwise uses algorithm.
    """
    log.info("📡 Fetching market data for '%s' from OKX...", TOKEN_ID)

    market = fetch_market_data(TOKEN_ID)
    if market is None:
        log.warning("⚠️  Could not fetch market data, defaulting to risk=0")
        return 0

    # Log the real data
    log.info("💰 Price: $%s", f"{market['price_usd']:,.2f}")
    log.info("📊 24h Change: %s%%", f"{market['change_24h']:+.2f}")
    log.info("📈 24h Volume: $%s", f"{market['volume_24h']:,.0f}")
    log.info("📉 24h Range: $%s — $%s",
             f"{market['low_24h']:,.2f}", f"{market['high_24h']:,.2f}")

    # Try LLM first, fall back to algorithm
    risk_score = analyze_with_llm(market)
    if risk_score is None:
        log.info("🧮 Using algorithmic risk scoring")
        risk_score = compute_risk_score(market)

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
