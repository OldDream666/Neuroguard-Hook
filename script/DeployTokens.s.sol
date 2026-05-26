// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {Currency} from "@uniswap/v4-core/src/types/Currency.sol";
import {TickMath} from "@uniswap/v4-core/src/libraries/TickMath.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";

/// @title Deploy two test ERC20 tokens for NeuroGuard demo
/// @notice Usage:
///   forge script script/DeployTokens.s.sol:DeployTokens \
///     --rpc-url https://testrpc.xlayer.tech \
///     --private-key $DEPLOYER_PRIVATE_KEY \
///     --broadcast -vvvv
contract DeployTokens is Script {
    function run() external {
        vm.startBroadcast();

        // Deploy two simple ERC20 tokens using Solmate's MockERC20
        // We'll use raw creation since we don't need a complex token
        address deployer = msg.sender;

        console.log("=== Deploying Test Tokens ===");
        console.log("Deployer:", deployer);

        // Token A: "NeuroGuard Token" (NGT)
        address tokenA = deployNewToken("NeuroGuard Token", "NGT", 18);
        console.log("[OK] Token A (NGT):", tokenA);

        // Token B: "Wrapped XLayer OKB" (WOKB)
        address tokenB = deployNewToken("Wrapped OKB", "WOKB", 18);
        console.log("[OK] Token B (WOKB):", tokenB);

        // Sort tokens (Uniswap requires token0 < token1)
        address token0 = tokenA < tokenB ? tokenA : tokenB;
        address token1 = tokenA < tokenB ? tokenB : tokenA;

        console.log("");
        console.log("=== Token Addresses (sorted) ===");
        console.log(string.concat("TOKEN_0=", vm.toString(token0)));
        console.log(string.concat("TOKEN_1=", vm.toString(token1)));

        vm.stopBroadcast();
    }

    function deployNewToken(string memory name, string memory symbol, uint8 decimals)
        internal
        returns (address)
    {
        // Minimal ERC20 deployment via raw bytecode
        // Using a simple mintable ERC20
        bytes memory bytecode = abi.encodePacked(
            type(SimpleToken).creationCode,
            abi.encode(name, symbol, decimals)
        );
        address addr;
        assembly {
            addr := create2(0, add(bytecode, 0x20), mload(bytecode), 0)
        }
        // Mint 1 billion tokens to deployer
        SimpleToken(addr).mint(msg.sender, 1_000_000_000 * 10 ** decimals);
        return addr;
    }
}

/// @title Simple mintable ERC20 for testing
contract SimpleToken {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
    }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "insufficient balance");
        require(allowance[from][msg.sender] >= amount, "insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}
