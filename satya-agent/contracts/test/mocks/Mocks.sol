// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ISelfAgentRegistry} from "../../src/interfaces/ISelfAgentRegistry.sol";
import {IIdentityRegistry8004} from "../../src/interfaces/IIdentityRegistry8004.sol";

/// @dev Stand-in for Self Agent ID with the same call surface Satya relies on.
contract MockSelfAgentRegistry is ISelfAgentRegistry {
    mapping(bytes32 => uint256) private _idByKey;
    mapping(uint256 => address) private _owner;
    mapping(uint256 => uint256) private _nullifier;
    mapping(uint256 => bool) private _hasProof;
    mapping(uint256 => bool) private _fresh;
    mapping(uint256 => uint256) private _expiry;

    /// @param agentKeyHolder the signing key registered for the agent
    /// @param nftOwner       who holds the soulbound NFT (the human in `linked` mode)
    function addAgent(uint256 agentId, address agentKeyHolder, address nftOwner, uint256 nullifier) external {
        _idByKey[bytes32(uint256(uint160(agentKeyHolder)))] = agentId;
        _owner[agentId] = nftOwner;
        _nullifier[agentId] = nullifier;
        _hasProof[agentId] = nullifier != 0;
        _fresh[agentId] = nullifier != 0;
        _expiry[agentId] = block.timestamp + 365 days;
    }

    function setFresh(uint256 agentId, bool v) external {
        _fresh[agentId] = v;
    }

    function setOwner(uint256 agentId, address newOwner) external {
        _owner[agentId] = newOwner;
    }

    function setHasProof(uint256 agentId, bool v) external {
        _hasProof[agentId] = v;
    }

    function getAgentId(bytes32 agentPubKey) external view returns (uint256) {
        return _idByKey[agentPubKey];
    }

    function isVerifiedAgent(bytes32 agentPubKey) external view returns (bool) {
        return _idByKey[agentPubKey] != 0;
    }

    function hasHumanProof(uint256 agentId) external view returns (bool) {
        return _hasProof[agentId];
    }

    function getHumanNullifier(uint256 agentId) external view returns (uint256) {
        return _nullifier[agentId];
    }

    function isProofFresh(uint256 agentId) external view returns (bool) {
        return _fresh[agentId];
    }

    function proofExpiresAt(uint256 agentId) external view returns (uint256) {
        return _expiry[agentId];
    }

    function sameHuman(uint256 a, uint256 b) external view returns (bool) {
        return _nullifier[a] != 0 && _nullifier[a] == _nullifier[b];
    }

    function verificationStrength() external pure returns (uint8) {
        return 3;
    }

    function ownerOf(uint256 tokenId) external view returns (address) {
        address o = _owner[tokenId];
        require(o != address(0), "ERC721: nonexistent token");
        return o;
    }
}

/// @dev Stand-in for the reference ERC-8004 identity registry.
contract MockIdentityRegistry8004 is IIdentityRegistry8004 {
    mapping(uint256 => address) private _wallet;
    mapping(uint256 => address) private _owner;

    function addAgent(uint256 agentId, address wallet, address owner_) external {
        _wallet[agentId] = wallet;
        _owner[agentId] = owner_;
    }

    function clearWallet(uint256 agentId) external {
        _wallet[agentId] = address(0);
    }

    function getAgentWallet(uint256 agentId) external view returns (address) {
        return _wallet[agentId];
    }

    function ownerOf(uint256 agentId) external view returns (address) {
        address o = _owner[agentId];
        require(o != address(0), "ERC721: nonexistent token");
        return o;
    }
}
