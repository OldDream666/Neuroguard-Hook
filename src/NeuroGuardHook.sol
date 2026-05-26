// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseTestHooks} from "@uniswap/v4-core/src/test/BaseTestHooks.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {SwapParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {BeforeSwapDelta, BeforeSwapDeltaLibrary} from "@uniswap/v4-core/src/types/BeforeSwapDelta.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";

/// @title NeuroGuardHook (智卫)
/// @notice AI-driven adaptive liquidity & anti-sniping Hook for Uniswap V4
/// @dev Two-layer defense: on-chain sniper trap + off-chain AI sentiment monitoring
contract NeuroGuardHook is BaseTestHooks {
    using LPFeeLibrary for uint24;

    // ──────────────────── Constants ────────────────────
    uint24 public constant DEFAULT_FEE = 3000;           // 0.3%
    uint24 public constant SNIPER_FEE = 900000;           // 90%
    uint24 public constant HIGH_RISK_SELL_FEE = 100000;   // 10%
    uint24 public constant LOW_RISK_BUY_FEE = 1000;       // 0.1%
    uint256 public constant SNIPER_WINDOW = 3;
    uint256 public constant LARGE_SWAP_THRESHOLD = 10000;

    // ──────────────────── State ────────────────────
    IPoolManager public immutable manager;
    address public aiAgent;
    uint256 public poolCreationBlock;
    uint8 public riskScore;
    mapping(address => uint256) public sniperVolume;

    // ──────────────────── Events ────────────────────
    event SniperDetected(address indexed trader, uint256 volume, uint24 penaltyFee);
    event RiskLevelUpdated(uint8 oldScore, uint8 newScore);
    event AIAgentUpdated(address oldAgent, address newAgent);
    event FeeApplied(address indexed trader, uint24 fee, string reason);

    // ──────────────────── Errors ────────────────────
    error Unauthorized();
    error InvalidRiskScore();

    // ──────────────────── Constructor ────────────────────
    constructor(IPoolManager _manager, address _aiAgent) {
        manager = _manager;
        aiAgent = _aiAgent;
        Hooks.validateHookPermissions(
            IHooks(address(this)),
            Hooks.Permissions({
                beforeInitialize: false,
                afterInitialize: true,
                beforeAddLiquidity: false,
                afterAddLiquidity: false,
                beforeRemoveLiquidity: false,
                afterRemoveLiquidity: false,
                beforeSwap: true,
                afterSwap: false,
                beforeDonate: false,
                afterDonate: false,
                beforeSwapReturnDelta: false,
                afterSwapReturnDelta: false,
                afterAddLiquidityReturnDelta: false,
                afterRemoveLiquidityReturnDelta: false
            })
        );
    }

    // ──────────────────── Access Control ────────────────────
    modifier onlyAIAgent() {
        if (msg.sender != aiAgent) revert Unauthorized();
        _;
    }

    function setAIAgent(address _newAgent) external onlyAIAgent {
        emit AIAgentUpdated(aiAgent, _newAgent);
        aiAgent = _newAgent;
    }

    /// @notice AI Agent updates risk score (0=safe, 10=extreme FUD)
    function setRiskLevel(uint8 _riskScore) external onlyAIAgent {
        if (_riskScore > 10) revert InvalidRiskScore();
        emit RiskLevelUpdated(riskScore, _riskScore);
        riskScore = _riskScore;
    }

    // ──────────────────── Hooks ────────────────────

    function afterInitialize(address, PoolKey calldata key, uint160, int24)
        external
        override
        returns (bytes4)
    {
        poolCreationBlock = block.number;
        manager.updateDynamicLPFee(key, DEFAULT_FEE);
        return IHooks.afterInitialize.selector;
    }

    /// @notice Core: adaptive fee via sniper trap + AI risk scoring
    /// @dev hookData contains abi-encoded trader address for identity tracking
    function beforeSwap(address, PoolKey calldata key, SwapParams calldata params, bytes calldata hookData)
        external
        override
        returns (bytes4, BeforeSwapDelta, uint24)
    {
        // Decode the actual trader address from hookData (first 32 bytes)
        address trader = hookData.length >= 32 ? abi.decode(hookData[:32], (address)) : msg.sender;

        // zeroForOne=true: selling token0 for token1 (BUY from token1 perspective)
        // zeroForOne=false: selling token1 for token0 (SELL from token1 perspective)
        bool isBuy = params.zeroForOne;
        uint256 swapAmount = params.amountSpecified < 0
            ? uint256(-params.amountSpecified)
            : uint256(params.amountSpecified);
        uint24 fee;

        // ═══════ Layer 1: Sniper Trap ═══════
        if (block.number <= poolCreationBlock + SNIPER_WINDOW) {
            uint256 cumVol = sniperVolume[trader] + swapAmount;

            if (isBuy && cumVol > LARGE_SWAP_THRESHOLD) {
                fee = SNIPER_FEE;
                emit SniperDetected(trader, cumVol, SNIPER_FEE);
                emit FeeApplied(trader, fee, "sniper_trap");
                manager.updateDynamicLPFee(key, fee);
                return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
            }

            if (isBuy) {
                fee = DEFAULT_FEE;
                emit FeeApplied(trader, fee, "sniper_window_normal");
                manager.updateDynamicLPFee(key, fee);
                return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
            }
        }

        // ═══════ Layer 2: AI-Driven Dynamic Fee ═══════
        if (riskScore == 0) {
            fee = DEFAULT_FEE;
        } else if (riskScore <= 3) {
            fee = isBuy ? DEFAULT_FEE : uint24(uint256(DEFAULT_FEE) * 2);
        } else if (riskScore <= 6) {
            fee = isBuy ? LOW_RISK_BUY_FEE : uint24(uint256(DEFAULT_FEE) * 10);
        } else {
            fee = isBuy ? LOW_RISK_BUY_FEE : HIGH_RISK_SELL_FEE;
        }

        emit FeeApplied(trader, fee, isBuy ? "buy" : "sell");
        manager.updateDynamicLPFee(key, fee);
        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    // ──────────────────── View ────────────────────
    function isInSniperWindow() external view returns (bool) {
        return block.number <= poolCreationBlock + SNIPER_WINDOW;
    }
}
