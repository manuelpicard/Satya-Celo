// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";
import {IERC5192} from "../interfaces/IERC5192.sol";
import {ISelfAgentRegistry} from "../interfaces/ISelfAgentRegistry.sol";

/// @title SatyaHumanSBT
/// @notice Non-transferable proof-of-personhood credential backed by a fresh Self proof.
/// @dev One token is allowed per Self human nullifier. Tokens can only be minted, burned
///      or explicitly recovered to a new wallet by the same nullifier after that wallet
///      becomes the owner of a fresh Self Agent ID. This contract has no admin or issuer.
///      It proves a current Self-backed human credential, not authorship of any content.
contract SatyaHumanSBT is ERC721, IERC5192 {
    using Strings for uint256;

    struct Credential {
        uint256 agentId;
        uint256 humanNullifier;
        uint64 issuedAt;
        uint64 validUntil;
    }

    ISelfAgentRegistry public immutable selfAgents;

    /// @notice Current credential token held by an account; zero means none.
    mapping(address account => uint256 tokenId) public tokenOf;
    mapping(uint256 tokenId => Credential credentialData) private _credentials;
    mapping(uint256 humanNullifier => uint256 tokenId) private _tokenByNullifier;

    uint256 private _nextTokenId = 1;

    event CredentialClaimed(address indexed holder, uint256 indexed tokenId, uint256 indexed agentId, uint64 validUntil);
    event CredentialRefreshed(address indexed holder, uint256 indexed tokenId, uint256 indexed agentId, uint64 validUntil);
    event CredentialRecovered(
        uint256 indexed oldTokenId,
        address indexed oldHolder,
        uint256 indexed newTokenId,
        address newHolder,
        uint256 agentId
    );
    event CredentialRenounced(address indexed holder, uint256 indexed tokenId);

    error InvalidConfig();
    error NotAgentOwner(address caller, uint256 agentId);
    error NoFreshHumanProof(uint256 agentId);
    error InvalidHumanNullifier(uint256 agentId);
    error InvalidProofExpiry(uint256 agentId);
    error WalletAlreadyHasCredential(uint256 tokenId);
    error RecoveryRequired(uint256 tokenId, address currentHolder);
    error NoCredentialToRecover(uint256 agentId);
    error RecoveryNotNeeded(uint256 tokenId);
    error NoCredential();
    error Soulbound();

    constructor(ISelfAgentRegistry selfAgentRegistry)
        ERC721("Satya Human Credential", "SATYAH")
    {
        if (address(selfAgentRegistry) == address(0)) revert InvalidConfig();
        selfAgents = selfAgentRegistry;
    }

    /// @notice Claim a credential or refresh the caller's existing one.
    /// @dev A different holder for the same human must use `recover` explicitly.
    function claim(uint256 agentId) external returns (uint256 tokenId) {
        (uint256 nullifier, uint64 validUntil) = _verifiedProofForCaller(agentId);
        tokenId = _tokenByNullifier[nullifier];

        if (tokenId != 0) {
            address currentHolder = _ownerOf(tokenId);
            if (currentHolder != msg.sender) revert RecoveryRequired(tokenId, currentHolder);
            Credential storage existing = _credentials[tokenId];
            existing.agentId = agentId;
            existing.issuedAt = uint64(block.timestamp);
            existing.validUntil = validUntil;
            emit CredentialRefreshed(msg.sender, tokenId, agentId, validUntil);
            return tokenId;
        }

        if (tokenOf[msg.sender] != 0) revert WalletAlreadyHasCredential(tokenOf[msg.sender]);
        return _issue(msg.sender, agentId, nullifier, validUntil);
    }

    /// @notice Recover the caller's credential after the same person re-verifies to a new wallet.
    /// @dev The old token is burned and replaced. Recovery is possible only while the caller
    ///      owns an Agent ID with a fresh proof that yields the identical Self nullifier.
    function recover(uint256 agentId) external returns (uint256 newTokenId) {
        (uint256 nullifier, uint64 validUntil) = _verifiedProofForCaller(agentId);
        uint256 oldTokenId = _tokenByNullifier[nullifier];
        if (oldTokenId == 0) revert NoCredentialToRecover(agentId);

        address oldHolder = _ownerOf(oldTokenId);
        if (oldHolder == msg.sender) revert RecoveryNotNeeded(oldTokenId);
        if (tokenOf[msg.sender] != 0) revert WalletAlreadyHasCredential(tokenOf[msg.sender]);

        delete tokenOf[oldHolder];
        delete _credentials[oldTokenId];
        _burn(oldTokenId);

        newTokenId = _issue(msg.sender, agentId, nullifier, validUntil);
        emit CredentialRecovered(oldTokenId, oldHolder, newTokenId, msg.sender, agentId);
    }

    /// @notice Burn the caller's current token; a later claim still requires a fresh Self proof.
    function renounce() external {
        uint256 tokenId = tokenOf[msg.sender];
        if (tokenId == 0) revert NoCredential();
        uint256 nullifier = _credentials[tokenId].humanNullifier;
        delete tokenOf[msg.sender];
        delete _tokenByNullifier[nullifier];
        delete _credentials[tokenId];
        _burn(tokenId);
        emit CredentialRenounced(msg.sender, tokenId);
    }

    /// @notice True only while the holder still controls the bound Self Agent ID and its proof is fresh.
    function isHuman(address account) public view returns (bool) {
        uint256 tokenId = tokenOf[account];
        if (tokenId == 0 || _ownerOf(tokenId) != account) return false;
        return _proofCurrentlyValid(_credentials[tokenId], account);
    }

    /// @notice Find the credential associated with an Agent ID's human, including a stale credential.
    /// @dev `holder` may differ from the current Agent ID owner; that case is recoverable by the
    ///      verified owner through `recover`. The nullifier itself is not returned by this API.
    function credentialOfAgent(uint256 agentId) external view returns (uint256 tokenId, address holder) {
        if (!selfAgents.hasHumanProof(agentId)) return (0, address(0));
        uint256 nullifier = selfAgents.getHumanNullifier(agentId);
        if (nullifier == 0) return (0, address(0));
        tokenId = _tokenByNullifier[nullifier];
        if (tokenId != 0) holder = _ownerOf(tokenId);
    }

    function credentialDetails(uint256 tokenId)
        external
        view
        returns (uint256 agentId, uint64 issuedAt, uint64 validUntil, bool currentlyValid)
    {
        _requireOwned(tokenId);
        Credential storage c = _credentials[tokenId];
        return (c.agentId, c.issuedAt, c.validUntil, _proofCurrentlyValid(c, _ownerOf(tokenId)));
    }

    /// @inheritdoc IERC5192
    function locked(uint256 tokenId) external view returns (bool) {
        _requireOwned(tokenId);
        return true;
    }

    /// @notice On-chain, data-URI metadata. Includes no passport data or nullifier.
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        Credential storage c = _credentials[tokenId];
        bool valid = _proofCurrentlyValid(c, _ownerOf(tokenId));
        string memory json = string.concat(
            '{"name":"Satya Human Credential #',
            tokenId.toString(),
            '","description":"Non-transferable credential backed by a fresh Self proof. It does not prove content authorship.",',
            '"attributes":[{"trait_type":"soulbound","value":true},{"trait_type":"current_human_proof","value":"',
            valid ? "valid" : "expired_or_relinked",
            '"},{"display_type":"date","trait_type":"valid_until","value":',
            uint256(c.validUntil).toString(),
            '}]}'
        );
        return string.concat("data:application/json;base64,", Base64.encode(bytes(json)));
    }

    function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
        return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
    }

    function approve(address, uint256) public pure override {
        revert Soulbound();
    }

    function setApprovalForAll(address, bool) public pure override {
        revert Soulbound();
    }

    /// @dev Only mint and burn are allowed; any transfer between nonzero addresses reverts.
    function _update(address to, uint256 tokenId, address auth) internal override returns (address from) {
        from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert Soulbound();
        return super._update(to, tokenId, auth);
    }

    function _verifiedProofForCaller(uint256 agentId) private view returns (uint256 nullifier, uint64 validUntil) {
        address agentOwner = selfAgents.ownerOf(agentId);
        if (agentOwner != msg.sender) revert NotAgentOwner(msg.sender, agentId);
        if (!selfAgents.hasHumanProof(agentId) || !selfAgents.isProofFresh(agentId)) revert NoFreshHumanProof(agentId);

        nullifier = selfAgents.getHumanNullifier(agentId);
        if (nullifier == 0) revert InvalidHumanNullifier(agentId);

        uint256 expiry = selfAgents.proofExpiresAt(agentId);
        if (expiry <= block.timestamp || expiry > type(uint64).max) revert InvalidProofExpiry(agentId);
        validUntil = uint64(expiry);
    }

    function _issue(address holder, uint256 agentId, uint256 nullifier, uint64 validUntil)
        private
        returns (uint256 tokenId)
    {
        tokenId = _nextTokenId++;
        tokenOf[holder] = tokenId;
        _tokenByNullifier[nullifier] = tokenId;
        _credentials[tokenId] = Credential({
            agentId: agentId,
            humanNullifier: nullifier,
            issuedAt: uint64(block.timestamp),
            validUntil: validUntil
        });
        _mint(holder, tokenId);
        emit Locked(tokenId);
        emit CredentialClaimed(holder, tokenId, agentId, validUntil);
    }

    function _proofCurrentlyValid(Credential storage c, address holder) private view returns (bool) {
        if (c.validUntil <= block.timestamp) return false;
        if (!selfAgents.hasHumanProof(c.agentId) || !selfAgents.isProofFresh(c.agentId)) return false;
        if (selfAgents.getHumanNullifier(c.agentId) != c.humanNullifier) return false;
        try selfAgents.ownerOf(c.agentId) returns (address currentAgentOwner) {
            return currentAgentOwner == holder;
        } catch {
            return false;
        }
    }
}
