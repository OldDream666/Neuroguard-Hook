     1|<div align="center">
     2|
     3|# 🛡️ NeuroGuard Hook · 智卫
     4|
     5|### *首个 AI 驱动的自适应流动性 & 防狙击护盾 — 为 Uniswap V4 而生*
     6|
     7|**保护散户。惩罚狙击手。AI 加持。**
     8|
     9|[![X Layer](https://img.shields.io/badge/链-X%20Layer%20测试网-000?style=for-the-badge&logo=okx&logoColor=fff)](https://www.oklink.com/xlayer-test)
    10|[![Uniswap V4](https://img.shields.io/badge/协议-Uniswap%20V4-FF007A?style=for-the-badge&logo=uniswap&logoColor=fff)](https://docs.uniswap.org/contracts/v4/overview)
    11|[![Foundry](https://img.shields.io/badge/构建工具-Foundry-000?style=for-the-badge)](https://book.getfoundry.sh/)
    12|[![Solidity](https://img.shields.io/badge/Solidity-0.8.26-363636?style=for-the-badge&logo=solidity&logoColor=fff)](https://soliditylang.org/)
    13|
    14|---
    15|
    16|**🏆 OKX Build-X 黑客松 — Uniswap V4 Hook 赛道**
    17|
    18|</div>
    19|
    20|---
    21|
    22|## 📖 目录
    23|
    24|- [灵感来源](#-灵感来源)
    25|- [我们的方案](#-我们的方案)
    26|- [核心机制](#-核心机制)
    27|- [为什么选择 X Layer](#-为什么选择-x-layer)
    28|- [系统架构](#-系统架构)
    29|- [智能合约地址](#-智能合约地址)
    30|- [快速开始](#-快速开始)
    31|- [AI Agent 使用指南](#-ai-agent-使用指南)
    32|
    33|---
    34|
    35|## 🔥 灵感来源
    36|
    37|> *"在当前的 DeFi 世界里，散户就是退出流动性。"*
    38|
    39|每一天，成千上万的新代币在 DEX 上首发。故事总是惊人地相似：
    40|
    41|### 🤖 科学家狙击机器人
    42|
    43|毫秒级的机器人在每个新池子开盘时抢先买入，在散户看到代币之前就已经吃掉了大量筹码。散户只能在高位接盘，几分钟后机器人砸盘离场。
    44|
    45|**结果：90% 以上的开盘参与者亏损。**
    46|
    47|### 😱 FUD 恐慌性砸盘
    48|
    49|协调一致的做空攻击引发连锁恐慌。没有熔断机制，没有防御手段。一个大户抛售 → 价格暴跌 → 止损触发 → 更多抛售 → 死亡螺旋。
    50|
    51|**结果：合法项目在几小时内归零。**
    52|
    53|**核心问题：AMM 是被动的。** 它们没有智能、没有记忆、没有防御。直到现在。
    54|
    55|---
    56|
    57|## 💡 我们的方案
    58|
    59|**NeuroGuard Hook** 是一个为 Uniswap V4 设计的**动态防御型 AMM Hook**，融合了：
    60|
    61|- 🧱 **纯链上防狙击陷阱** — 确定性、不可篡改、无法绕过
    62|- 🧠 **链下 AI 情绪引擎** — 自适应、实时、智能
    63|
    64|两层防御系统，让代币首发对每个人都公平 — 而不仅仅是机器人的游戏。
    65|
    66|```
    67|┌─────────────────────────────────────────────────┐
    68|│              NeuroGuard Hook · 智卫              │
    69|│                                                  │
    70|│   第一层：防狙击陷阱（纯链上）                    │
    71|│   ├─ 区块高度检测                                │
    72|│   ├─ 对狙击手征收 90% 惩罚性费率                │
    73|│   └─ 手续费 → 协议控制流动性 (POL)              │
    74|│                                                  │
    75|│   第二层：AI 情绪熔断器                          │
    76|│   ├─ 链下情绪实时监控（AI Agent）               │
    77|│   ├─ 链上风险评分 (0-10)                        │
    78|│   └─ 动态卖出费率 (0.3% → 10%)                  │
    79|└─────────────────────────────────────────────────┘
    80|```
    81|
    82|---
    83|
    84|## ⚙️ 核心机制
    85|
    86|### 🪤 第一层：防狙击陷阱 — *消灭机器人*
    87|
    88|> **设计哲学：** 不要 revert 狙击交易 — *收税*。
    89|
    90|当新代币池创建后，NeuroGuard 激活 **3 个区块的狙击窗口**：
    91|
    92|**① 检测**：Hook 通过 `afterInitialize` 记录 `poolCreationBlock`。前 3 个区块内的任何 swap 都会触发狙击检测模式。
    93|
    94|**② 识别**：如果单一地址在窗口期内进行**大额买入**（超过 `LARGE_SWAP_THRESHOLD`），即被判定为狙击机器人。
    95|
    96|**③ 惩罚**：不会 revert 交易（这会让机器人不断重试），而是通过 Uniswap V4 的 `updateDynamicLPFee()` 施加 **90% 动态费率**。
    97|
    98|**④ 转化**：巨额手续费不会被销毁 — 它**自动成为协议控制的公共流动性 (POL)**，为真正的交易者加深池子深度。
    99|
   100|```solidity
   101|// NeuroGuardHook.sol — beforeSwap()
   102|if (block.number <= poolCreationBlock + SNIPER_WINDOW) {
   103|    if (isBuy && cumVolume > LARGE_SWAP_THRESHOLD) {
   104|        fee = SNIPER_FEE; // 90%
   105|        manager.updateDynamicLPFee(key, fee);
   106|        // 狙击手的 ETH → POL → 保护真正的用户
   107|    }
   108|}
   109|```
   110|
   111|> **🎯 结果：** 狙击机器人每次尝试都会损失 90% 的资金。它们偷来的钱变成了保护社区的流动性。
   112|
   113|---
   114|
   115|### 🧠 第二层：AI 情绪熔断器 — *智能防御*
   116|
   117|> **设计哲学：** 市场需要的是恒温器，而不是火警铃。
   118|
   119|开盘后，威胁从狙击手转向**协调性 FUD 攻击**和**恐慌性抛售**。
   120|
   121|#### 🔗 链下：实时市场监控 Agent
   122|
   123|Python/Node.js Agent 从 **CoinGecko 获取真实市场数据**（免费，无需 API Key）：
   124|
   125|| 信号 | 权重 | 数据源 | 说明 |
   126||:-----|:----:|:------:|:-----|
   127|| 📉 24h 价格变化 | 70% | CoinGecko API | 跌幅大小 → 风险等级 |
   128|| 📈 交易量异常 | 30% | CoinGecko API | 当前量 vs 7天均量（放量暴跌 = 恐慌） |
   129|
   130|**风险阈值（基于真实 24h 价格变化）：**
   131|
   132|| 24h 跌幅 | 风险评分 | 状态 |
   133||:---------|:--------:|:----:|
   134|| 0% 或上涨 | 0 | 🟢 平静 |
   135|| -1% ~ -2% | 1-2 | 🟢 平静 |
   136|| -2% ~ -5% | 3-4 | 🟡 谨慎 |
   137|| -5% ~ -10% | 5-7 | 🟠 恐惧 |
   138|| 超过 -10% | 8-10 | 🔴 恐慌 |
   139|
   140|Agent 计算出**风险评分 (0-10)**，当阈值被触发时，自动调用链上 `setRiskLevel()` 接口。
   141|
   142|#### ⛓️ 链上：动态费率响应
   143|
   144|| 风险评分 | 状态 | 买入费率 | 卖出费率 | 策略 |
   145||:--------:|:----:|:--------:|:--------:|:-----|
   146|| 0-2 | 🟢 平静 | 0.3% | 0.3% | 正常交易 |
   147|| 3-4 | 🟡 谨慎 | 0.3% | 0.6% | 轻度警惕 |
   148|| 5-7 | 🟠 恐惧 | 0.1% | 3.0% | 抑制卖出，激励买入 |
   149|| 8-10 | 🔴 恐慌 | 0.1% | **10%** | 最大卖出防御 |
   150|
   151|```solidity
   152|// 风险自适应费率逻辑
   153|if (riskScore >= 7) {
   154|    buyFee  = 0.1%;   // 吸引买家（软底）
   155|    sellFee = 10%;     // 阻止恐慌性抛售
   156|}
   157|```
   158|
   159|> **🎯 结果：** 当 FUD 来袭时，卖出变得昂贵而买入变得便宜。这形成了一个**天然熔断器**，防止死亡螺旋，同时允许真正的价格发现。
   160|
   161|---
   162|
   163|## 🌐 为什么选择 X Layer
   164|
   165|> *"X Layer 不仅仅是一条链 — 它是 OKX Web3 生态的神经系统。"*
   166|
   167|我们选择 **X Layer** 绝非偶然：
   168|
   169|| 特性 | 对 NeuroGuard 的意义 |
   170||:-----|:---------------------|
   171|| ⚡ **极低 Gas 费** | AI Agent 需要频繁调用 `setRiskLevel()`。在以太坊上，每笔交易 $5-50。在 X Layer 上，仅需**几分之一美分**。高频 AI 监控只有在这里才经济可行。 |
   172|| 🔥 **高吞吐量** | 狙击检测需要按区块粒度进行。X Layer 的快速出块时间提供了**更精细的保护窗口**。 |
   173|| 🏗️ **OKX 生态系统** | X Layer 是 OKX Web3 的**基础设施骨干**。任何通过 OKX Wallet 或 OKX DEX 发行的代币都可以无缝接入 NeuroGuard 作为**原生安全层**。 |
   174|| 🚀 **OP Stack / Polygon CDK** | EVM 兼容意味着我们的 Hook **无需任何修改**即可运行。 |
   175|| 🌍 **生态增长** | 随着 X Layer 吸引更多 DeFi 协议，NeuroGuard 成为每个新池子的**默认安全基础设施**。 |
   176|
   177|> **愿景：** NeuroGuard Hook 致力于成为 X Layer 代币首发的**标准安全基础设施** — 将每一个新池子变成**受保护的公平发射环境**。
   178|
   179|---
   180|
   181|## 🏗️ 系统架构
   182|
   183|```
   184|                    ┌──────────────────┐
   185|                    │    市场数据       │
   186|                    │ (社交、链上、     │
   187|                    │  鲸鱼、永续合约)  │
   188|                    └────────┬─────────┘
   189|                             │
   190|                    ┌────────▼─────────┐
   191|                    │    AI Agent       │
   192|                    │ (Python/Node.js) │
   193|                    │   情绪评分器      │
   194|                    └────────┬─────────┘
   195|                             │ setRiskLevel(score)
   196|                    ┌────────▼─────────┐
   197|                    │  X Layer 测试网   │
   198|                    │                  │
   199|    ┌───────────────┤  PoolManager    ├───────────────┐
   200|    │               │                  │               │
   201|    │               └────────┬─────────┘               │
   202|    │                        │                         │
   203|    │               ┌────────▼─────────┐               │
   204|    │               │  NeuroGuardHook  │               │
   205|    │               │                  │               │
   206|    │               │ ┌──────────────┐ │               │
   207|    │               │ │  防狙击陷阱   │ │               │
   208|    │               │ │ (beforeSwap) │ │               │
   209|    │               │ └──────────────┘ │               │
   210|    │               │ ┌──────────────┐ │               │
   211|    │               │ │  AI 费率逻辑  │ │               │
   212|    │               │ │  (riskScore) │ │               │
   213|    │               │ └──────────────┘ │               │
   214|    │               └──────────────────┘               │
   215|    │                                                   │
   216|    ▼                                                   ▼
   217|┌────────┐                                    ┌────────────┐
   218|│ 狙击手  │                                    │   散户      │
   219|│ (被收割) │──── 90% 手续费 ──→ POL           │  (受保护)   │
   220|└────────┘                                    └────────────┘
   221|```
   222|
   223|---
   224|
   225|## 📜 智能合约地址
   226|
   227|**部署于 X Layer 测试网（Chain ID: 1952）**
   228|
   229|| 合约 | 地址 | 浏览器 |
   230||:-----|:-----|:-------|
   231|| 🏭 **PoolManager** | `0x1AF4D7774351504dBddAada09122adB48fcE7ab6` | [OKLink 查看](https://www.oklink.com/xlayer-test/address/0x1AF4D7774351504dBddAada09122adB48fcE7ab6) |
   232|| 🛡️ **NeuroGuardHook** | `0x595ac52d42D77902dbF4fdD274456409C9CC1080` | [OKLink 查看](https://www.oklink.com/xlayer-test/address/0x595ac52d42D77902dbF4fdD274456409C9CC1080) |
   233|| 🤖 **AI Agent 钱包** | `0x07797e6C86302B6D4C23fe80A67ac42CeC4dfc28` | — |
   234|
   235|**核心合约函数：**
   236|
   237|| 函数 | 权限 | 说明 |
   238||:-----|:----:|:-----|
   239|| `setRiskLevel(uint8)` | 仅 AI Agent | 更新链上风险评分 (0-10) |
   240|| `setAIAgent(address)` | 仅 AI Agent | 转移 AI Agent 角色 |
   241|| `beforeSwap()` | 内部 | 狙击检测 + 动态费率路由 |
   242|| `afterInitialize()` | 内部 | 记录池子创建区块 |
   243|| `riskScore()` | 公开 | 读取当前风险等级 |
   244|| `isInSniperWindow()` | 公开 | 检查是否在狙击窗口期 |
   245|
   246|---
   247|
   248|## 🚀 快速开始
   249|
   250|### 前置条件
   251|
   252|- [Foundry](https://book.getfoundry.sh/getting-started/installation)（`forge`, `cast`）
   253|- Node.js 18+（AI Agent 使用）
   254|- Python 3.10+（AI Agent 备选）
   255|
   256|### 1. 克隆 & 编译
   257|
   258|```bash
   259|git clone https://github.com/your-org/neuroguard-hook.git
   260|cd neuroguard-hook
   261|forge install
   262|forge build
   263|```
   264|
   265|### 2. 运行测试
   266|
   267|```bash
   268|forge test -vvvv
   269|```
   270|
   271|### 3. 一键部署
   272|
   273|```bash
   274|# 设置部署者私钥
   275|export DEPLOYER_PRIVATE_KEY="0x..."
   276|
   277|# 一键部署 PoolManager + Hook
   278|forge script script/Deploy.s.sol:Deploy \
   279|  --rpc-url https://testrpc.xlayer.tech \
   280|  --private-key $DEPLOYER_PRIVATE_KEY \
   281|  --broadcast -vvvv
   282|```
   283|
   284|> ⚠️ 部署脚本会自动挖掘 CREATE2 salt，确保 Hook 地址的尾部位匹配 Uniswap V4 所需的权限标志。
   285|
   286|---
   287|
   288|## 🤖 AI Agent 使用指南
   289|
   290|### Python 版本
   291|
   292|```bash
   293|cd script
   294|pip install -r requirements.txt
   295|cp .env.example .env
   296|# 编辑 .env：填入 PRIVATE_KEY 和 HOOK_ADDRESS
   297|
   298|# 单次运行
   299|python ai_agent.py
   300|
   301|# 每 60 秒轮询
   302|python ai_agent.py --loop 60
   303|
   304|# 干跑模式（只评分，不发交易）
   305|python ai_agent.py --dry-run
   306|
   307|# 手动指定风险分数
   308|python ai_agent.py --score 7
   309|```
   310|
   311|### Node.js 版本
   312|
   313|```bash
   314|cd ai-agent
   315|npm install
   316|cp .env.example .env
   317|# 编辑 .env：填入 AI_AGENT_PRIVATE_KEY 和 HOOK_CONTRACT_ADDRESS
   318|
   319|# 单次运行
   320|node index.js
   321|
   322|# 每 60 秒轮询
   323|node index.js --loop 60
   324|
   325|# 干跑模式
   326|node index.js --dry-run
   327|```
   328|
   329|### 数据源
   330|
   331|两个版本均使用 **CoinGecko 真实市场数据**（免费，无需 API Key）：
   332|
   333|- **主信号**：24h 价格变化 → 映射为风险评分 0-10
   334|- **辅助信号**：交易量 vs 7 天均量（恐慌抛售时放量会放大风险）
   335|
   336|监控不同代币，在 `.env` 中设置 `TOKEN_ID`：
   337|```
   338|# CoinGecko 代币 ID：ethereum, bitcoin, solana, dogecoin, pepe, shiba-inu
   339|TOKEN_ID=pepe
   340|```
   341|
   342|### 可选：接入 LLM 增强
   343|
   344|两个版本都包含已注释的 **OpenAI GPT-4o-mini** 集成代码，可用于更丰富的情绪分析：
   345|
   346|```python
   347|# 在 ai_agent.py 中，取消注释 simulate_llm_sentiment() 函数
   348|# 在 .env 中设置 OPENAI_API_KEY
   349|```
   350|
   351|---
   352|
   353|## 🧪 测试覆盖
   354|
   355|| 测试用例 | 描述 | 预期结果 |
   356||:---------|:-----|:---------|
   357|| `test_sniperDetection_highFee` | 机器人在第 1 个区块大额买入 | 施加 90% 费率 |
   358|| `test_normalUser_normalFee` | 普通用户在狙击窗口后买入 | 正常 0.3% 费率 |
   359|| `test_aiHighRisk_highSellFee` | AI 设置风险=8，用户卖出 | 收取 10% 卖出费率 |
   360|| `test_aiLowRisk_normalFee` | AI 设置风险=0，正常交易 | 正常 0.3% 费率 |
   361|| `test_unauthorizedCaller_reverts` | 非 AI Agent 调用 setRiskLevel | 交易回滚 |
   362|| `test_sniperVolumeAccumulation` | 同一地址多笔小额买入 | 累计量触发检测 |
   363|
   364|---
   365|
   366|## 🙏 致谢
   367|
   368|- [Uniswap V4](https://docs.uniswap.org/contracts/v4/overview) — 革命性的 Hook 架构
   369|- [OKX X Layer](https://web3.okx.com/xlayer) — 黑客松与链基础设施
   370|- [Foundry](https://book.getfoundry.sh/) — 最优秀的 Solidity 开发工具
   371|
   372|---
   373|
   374|<div align="center">
   375|
   376|**为 OKX Build-X 黑客松而建 🛡️**
   377|
   378|*NeuroGuard Hook — 让公平发射不再是神话。*
   379|
   380|</div>
   381|