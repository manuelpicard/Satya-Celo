// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ISelfAgentRegistry
/// @notice Read interface of Self Agent ID on Celo (identity registry with a
///         zero-knowledge proof-of-human extension on top of ERC-8004).
///
///         Mainnet 42220:      0xaC3DF9ABf80d0F5c020C06B04Cced27763355944
///         Celo Sepolia 11142220: 0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379
///
///         `agentPubKey` is the agent's address left-padded to 32 bytes:
///         bytes32(uint256(uint160(addr))) — the same encoding the official SDK uses.
interface ISelfAgentRegistry {
    /// @notice Agent id registered for this key, or 0 if unknown.
    function getAgentId(bytes32 agentPubKey) external view returns (uint256);

    /// @notice True if the key belongs to a registered agent.
    function isVerifiedAgent(bytes32 agentPubKey) external view returns (bool);

    /// @notice True if a zero-knowledge human proof backs this agent id.
    function hasHumanProof(uint256 agentId) external view returns (bool);

    /// @notice Unique, pseudonymous identifier of the human behind the agent
    ///         (the passport/ID nullifier). Stable across keys, never reveals identity.
    function getHumanNullifier(uint256 agentId) external view returns (uint256);

    /// @notice False once the human proof has aged past its validity window.
    function isProofFresh(uint256 agentId) external view returns (bool);

    function proofExpiresAt(uint256 agentId) external view returns (uint256);

    /// @notice True if both agent ids are backed by the same human.
    function sameHuman(uint256 agentIdA, uint256 agentIdB) external view returns (bool);

    function ownerOf(uint256 tokenId) external view returns (address);
}
