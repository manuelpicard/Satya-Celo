// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ERC-5192: Minimal Soulbound NFTs
/// @notice https://eips.ethereum.org/EIPS/eip-5192
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);

    /// @notice Returns whether the token is permanently locked; reverts for unknown token IDs.
    function locked(uint256 tokenId) external view returns (bool);
}
