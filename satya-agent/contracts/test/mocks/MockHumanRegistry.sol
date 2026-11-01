// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IHumanRegistry} from "../../src/interfaces/IHumanRegistry.sol";

/// @dev Test-only substitute for the separate HMN issuer system.
///      It models credential activation, recovery and fraud bans; it is not production code.
contract MockHumanRegistry is IHumanRegistry {
    mapping(address account => bool) private _human;
    mapping(address account => uint8) private _level;
    mapping(address account => bytes32) private _personId;
    mapping(address account => uint64) private _validUntil;
    mapping(bytes32 personId => bool) public bannedPerson;
    mapping(address account => uint256 tokenId) public tokenOf;
    mapping(uint256 tokenId => address account) private _holderOf;
    mapping(bytes32 personId => address account) private _currentAccountOf;
    uint256 private _nextTokenId = 1;

    function setHuman(address account, bytes32 personId, uint8 level) external {
        require(account != address(0) && personId != bytes32(0) && level != 0, "invalid human");
        address previous = _currentAccountOf[personId];
        if (previous != address(0) && previous != account) _human[previous] = false;
        if (tokenOf[account] == 0) {
            uint256 tokenId = _nextTokenId++;
            tokenOf[account] = tokenId;
            _holderOf[tokenId] = account;
        }
        _human[account] = true;
        _level[account] = level;
        _personId[account] = personId;
        _validUntil[account] = uint64(block.timestamp + 180 days);
        _currentAccountOf[personId] = account;
        bannedPerson[personId] = false;
    }

    function revoke(uint256 tokenId, bool banPerson) external {
        address account = _holderOf[tokenId];
        require(account != address(0), "unknown token");
        _human[account] = false;
        bytes32 personId = _personId[account];
        if (banPerson) bannedPerson[personId] = true;
    }

    function isHuman(address account) external view returns (bool) {
        return _isActive(account);
    }

    function humanLevel(address account) external view returns (uint8) {
        return _isActive(account) ? _level[account] : 0;
    }

    function personIdOf(address account) external view returns (bytes32) {
        return _isActive(account) ? _personId[account] : bytes32(0);
    }

    function _isActive(address account) private view returns (bool) {
        return _human[account] && _validUntil[account] > block.timestamp && !bannedPerson[_personId[account]];
    }
}
