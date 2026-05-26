// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Deployers} from "@uniswap/v4-core/test/utils/Deployers.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {StateLibrary} from "@uniswap/v4-core/src/libraries/StateLibrary.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {PoolId} from "@uniswap/v4-core/src/types/PoolId.sol";
import {SwapParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {PoolSwapTest} from "@uniswap/v4-core/src/test/PoolSwapTest.sol";
import {Currency} from "@uniswap/v4-core/src/types/Currency.sol";
import {MockERC20} from "solmate/src/test/utils/mocks/MockERC20.sol";
import {NeuroGuardHook} from "../src/NeuroGuardHook.sol";

contract NeuroGuardHookTest is Test, Deployers {
    using LPFeeLibrary for uint24;
    using Hooks for IHooks;
    using StateLibrary for IPoolManager;

    NeuroGuardHook hook;
    address aiAgent;
    address user;
    address sniper;

    event SniperDetected(address indexed trader, uint256 volume, uint24 penaltyFee);
    event RiskLevelUpdated(uint8 oldScore, uint8 newScore);
    event FeeApplied(address indexed trader, uint24 fee, string reason);

    function setUp() public {
        deployFreshManagerAndRouters();
        deployMintAndApprove2Currencies();

        aiAgent = makeAddr("aiAgent");
        user = makeAddr("user");
        sniper = makeAddr("sniper");

        // Deploy hook via CREATE2 with correct permission bits
        uint160 targetFlags = Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_INITIALIZE_FLAG;
        bytes memory bytecode = abi.encodePacked(
            type(NeuroGuardHook).creationCode,
            abi.encode(IPoolManager(manager), aiAgent)
        );

        for (uint256 i = 0; i < 100000; i++) {
            address candidate = address(
                uint160(uint256(keccak256(abi.encodePacked(bytes1(0xff), address(this), bytes32(i), keccak256(bytecode)))))
            );
            if (uint160(candidate) & Hooks.ALL_HOOK_MASK == targetFlags) {
                hook = NeuroGuardHook(address(new NeuroGuardHook{salt: bytes32(i)}(IPoolManager(manager), aiAgent)));
                break;
            }
        }
        require(address(hook) != address(0), "Failed to mine hook address");

        // Initialize pool with DYNAMIC_FEE_FLAG
        (key,) = initPoolAndAddLiquidity(
            currency0, currency1, IHooks(address(hook)), LPFeeLibrary.DYNAMIC_FEE_FLAG, SQRT_PRICE_1_1
        );

        _setupUser(user);
        _setupUser(sniper);
    }

    function _setupUser(address _user) internal {
        MockERC20(Currency.unwrap(currency0)).mint(_user, 1e30);
        MockERC20(Currency.unwrap(currency1)).mint(_user, 1e30);
        vm.startPrank(_user);
        MockERC20(Currency.unwrap(currency0)).approve(address(swapRouter), type(uint256).max);
        MockERC20(Currency.unwrap(currency1)).approve(address(swapRouter), type(uint256).max);
        vm.stopPrank();
    }

    // ═══════════════════════════════════════════════
    //  Sniper Trap Tests
    // ═══════════════════════════════════════════════

    function test_sniperTrap_largeBuyInBlock1() public {
        assertTrue(hook.isInSniperWindow());

        vm.expectEmit(true, true, true, true, address(hook));
        emit SniperDetected(sniper, 20000, hook.SNIPER_FEE());

        _doBuy(sniper, 20000);

        assertEq(_fetchPoolLPFee(key), hook.SNIPER_FEE(), "Sniper -> 90%");
    }

    function test_sniperTrap_smallBuyInWindow() public {
        _doBuy(user, 100);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "Small buy -> 0.3%");
    }

    function test_sniperTrap_sellInWindow() public {
        _doBuy(user, 100);
        _doSell(user, 100);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "Sell -> default");
    }

    function test_sniperTrap_afterWindow() public {
        vm.roll(block.number + hook.SNIPER_WINDOW() + 1);
        _doBuy(sniper, 50000);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "After window -> default");
    }

    // ═══════════════════════════════════════════════
    //  AI Dynamic Fee Tests
    // ═══════════════════════════════════════════════

    function test_aiFee_normalConditions() public {
        _enterNormalPeriod();
        _doBuy(user, 1000);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "Normal -> 0.3%");
    }

    function test_aiFee_lowRisk_sell() public {
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(2);

        _doSell(user, 1000);
        assertEq(_fetchPoolLPFee(key), 6000, "Low risk sell -> 0.6%");
    }

    function test_aiFee_lowRisk_buy() public {
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(2);

        _doBuy(user, 1000);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "Low risk buy -> 0.3%");
    }

    function test_aiFee_mediumRisk_sell() public {
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(5);

        _doSell(user, 1000);
        assertEq(_fetchPoolLPFee(key), 30000, "Medium risk sell -> 3%");
    }

    function test_aiFee_mediumRisk_buy() public {
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(5);

        _doBuy(user, 1000);
        assertEq(_fetchPoolLPFee(key), 1000, "Medium risk buy -> 0.1%");
    }

    function test_aiFee_highRisk_sell() public {
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(9);

        vm.expectEmit(true, true, true, true, address(hook));
        emit FeeApplied(user, 100000, "sell");

        _doSell(user, 1000);
        assertEq(_fetchPoolLPFee(key), 100000, "High risk sell -> 10%");
    }

    function test_aiFee_highRisk_buy() public {
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(9);

        _doBuy(user, 1000);
        assertEq(_fetchPoolLPFee(key), 1000, "High risk buy -> 0.1%");
    }

    // ═══════════════════════════════════════════════
    //  Access Control Tests
    // ═══════════════════════════════════════════════

    function test_accessControl_onlyAIAgent() public {
        vm.prank(user);
        vm.expectRevert(NeuroGuardHook.Unauthorized.selector);
        hook.setRiskLevel(5);
    }

    function test_accessControl_invalidScore() public {
        vm.prank(aiAgent);
        vm.expectRevert(NeuroGuardHook.InvalidRiskScore.selector);
        hook.setRiskLevel(11);
    }

    function test_accessControl_maxScore() public {
        vm.prank(aiAgent);
        hook.setRiskLevel(10);
        assertEq(hook.riskScore(), 10);
    }

    function test_accessControl_updateAIAgent() public {
        address newAgent = makeAddr("newAgent");
        vm.prank(aiAgent);
        hook.setAIAgent(newAgent);
        assertEq(hook.aiAgent(), newAgent);
    }

    // ═══════════════════════════════════════════════
    //  Full Lifecycle Integration
    // ═══════════════════════════════════════════════

    function test_fullLifecycle() public {
        // Phase 1: Sniper blocked at launch
        _doBuy(sniper, 50000);
        assertEq(_fetchPoolLPFee(key), hook.SNIPER_FEE(), "P1: Sniper 90%");

        // Phase 2: Normal user gets default fee
        _doBuy(user, 500);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "P2: User 0.3%");

        // Phase 3: AI detects FUD
        _enterNormalPeriod();
        vm.prank(aiAgent);
        hook.setRiskLevel(8);

        // Phase 4: Panic sell -> 10% fee
        _doSell(user, 1000);
        assertEq(_fetchPoolLPFee(key), hook.HIGH_RISK_SELL_FEE(), "P4: Panic sell 10%");

        // Phase 5: AI clears risk -> normal
        vm.prank(aiAgent);
        hook.setRiskLevel(0);
        _doSell(user, 1000);
        assertEq(_fetchPoolLPFee(key), hook.DEFAULT_FEE(), "P5: Back to 0.3%");
    }

    // ──────────────────── Helpers ────────────────────

    function _enterNormalPeriod() internal {
        vm.roll(block.number + hook.SNIPER_WINDOW() + 1);
    }

    /// @dev Encode trader address into hookData for identity tracking
    function _hookData(address _trader) internal pure returns (bytes memory) {
        return abi.encode(_trader);
    }

    function _doBuy(address _user, uint256 amount) internal {
        SwapParams memory params = SwapParams({
            zeroForOne: true,
            amountSpecified: -int256(amount),
            sqrtPriceLimitX96: SQRT_PRICE_1_2
        });
        PoolSwapTest.TestSettings memory ts =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});
        vm.prank(_user);
        swapRouter.swap(key, params, ts, _hookData(_user));
    }

    function _doSell(address _user, uint256 amount) internal {
        SwapParams memory params = SwapParams({
            zeroForOne: false,
            amountSpecified: -int256(amount),
            sqrtPriceLimitX96: SQRT_PRICE_2_1
        });
        PoolSwapTest.TestSettings memory ts =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});
        vm.prank(_user);
        swapRouter.swap(key, params, ts, _hookData(_user));
    }

    function _fetchPoolLPFee(PoolKey memory _key) internal view returns (uint256 lpFee) {
        PoolId id = _key.toId();
        (,,, lpFee) = manager.getSlot0(id);
    }
}
