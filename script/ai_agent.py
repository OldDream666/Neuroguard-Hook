     1|#!/usr/bin/env python3
     2|"""
     3|NeuroGuard Hook — Off-Chain AI Sentiment Agent (Real Data)
     4|===========================================================
     5|Fetches real market data from CoinGecko (free, no API key),
     6|computes a risk score 0-10, and calls setRiskLevel() on the
     7|deployed NeuroGuardHook contract via X Layer testnet.
     8|
     9|Usage:
    10|    cp .env.example .env   # fill in your keys
    11|    pip install -r requirements.txt
    12|    python ai_agent.py              # run once
    13|    python ai_agent.py --loop 60    # loop every 60 seconds
    14|    python ai_agent.py --dry-run    # score only, no tx
    15|    python ai_agent.py --score 7    # manual override
    16|"""
    17|
    18|import os
    19|import sys
    20|import json
    21|import time
    22|import argparse
    23|import logging
    24|from pathlib import Path
    25|from datetime import datetime, timezone
    26|
    27|import requests
    28|from web3 import Web3
    29|from dotenv import load_dotenv
    30|
    31|# ──────────────────────────────────────────────
    32|#  Logging
    33|# ──────────────────────────────────────────────
    34|logging.basicConfig(
    35|    level=logging.INFO,
    36|    format="%(asctime)s [%(levelname)s] %(message)s",
    37|    datefmt="%Y-%m-%d %H:%M:%S",
    38|)
    39|log = logging.getLogger("NeuroGuard-Agent")
    40|
    41|# ──────────────────────────────────────────────
    42|#  Environment
    43|# ──────────────────────────────────────────────
    44|load_dotenv(Path(__file__).parent / ".env")
    45|
    46|RPC_URL = os.getenv("RPC_URL", "https://testrpc.xlayer.tech")
    47|PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    48|HOOK_ADDRESS = os.getenv("HOOK_ADDRESS", "")
    49|CHAIN_ID = int(os.getenv("CHAIN_ID", "1952"))
    50|
    51|# Token to monitor (CoinGecko ID)
    52|# Common: ethereum, bitcoin, solana, dogecoin, pepe, shiba-inu
    53|TOKEN_ID = os.getenv("TOKEN_ID", "ethereum")
    54|
    55|# ──────────────────────────────────────────────
    56|#  Minimal ABI (only what we need)
    57|# ──────────────────────────────────────────────
    58|HOOK_ABI = [
    59|    {
    60|        "inputs": [{"internalType": "uint8", "name": "_riskScore", "type": "uint8"}],
    61|        "name": "setRiskLevel",
    62|        "outputs": [],
    63|        "stateMutability": "nonpayable",
    64|        "type": "function",
    65|    },
    66|    {
    67|        "inputs": [],
    68|        "name": "riskScore",
    69|        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
    70|        "stateMutability": "view",
    71|        "type": "function",
    72|    },
    73|    {
    74|        "inputs": [],
    75|        "name": "aiAgent",
    76|        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
    77|        "stateMutability": "view",
    78|        "type": "function",
    79|    },
    80|]
    81|
    82|
    83|# ═══════════════════════════════════════════════
    84|#  Real Market Data — CoinGecko (Free, No API Key)
    85|# ═══════════════════════════════════════════════
    86|
    87|SENTIMENT_LABELS = {
    88|    range(0, 3):  "🟢 CALM — Normal trading conditions",
    89|    range(3, 5):  "🟡 CAUTIOUS — Mild concern detected",
    90|    range(5, 8):  "🟠 FEAR — Significant negative sentiment",
    91|    range(8, 11): "🔴 PANIC — Extreme FUD, activating sell-side defense",
    92|}
    93|
    94|
    95|def fetch_market_data(token_id: str) -> dict | None:
    96|    """
    97|    Fetch real market data from CoinGecko free API.
    98|    Returns dict with: price, 24h_change, 24h_volume, market_cap.
    99|    """
   100|    url = "https://api.coingecko.com/api/v3/simple/price"
   101|    params = {
   102|        "ids": token_id,
   103|        "vs_currencies": "usd",
   104|        "include_24hr_change": "true",
   105|        "include_24hr_vol": "true",
   106|        "include_market_cap": "true",
   107|    }
   108|
   109|    try:
   110|        resp = requests.get(url, params=params, timeout=10)
   111|        resp.raise_for_status()
   112|        data = resp.json()
   113|
   114|        if token_id not in data:
   115|            log.error("Token '%s' not found in CoinGecko response", token_id)
   116|            return None
   117|
   118|        token_data = data[token_id]
   119|        return {
   120|            "price_usd": token_data.get("usd", 0),
   121|            "change_24h": token_data.get("usd_24h_change", 0),  # percentage
   122|            "volume_24h": token_data.get("usd_24h_vol", 0),
   123|            "market_cap": token_data.get("usd_market_cap", 0),
   124|        }
   125|    except requests.RequestException as e:
   126|        log.error("Failed to fetch CoinGecko data: %s", e)
   127|        return None
   128|
   129|
   130|def fetch_historical_volume(token_id: str) -> float:
   131|    """
   132|    Fetch 7-day average volume to compare against current volume.
   133|    Returns average daily volume in USD.
   134|    """
   135|    url = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart"
   136|    params = {"vs_currency": "usd", "days": "7", "interval": "daily"}
   137|
   138|    try:
   139|        resp = requests.get(url, params=params, timeout=10)
   140|        resp.raise_for_status()
   141|        data = resp.json()
   142|        volumes = [v[1] for v in data.get("total_volumes", [])]
   143|        if volumes:
   144|            return sum(volumes) / len(volumes)
   145|        return 0
   146|    except requests.RequestException:
   147|        return 0
   148|
   149|
   150|def compute_risk_score(market: dict, avg_volume: float) -> int:
   151|    """
   152|    Compute risk score 0-10 from real market signals.
   153|
   154|    Signals:
   155|      1. 24h price change (negative = bearish)  — weight 70%
   156|      2. Volume spike (high volume + drop = panic selling) — weight 30%
   157|
   158|    Scoring:
   159|      price_change  → risk contribution
   160|      -3% ~ 0%      → 0-2   (calm)
   161|      -7% ~ -3%     → 2-4   (cautious)
   162|      -15% ~ -7%    → 4-7   (fear)
   163|      < -15%         → 7-10  (panic)
   164|      positive       → 0-2   (bullish, low risk)
   165|    """
   166|    change = market["change_24h"]  # e.g. -5.2 means -5.2%
   167|
   168|    # ── Signal 1: Price change → risk ──
   169|    if change >= 0:
   170|        price_risk = 0  # bullish, no risk
   171|    elif change >= -2:
   172|        price_risk = abs(change) / 2 * 2        # 0-2
   173|    elif change >= -5:
   174|        price_risk = 2 + (abs(change) - 2) / 3 * 2  # 2-4
   175|    elif change >= -10:
   176|        price_risk = 4 + (abs(change) - 5) / 5 * 3  # 4-7
   177|    else:
   178|        price_risk = min(10, 7 + (abs(change) - 10) / 10 * 3)  # 7-10
   179|
   180|    # ── Signal 2: Volume spike multiplier ──
   181|    volume_multiplier = 1.0
   182|    if avg_volume > 0 and market["volume_24h"] > 0:
   183|        ratio = market["volume_24h"] / avg_volume
   184|        if ratio > 3.0:
   185|            volume_multiplier = 1.5   # massive volume spike during dump
   186|        elif ratio > 2.0:
   187|            volume_multiplier = 1.3
   188|        elif ratio > 1.5:
   189|            volume_multiplier = 1.1
   190|        # Low volume dump is less concerning
   191|        elif ratio < 0.5:
   192|            volume_multiplier = 0.8
   193|
   194|    # ── Final score ──
   195|    raw_score = price_risk * volume_multiplier
   196|    risk_score = min(10, max(0, round(raw_score)))
   197|
   198|    return risk_score
   199|
   200|
   201|def analyze_market() -> int:
   202|    """
   203|    Full pipeline: fetch real data → compute risk → return score.
   204|    This replaces the old simulate_ai_sentiment() with real market analysis.
   205|    """
   206|    log.info("📡 Fetching market data for '%s' from CoinGecko...", TOKEN_ID)
   207|
   208|    market = fetch_market_data(TOKEN_ID)
   209|    if market is None:
   210|        log.warning("⚠️  Could not fetch market data, defaulting to risk=0")
   211|        return 0
   212|
   213|    # Fetch 7-day average volume for comparison
   214|    avg_vol = fetch_historical_volume(TOKEN_ID)
   215|
   216|    # Log the real data
   217|    log.info("💰 Price: $%s", f"{market['price_usd']:,.2f}")
   218|    log.info("📊 24h Change: %s%%", f"{market['change_24h']:+.2f}")
   219|    log.info("📈 24h Volume: $%s", f"{market['volume_24h']:,.0f}")
   220|    if avg_vol > 0:
   221|        vol_ratio = market['volume_24h'] / avg_vol
   222|        log.info("📉 7d Avg Volume: $%s (current/avg = %.2fx)", f"{avg_vol:,.0f}", vol_ratio)
   223|
   224|    # Compute risk
   225|    risk_score = compute_risk_score(market, avg_vol)
   226|
   227|    # Label
   228|    label = "UNKNOWN"
   229|    for r, lbl in SENTIMENT_LABELS.items():
   230|        if risk_score in r:
   231|            label = lbl
   232|            break
   233|    log.info("🧠 AI Risk Score: %d/10  →  %s", risk_score, label)
   234|
   235|    return risk_score
   236|
   237|
   238|# ═══════════════════════════════════════════════
   239|#  On-Chain Interaction
   240|# ═══════════════════════════════════════════════
   241|
   242|def init_web3() -> Web3:
   243|    """Initialize Web3 connection."""
   244|    w3 = Web3(Web3.HTTPProvider(RPC_URL))
   245|    if not w3.is_connected():
   246|        log.error("❌ Failed to connect to RPC: %s", RPC_URL)
   247|        sys.exit(1)
   248|    log.info("✅ Connected to X Layer (chain %d) via %s", CHAIN_ID, RPC_URL)
   249|    return w3
   250|
   251|
   252|def get_hook_contract(w3: Web3):
   253|    """Return contract instance."""
   254|    if not HOOK_ADDRESS:
   255|        log.error("❌ HOOK_ADDRESS not set in .env")
   256|        sys.exit(1)
   257|    return w3.eth.contract(
   258|        address=Web3.to_checksum_address(HOOK_ADDRESS),
   259|        abi=HOOK_ABI,
   260|    )
   261|
   262|
   263|def verify_agent(w3: Web3, contract, account: str):
   264|    """Verify that the private key matches the contract's aiAgent."""
   265|    on_chain_agent = contract.functions.aiAgent().call()
   266|    if on_chain_agent.lower() != account.lower():
   267|        log.error(
   268|            "❌ Wallet mismatch!\n"
   269|            "   Your address:  %s\n"
   270|            "   Contract aiAgent: %s\n"
   271|            "   Only the aiAgent can call setRiskLevel.",
   272|            account,
   273|            on_chain_agent,
   274|        )
   275|        sys.exit(1)
   276|    log.info("🔐 Agent verification passed: %s", account)
   277|
   278|
   279|def get_current_risk(contract) -> int:
   280|    """Read current risk score from chain."""
   281|    score = contract.functions.riskScore().call()
   282|    log.info("📊 Current on-chain risk score: %d", score)
   283|    return score
   284|
   285|
   286|def send_risk_update(w3: Web3, contract, new_score: int) -> str:
   287|    """
   288|    Build, sign, and send setRiskLevel transaction.
   289|    Returns tx hash.
   290|    """
   291|    account = w3.eth.account.from_key(PRIVATE_KEY)
   292|    current = get_current_risk(contract)
   293|
   294|    if current == new_score:
   295|        log.info("⏭️  Risk score unchanged (%d), skipping tx.", new_score)
   296|        return ""
   297|
   298|    # Build transaction
   299|    tx = contract.functions.setRiskLevel(new_score).build_transaction({
   300|        "from": account.address,
   301|        "nonce": w3.eth.get_transaction_count(account.address),
   302|        "gas": 100_000,
   303|        "gasPrice": w3.eth.gas_price,
   304|        "chainId": CHAIN_ID,
   305|    })
   306|
   307|    # Sign and send
   308|    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
   309|    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
   310|    log.info("📤 TX sent: %s", tx_hash.hex())
   311|
   312|    # Wait for confirmation
   313|    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
   314|    if receipt.status == 1:
   315|        log.info("✅ TX confirmed in block %d — risk score: %d → %d",
   316|                 receipt.blockNumber, current, new_score)
   317|    else:
   318|        log.error("❌ TX reverted! Check on explorer.")
   319|
   320|    return tx_hash.hex()
   321|
   322|
   323|# ═══════════════════════════════════════════════
   324|#  Main Loop
   325|# ═══════════════════════════════════════════════
   326|
   327|def run_once(w3, contract):
   328|    """Single iteration: fetch real data → score → send if changed."""
   329|    log.info("─" * 50)
   330|    score = analyze_market()
   331|    tx_hash = send_risk_update(w3, contract, score)
   332|    return tx_hash
   333|
   334|
   335|def main():
   336|    parser = argparse.ArgumentParser(description="NeuroGuard AI Sentiment Agent")
   337|    parser.add_argument("--loop", type=int, default=0,
   338|                        help="Run in loop mode with N-second interval (0 = run once)")
   339|    parser.add_argument("--dry-run", action="store_true",
   340|                        help="Score sentiment but don't send transactions")
   341|    parser.add_argument("--score", type=int, default=None,
   342|                        help="Override: manually set risk score (0-10), skip AI")
   343|    args = parser.parse_args()
   344|
   345|    # Dry run — only analyze market, no chain interaction needed
   346|    if args.dry_run:
   347|        log.info("🧪 DRY RUN mode — no transactions will be sent")
   348|        log.info("   Monitoring: %s", os.getenv("TOKEN_ID", "ethereum"))
   349|        analyze_market()
   350|        return
   351|
   352|    if not PRIVATE_KEY:
   353|        log.error("❌ PRIVATE_KEY not set. Copy .env.example → .env and fill in.")
   354|        sys.exit(1)
   355|
   356|    w3 = init_web3()
   357|    contract = get_hook_contract(w3)
   358|    account = w3.eth.account.from_key(PRIVATE_KEY)
   359|
   360|    log.info("🤖 NeuroGuard AI Agent starting")
   361|    log.info("   Wallet:     %s", account.address)
   362|    log.info("   Hook:       %s", HOOK_ADDRESS)
   363|    log.info("   Monitoring: %s", TOKEN_ID)
   364|
   365|    verify_agent(w3, contract, account.address)
   366|
   367|    if args.score is not None:
   368|        if not 0 <= args.score <= 10:
   369|            log.error("Score must be 0-10")
   370|            sys.exit(1)
   371|        log.info("🎯 Manual mode: setting risk score to %d", args.score)
   372|        send_risk_update(w3, contract, args.score)
   373|        return
   374|
   375|    if args.loop > 0:
   376|        log.info("🔄 Loop mode: checking every %d seconds (Ctrl+C to stop)", args.loop)
   377|        try:
   378|            while True:
   379|                run_once(w3, contract)
   380|                time.sleep(args.loop)
   381|        except KeyboardInterrupt:
   382|            log.info("\n👋 Agent stopped by user.")
   383|    else:
   384|        run_once(w3, contract)
   385|
   386|
   387|if __name__ == "__main__":
   388|    main()
   389|