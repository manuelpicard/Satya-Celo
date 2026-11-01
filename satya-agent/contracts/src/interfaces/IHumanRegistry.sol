// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IHumanRegistry
/// @notice Minimal read interface for a verified-human credential registry.
interface IHumanRegistry {
    function isHuman(address account) external view returns (bool);
    function humanLevel(address account) external view returns (uint8);
    function personIdOf(address account) external view returns (bytes32);
}
