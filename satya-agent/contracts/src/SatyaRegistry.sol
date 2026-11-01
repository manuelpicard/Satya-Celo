// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

import {IHumanRegistry} from "./interfaces/IHumanRegistry.sol";

/// @dev HumanCredential exposes `bannedPerson(bytes32)` as a public mapping getter.
interface IHumanFraudRegistry {
    function bannedPerson(bytes32 personId) external view returns (bool);
}

/// @title SatyaRegistry - Layer 2 of the Satya stack
/// @notice Public, tamper-evident register of *who vouches for the origin of a piece of content*.
///
///  Satya never guesses. It only records statements by accountable parties:
///   - HUMANS holding a valid HMN credential (Layer 1) declare how a content was made
///     (NONE = without AI, ASSISTED = with AI assistance, GENERATED = AI-generated).
///   - Registered AI PROVIDERS register hashes of their own outputs.
///  Contradictions (a human declares NONE for content an AI provider registered) become
///  publicly visible and can be flagged as fraud; HMN governance can then ban the person.
///
///  contentHash = SHA-256 of the file bytes, or of the Satya-normalised UTF-8 text.
///  softHash    = optional 64-bit perceptual hash (images) / SimHash (text) for
///                similarity lookups by off-chain indexers (never treated as proof).
contract SatyaRegistry is Ownable2Step, EIP712 {
    enum Kind {
        HUMAN,
        AI_PROVIDER
    }

    enum AiUse {
        NONE,
        ASSISTED,
        GENERATED
    }

    struct Attestation {
        address attester;
        uint64 anchoredAt;
        Kind kind;
        AiUse aiUse;
        uint8 level; // HMN level at anchoring time (0 for providers)
        bool revoked;
        bool fraud;
        bytes32 personId; // HMN personId (0 for providers)
    }

    /// @notice Off-chain "Satya seal" a human signs (free, no gas). Anyone may anchor it.
    struct Seal {
        bytes32 contentHash;
        uint8 aiUse;
        uint64 createdAt;
        address signer;
    }

    struct Provider {
        bool active;
        string name;
    }

    struct Summary {
        uint32 humanNone;
        uint32 humanAssisted;
        uint32 humanGenerated;
        uint32 aiProvider;
        uint32 invalid; // revoked, fraud or banned person
        bool contradiction; // AI provider vs. human "NONE"
    }

    bytes32 public constant SEAL_TYPEHASH =
        keccak256("Seal(bytes32 contentHash,uint8 aiUse,uint64 createdAt,address signer)");

    IHumanRegistry public immutable hmn;

    mapping(address => Provider) private _providers;
    mapping(bytes32 contentHash => Attestation[]) private _attestations;
    mapping(bytes32 contentHash => mapping(bytes32 actor => bool)) public hasAttested;

    event ProviderSet(address indexed provider, bool active, string name);
    event HumanAttested(
        bytes32 indexed contentHash, bytes32 indexed personId, address indexed attester, AiUse aiUse, uint8 level, bytes8 softHash, uint256 index
    );
    event AiAttested(bytes32 indexed contentHash, address indexed provider, bytes8 softHash, uint256 index);
    event AttestationRevoked(bytes32 indexed contentHash, uint256 indexed index);
    event FraudFlagged(bytes32 indexed contentHash, uint256 indexed index, bytes32 personId);

    error NotHuman(address account);
    error NotProvider(address account);
    error AlreadyAttested();
    error InvalidSignature();
    error InvalidSeal();
    error InvalidContentHash();
    error UnknownAttestation();
    error NotAttester();
    error InvalidConfig();

    constructor(IHumanRegistry hmnRegistry, address governance)
        Ownable(governance)
        EIP712("Satya", "1")
    {
        if (address(hmnRegistry) == address(0)) revert InvalidConfig();
        hmn = hmnRegistry;
    }

    // ------------------------------------------------------------ governance

    function setProvider(address provider, bool active, string calldata name) external onlyOwner {
        if (provider == address(0)) revert InvalidConfig();
        _providers[provider] = Provider({active: active, name: name});
        emit ProviderSet(provider, active, name);
    }

    /// @notice Mark an attestation as fraudulent (e.g. proven false "NONE" declaration).
    ///         HMN governance can additionally revoke the person's credential with fraud=true.
    function flagFraud(bytes32 contentHash, uint256 index) external onlyOwner {
        Attestation storage a = _get(contentHash, index);
        a.fraud = true;
        emit FraudFlagged(contentHash, index, a.personId);
    }

    // ----------------------------------------------------------- attestations

    /// @notice A verified human declares how `contentHash` was made.
    function attest(bytes32 contentHash, AiUse aiUse, bytes8 softHash) external returns (uint256) {
        return _attestHuman(msg.sender, contentHash, aiUse, softHash);
    }

    /// @notice Anchor an off-chain seal signed by a verified human (supports EOAs and ERC-1271 accounts).
    ///         The signer must hold a valid HMN credential at anchoring time.
    function anchorSeal(Seal calldata s, bytes calldata signature, bytes8 softHash) external returns (uint256) {
        if (s.aiUse > uint8(AiUse.GENERATED) || s.createdAt > block.timestamp) revert InvalidSeal();
        if (!SignatureChecker.isValidSignatureNow(s.signer, hashSeal(s), signature)) revert InvalidSignature();
        return _attestHuman(s.signer, s.contentHash, AiUse(s.aiUse), softHash);
    }

    /// @notice A registered AI provider registers one of its own outputs.
    function attestAI(bytes32 contentHash, bytes8 softHash) external returns (uint256 index) {
        if (!_providers[msg.sender].active) revert NotProvider(msg.sender);
        if (contentHash == bytes32(0)) revert InvalidContentHash();
        bytes32 actor = bytes32(uint256(uint160(msg.sender)));
        if (hasAttested[contentHash][actor]) revert AlreadyAttested();
        hasAttested[contentHash][actor] = true;

        index = _attestations[contentHash].length;
        _attestations[contentHash].push(
            Attestation({
                attester: msg.sender,
                anchoredAt: uint64(block.timestamp),
                kind: Kind.AI_PROVIDER,
                aiUse: AiUse.GENERATED,
                level: 0,
                revoked: false,
                fraud: false,
                personId: bytes32(0)
            })
        );
        emit AiAttested(contentHash, msg.sender, softHash, index);
    }

    /// @notice The original attester may withdraw its statement (stays visible as revoked).
    function revoke(bytes32 contentHash, uint256 index) external {
        Attestation storage a = _get(contentHash, index);
        if (a.attester != msg.sender) revert NotAttester();
        a.revoked = true;
        emit AttestationRevoked(contentHash, index);
    }

    // ------------------------------------------------------------------ views

    function hashSeal(Seal calldata s) public view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(SEAL_TYPEHASH, s.contentHash, s.aiUse, s.createdAt, s.signer)));
    }

    /// @notice Check an off-chain seal without anchoring it.
    /// @return validSignature signature matches `s.signer` (EOA or ERC-1271)
    /// @return signerIsHuman  signer currently holds a valid HMN credential
    /// @return level          signer's current HMN level
    /// @return personId       signer's current HMN personId
    function verifySeal(Seal calldata s, bytes calldata signature)
        external
        view
        returns (bool validSignature, bool signerIsHuman, uint8 level, bytes32 personId)
    {
        validSignature = SignatureChecker.isValidSignatureNow(s.signer, hashSeal(s), signature);
        signerIsHuman = hmn.isHuman(s.signer);
        level = hmn.humanLevel(s.signer);
        personId = hmn.personIdOf(s.signer);
    }

    function provider(address account) external view returns (Provider memory) {
        return _providers[account];
    }

    function attestationCount(bytes32 contentHash) external view returns (uint256) {
        return _attestations[contentHash].length;
    }

    function attestation(bytes32 contentHash, uint256 index) external view returns (Attestation memory) {
        if (index >= _attestations[contentHash].length) revert UnknownAttestation();
        return _attestations[contentHash][index];
    }

    function attestations(bytes32 contentHash) external view returns (Attestation[] memory) {
        return _attestations[contentHash];
    }

    /// @notice Whether an attestation still counts (not revoked, not fraud, person not banned,
    ///         provider still active).
    function isValid(bytes32 contentHash, uint256 index) public view returns (bool) {
        Attestation storage a = _get(contentHash, index);
        return _isValid(a);
    }

    function summary(bytes32 contentHash) external view returns (Summary memory s) {
        Attestation[] storage list = _attestations[contentHash];
        for (uint256 i; i < list.length; i++) {
            Attestation storage a = list[i];
            if (!_isValid(a)) {
                s.invalid++;
            } else if (a.kind == Kind.AI_PROVIDER) {
                s.aiProvider++;
            } else if (a.aiUse == AiUse.NONE) {
                s.humanNone++;
            } else if (a.aiUse == AiUse.ASSISTED) {
                s.humanAssisted++;
            } else {
                s.humanGenerated++;
            }
        }
        s.contradiction = s.humanNone > 0 && (s.aiProvider > 0 || s.humanGenerated > 0);
    }

    // --------------------------------------------------------------- internal

    function _attestHuman(address who, bytes32 contentHash, AiUse aiUse, bytes8 softHash)
        private
        returns (uint256 index)
    {
        if (contentHash == bytes32(0)) revert InvalidContentHash();
        if (!hmn.isHuman(who)) revert NotHuman(who);
        bytes32 personId = hmn.personIdOf(who);
        // one statement per person and content - survives wallet recovery (personId is stable)
        if (hasAttested[contentHash][personId]) revert AlreadyAttested();
        hasAttested[contentHash][personId] = true;
        uint8 level = hmn.humanLevel(who);

        index = _attestations[contentHash].length;
        _attestations[contentHash].push(
            Attestation({
                attester: who,
                anchoredAt: uint64(block.timestamp),
                kind: Kind.HUMAN,
                aiUse: aiUse,
                level: level,
                revoked: false,
                fraud: false,
                personId: personId
            })
        );
        emit HumanAttested(contentHash, personId, who, aiUse, level, softHash, index);
    }

    function _isValid(Attestation storage a) private view returns (bool) {
        if (a.revoked || a.fraud) return false;
        if (a.kind == Kind.AI_PROVIDER) return _providers[a.attester].active;
        // a later proven fraud of the person invalidates all their statements
        try IHumanFraudRegistry(address(hmn)).bannedPerson(a.personId) returns (bool banned) {
            return !banned;
        } catch {
            return true;
        }
    }

    function _get(bytes32 contentHash, uint256 index) private view returns (Attestation storage) {
        if (index >= _attestations[contentHash].length) revert UnknownAttestation();
        return _attestations[contentHash][index];
    }
}
