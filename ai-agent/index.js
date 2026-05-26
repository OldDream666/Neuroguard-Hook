#!/usr/bin/env node
/**
 * NeuroGuard Hook — Off-Chain AI Sentiment Agent (Node.js / Ethers.js)
 * =====================================================================
 * Fetches real market data from CoinGecko (free, no API key),
 * computes a risk score 0-10, and calls setRiskLevel() on the
 * deployed NeuroGuardHook contract via X Layer testnet.
 *
 * Usage:
 *   cp .env.example .env   # fill in your keys
 *   npm install
 *   node index.js              # run once
 *   node index.js --loop 60    # loop every 60 seconds
 *   node index.js --dry-run    # score only, no tx
 *   node index.js --score 7    # manual override
 */

import "dotenv/config";
import { ethers } from "ethers";

// ──────────────────────────────────────────────
//  Environment
// ──────────────────────────────────────────────
const RPC_URL    = process.env.X_LAYER_RPC              || "https://testrpc.xlayer.tech";
const CHAIN_ID   = parseInt(process.env.X_LAYER_CHAIN_ID || "195");
const HOOK_ADDR  = process.env.HOOK_CONTRACT_ADDRESS;
const PRIV_KEY   = process.env.AI_AGENT_PRIVATE_KEY;
const TOKEN_ID   = process.env.TOKEN_ID                 || "ethereum";

// ──────────────────────────────────────────────
//  Minimal ABI
// ──────────────────────────────────────────────
const HOOK_ABI = [
  "function setRiskLevel(uint8 _riskScore) external",
  "function riskScore() view returns (uint8)",
  "function aiAgent() view returns (address)",
  "event RiskLevelUpdated(uint8 oldScore, uint8 newScore)",
];

// ──────────────────────────────────────────────
//  Logging helpers
// ──────────────────────────────────────────────
const ts = () => new Date().toISOString().replace("T", " ").slice(0, 19);
const log  = (...a) => console.log(`${ts()} [INFO] `, ...a);
const warn = (...a) => console.warn(`${ts()} [WARN] `, ...a);
const err  = (...a) => console.error(`${ts()} [ERROR]`, ...a);

// ═══════════════════════════════════════════════
//  Real Market Data — CoinGecko (Free, No API Key)
// ═══════════════════════════════════════════════

const SENTIMENT_LABELS = [
  { range: [0, 3],  label: "🟢 CALM — Normal trading conditions" },
  { range: [3, 5],  label: "🟡 CAUTIOUS — Mild concern detected" },
  { range: [5, 8],  label: "🟠 FEAR — Significant negative sentiment" },
  { range: [8, 11], label: "🔴 PANIC — Extreme FUD, activating sell-side defense" },
];

/**
 * Fetch real market data from CoinGecko free API.
 */
async function fetchMarketData(tokenId) {
  const params = new URLSearchParams({
    ids: tokenId,
    vs_currencies: "usd",
    include_24hr_change: "true",
    include_24hr_vol: "true",
    include_market_cap: "true",
  });

  const resp = await fetch(
    `https://api.coingecko.com/api/v3/simple/price?${params}`,
    { signal: AbortSignal.timeout(10000) }
  );

  if (!resp.ok) throw new Error(`CoinGecko API error: ${resp.status}`);
  const data = await resp.json();

  if (!data[tokenId]) {
    warn(`Token '${tokenId}' not found in CoinGecko response`);
    return null;
  }

  const d = data[tokenId];
  return {
    price_usd: d.usd || 0,
    change_24h: d.usd_24h_change || 0,
    volume_24h: d.usd_24h_vol || 0,
    market_cap: d.usd_market_cap || 0,
  };
}

/**
 * Fetch 7-day average volume for comparison.
 */
async function fetchHistoricalVolume(tokenId) {
  try {
    const resp = await fetch(
      `https://api.coingecko.com/api/v3/coins/${tokenId}/market_chart?vs_currency=usd&days=7&interval=daily`,
      { signal: AbortSignal.timeout(10000) }
    );
    if (!resp.ok) return 0;
    const data = await resp.json();
    const volumes = (data.total_volumes || []).map((v) => v[1]);
    if (volumes.length === 0) return 0;
    return volumes.reduce((a, b) => a + b, 0) / volumes.length;
  } catch {
    return 0;
  }
}

/**
 * Compute risk score 0-10 from real market signals.
 */
function computeRiskScore(market, avgVolume) {
  const change = market.change_24h;

  // Signal 1: Price change → risk
  let priceRisk;
  if (change >= 0) {
    priceRisk = 0;
  } else if (change >= -2) {
    priceRisk = (Math.abs(change) / 2) * 2;
  } else if (change >= -5) {
    priceRisk = 2 + ((Math.abs(change) - 2) / 3) * 2;
  } else if (change >= -10) {
    priceRisk = 4 + ((Math.abs(change) - 5) / 5) * 3;
  } else {
    priceRisk = Math.min(10, 7 + ((Math.abs(change) - 10) / 10) * 3);
  }

  // Signal 2: Volume spike multiplier
  let volumeMultiplier = 1.0;
  if (avgVolume > 0 && market.volume_24h > 0) {
    const ratio = market.volume_24h / avgVolume;
    if (ratio > 3.0) volumeMultiplier = 1.5;
    else if (ratio > 2.0) volumeMultiplier = 1.3;
    else if (ratio > 1.5) volumeMultiplier = 1.1;
    else if (ratio < 0.5) volumeMultiplier = 0.8;
  }

  return Math.min(10, Math.max(0, Math.round(priceRisk * volumeMultiplier)));
}

/**
 * Full pipeline: fetch real data → compute risk → return score.
 */
async function analyzeMarket() {
  log(`📡 Fetching market data for '${TOKEN_ID}' from CoinGecko...`);

  const market = await fetchMarketData(TOKEN_ID);
  if (!market) {
    warn("Could not fetch market data, defaulting to risk=0");
    return 0;
  }

  const avgVol = await fetchHistoricalVolume(TOKEN_ID);

  log(`💰 Price: $${market.price_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })}`);
  log(`📊 24h Change: ${market.change_24h >= 0 ? "+" : ""}${market.change_24h.toFixed(2)}%`);
  log(`📈 24h Volume: $${Math.round(market.volume_24h).toLocaleString()}`);
  if (avgVol > 0) {
    const volRatio = market.volume_24h / avgVol;
    log(`📉 7d Avg Volume: $${Math.round(avgVol).toLocaleString()} (current/avg = ${volRatio.toFixed(2)}x)`);
  }

  const riskScore = computeRiskScore(market, avgVol);
  const label = SENTIMENT_LABELS.find(
    ({ range }) => riskScore >= range[0] && riskScore < range[1]
  )?.label || "UNKNOWN";

  log(`🧠 AI Risk Score: ${riskScore}/10  →  ${label}`);
  return riskScore;
}

// ═══════════════════════════════════════════════
//  On-Chain Interaction
// ═══════════════════════════════════════════════

async function initProvider() {
  const provider = new ethers.JsonRpcProvider(RPC_URL, CHAIN_ID);
  const network = await provider.getNetwork();
  log(`✅ Connected to X Layer (chain ${network.chainId}) via ${RPC_URL}`);
  return provider;
}

function getHookContract(provider) {
  if (!HOOK_ADDR) {
    err("❌ HOOK_CONTRACT_ADDRESS not set in .env");
    process.exit(1);
  }
  return new ethers.Contract(HOOK_ADDR, HOOK_ABI, provider);
}

async function verifyAgent(contract, wallet) {
  const onChainAgent = await contract.aiAgent();
  if (onChainAgent.toLowerCase() !== wallet.address.toLowerCase()) {
    err(
      `❌ Wallet mismatch!\n` +
      `   Your address:     ${wallet.address}\n` +
      `   Contract aiAgent: ${onChainAgent}\n` +
      `   Only the aiAgent can call setRiskLevel.`
    );
    process.exit(1);
  }
  log(`🔐 Agent verification passed: ${wallet.address}`);
}

async function getCurrentRisk(contract) {
  const score = await contract.riskScore();
  log(`📊 Current on-chain risk score: ${score}`);
  return Number(score);
}

async function sendRiskUpdate(contract, wallet, newScore) {
  const current = await getCurrentRisk(contract);

  if (current === newScore) {
    log(`⏭️  Risk score unchanged (${newScore}), skipping tx.`);
    return null;
  }

  const contractWithSigner = contract.connect(wallet);
  const tx = await contractWithSigner.setRiskLevel(newScore);
  log(`📤 TX sent: ${tx.hash}`);

  const receipt = await tx.wait();
  if (receipt.status === 1) {
    log(`✅ TX confirmed in block ${receipt.blockNumber} — risk score: ${current} → ${newScore}`);
  } else {
    err("❌ TX reverted! Check on explorer.");
  }

  return tx.hash;
}

// ═══════════════════════════════════════════════
//  Main
// ═══════════════════════════════════════════════

async function runOnce(contract, wallet) {
  log("─".repeat(50));
  const score = await analyzeMarket();
  return await sendRiskUpdate(contract, wallet, score);
}

async function main() {
  const args = process.argv.slice(2);
  const loopIdx   = args.indexOf("--loop");
  const loopSec   = loopIdx !== -1 ? parseInt(args[loopIdx + 1]) || 0 : 0;
  const dryRun    = args.includes("--dry-run");
  const scoreIdx  = args.indexOf("--score");
  const manScore  = scoreIdx !== -1 ? parseInt(args[scoreIdx + 1]) : null;

  if (!PRIV_KEY) {
    err("❌ AI_AGENT_PRIVATE_KEY not set. Copy .env.example → .env and fill in.");
    process.exit(1);
  }

  const provider = await initProvider();
  const wallet   = new ethers.Wallet(PRIV_KEY, provider);
  const contract = getHookContract(provider);

  log("🤖 NeuroGuard AI Agent starting (Node.js / Ethers.js)");
  log(`   Wallet:     ${wallet.address}`);
  log(`   Hook:       ${HOOK_ADDR}`);
  log(`   Monitoring: ${TOKEN_ID}`);

  await verifyAgent(contract, wallet);

  // Manual override
  if (manScore !== null) {
    if (manScore < 0 || manScore > 10) {
      err("Score must be 0-10");
      process.exit(1);
    }
    log(`🎯 Manual mode: setting risk score to ${manScore}`);
    await sendRiskUpdate(contract, wallet, manScore);
    return;
  }

  // Dry run
  if (dryRun) {
    log("🧪 DRY RUN mode — no transactions will be sent");
    await analyzeMarket();
    return;
  }

  // Loop or once
  if (loopSec > 0) {
    log(`🔄 Loop mode: checking every ${loopSec}s (Ctrl+C to stop)`);
    const intervalMs = loopSec * 1000;

    const tick = async () => {
      try {
        await runOnce(contract, wallet);
      } catch (e) {
        err("Loop iteration failed:", e.message);
      }
    };

    await tick();
    setInterval(tick, intervalMs);

    process.on("SIGINT", () => {
      log("\n👋 Agent stopped by user.");
      process.exit(0);
    });
  } else {
    await runOnce(contract, wallet);
  }
}

main().catch((e) => {
  err("Fatal:", e.message);
  process.exit(1);
});
