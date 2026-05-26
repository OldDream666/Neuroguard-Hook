# 🛡️ NeuroGuard Hook — 项目全览 & 使用指南

> **给零 Web3 经验的你看的完整说明。** 本文档用大白话解释这个项目是什么、为什么要做、怎么用。

---

## 一、这个项目到底在干什么？

### 一句话版本
> NeuroGuard Hook 是一个「交易手续费调节器」，插在 Uniswap（去中心化交易所）里，自动帮散户防两种坏人：**开盘抢跑的机器人** 和 **恶意砸盘的大户**。

### 展开说

想象你要在 Uniswap 上买一个新币。正常流程是：项目方创建一个「交易池」→ 大家来买卖。

**问题 1：机器人抢跑**
- 池子刚创建（第 1 个区块），机器人就在 0.1 秒内买入大量代币
- 等你看到的时候，价格已经被拉高了
- 机器人随后高位卖出，你接盘亏钱

**问题 2：恐慌砸盘**
- 有人散布假消息引发恐慌
- 大家疯狂卖出 → 价格暴跌 → 更多人恐慌卖出 → 死亡螺旋
- 没有任何机制能踩刹车

**NeuroGuard 的解决方案：**

```
                    有人发起交易
                         │
                         ▼
              ┌─────────────────────┐
              │   NeuroGuard Hook   │  ← 插在交易所里的「智能守卫」
              │                     │
              │  检查 1: 开盘前3个区块？ │
              │    是 → 大额买入？     │
              │         是 → 收 90% 手续费！（机器人被收割）
              │         否 → 正常费率 0.3%
              │                     │
              │  检查 2: AI 说现在恐慌？│
              │    是 → 卖出收 10%（阻止恐慌抛售）
              │         买入只收 0.1%（鼓励抄底）
              │    否 → 正常费率 0.3%
              └─────────────────────┘
```

---

## 二、项目文件结构

```
neuroguard-hook/
│
├── src/                          ← 核心智能合约（Solidity 语言）
│   ├── NeuroGuardHook.sol        ← ⭐ 主合约！所有防御逻辑都在这里
│   └── HookMiner.sol             ← 辅助工具：挖一个合法的合约地址
│
├── test/
│   └── NeuroGuardHook.t.sol      ← 测试文件（18 个测试用例）
│
├── script/
│   ├── Deploy.s.sol              ← 部署脚本（一键部署到区块链）
│   ├── ai_agent.py               ← ⭐ Python 版 AI Agent（OKX 真实数据）
│   ├── requirements.txt          ← Python 依赖
│   └── .env                      ← 你的私钥配置（不要提交到 git！）
│
├── ai-agent/
│   ├── index.js                  ← ⭐ Node.js 版 AI Agent
│   ├── package.json              ← Node.js 依赖
│   ├── abi.json                  ← 合约 ABI（接口定义）
│   └── .env.example              ← 配置模板
│
├── README.md                     ← 黑客松提交的英文 README
├── README_CN.md                  ← 中文版 README
├── foundry.toml                  ← Foundry 编译配置
└── .gitignore                    ← Git 忽略规则
```

---

## 三、核心文件详解

### 📄 `src/NeuroGuardHook.sol` — 主合约（157 行）

这是整个项目的灵魂。它是一个 **Uniswap V4 Hook**，意思是：Uniswap 在执行交易的前后，会「回调」这个合约，让它决定要不要干预。

**它做了什么：**

| 功能 | 怎么做的 | 在哪一行 |
|------|---------|---------|
| 记录池子创建时间 | `afterInitialize()` 里保存 `poolCreationBlock` | 第 89-97 行 |
| 防狙击 | `beforeSwap()` 里检查是否在前 3 个区块 + 大额买入 → 收 90% | 第 117-135 行 |
| AI 动态费率 | `beforeSwap()` 里读取 `riskScore`，按分数调整买入/卖出费率 | 第 137-150 行 |
| 权限控制 | `onlyAIAgent` 修饰符，只有 AI Agent 钱包能调 `setRiskLevel` | 第 70-73 行 |

**关键数字：**
- `SNIPER_FEE = 900000` → 90% 手续费（惩罚狙击手）
- `DEFAULT_FEE = 3000` → 0.3% 手续费（正常交易）
- `HIGH_RISK_SELL_FEE = 100000` → 10% 卖出费（恐慌时的防御）
- `LOW_RISK_BUY_FEE = 1000` → 0.1% 买入费（恐慌时鼓励抄底）
- `SNIPER_WINDOW = 3` → 开盘后 3 个区块为狙击窗口

### 📄 `script/ai_agent.py` — Python AI Agent（308 行）

这是「链下大脑」。它是一个 Python 脚本，做三件事：

   **① 模拟 AI 打分**：通过 OKX API 获取真实市场数据（24h 价格变化），加权计算出 0-10 的风险分
2. **检查链上状态**：读取合约当前的 `riskScore`
3. **发送交易**：如果分数变了，调用合约的 `setRiskLevel()` 更新链上状态

```
AI Agent 工作循环：

  每隔 N 秒 → 计算风险分 → 分数变了？ → 发交易更新链上
                         → 分数没变？ → 跳过，等下一轮
```

### 📄 `test/NeuroGuardHook.t.sol` — 测试文件（273 行）

包含 18 个测试用例，覆盖所有核心场景：

| 测试 | 验证什么 |
|------|---------|
| `test_sniperTrap_largeBuyInBlock1` | 机器人第 1 区块大额买入 → 被收 90% |
| `test_sniperTrap_smallBuyInWindow` | 普通用户小额买入 → 正常 0.3% |
| `test_sniperTrap_afterWindow` | 3 个区块后 → 不再触发狙击检测 |
| `test_aiFee_highRisk_sell` | AI 设风险=9，卖出 → 收 10% |
| `test_aiFee_highRisk_buy` | AI 设风险=9，买入 → 只收 0.1% |
| `test_accessControl_onlyAIAgent` | 非 AI Agent 调用 → 回滚报错 |
| `test_fullLifecycle` | 完整生命周期：狙击→正常→FUD→恢复 |

---

## 四、已部署的合约

| 名称 | 地址 | 说明 |
|------|------|------|
| PoolManager | `0x1AF4D7774351504dBddAada09122adB48fcE7ab6` | Uniswap V4 的核心池管理器 |
| **NeuroGuardHook** | `0x595ac52d42D77902dbF4fdD274456409C9CC1080` | 我们的 Hook 合约 |
| AI Agent 钱包 | `0x07797e6C86302B6D4C23fe80A67ac42CeC4dfc28` | 有权调用 setRiskLevel 的钱包 |

部署在 **X Layer 测试网**（Chain ID: 1952），可以在 [OKLink 浏览器](https://www.oklink.com/xlayer-test) 查看。

---

## 五、你可以亲自做的事

### ✅ 1. 运行测试（本地验证，不需要花钱）

```bash
cd ~/neuroguard-hook
~/.foundry/bin/forge test -vvvv
```

这会在本地模拟器上运行 18 个测试，验证所有逻辑是否正确。不需要网络，不需要 gas 费。

### ✅ 2. 运行 AI Agent（干跑模式，不发交易）

**Python 版：**
```bash
cd ~/neuroguard-hook/script
pip install -r requirements.txt
python ai_agent.py --dry-run
```

**Node.js 版：**
```bash
cd ~/neuroguard-hook/ai-agent
npm install
cp .env.example .env
node index.js --dry-run
```

干跑模式只计算风险分，不发送任何交易，不花一分钱。

### ✅ 3. 运行 AI Agent（真实模式，发交易到链上）

```bash
# Python 版
cd ~/neuroguard-hook/script
# 编辑 .env，填入你的私钥和 Hook 地址
python ai_agent.py --loop 60    # 每 60 秒检查一次
```

⚠️ **注意**：真实模式会发送交易到 X Layer 测试网，需要：
- 钱包里有测试网 OKB（去 [水龙头](https://www.okx.com/xlayer/faucet) 领取）
- 钱包地址必须是合约的 `aiAgent`（就是部署时用的那个地址）

### ✅ 4. 手动设置风险分数

```bash
# Python 版
python ai_agent.py --score 7    # 手动设为 7（恐惧级别）
python ai_agent.py --score 0    # 恢复正常
```

---

## 六、常见问题

### Q: 我不懂 Solidity，能改合约逻辑吗？
A: 不需要改。合约已经编译部署好了。如果你真的想改，修改 `src/NeuroGuardHook.sol` 后需要重新 `forge build` 和重新部署。

   ### Q: AI Agent 的「AI」是真的 AI 吗？
   A: **是真实的市场数据分析。** 它通过 OKX API 获取实时价格和交易量，基于 24h 涨跌幅计算风险分。代码里还有 OpenAI GPT-4o-mini 的调用模板（已注释），取消注释可接入 LLM 做更丰富的情绪分析。

### Q: 90% 手续费去哪了？
A: 手续费沉淀在 Uniswap V4 的池子里，成为**协议控制的公共流动性 (POL)**，实际上是在帮所有交易者加深池子深度。

### Q: 测试跑失败了怎么办？
A: 确保在项目根目录运行，且 Foundry 版本是最新的。运行 `~/.foundry/bin/foundryup` 更新。

### Q: 这个项目还能做什么改进？
A: 几个方向：
- 接入真实的情绪分析 API（LunarCrush、Santiment）
- 支持多个代币池同时监控
- 加入 TWAP（时间加权均价）检测异常价格波动
- 前端仪表盘展示实时风险状态
