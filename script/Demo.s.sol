// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {SwapParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {ModifyLiquidityParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {Currency} from "@uniswap/v4-core/src/types/Currency.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";

/// @title Simple ERC20 for demo
contract DemoToken {
    string public name;
    string public symbol;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(string memory _name, string memory _symbol) {
        name = _name;
        symbol = _symbol;
    }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount);
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount);
        require(allowance[from][msg.sender] >= amount);
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

/// @title NeuroGuard Full Demo
/// @notice Deploys tokens, creates pool with hook, adds liquidity, does swaps.
///
///   forge script script/Demo.s.sol:FullDemo \
///     --rpc-url https://testrpc.xlayer.tech \
///     --private-key $DEPLOYER_PRIVATE_KEY \
///     --broadcast -vvvv
contract FullDemo is Script {
    // sqrtPriceX96 for 1:1 price ratio
    uint160 constant SQRT_PRICE_1_1 = 79228162514264337593543950336;
    // sqrtPriceX96 for price limit (0.5)
    uint160 constant SQRT_PRICE_1_2 = 56022770974786139918731938227;

    function run() external {
        vm.startBroadcast();
        address deployer = msg.sender;

        console.log("=== NeuroGuard Full Demo ===");

        // ── Step 1: Deploy test tokens ──
        console.log("--- Step 1: Deploy Tokens ---");
        DemoToken tokenA = new DemoToken("NeuroGuard Token", "NGT");
        DemoToken tokenB = new DemoToken("Wrapped OKB", "WOKB");
        console.log("NGT:", address(tokenA));
        console.log("WOKB:", address(tokenB));

        tokenA.mint(deployer, 1_000_000e18);
        tokenB.mint(deployer, 1_000_000e18);

        address t0 = address(tokenA) < address(tokenB) ? address(tokenA) : address(tokenB);
        address t1 = address(tokenA) < address(tokenB) ? address(tokenB) : address(tokenA);

        // ── Step 2: Create pool with hook ──
        console.log("--- Step 2: Create Pool ---");
        address pmAddr = vm.envAddress("POOL_MANAGER");
        address hookAddr = vm.envAddress("HOOK_ADDRESS");
        IPoolManager pm = IPoolManager(pmAddr);

        PoolKey memory key = PoolKey({
            currency0: Currency.wrap(t0),
            currency1: Currency.wrap(t1),
            fee: LPFeeLibrary.DYNAMIC_FEE_FLAG,
            tickSpacing: 60,
            hooks: IHooks(hookAddr)
        });

        int24 tick = pm.initialize(key, SQRT_PRICE_1_1);
        console.log("Pool initialized, tick:", tick);

        // ── Step 3: Add liquidity ──
        console.log("--- Step 3: Add Liquidity ---");
        DemoToken(t0).approve(pmAddr, type(uint256).max);
        DemoToken(t1).approve(pmAddr, type(uint256).max);
        DemoToken(t0).transfer(pmAddr, 100_000e18);
        DemoToken(t1).transfer(pmAddr, 100_000e18);

        pm.modifyLiquidity(key, ModifyLiquidityParams({
            tickLower: -887220,
            tickUpper: 887220,
            liquidityDelta: int256(50_000e18),
            salt: bytes32(0)
        }), "");
        console.log("Liquidity added");

        // ── Step 4: Normal swap ──
        console.log("--- Step 4: Normal Swap ---");
        pm.swap(key, SwapParams({
            zeroForOne: true,
            amountSpecified: -int256(1000e18),
            sqrtPriceLimitX96: SQRT_PRICE_1_2
        }), abi.encode(deployer));
        console.log("Normal swap done (1000 tokens)");

        // ── Step 5: Sniper swap ──
        console.log("--- Step 5: Sniper Swap (large buy) ---");
        address sniper = vm.addr(0xdead);
        pm.swap(key, SwapParams({
            zeroForOne: true,
            amountSpecified: -int256(50_000e18),
            sqrtPriceLimitX96: SQRT_PRICE_1_2
        }), abi.encode(sniper));
        console.log("Sniper swap done (50k tokens, 90% penalty!)");

        console.log("=== Demo Complete ===");
        vm.stopBroadcast();
    }
}
