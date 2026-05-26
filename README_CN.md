<div align="center">

# 🛡️ NeuroGuard Hook · 智卫

### *首个 AI 驱动的自适应流动性 & 防狙击护盾 — 为 Uniswap V4 而生*

**保护散户。惩罚狙击手。AI 加持。**

[![X Layer](https://img.shields.io/badge/链-X%20Layer%20测试网-000?style=for-the-badge&logo=okx&logoColor=fff)](https://www.oklink.com/xlayer-test)
[![Uniswap V4](https://img.shields.io/badge/协议-Uniswap%20V4-FF007A?style=for-the-badge&logo=uniswap&logoColor=fff)](https://docs.uniswap.org/contracts/v4/overview)
[![Foundry](https://img.shields.io/badge/构建工具-Foundry-000?style=for-the-badge)](https://book.getfoundry.sh/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.26-363636?style=for-the-badge&logo=solidity&logoColor=fff)](https://soliditylang.org/)

---

**🏆 OKX Build-X 黑客松 — Uniswap V4 Hook 赛道**

</div>

---

## 📖 目录

- [灵感来源](#-灵感来源)
- [我们的方案](#-我们的方案)
- [核心机制](#-核心机制)
- [为什么选择 X Layer](#-为什么选择-x-layer)
- [系统架构](#-系统架构)
- [智能合约地址](#-智能合约地址)
- [快速开始](#-快速开始)
- [AI Agent 使用指南](#-ai-agent-使用指南)

---

## 🔥 灵感来源

> *"在当前的 DeFi 世界里，散户就是退出流动性。"*

每一天，成千上万的新代币在 DEX 上首发。故事总是惊人地相似：

### 🤖 科学家狙击机器人

毫秒级的机器人在每个新池子开盘时抢先买入，在散户看到代币之前就已经吃掉了大量筹码。散户只能在高位接盘，几分钟后机器人砸盘离场。

**结果：90% 以上的开盘参与者亏损。**

### 😱 FUD 恐慌性砸盘

协调一致的做空攻击引发连锁恐慌。没有熔断机制，没有防御手段。一个大户抛售 → 价格暴跌 → 止损触发 → 更多抛售 → 死亡螺旋。

**结果：合法项目在几小时内归零。**

**核心问题：AMM 是被动的。** 它们没有智能、没有记忆、没有防御。直到现在。

---

## 💡 我们的方案

**NeuroGuard Hook** 是一个为 Uniswap V4 设计的**动态防御型 AMM Hook**，融合了：

- 🧱 **纯链上防狙击陷阱** — 确定性、不可篡改、无法绕过
- 🧠 **链下 AI 情绪引擎** — 自适应、实时、智能

两层防御系统，让代币首发对每个人都公平 — 而不仅仅是机器人的游戏。

```
┌─────────────────────────────────────────────────┐
│              NeuroGuard Hook · 智卫              │
│                                                  │
│   第一层：防狙击陷阱（纯链上）                    │
│   ├─ 区块高度检测                                │
│   ├─ 对狙击手征收 90% 惩罚性费率                │
│   └─ 手续费 → 协议控制流动性 (POL)              │
│                                                  │
│   第二层：AI 情绪熔断器                          │
│   ├─ 链下情绪实时监控（AI Agent）               │
│   ├─ 链上风险评分 (0-10)                        │
│   └─ 动态卖出费率 (0.3% → 10%)                  │
└─────────────────────────────────────────────────┘
```

---

## ⚙️ 核心机制

### 🪤 第一层：防狙击陷阱 — *消灭机器人*

> **设计哲学：** 不要 revert 狙击交易 — *收税*。

当新代币池创建后，NeuroGuard 激活 **3 个区块的狙击窗口**：

**① 检测**：Hook 通过 `afterInitialize` 记录 `poolCreationBlock`。前 3 个区块内的任何 swap 都会触发狙击检测模式。

**② 识别**：如果单一地址在窗口期内进行**大额买入**（超过 `LARGE_SWAP_THRESHOLD`），即被判定为狙击机器人。

**③ 惩罚**：不会 revert 交易（这会让机器人不断重试），而是通过 Uniswap V4 的 `updateDynamicLPFee()` 施加 **90% 动态费率**。

**④ 转化**：巨额手续费不会被销毁 — 它**自动成为协议控制的公共流动性 (POL)**，为真正的交易者加深池子深度。

```solidity
// NeuroGuardHook.sol — beforeSwap()
if (block.number <= poolCreationBlock + SNIPER_WINDOW) {
    if (isBuy && cumVolume > LARGE_SWAP_THRESHOLD) {
        fee = SNIPER_FEE; // 90%
        manager.updateDynamicLPFee(key, fee);
        // 狙击手的 ETH → POL → 保护真正的用户
    }
}
```

> **🎯 结果：** 狙击机器人每次尝试都会损失 90% 的资金。它们偷来的钱变成了保护社区的流动性。

---

### 🧠 第二层：AI 情绪熔断器 — *智能防御*

> **设计哲学：** 市场需要的是恒温器，而不是火警铃。

开盘后，威胁从狙击手转向**协调性 FUD 攻击**和**恐慌性抛售**。

#### 🔗 链下：实时市场监控 Agent

Python/Node.js Agent 从 **OKX 获取真实市场数据**（免费，无需 API Key）：

| 信号 | 权重 | 数据源 | 说明 |
|:-----|:----:|:------:|:-----|
| 📉 24h 价格变化 | 100% | OKX API | 跌幅大小 → 风险等级 |

**风险阈值（基于真实 24h 价格变化）：**

| 24h 跌幅 | 风险评分 | 状态 |
|:---------|:--------:|:----:|
| 0% 或上涨 | 0 | 🟢 平静 |
| -1% ~ -2% | 1-2 | 🟢 平静 |
| -2% ~ -5% | 3-4 | 🟡 谨慎 |
| -5% ~ -10% | 5-7 | 🟠 恐惧 |
| 超过 -10% | 8-10 | 🔴 恐慌 |

Agent 计算出**风险评分 (0-10)**，当阈值被触发时，自动调用链上 `setRiskLevel()` 接口。

#### ⛓️ 链上：动态费率响应

| 风险评分 | 状态 | 买入费率 | 卖出费率 | 策略 |
|:--------:|:----:|:--------:|:--------:|:-----|
| 0-2 | 🟢 平静 | 0.3% | 0.3% | 正常交易 |
| 3-4 | 🟡 谨慎 | 0.3% | 0.6% | 轻度警惕 |
| 5-7 | 🟠 恐惧 | 0.1% | 3.0% | 抑制卖出，激励买入 |
| 8-10 | 🔴 恐慌 | 0.1% | **10%** | 最大卖出防御 |

```solidity
// 风险自适应费率逻辑
if (riskScore >= 7) {
    buyFee  = 0.1%;   // 吸引买家（软底）
    sellFee = 10%;     // 阻止恐慌性抛售
}
```

> **🎯 结果：** 当 FUD 来袭时，卖出变得昂贵而买入变得便宜。这形成了一个**天然熔断器**，防止死亡螺旋，同时允许真正的价格发现。

---

## 🌐 为什么选择 X Layer

> *"X Layer 不仅仅是一条链 — 它是 OKX Web3 生态的神经系统。"*

我们选择 **X Layer** 绝非偶然：

| 特性 | 对 NeuroGuard 的意义 |
|:-----|:---------------------|
| ⚡ **极低 Gas 费** | AI Agent 需要频繁调用 `setRiskLevel()`。在以太坊上，每笔交易 $5-50。在 X Layer 上，仅需**几分之一美分**。高频 AI 监控只有在这里才经济可行。 |
| 🔥 **高吞吐量** | 狙击检测需要按区块粒度进行。X Layer 的快速出块时间提供了**更精细的保护窗口**。 |
| 🏗️ **OKX 生态系统** | X Layer 是 OKX Web3 的**基础设施骨干**。任何通过 OKX Wallet 或 OKX DEX 发行的代币都可以无缝接入 NeuroGuard 作为**原生安全层**。 |
| 🚀 **OP Stack / Polygon CDK** | EVM 兼容意味着我们的 Hook **无需任何修改**即可运行。 |
| 🌍 **生态增长** | 随着 X Layer 吸引更多 DeFi 协议，NeuroGuard 成为每个新池子的**默认安全基础设施**。 |

> **愿景：** NeuroGuard Hook 致力于成为 X Layer 代币首发的**标准安全基础设施** — 将每一个新池子变成**受保护的公平发射环境**。

---

## 🏗️ 系统架构

```
                    ┌──────────────────┐
                    │    市场数据       │
                    │ (社交、链上、     │
                    │  鲸鱼、永续合约)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    AI Agent       │
                    │ (Python/Node.js) │
                    │   情绪评分器      │
                    └────────┬─────────┘
                             │ setRiskLevel(score)
                    ┌────────▼─────────┐
                    │  X Layer 测试网   │
                    │                  │
    ┌───────────────┤  PoolManager    ├───────────────┐
    │               │                  │               │
    │               └────────┬─────────┘               │
    │                        │                         │
    │               ┌────────▼─────────┐               │
    │               │  NeuroGuardHook  │               │
    │               │                  │               │
    │               │ ┌──────────────┐ │               │
    │               │ │  防狙击陷阱   │ │               │
    │               │ │ (beforeSwap) │ │               │
    │               │ └──────────────┘ │               │
    │               │ ┌──────────────┐ │               │
    │               │ │  AI 费率逻辑  │ │               │
    │               │ │  (riskScore) │ │               │
    │               │ └──────────────┘ │               │
    │               └──────────────────┘               │
    │                                                   │
    ▼                                                   ▼
┌────────┐                                    ┌────────────┐
│ 狙击手  │                                    │   散户      │
│ (被收割) │──── 90% 手续费 ──→ POL           │  (受保护)   │
└────────┘                                    └────────────┘
```

---

## 📜 智能合约地址

**部署于 X Layer 测试网（Chain ID: 1952）**

| 合约 | 地址 | 浏览器 |
|:-----|:-----|:-------|
| 🏭 **PoolManager** | `0x1AF4D7774351504dBddAada09122adB48fcE7ab6` | [OKLink 查看](https://www.oklink.com/xlayer-test/address/0x1AF4D7774351504dBddAada09122adB48fcE7ab6) |
| 🛡️ **NeuroGuardHook** | `0x595ac52d42D77902dbF4fdD274456409C9CC1080` | [OKLink 查看](https://www.oklink.com/xlayer-test/address/0x595ac52d42D77902dbF4fdD274456409C9CC1080) |
| 🤖 **AI Agent 钱包** | `0x07797e6C86302B6D4C23fe80A67ac42CeC4dfc28` | — |

**核心合约函数：**

| 函数 | 权限 | 说明 |
|:-----|:----:|:-----|
| `setRiskLevel(uint8)` | 仅 AI Agent | 更新链上风险评分 (0-10) |
| `setAIAgent(address)` | 仅 AI Agent | 转移 AI Agent 角色 |
| `beforeSwap()` | 内部 | 狙击检测 + 动态费率路由 |
| `afterInitialize()` | 内部 | 记录池子创建区块 |
| `riskScore()` | 公开 | 读取当前风险等级 |
| `isInSniperWindow()` | 公开 | 检查是否在狙击窗口期 |

---

## 🚀 快速开始

### 前置条件

- [Foundry](https://book.getfoundry.sh/getting-started/installation)（`forge`, `cast`）
- Node.js 18+（AI Agent 使用）
- Python 3.10+（AI Agent 备选）

### 1. 克隆 & 编译

```bash
git clone https://github.com/your-org/neuroguard-hook.git
cd neuroguard-hook
forge install
forge build
```

### 2. 运行测试

```bash
forge test -vvvv
```

### 3. 一键部署

```bash
# 设置部署者私钥
export DEPLOYER_PRIVATE_KEY="0x..."

# 一键部署 PoolManager + Hook
forge script script/Deploy.s.sol:Deploy \
  --rpc-url https://testrpc.xlayer.tech \
  --private-key $DEPLOYER_PRIVATE_KEY \
  --broadcast -vvvv
```

> ⚠️ 部署脚本会自动挖掘 CREATE2 salt，确保 Hook 地址的尾部位匹配 Uniswap V4 所需的权限标志。

---

## 🤖 AI Agent 使用指南

### Python 版本

```bash
cd script
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：填入 PRIVATE_KEY 和 HOOK_ADDRESS

# 单次运行
python ai_agent.py

# 每 60 秒轮询
python ai_agent.py --loop 60

# 干跑模式（只评分，不发交易）
python ai_agent.py --dry-run

# 手动指定风险分数
python ai_agent.py --score 7
```

### Node.js 版本

```bash
cd ai-agent
npm install
cp .env.example .env
# 编辑 .env：填入 AI_AGENT_PRIVATE_KEY 和 HOOK_CONTRACT_ADDRESS

# 单次运行
node index.js

# 每 60 秒轮询
node index.js --loop 60

# 干跑模式
node index.js --dry-run
```

### 数据源

两个版本均使用 **OKX 官方公开 API**（免费，无需 API Key，无限速）：

- **信号**：24h 价格变化（由 `last` 与 `open24h` 计算）→ 映射为风险评分 0-10


监控不同代币，在 `.env` 中设置 `TOKEN_ID`：
```
# OKX 交易对 ID：ETH-USDT, BTC-USDT, SOL-USDT, DOGE-USDT, PEPE-USDT, SHIB-USDT
TOKEN_ID=pepe
```

### 可选：接入 LLM 增强

两个版本均支持**任意 OpenAI 兼容的 LLM API**，用于更丰富的情绪分析：

```bash
# 在 .env 中设置以下三个变量：
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=*** LLM_MODEL=gpt-4o-mini
```

支持的供应商（任何 OpenAI 兼容 API）：
- **OpenAI**：`https://api.openai.com/v1/chat/completions`
- **DeepSeek**：`https://api.deepseek.com/v1/chat/completions`
- **Groq**：`https://api.groq.com/openai/v1/chat/completions`
- **Ollama（本地）**：`http://localhost:11434/v1/chat/completions`
- **任意代理/自定义端点**

设置 `LLM_API_KEY` 后，Agent 会使用 LLM 进行风险评估。未设置时自动使用内置算法。

---

## 🧪 测试覆盖

| 测试用例 | 描述 | 预期结果 |
|:---------|:-----|:---------|
| `test_sniperDetection_highFee` | 机器人在第 1 个区块大额买入 | 施加 90% 费率 |
| `test_normalUser_normalFee` | 普通用户在狙击窗口后买入 | 正常 0.3% 费率 |
| `test_aiHighRisk_highSellFee` | AI 设置风险=8，用户卖出 | 收取 10% 卖出费率 |
| `test_aiLowRisk_normalFee` | AI 设置风险=0，正常交易 | 正常 0.3% 费率 |
| `test_unauthorizedCaller_reverts` | 非 AI Agent 调用 setRiskLevel | 交易回滚 |
| `test_sniperVolumeAccumulation` | 同一地址多笔小额买入 | 累计量触发检测 |

---

## 🙏 致谢

- [Uniswap V4](https://docs.uniswap.org/contracts/v4/overview) — 革命性的 Hook 架构
- [OKX X Layer](https://web3.okx.com/xlayer) — 黑客松与链基础设施
- [Foundry](https://book.getfoundry.sh/) — 最优秀的 Solidity 开发工具

---

<div align="center">

**为 OKX Build-X 黑客松而建 🛡️**

*NeuroGuard Hook — 让公平发射不再是神话。*

</div>
