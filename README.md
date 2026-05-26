<div align="center">

# 🛡️ NeuroGuard Hook

### *The First AI-Driven Adaptive Liquidity & Anti-Sniper Shield for Uniswap V4*

**Protecting retail traders. Punishing snipers. Powered by AI.**

[![X Layer](https://img.shields.io/badge/Chain-X%20Layer%20Testnet-000?style=for-the-badge&logo=okx&logoColor=fff)](https://www.oklink.com/xlayer-test)
[![Uniswap V4](https://img.shields.io/badge/Protocol-Uniswap%20V4-FF007A?style=for-the-badge&logo=uniswap&logoColor=fff)](https://docs.uniswap.org/contracts/v4/overview)
[![Foundry](https://img.shields.io/badge/Built%20with-Foundry-000?style=for-the-badge)](https://book.getfoundry.sh/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.26-363636?style=for-the-badge&logo=solidity&logoColor=fff)](https://soliditylang.org/)

---

**🏆 OKX Build-X Hackathon — Uniswap V4 Hook Track**

</div>

---

## 📖 Table of Contents

- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [How It Works](#-how-it-works)
- [Why X Layer](#-why-x-layer)
- [Architecture](#-architecture)
- [Smart Contracts](#-smart-contracts)
- [Quick Start](#-quick-start)
- [AI Agent](#-ai-agent)
- [Team](#-team)

---

## 🔥 The Problem

> *"In the current DeFi landscape, retail traders are the exit liquidity."*

Every day, thousands of new tokens launch on DEXs. The story is always the same:

| 🤖 **Sniper Bots** | 😱 **FUD Panic Sells** |
|:---|:---|
| Millisecond-speed bots front-run every new pool, buying up supply before retail even sees the listing. | Coordinated dump attacks trigger cascading panic. No circuit breaker exists. No defense mechanism. |
| Retail buys at inflated prices. Bots dump on them minutes later. | One whale sells → price crashes → stop losses trigger → more selling → death spiral. |
| **Result: 90%+ of launch participants lose money.** | **Result: Legitimate projects die in hours.** |

**The core issue:** AMMs are **passive**. They have no intelligence, no memory, no defense. Until now.

---

## 💡 Our Solution

**NeuroGuard Hook** is a **dynamic defense AMM Hook** for Uniswap V4 that combines:

- 🧱 **On-Chain Sniper Trap** — deterministic, immutable, unstoppable
- 🧠 **Off-Chain AI Sentiment Engine** — adaptive, real-time, intelligent

Together, they create a **two-layer defense system** that makes token launches fair for everyone — not just bots.

```
┌─────────────────────────────────────────────────┐
│              NeuroGuard Hook                     │
│                                                  │
│   Layer 1: Sniper Trap (Pure On-Chain)          │
│   ├─ Block-height detection                      │
│   ├─ 90% punitive fee on sniper buys            │
│   └─ Fees → Protocol-Owned Liquidity (POL)      │
│                                                  │
│   Layer 2: AI Emotion Circuit Breaker            │
│   ├─ Off-chain sentiment monitoring (AI Agent)   │
│   ├─ On-chain risk score (0-10)                 │
│   └─ Dynamic sell-side fee (0.3% → 10%)         │
└─────────────────────────────────────────────────┘
```

---

## ⚙️ How It Works

### 🪤 Layer 1: Sniper Trap — *Kill the Bots*

> **Philosophy:** Don't `revert` sniper transactions — *tax* them.

When a new token pool is created, NeuroGuard activates a **3-block sniper window**:

1. **Detection**: The hook tracks `poolCreationBlock` via `afterInitialize`. Any swap within the first 3 blocks triggers sniper detection mode.

2. **Identification**: If a single address attempts a **large buy** (above `LARGE_SWAP_THRESHOLD`) during this window, it is classified as a sniper bot.

3. **Punishment**: Instead of reverting (which lets bots retry), the hook applies a **90% dynamic fee** via Uniswap V4's `updateDynamicLPFee()`.

4. **Conversion**: The massive fee isn't burned — it **automatically becomes Protocol-Owned Liquidity (POL)**, deepening the pool for real traders.

```solidity
// From NeuroGuardHook.sol — beforeSwap()
if (block.number <= poolCreationBlock + SNIPER_WINDOW) {
    if (isBuy && cumVolume > LARGE_SWAP_THRESHOLD) {
        fee = SNIPER_FEE; // 90%
        manager.updateDynamicLPFee(key, fee);
        // Sniper's ETH → POL → protects real users
    }
}
```

**🎯 Result:** Sniper bots lose 90% of their capital on every attempt. Their stolen funds become the liquidity that protects the very community they tried to exploit.

---

### 🧠 Layer 2: AI Emotion Circuit Breaker — *Smart Defense*

> **Philosophy:** Markets need a thermostat, not a fire alarm.

After launch, the threat shifts from snipers to **coordinated FUD attacks** and **panic sells**.

#### 🔗 Off-Chain: Real-Time Market Monitoring Agent

A Python/Node.js agent fetches **real market data from OKX** (free, no API key needed):

| Signal | Weight | Source | Description |
|:-------|:------:|:------:|:------------|
| 📉 24h Price Change | 100% | OKX API | Price drop magnitude → risk level |

**Risk Thresholds (based on real 24h price change):**

| Price Change | Risk Score | State |
|:-------------|:----------:|:-----:|
| 0% or positive | 0 | 🟢 Calm |
| -1% to -2% | 1-2 | 🟢 Calm |
| -2% to -5% | 3-4 | 🟡 Cautious |
| -5% to -10% | 5-7 | 🟠 Fear |
| beyond -10% | 8-10 | 🔴 Panic |

The agent computes a **Risk Score (0-10)** from live data and, when the score changes, calls `setRiskLevel()` on-chain via X Layer testnet.

#### ⛓️ On-Chain: Dynamic Fee Response

| Risk Score | State | Buy Fee | Sell Fee | Strategy |
|:----------:|:-----:|:-------:|:--------:|:---------|
| 0-2 | 🟢 Calm | 0.3% | 0.3% | Normal trading |
| 3-4 | 🟡 Cautious | 0.3% | 0.6% | Mild caution |
| 5-7 | 🟠 Fear | 0.1% | 3.0% | Discourage sells, incentivize buys |
| 8-10 | 🔴 Panic | 0.1% | **10%** | Maximum sell-side defense |

```solidity
// Risk-adaptive fee logic
if (riskScore >= 7) {
    buyFee  = 0.1%;   // Attract buyers (soft floor)
    sellFee = 10%;     // Deter panic selling
}
```

**🎯 Result:** When FUD strikes, selling becomes expensive while buying becomes cheap. This creates a **natural circuit breaker** that prevents death spirals while allowing genuine price discovery.

---

## 🌐 Why X Layer

> *"X Layer isn't just a chain — it's the nervous system of the OKX Web3 ecosystem."*

We chose **X Layer** specifically because:

| Feature | Why It Matters for NeuroGuard |
|:--------|:------------------------------|
| ⚡ **Ultra-Low Gas** | AI Agent calls `setRiskLevel()` frequently. On Ethereum, each tx costs $5-50. On X Layer, it costs **fractions of a cent**. High-frequency AI monitoring is only economically viable here. |
| 🔥 **High Throughput** | Sniper detection requires per-block granularity. X Layer's fast block times give us **finer-grained protection windows**. |
| 🏗️ **OKX Ecosystem** | X Layer is the **infrastructure backbone** of OKX Web3. Any token launching through OKX Wallet or OKX DEX can plug in NeuroGuard as a **native safety layer**. |
| 🚀 **OP Stack / Polygon CDK** | EVM-equivalent means our hook works **unchanged**. Zero modifications needed. |
| 🌍 **Growing Ecosystem** | As X Layer attracts more DeFi protocols, NeuroGuard becomes the **default safety primitive** for every new pool. |

> **Vision:** NeuroGuard Hook aims to become the **standard security infrastructure** for token launches on X Layer — turning every new pool into a **protected, fair-launch environment**.

---

## 🏗️ Architecture

```
                    ┌──────────────────┐
                    │   Market Data    │
                    │  (Social, On-chain│
                    │   Whale, Perps)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   AI Agent       │
                    │  (Python/Node.js)│
                    │  Sentiment Scorer│
                    └────────┬─────────┘
                             │ setRiskLevel(score)
                    ┌────────▼─────────┐
                    │  X Layer Testnet │
                    │                  │
    ┌───────────────┤  PoolManager    ├───────────────┐
    │               │                  │               │
    │               └────────┬─────────┘               │
    │                        │                         │
    │               ┌────────▼─────────┐               │
    │               │ NeuroGuardHook   │               │
    │               │                  │               │
    │               │ ┌──────────────┐ │               │
    │               │ │ Sniper Trap  │ │               │
    │               │ │ (beforeSwap) │ │               │
    │               │ └──────────────┘ │               │
    │               │ ┌──────────────┐ │               │
    │               │ │ AI Fee Logic │ │               │
    │               │ │ (riskScore)  │ │               │
    │               │ └──────────────┘ │               │
    │               └──────────────────┘               │
    │                                                   │
    ▼                                                   ▼
┌────────┐                                    ┌────────────┐
│ Sniper │                                    │  Retail     │
│  Bot   │──── 90% fee ──→ POL               │  Traders    │
│ (REKT) │                                    │ (Protected) │
└────────┘                                    └────────────┘
```

---

## 📜 Smart Contracts

**Deployed on X Layer Testnet (Chain ID: 1952)**

| Contract | Address | Explorer |
|:---------|:--------|:---------|
| 🏭 **PoolManager** | `0x1AF4D7774351504dBddAada09122adB48fcE7ab6` | [View on OKLink](https://www.oklink.com/xlayer-test/address/0x1AF4D7774351504dBddAada09122adB48fcE7ab6) |
| 🛡️ **NeuroGuardHook** | `0x595ac52d42D77902dbF4fdD274456409C9CC1080` | [View on OKLink](https://www.oklink.com/xlayer-test/address/0x595ac52d42D77902dbF4fdD274456409C9CC1080) |
| 🤖 **AI Agent Wallet** | `0x07797e6C86302B6D4C23fe80A67ac42CeC4dfc28` | — |

**Key Contract Functions:**

| Function | Access | Description |
|:---------|:------:|:------------|
| `setRiskLevel(uint8)` | AI Agent Only | Update on-chain risk score (0-10) |
| `setAIAgent(address)` | AI Agent Only | Transfer AI Agent role |
| `beforeSwap()` | Internal | Sniper detection + dynamic fee routing |
| `afterInitialize()` | Internal | Record pool creation block |
| `riskScore()` | Public | Read current risk level |
| `isInSniperWindow()` | Public | Check if sniper window is active |

---

## 🚀 Quick Start

### Prerequisites

- [Foundry](https://book.getfoundry.sh/getting-started/installation) (`forge`, `cast`)
- Node.js 18+ (for AI Agent)
- Python 3.10+ (for AI Agent alternative)

### 1. Clone & Build

```bash
git clone https://github.com/OldDream666/Neuroguard-Hook.git
cd Neuroguard-Hook
forge build
```

### 2. Run Tests

```bash
forge test -vvvv
```

### 3. Deploy (One-Click)

```bash
# Set your deployer private key
export DEPLOYER_PRIVATE_KEY="0x..."

# Deploy PoolManager + Hook in one transaction
forge script script/Deploy.s.sol:Deploy \
  --rpc-url https://testrpc.xlayer.tech \
  --private-key $DEPLOYER_PRIVATE_KEY \
  --broadcast -vvvv
```

> ⚠️ The deploy script auto-mines a CREATE2 salt to ensure the hook address has the correct permission bits for Uniswap V4.

### 4. Verify on Explorer

```bash
forge verify-contract <HOOK_ADDRESS> src/NeuroGuardHook.sol:NeuroGuardHook \
  --chain-id 1952 \
  --verifier oklink \
  --verifier-url https://www.oklink.com/api/v5/explorer/contract/verify-source-code \
  --etherscan-api-key $OKLINK_API_KEY
```

---

## 🤖 AI Agent

The AI Agent monitors market conditions and updates the on-chain risk score. **Without it, only Layer 1 (sniper protection) works.** With it, Layer 2 (AI-driven dynamic fees) activates.

### Python Version

```bash
cd script
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values:
#   PRIVATE_KEY=0x...           (AI Agent wallet private key)
#   HOOK_ADDRESS=0x595ac5...    (deployed Hook address)
#   TOKEN_ID=ETH-USDT           (OKX instrument ID to monitor)
#   LLM_API_KEY=sk-xxx          (optional: for LLM enhancement)

# Run once
python3 ai_agent.py

# Loop every 60 seconds
python3 ai_agent.py --loop 60

# Dry run (score only, no tx)
python3 ai_agent.py --dry-run

# Manual override
python3 ai_agent.py --score 7
```

### Node.js Version

```bash
cd ai-agent
npm install
cp .env.example .env
# Edit .env: set AI_AGENT_PRIVATE_KEY, HOOK_CONTRACT_ADDRESS

# Run once
node index.js

# Loop every 60 seconds
node index.js --loop 60

# Dry run
node index.js --dry-run
```

### Data Source

Both agents use **real market data from OKX** (free, no API key, no rate limit):

- **Signal**: 24h price change (calculated from `last` vs `open24h`) → mapped to risk score 0-10


To monitor a different token, set `TOKEN_ID` in `.env`:
```
# OKX instrument IDs: ETH-USDT, BTC-USDT, SOL-USDT, DOGE-USDT, PEPE-USDT, SHIB-USDT
TOKEN_ID=pepe
```

### Optional: LLM Enhancement

Both agents support **any OpenAI-compatible LLM API** for richer sentiment analysis:

```bash
# In .env, set these three variables:
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=*** LLM_MODEL=gpt-4o-mini
```

Supported providers (any OpenAI-compatible API):
- **OpenAI**: `https://api.openai.com/v1/chat/completions`
- **DeepSeek**: `https://api.deepseek.com/v1/chat/completions`
- **Groq**: `https://api.groq.com/openai/v1/chat/completions`
- **Ollama (local)**: `http://localhost:11434/v1/chat/completions`
- **Any proxy/custom endpoint**

When `LLM_API_KEY` is set, the agent uses the LLM for risk assessment. Otherwise, it falls back to the built-in algorithm.

---

## 📊 Fee Mechanism Summary

```
                    ┌─────────────────────┐
                    │   Swap Arrives      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Within 3 blocks of  │
                    │ pool creation?      │
                    └──────────┬──────────┘
                          YES/ \NO
                         /     \
              ┌─────────▼┐   ┌▼──────────────┐
              │ Large buy │   │ Check riskScore│
              │ (>10k)?   │   └──────┬────────┘
              └─────┬─────┘          │
               YES/ \NO         ┌────▼────┐
               /     \          │ Score   │
         ┌────▼──┐ ┌──▼──┐     │ 0-10    │
         │ 90%   │ │0.3% │     └────┬────┘
         │ FEE   │ │ FEE │          │
         │(SNIPER│ │     │    ┌─────▼──────┐
         │ TRAP) │ │     │    │ Adaptive    │
         └───────┘ └─────┘    │ Fee Engine  │
                              │             │
                              │ Buy:  0.1-  │
                              │        0.3% │
                              │ Sell: 0.3-  │
                              │        10%  │
                              └─────────────┘
```

---

## 🧪 Test Coverage

| Test Case | Description | Expected |
|:----------|:------------|:---------|
| `test_sniperDetection_highFee` | Bot buys large amount in block 1 | 90% fee applied |
| `test_normalUser_normalFee` | Regular user buys after sniper window | 0.3% fee |
| `test_aiHighRisk_highSellFee` | AI sets risk=8, user sells | 10% sell fee |
| `test_aiLowRisk_normalFee` | AI sets risk=0, normal trading | 0.3% fee |
| `test_unauthorizedCaller_reverts` | Non-AI agent calls setRiskLevel | Reverts |
| `test_sniperVolumeAccumulation` | Multiple small buys from same address | Cumulative detection |

---

## 🙏 Acknowledgments

- [Uniswap V4](https://docs.uniswap.org/contracts/v4/overview) — For the revolutionary hook architecture
- [OKX X Layer](https://web3.okx.com/xlayer) — For the hackathon and the chain
- [Foundry](https://book.getfoundry.sh/) — For the best Solidity dev tooling

---

<div align="center">

**Built with 🛡️ for the OKX Build-X Hackathon**

*NeuroGuard Hook — Because fair launches shouldn't be a myth.*

</div>
