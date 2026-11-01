// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IIdentityRegistry8004
/// @notice Minimal read interface of the reference ERC-8004 Identity Registry.
///
///         Celo mainnet 42220:    0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
///         Celo Sepolia 11142220: 0x8004A818BFB912233c491871b3d84c89A494BD9e
///
///         The registry has no wallet -> agentId lookup, so callers pass their
///         `agentId` and the consumer checks `getAgentWallet(agentId) == caller`.
///         Transferring the agent NFT clears `agentWallet`, which makes a stale
///         claim fail automatically.
interface IIdentityRegistry8004 {
    /// @notice Wallet published for this agent (address(0) if unset or cleared by a transfer).
    function getAgentWallet(uint256 agentId) external view returns (address);

    /// @notice ERC-721 owner of the agent identity. Reverts for unknown ids.
    function ownerOf(uint256 agentId) external view returns (address);
}
