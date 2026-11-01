// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import {ISelfAgentRegistry} from "./interfaces/ISelfAgentRegistry.sol";
import {IIdentityRegistry8004} from "./interfaces/IIdentityRegistry8004.sol";

/// @title SatyaCelo — provenance of record for the agent economy
/// @author Satya stack
///
/// @notice Satya never guesses whether content is AI-generated. Detection is
///         unreliable by construction, so this contract records something that can
///         actually be proven: **accountable statements about origin**, each one
///         bound to a unique human.
///
///         On Celo that binding comes from Self Agent ID, which links an agent's
///         signing key to a zero-knowledge passport proof. Satya reads the
///         resulting nullifier — a stable pseudonym that reveals nothing about the
///         person — and stores it next to every statement. That gives the register
///         two properties a plain attestation list cannot have:
///
///          1. **One person, one statement per content.** Spinning up more wallets or
///             more agents does not buy more voices; the nullifier is the identity.
///          2. **Self-contradiction is provable on-chain.** If the same human both
///             declares a content AI-generated (through an agent they registered) and
///             human-made (in person), anyone can call `proveSelfContradiction` and the
///             register marks both statements as disputed. No governance, no trusted
///             operator, no appeal to an off-chain authority.
///
///         The contract is deliberately **ownerless**: there is no admin, no pause, no
///         curated provider list, and no privileged key that can rewrite history.
///
/// @dev Identity sources, in descending order of what they prove:
///       - `SELF_HUMAN`  — caller owns a Self Agent ID NFT backed by a fresh human
///                         proof, i.e. a verified person speaking for themselves.
///       - `SELF_AGENT`  — caller is the registered signing key of such an agent. The
///                         human who registered it is recorded and accountable.
///       - `AGENT_8004`  — caller is the published wallet of a reference ERC-8004
///                         agent with no human proof. May only self-incriminate
///                         (`AI_GENERATED`); carries no nullifier and never
///                         establishes human authorship.
///
///      `contentHash` is the SHA-256 of the file bytes, or of the Satya-normalised
///      UTF-8 text. `softHash` is an optional 64-bit perceptual hash / SimHash used by
///      off-chain indexers for near-duplicate lookup — never treated as proof.
contract SatyaCelo is EIP712 {
    // --------------------------------------------------------------- types

    /// @notice What the declaring party says about how the content came to be.
    enum Origin {
        HUMAN_ONLY, // made without generative AI
        HUMAN_WITH_AI, // human work with AI assistance
        AI_GENERATED // produced by an AI system
    }

    /// @notice Which registry established the declaring party's identity.
    enum Via {
        SELF_HUMAN,
        SELF_AGENT,
        AGENT_8004
    }

    struct Attestation {
        address attester; // 20 bytes
        uint64 at; // 8
        Origin origin; // 1
        Via via_; // 1
        bool revoked; // 1  — withdrawn by its author
        bool disputed; // 1  — part of a proven self-contradiction
        uint256 agentId; // Self Agent ID / ERC-8004 agent id
        uint256 nullifier; // ZK proof-of-human nullifier (0 when none)
    }

    /// @notice Off-chain statement a person signs for free. Anyone may pay the gas to
    ///         anchor it, so a human never needs CELO, a wallet balance or even a chain
    ///         connection to go on record.
    struct Seal {
        bytes32 contentHash;
        uint8 origin;
        uint64 createdAt;
        address signer;
    }

    struct Summary {
        uint32 humanOnly;
        uint32 humanWithAi;
        uint32 aiGenerated;
        uint32 inactive; // revoked or disputed
        bool contradiction; // different parties disagree
        bool provenFraud; // one and the same human contradicted themselves
    }

    bytes32 public constant SEAL_TYPEHASH =
        keccak256("Seal(bytes32 contentHash,uint8 origin,uint64 createdAt,address signer)");

    // -------------------------------------------------------------- storage

    /// @notice Self Agent ID registry (identity + zero-knowledge proof-of-human).
    ISelfAgentRegistry public immutable selfAgents;

    /// @notice Reference ERC-8004 identity registry.
    IIdentityRegistry8004 public immutable agents8004;

    mapping(bytes32 contentHash => Attestation[]) private _list;

    /// @notice One statement per content and identity. The key is the nullifier when a
    ///         human proof exists, otherwise the declaring address. Extra wallets and
    ///         extra agents therefore do not multiply a person's voice.
    mapping(bytes32 contentHash => mapping(bytes32 identity => bool)) public hasDeclared;

    // --------------------------------------------------------------- events

    event Declared(
        bytes32 indexed contentHash,
        uint256 indexed nullifier,
        address indexed attester,
        Origin origin,
        Via via_,
        uint256 agentId,
        bytes8 softHash,
        uint256 index
    );
    event Revoked(bytes32 indexed contentHash, uint256 indexed index);
    event SelfContradictionProven(
        bytes32 indexed contentHash, uint256 indexed nullifier, uint256 indexA, uint256 indexB, address prover
    );

    // --------------------------------------------------------------- errors

    error InvalidConfig();
    error InvalidContentHash();
    error AlreadyDeclared();
    error NotAnAgentKey(address caller);
    error NoFreshHumanProof(uint256 agentId);
    error NotAgentOwner(address caller, uint256 agentId);
    error NotAgentWallet(address caller, uint256 agentId);
    error AgentsCannotClaimHumanAuthorship();
    error UnknownAttestation();
    error NotAttester();
    error InvalidSignature();
    error InvalidSeal();
    error NotContradictory();
    error SameStatement();

    // ---------------------------------------------------------- constructor

    /// @param selfAgentRegistry Self Agent ID. Celo mainnet
    ///        0xaC3DF9ABf80d0F5c020C06B04Cced27763355944, Celo Sepolia
    ///        0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379.
    /// @param identityRegistry8004 Reference ERC-8004 identity registry. Celo mainnet
    ///        0x8004A169FB4a3325136EB29fA0ceB6D2e539a432, Celo Sepolia
    ///        0x8004A818BFB912233c491871b3d84c89A494BD9e. May be address(0) to run
    ///        with Self Agent ID only.
    constructor(ISelfAgentRegistry selfAgentRegistry, IIdentityRegistry8004 identityRegistry8004)
        EIP712("Satya", "2")
    {
        if (address(selfAgentRegistry) == address(0)) revert InvalidConfig();
        selfAgents = selfAgentRegistry;
        agents8004 = identityRegistry8004;
    }

    // ---------------------------------------------------------- declaring

    /// @notice Declare origin as the human behind a Self Agent ID.
    /// @dev The caller must own the agent NFT (Self's `linked` registration mode puts
    ///      it in the human's own wallet) and the proof must still be fresh.
    function declareAsHuman(uint256 agentId, bytes32 contentHash, Origin origin, bytes8 softHash)
        external
        returns (uint256)
    {
        if (selfAgents.ownerOf(agentId) != msg.sender) revert NotAgentOwner(msg.sender, agentId);
        uint256 nullifier = _requireFreshHuman(agentId);
        return _record(msg.sender, contentHash, origin, Via.SELF_HUMAN, agentId, nullifier, softHash);
    }

    /// @notice Declare origin as a Self-registered agent. The human who registered the
    ///         agent is recorded through their nullifier and stays accountable.
    /// @dev An agent cannot assert human authorship — that is the one claim a machine
    ///      has no standing to make.
    function declareAsAgent(bytes32 contentHash, Origin origin, bytes8 softHash) external returns (uint256) {
        if (origin == Origin.HUMAN_ONLY) revert AgentsCannotClaimHumanAuthorship();
        uint256 agentId = selfAgents.getAgentId(_key(msg.sender));
        if (agentId == 0) revert NotAnAgentKey(msg.sender);
        uint256 nullifier = _requireFreshHuman(agentId);
        return _record(msg.sender, contentHash, origin, Via.SELF_AGENT, agentId, nullifier, softHash);
    }

    /// @notice Declare an output as AI-generated from a reference ERC-8004 agent wallet
    ///         that carries no human proof.
    /// @dev Permissionless and self-incriminating only: it can add AI provenance but can
    ///      never support a claim of human authorship, and it contributes no nullifier.
    function declareAsAgent8004(uint256 agentId, bytes32 contentHash, bytes8 softHash) external returns (uint256) {
        if (address(agents8004) == address(0)) revert InvalidConfig();
        if (agents8004.getAgentWallet(agentId) != msg.sender) revert NotAgentWallet(msg.sender, agentId);
        return _record(msg.sender, contentHash, Origin.AI_GENERATED, Via.AGENT_8004, agentId, 0, softHash);
    }

    /// @notice Anchor a seal a person signed off-chain. Works for EOAs and ERC-1271
    ///         smart accounts; the signer pays nothing and anyone may submit it.
    function anchorSeal(uint256 agentId, Seal calldata s, bytes calldata signature, bytes8 softHash)
        external
        returns (uint256)
    {
        if (s.origin > uint8(Origin.AI_GENERATED) || s.createdAt > block.timestamp) revert InvalidSeal();
        if (!SignatureChecker.isValidSignatureNow(s.signer, hashSeal(s), signature)) revert InvalidSignature();
        if (selfAgents.ownerOf(agentId) != s.signer) revert NotAgentOwner(s.signer, agentId);
        uint256 nullifier = _requireFreshHuman(agentId);
        return _record(s.signer, s.contentHash, Origin(s.origin), Via.SELF_HUMAN, agentId, nullifier, softHash);
    }

    /// @notice Withdraw your own statement. It stays visible, marked as revoked —
    ///         the register is append-only and never rewrites the past.
    function revoke(bytes32 contentHash, uint256 index) external {
        Attestation storage a = _at(contentHash, index);
        if (a.attester != msg.sender) revert NotAttester();
        a.revoked = true;
        emit Revoked(contentHash, index);
    }

    // ------------------------------------------------------ fraud, by anyone

    /// @notice Prove that one and the same human made contradictory statements about
    ///         the same content, and mark both as disputed.
    ///
    /// @dev This is the part Celo makes possible. Because Self binds every agent to a
    ///      passport nullifier, "the agent that generated this" and "the person who
    ///      swears no AI was involved" can be shown to be the same human — on-chain,
    ///      by anyone, with no privileged role and nothing to trust. A contradiction
    ///      between two *different* people is merely disagreement and is reported by
    ///      `summary().contradiction`; only self-contradiction is fraud.
    function proveSelfContradiction(bytes32 contentHash, uint256 indexA, uint256 indexB) external {
        if (indexA == indexB) revert SameStatement();
        Attestation storage a = _at(contentHash, indexA);
        Attestation storage b = _at(contentHash, indexB);

        // Both statements must be backed by a human proof, and by the same human.
        if (a.nullifier == 0 || a.nullifier != b.nullifier) revert NotContradictory();
        // "No AI was involved" against "this is AI output" — from one person.
        bool clash = (a.origin == Origin.HUMAN_ONLY && b.origin == Origin.AI_GENERATED)
            || (b.origin == Origin.HUMAN_ONLY && a.origin == Origin.AI_GENERATED);
        if (!clash) revert NotContradictory();

        a.disputed = true;
        b.disputed = true;
        emit SelfContradictionProven(contentHash, a.nullifier, indexA, indexB, msg.sender);
    }

    // ----------------------------------------------------------------- views

    function hashSeal(Seal calldata s) public view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(SEAL_TYPEHASH, s.contentHash, s.origin, s.createdAt, s.signer)));
    }

    /// @notice Check a seal without anchoring it.
    function verifySeal(uint256 agentId, Seal calldata s, bytes calldata signature)
        external
        view
        returns (bool validSignature, bool signerIsHuman, uint256 nullifier)
    {
        validSignature = SignatureChecker.isValidSignatureNow(s.signer, hashSeal(s), signature);
        signerIsHuman = _ownsAgent(s.signer, agentId) && selfAgents.hasHumanProof(agentId)
            && selfAgents.isProofFresh(agentId);
        nullifier = signerIsHuman ? selfAgents.getHumanNullifier(agentId) : 0;
    }

    /// @notice The human proof currently backing an address, if any.
    /// @return isHuman    a fresh zero-knowledge human proof covers this key
    /// @return agentId    the Self Agent ID
    /// @return nullifier  the unique pseudonym of the human (0 when unproven)
    function humanBehind(address account) external view returns (bool isHuman, uint256 agentId, uint256 nullifier) {
        agentId = selfAgents.getAgentId(_key(account));
        if (agentId == 0) return (false, 0, 0);
        if (!selfAgents.hasHumanProof(agentId) || !selfAgents.isProofFresh(agentId)) return (false, agentId, 0);
        return (true, agentId, selfAgents.getHumanNullifier(agentId));
    }

    function count(bytes32 contentHash) external view returns (uint256) {
        return _list[contentHash].length;
    }

    function attestation(bytes32 contentHash, uint256 index) external view returns (Attestation memory) {
        return _at(contentHash, index);
    }

    function attestations(bytes32 contentHash) external view returns (Attestation[] memory) {
        return _list[contentHash];
    }

    /// @notice A statement counts unless its author withdrew it or it was proven to be
    ///         part of a self-contradiction.
    function isActive(bytes32 contentHash, uint256 index) external view returns (bool) {
        Attestation storage a = _at(contentHash, index);
        return !a.revoked && !a.disputed;
    }

    /// @notice Aggregate view used by clients to reach a verdict.
    function summary(bytes32 contentHash) external view returns (Summary memory s) {
        Attestation[] storage list = _list[contentHash];
        for (uint256 i; i < list.length; ++i) {
            Attestation storage a = list[i];
            if (a.revoked || a.disputed) {
                s.inactive++;
                if (a.disputed) s.provenFraud = true;
                continue;
            }
            if (a.origin == Origin.HUMAN_ONLY) s.humanOnly++;
            else if (a.origin == Origin.HUMAN_WITH_AI) s.humanWithAi++;
            else s.aiGenerated++;
        }
        s.contradiction = s.humanOnly > 0 && (s.aiGenerated > 0 || s.humanWithAi > 0);
    }

    // -------------------------------------------------------------- internal

    /// @dev Self encodes an agent key as the address left-padded to 32 bytes.
    function _key(address account) private pure returns (bytes32) {
        return bytes32(uint256(uint160(account)));
    }

    function _ownsAgent(address account, uint256 agentId) private view returns (bool) {
        try selfAgents.ownerOf(agentId) returns (address owner) {
            return owner == account;
        } catch {
            return false;
        }
    }

    function _requireFreshHuman(uint256 agentId) private view returns (uint256 nullifier) {
        if (!selfAgents.hasHumanProof(agentId) || !selfAgents.isProofFresh(agentId)) {
            revert NoFreshHumanProof(agentId);
        }
        nullifier = selfAgents.getHumanNullifier(agentId);
        if (nullifier == 0) revert NoFreshHumanProof(agentId);
    }

    function _record(
        address attester,
        bytes32 contentHash,
        Origin origin,
        Via via_,
        uint256 agentId,
        uint256 nullifier,
        bytes8 softHash
    ) private returns (uint256 index) {
        if (contentHash == bytes32(0)) revert InvalidContentHash();

        // The nullifier is the identity whenever one exists, so a person cannot speak
        // twice about the same content by switching wallet or registering more agents.
        bytes32 identity = nullifier != 0 ? bytes32(nullifier) : _key(attester);
        if (hasDeclared[contentHash][identity]) revert AlreadyDeclared();
        hasDeclared[contentHash][identity] = true;

        index = _list[contentHash].length;
        _list[contentHash].push(
            Attestation({
                attester: attester,
                at: uint64(block.timestamp),
                origin: origin,
                via_: via_,
                revoked: false,
                disputed: false,
                agentId: agentId,
                nullifier: nullifier
            })
        );
        emit Declared(contentHash, nullifier, attester, origin, via_, agentId, softHash, index);
    }

    function _at(bytes32 contentHash, uint256 index) private view returns (Attestation storage) {
        if (index >= _list[contentHash].length) revert UnknownAttestation();
        return _list[contentHash][index];
    }
}
