// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {NeuroGuardHook} from "../src/NeuroGuardHook.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {PoolManager} from "@uniswap/v4-core/src/PoolManager.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";

/// @title NeuroGuard Hook — One-Click Deploy (CREATE2 with inline salt mining)
/// @notice Deploys PoolManager + NeuroGuardHook in a single broadcast.
///
///   forge script script/Deploy.s.sol:Deploy \
///     --rpc-url https://testrpc.xlayer.tech \
///     --private-key $DEPLOYER_PRIVATE_KEY \
///     --broadcast -vvvv
contract Deploy is Script {
    /// @notice The canonical Create2Deployer used by Foundry's `new C{salt}(...)`
    address constant CREATE2_DEPLOYER = 0x4e59b44847b379578588920cA78FbF26c0B4956C;

    /// @notice Mine a salt off-chain so the deployed hook address has the correct permission bits.
    function _findSalt(
        address deployer,
        uint160 flags,
        bytes memory creationCode
    ) internal pure returns (bytes32 salt) {
        for (uint256 i = 0; i < type(uint256).max; i++) {
            address candidate = address(
                uint160(
                    uint256(
                        keccak256(
                            abi.encodePacked(
                                bytes1(0xff),
                                deployer,
                                bytes32(i),
                                keccak256(creationCode)
                            )
                        )
                    )
                )
            );
            if (uint160(candidate) & Hooks.ALL_HOOK_MASK == flags) {
                return bytes32(i);
            }
        }
        revert("No valid salt found");
    }

    function run() external {
        vm.startBroadcast();

        address deployer = msg.sender;

        console.log("=== NeuroGuard One-Click Deployment ===");
        console.log("Deployer (also AI Agent):", deployer);

        // 1. Deploy PoolManager
        PoolManager poolManager = new PoolManager(deployer);
        console.log("[OK] PoolManager:", address(poolManager));

        // 2. Mine a valid CREATE2 salt
        //    afterInitialize = bit 12, beforeSwap = bit 7
        uint160 flags = uint160(Hooks.AFTER_INITIALIZE_FLAG | Hooks.BEFORE_SWAP_FLAG);
        console.log("Permission flags:", flags);

        bytes memory bytecode = abi.encodePacked(
            type(NeuroGuardHook).creationCode,
            abi.encode(IPoolManager(address(poolManager)), deployer)
        );

        // Use the Create2Deployer address (NOT msg.sender)
        bytes32 salt = _findSalt(CREATE2_DEPLOYER, flags, bytecode);
        console.log("Mined salt found");

        // 3. Deploy Hook via CREATE2
        NeuroGuardHook hook = new NeuroGuardHook{salt: salt}(
            IPoolManager(address(poolManager)),
            deployer
        );
        console.log("[OK] NeuroGuardHook:", address(hook));

        console.log("");
        console.log("=== Save These ===");
        console.log(string.concat("POOL_MANAGER=", vm.toString(address(poolManager))));
        console.log(string.concat("HOOK_ADDRESS=", vm.toString(address(hook))));
        console.log(string.concat("AI_AGENT    =", vm.toString(deployer)));

        vm.stopBroadcast();
    }
}
