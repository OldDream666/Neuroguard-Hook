     1|<div align="center">
     2|
     3|# 🛡️ NeuroGuard Hook
     4|
     5|### *The First AI-Driven Adaptive Liquidity & Anti-Sniper Shield for Uniswap V4*
     6|
     7|**Protecting retail traders. Punishing snipers. Powered by AI.**
     8|
     9|[![X Layer](https://img.shields.io/badge/Chain-X%20Layer%20Testnet-000?style=for-the-badge&logo=okx&logoColor=fff)](https://www.oklink.com/xlayer-test)
    10|[![Uniswap V4](https://img.shields.io/badge/Protocol-Uniswap%20V4-FF007A?style=for-the-badge&logo=uniswap&logoColor=fff)](https://docs.uniswap.org/contracts/v4/overview)
    11|[![Foundry](https://img.shields.io/badge/Built%20with-Foundry-000?style=for-the-badge)](https://book.getfoundry.sh/)
    12|[![Solidity](https://img.shields.io/badge/Solidity-0.8.26-363636?style=for-the-badge&logo=solidity&logoColor=fff)](https://soliditylang.org/)
    13|
    14|---
    15|
    16|**🏆 OKX Build-X Hackathon — Uniswap V4 Hook Track**
    17|
    18|</div>
    19|
    20|---
    21|
    22|## 📖 Table of Contents
    23|
    24|- [The Problem](#-the-problem)
    25|- [Our Solution](#-our-solution)
    26|- [How It Works](#-how-it-works)
    27|- [Why X Layer](#-why-x-layer)
    28|- [Architecture](#-architecture)
    29|- [Smart Contracts](#-smart-contracts)
    30|- [Quick Start](#-quick-start)
    31|- [AI Agent](#-ai-agent)
    32|- [Team](#-team)
    33|
    34|---
    35|
    36|## 🔥 The Problem
    37|
    38|> *"In the current DeFi landscape, retail traders are the exit liquidity."*
    39|
    40|Every day, thousands of new tokens launch on DEXs. The story is always the same:
    41|
    42|| 🤖 **Sniper Bots** | 😱 **FUD Panic Sells** |
    43||:---|:---|
    44|| Millisecond-speed bots front-run every new pool, buying up supply before retail even sees the listing. | Coordinated dump attacks trigger cascading panic. No circuit breaker exists. No defense mechanism. |
    45|| Retail buys at inflated prices. Bots dump on them minutes later. | One whale sells → price crashes → stop losses trigger → more selling → death spiral. |
    46|| **Result: 90%+ of launch participants lose money.** | **Result: Legitimate projects die in hours.** |
    47|
    48|**The core issue:** AMMs are **passive**. They have no intelligence, no memory, no defense. Until now.
    49|
    50|---
    51|
    52|## 💡 Our Solution
    53|
    54|**NeuroGuard Hook** is a **dynamic defense AMM Hook** for Uniswap V4 that combines:
    55|
    56|- 🧱 **On-Chain Sniper Trap** — deterministic, immutable, unstoppable
    57|- 🧠 **Off-Chain AI Sentiment Engine** — adaptive, real-time, intelligent
    58|
    59|Together, they create a **two-layer defense system** that makes token launches fair for everyone — not just bots.
    60|
    61|```
    62|┌─────────────────────────────────────────────────┐
    63|│              NeuroGuard Hook                     │
    64|│                                                  │
    65|│   Layer 1: Sniper Trap (Pure On-Chain)          │
    66|│   ├─ Block-height detection                      │
    67|│   ├─ 90% punitive fee on sniper buys            │
    68|│   └─ Fees → Protocol-Owned Liquidity (POL)      │
    69|│                                                  │
    70|│   Layer 2: AI Emotion Circuit Breaker            │
    71|│   ├─ Off-chain sentiment monitoring (AI Agent)   │
    72|│   ├─ On-chain risk score (0-10)                 │
    73|│   └─ Dynamic sell-side fee (0.3% → 10%)         │
    74|└─────────────────────────────────────────────────┘
    75|```
    76|
    77|---
    78|
    79|## ⚙️ How It Works
    80|
    81|### 🪤 Layer 1: Sniper Trap — *Kill the Bots*
    82|
    83|> **Philosophy:** Don't `revert` sniper transactions — *tax* them.
    84|
    85|When a new token pool is created, NeuroGuard activates a **3-block sniper window**:
    86|
    87|1. **Detection**: The hook tracks `poolCreationBlock` via `afterInitialize`. Any swap within the first 3 blocks triggers sniper detection mode.
    88|
    89|2. **Identification**: If a single address attempts a **large buy** (above `LARGE_SWAP_THRESHOLD`) during this window, it is classified as a sniper bot.
    90|
    91|3. **Punishment**: Instead of reverting (which lets bots retry), the hook applies a **90% dynamic fee** via Uniswap V4's `updateDynamicLPFee()`.
    92|
    93|4. **Conversion**: The massive fee isn't burned — it **automatically becomes Protocol-Owned Liquidity (POL)**, deepening the pool for real traders.
    94|
    95|```solidity
    96|// From NeuroGuardHook.sol — beforeSwap()
    97|if (block.number <= poolCreationBlock + SNIPER_WINDOW) {
    98|    if (isBuy && cumVolume > LARGE_SWAP_THRESHOLD) {
    99|        fee = SNIPER_FEE; // 90%
   100|        manager.updateDynamicLPFee(key, fee);
   101|        // Sniper's ETH → POL → protects real users
   102|    }
   103|}
   104|```
   105|
   106|**🎯 Result:** Sniper bots lose 90% of their capital on every attempt. Their stolen funds become the liquidity that protects the very community they tried to exploit.
   107|
   108|---
   109|
   110|### 🧠 Layer 2: AI Emotion Circuit Breaker — *Smart Defense*
   111|
   112|> **Philosophy:** Markets need a thermostat, not a fire alarm.
   113|
   114|After launch, the threat shifts from snipers to **coordinated FUD attacks** and **panic sells**.
   115|
   116|#### 🔗 Off-Chain: Real-Time Market Monitoring Agent
   117|
   118|A Python/Node.js agent fetches **real market data from CoinGecko** (free, no API key needed):
   119|
   120|| Signal | Weight | Source | Description |
   121||:-------|:------:|:------:|:------------|
   122|| 📉 24h Price Change | 70% | CoinGecko API | Price drop magnitude → risk level |
   123|| 📈 Volume Spike | 30% | CoinGecko API | Current vs 7d avg volume (high volume + dump = panic) |
   124|
   125|**Risk Thresholds (based on real 24h price change):**
   126|
   127|| Price Change | Risk Score | State |
   128||:-------------|:----------:|:-----:|
   129|| 0% or positive | 0 | 🟢 Calm |
   130|| -1% to -2% | 1-2 | 🟢 Calm |
   131|| -2% to -5% | 3-4 | 🟡 Cautious |
   132|| -5% to -10% | 5-7 | 🟠 Fear |
   133|| beyond -10% | 8-10 | 🔴 Panic |
   134|
   135|The agent computes a **Risk Score (0-10)** from live data and, when the score changes, calls `setRiskLevel()` on-chain via X Layer testnet.
   136|
   137|#### ⛓️ On-Chain: Dynamic Fee Response
   138|
   139|| Risk Score | State | Buy Fee | Sell Fee | Strategy |
   140||:----------:|:-----:|:-------:|:--------:|:---------|
   141|| 0-2 | 🟢 Calm | 0.3% | 0.3% | Normal trading |
   142|| 3-4 | 🟡 Cautious | 0.3% | 0.6% | Mild caution |
   143|| 5-7 | 🟠 Fear | 0.1% | 3.0% | Discourage sells, incentivize buys |
   144|| 8-10 | 🔴 Panic | 0.1% | **10%** | Maximum sell-side defense |
   145|
   146|```solidity
   147|// Risk-adaptive fee logic
   148|if (riskScore >= 7) {
   149|    buyFee  = 0.1%;   // Attract buyers (soft floor)
   150|    sellFee = 10%;     // Deter panic selling
   151|}
   152|```
   153|
   154|**🎯 Result:** When FUD strikes, selling becomes expensive while buying becomes cheap. This creates a **natural circuit breaker** that prevents death spirals while allowing genuine price discovery.
   155|
   156|---
   157|
   158|## 🌐 Why X Layer
   159|
   160|> *"X Layer isn't just a chain — it's the nervous system of the OKX Web3 ecosystem."*
   161|
   162|We chose **X Layer** specifically because:
   163|
   164|| Feature | Why It Matters for NeuroGuard |
   165||:--------|:------------------------------|
   166|| ⚡ **Ultra-Low Gas** | AI Agent calls `setRiskLevel()` frequently. On Ethereum, each tx costs $5-50. On X Layer, it costs **fractions of a cent**. High-frequency AI monitoring is only economically viable here. |
   167|| 🔥 **High Throughput** | Sniper detection requires per-block granularity. X Layer's fast block times give us **finer-grained protection windows**. |
   168|| 🏗️ **OKX Ecosystem** | X Layer is the **infrastructure backbone** of OKX Web3. Any token launching through OKX Wallet or OKX DEX can plug in NeuroGuard as a **native safety layer**. |
   169|| 🚀 **OP Stack / Polygon CDK** | EVM-equivalent means our hook works **unchanged**. Zero modifications needed. |
   170|| 🌍 **Growing Ecosystem** | As X Layer attracts more DeFi protocols, NeuroGuard becomes the **default safety primitive** for every new pool. |
   171|
   172|> **Vision:** NeuroGuard Hook aims to become the **standard security infrastructure** for token launches on X Layer — turning every new pool into a **protected, fair-launch environment**.
   173|
   174|---
   175|
   176|## 🏗️ Architecture
   177|
   178|```
   179|                    ┌──────────────────┐
   180|                    │   Market Data    │
   181|                    │  (Social, On-chain│
   182|                    │   Whale, Perps)  │
   183|                    └────────┬─────────┘
   184|                             │
   185|                    ┌────────▼─────────┐
   186|                    │   AI Agent       │
   187|                    │  (Python/Node.js)│
   188|                    │  Sentiment Scorer│
   189|                    └────────┬─────────┘
   190|                             │ setRiskLevel(score)
   191|                    ┌────────▼─────────┐
   192|                    │  X Layer Testnet │
   193|                    │                  │
   194|    ┌───────────────┤  PoolManager    ├───────────────┐
   195|    │               │                  │               │
   196|    │               └────────┬─────────┘               │
   197|    │                        │                         │
   198|    │               ┌────────▼─────────┐               │
   199|    │               │ NeuroGuardHook   │               │
   200|    │               │                  │               │
   201|    │               │ ┌──────────────┐ │               │
   202|    │               │ │ Sniper Trap  │ │               │
   203|    │               │ │ (beforeSwap) │ │               │
   204|    │               │ └──────────────┘ │               │
   205|    │               │ ┌──────────────┐ │               │
   206|    │               │ │ AI Fee Logic │ │               │
   207|    │               │ │ (riskScore)  │ │               │
   208|    │               │ └──────────────┘ │               │
   209|    │               └──────────────────┘               │
   210|    │                                                   │
   211|    ▼                                                   ▼
   212|┌────────┐                                    ┌────────────┐
   213|│ Sniper │                                    │  Retail     │
   214|│  Bot   │──── 90% fee ──→ POL               │  Traders    │
   215|│ (REKT) │                                    │ (Protected) │
   216|└────────┘                                    └────────────┘
   217|```
   218|
   219|---
   220|
   221|## 📜 Smart Contracts
   222|
   223|**Deployed on X Layer Testnet (Chain ID: 1952)**
   224|
   225|| Contract | Address | Explorer |
   226||:---------|:--------|:---------|
   227|| 🏭 **PoolManager** | `0x1AF4D7774351504dBddAada09122adB48fcE7ab6` | [View on OKLink](https://www.oklink.com/xlayer-test/address/0x1AF4D7774351504dBddAada09122adB48fcE7ab6) |
   228|| 🛡️ **NeuroGuardHook** | `0x595ac52d42D77902dbF4fdD274456409C9CC1080` | [View on OKLink](https://www.oklink.com/xlayer-test/address/0x595ac52d42D77902dbF4fdD274456409C9CC1080) |
   229|| 🤖 **AI Agent Wallet** | `0x07797e6C86302B6D4C23fe80A67ac42CeC4dfc28` | — |
   230|
   231|**Key Contract Functions:**
   232|
   233|| Function | Access | Description |
   234||:---------|:------:|:------------|
   235|| `setRiskLevel(uint8)` | AI Agent Only | Update on-chain risk score (0-10) |
   236|| `setAIAgent(address)` | AI Agent Only | Transfer AI Agent role |
   237|| `beforeSwap()` | Internal | Sniper detection + dynamic fee routing |
   238|| `afterInitialize()` | Internal | Record pool creation block |
   239|| `riskScore()` | Public | Read current risk level |
   240|| `isInSniperWindow()` | Public | Check if sniper window is active |
   241|
   242|---
   243|
   244|## 🚀 Quick Start
   245|
   246|### Prerequisites
   247|
   248|- [Foundry](https://book.getfoundry.sh/getting-started/installation) (`forge`, `cast`)
   249|- Node.js 18+ (for AI Agent)
   250|- Python 3.10+ (for AI Agent alternative)
   251|
   252|### 1. Clone & Build
   253|
   254|```bash
   255|git clone https://github.com/your-org/neuroguard-hook.git
   256|cd neuroguard-hook
   257|forge install
   258|forge build
   259|```
   260|
   261|### 2. Run Tests
   262|
   263|```bash
   264|forge test -vvvv
   265|```
   266|
   267|### 3. Deploy (One-Click)
   268|
   269|```bash
   270|# Set your deployer private key
   271|export DEPLOYER_PRIVATE_KEY="0x..."
   272|
   273|# Deploy PoolManager + Hook in one transaction
   274|forge script script/Deploy.s.sol:Deploy \
   275|  --rpc-url https://testrpc.xlayer.tech \
   276|  --private-key $DEPLOYER_PRIVATE_KEY \
   277|  --broadcast -vvvv
   278|```
   279|
   280|> ⚠️ The deploy script auto-mines a CREATE2 salt to ensure the hook address has the correct permission bits for Uniswap V4.
   281|
   282|### 4. Verify on Explorer
   283|
   284|```bash
   285|forge verify-contract <HOOK_ADDRESS> src/NeuroGuardHook.sol:NeuroGuardHook \
   286|  --chain-id 1952 \
   287|  --verifier oklink \
   288|  --verifier-url https://www.oklink.com/api/v5/explorer/contract/verify-source-code \
   289|  --etherscan-api-key $OKLINK_API_KEY
   290|```
   291|
   292|---
   293|
   294|## 🤖 AI Agent
   295|
   296|### Python Version
   297|
   298|```bash
   299|cd script
   300|pip install -r requirements.txt
   301|cp .env.example .env
   302|# Edit .env: set PRIVATE_KEY, HOOK_ADDRESS
   303|
   304|# Run once
   305|python ai_agent.py
   306|
   307|# Loop every 60 seconds
   308|python ai_agent.py --loop 60
   309|
   310|# Dry run (score only, no tx)
   311|python ai_agent.py --dry-run
   312|
   313|# Manual override
   314|python ai_agent.py --score 7
   315|```
   316|
   317|### Node.js Version
   318|
   319|```bash
   320|cd ai-agent
   321|npm install
   322|cp .env.example .env
   323|# Edit .env: set AI_AGENT_PRIVATE_KEY, HOOK_CONTRACT_ADDRESS
   324|
   325|# Run once
   326|node index.js
   327|
   328|# Loop every 60 seconds
   329|node index.js --loop 60
   330|
   331|# Dry run
   332|node index.js --dry-run
   333|```
   334|
   335|### Data Source
   336|
   337|Both agents use **real market data from CoinGecko** (free, no API key):
   338|
   339|- **Primary signal**: 24h price change → mapped to risk score 0-10
   340|- **Secondary signal**: Volume spike vs 7-day average (amplifies risk during panic selling)
   341|
   342|To monitor a different token, set `TOKEN_ID` in `.env`:
   343|```
   344|# CoinGecko token IDs: ethereum, bitcoin, solana, dogecoin, pepe, shiba-inu
   345|TOKEN_ID=pepe
   346|```
   347|
   348|### Optional: LLM Enhancement
   349|
   350|Both versions include commented-out **OpenAI GPT-4o-mini** integration for richer sentiment analysis:
   351|
   352|```python
   353|# In ai_agent.py, uncomment the simulate_llm_sentiment() function
   354|# Set OPENAI_API_KEY in .env
   355|```
   356|
   357|---
   358|
   359|## 📊 Fee Mechanism Summary
   360|
   361|```
   362|                    ┌─────────────────────┐
   363|                    │   Swap Arrives      │
   364|                    └──────────┬──────────┘
   365|                               │
   366|                    ┌──────────▼──────────┐
   367|                    │ Within 3 blocks of  │
   368|                    │ pool creation?      │
   369|                    └──────────┬──────────┘
   370|                          YES/ \NO
   371|                         /     \
   372|              ┌─────────▼┐   ┌▼──────────────┐
   373|              │ Large buy │   │ Check riskScore│
   374|              │ (>10k)?   │   └──────┬────────┘
   375|              └─────┬─────┘          │
   376|               YES/ \NO         ┌────▼────┐
   377|               /     \          │ Score   │
   378|         ┌────▼──┐ ┌──▼──┐     │ 0-10    │
   379|         │ 90%   │ │0.3% │     └────┬────┘
   380|         │ FEE   │ │ FEE │          │
   381|         │(SNIPER│ │     │    ┌─────▼──────┐
   382|         │ TRAP) │ │     │    │ Adaptive    │
   383|         └───────┘ └─────┘    │ Fee Engine  │
   384|                              │             │
   385|                              │ Buy:  0.1-  │
   386|                              │        0.3% │
   387|                              │ Sell: 0.3-  │
   388|                              │        10%  │
   389|                              └─────────────┘
   390|```
   391|
   392|---
   393|
   394|## 🧪 Test Coverage
   395|
   396|| Test Case | Description | Expected |
   397||:----------|:------------|:---------|
   398|| `test_sniperDetection_highFee` | Bot buys large amount in block 1 | 90% fee applied |
   399|| `test_normalUser_normalFee` | Regular user buys after sniper window | 0.3% fee |
   400|| `test_aiHighRisk_highSellFee` | AI sets risk=8, user sells | 10% sell fee |
   401|| `test_aiLowRisk_normalFee` | AI sets risk=0, normal trading | 0.3% fee |
   402|| `test_unauthorizedCaller_reverts` | Non-AI agent calls setRiskLevel | Reverts |
   403|| `test_sniperVolumeAccumulation` | Multiple small buys from same address | Cumulative detection |
   404|
   405|---
   406|
   407|## 🙏 Acknowledgments
   408|
   409|- [Uniswap V4](https://docs.uniswap.org/contracts/v4/overview) — For the revolutionary hook architecture
   410|- [OKX X Layer](https://web3.okx.com/xlayer) — For the hackathon and the chain
   411|- [Foundry](https://book.getfoundry.sh/) — For the best Solidity dev tooling
   412|
   413|---
   414|
   415|<div align="center">
   416|
   417|**Built with 🛡️ for the OKX Build-X Hackathon**
   418|
   419|*NeuroGuard Hook — Because fair launches shouldn't be a myth.*
   420|
   421|</div>
   422|