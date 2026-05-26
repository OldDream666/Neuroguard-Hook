// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";

/// @title HookMiner
/// @notice Mines a CREATE address that encodes the desired hook permission flags
library HookMiner {
    /// @notice Find a salt that, when combined with deployer + bytecode, produces a hook address
    ///         with the correct permission bits set
    /// @param deployer The address that will deploy the hook (CREATE)
    /// @param flags The desired hook permission flags
    /// @param bytecode The creation bytecode of the hook contract
    /// @return salt The uint256 salt to use with `new Hook{salt: bytes32(salt)}(...)`
    function find(address deployer, uint160 flags, bytes memory bytecode)
        internal
        view
        returns (uint256 salt)
    {
        // Iterate to find a valid salt
        for (salt = 0; salt < type(uint256).max; salt++) {
            address candidate = address(
                uint160(
                    uint256(
                        keccak256(
                            abi.encodePacked(
                                bytes1(0xff),
                                deployer,
                                bytes32(salt),
                                keccak256(bytecode)
                            )
                        )
                    )
                )
            );

            // Check that the lower 14 bits match the desired flags
            if (uint160(candidate) & Hooks.ALL_HOOK_MASK == flags) {
                return salt;
            }
        }
        revert("HookMiner: no valid salt found");
    }
}
