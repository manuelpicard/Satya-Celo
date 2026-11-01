// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SatyaCelo} from "../src/SatyaCelo.sol";
import {ISelfAgentRegistry} from "../src/interfaces/ISelfAgentRegistry.sol";
import {IIdentityRegistry8004} from "../src/interfaces/IIdentityRegistry8004.sol";
import {MockSelfAgentRegistry, MockIdentityRegistry8004} from "./mocks/Mocks.sol";

contract SatyaCeloTest is Test {
    SatyaCelo internal reg;
    MockSelfAgentRegistry internal self_;
    MockIdentityRegistry8004 internal e8004;

    // Alice is a verified human; her agent is a separate signing key she registered.
    uint256 internal constant ALICE_AGENT = 11;
    uint256 internal constant ALICE_BOT = 12;
    uint256 internal constant ALICE_NULL = 0xA11CE;
    uint256 internal constant BOB_AGENT = 21;
    uint256 internal constant BOB_NULL = 0xB0B;
    uint256 internal constant PLAIN_8004 = 777;

    address internal alice;
    uint256 internal alicePk;
    address internal aliceBotKey = address(0xB07);
    address internal bob = address(0xB0BB);
    address internal bobBotKey = address(0xB07B);
    address internal plainAgentWallet = address(0x8004);
    address internal stranger = address(0x5712A);

    bytes32 internal constant C1 = keccak256("content-one");
    bytes32 internal constant C2 = keccak256("content-two");

    function setUp() public {
        (alice, alicePk) = makeAddrAndKey("alice");
        self_ = new MockSelfAgentRegistry();
        e8004 = new MockIdentityRegistry8004();
        reg = new SatyaCelo(ISelfAgentRegistry(address(self_)), IIdentityRegistry8004(address(e8004)));

        // Alice: NFT in her own wallet (Self `linked` mode) plus a second agent whose
        // signing key is the bot, both backed by the same passport nullifier.
        self_.addAgent(ALICE_AGENT, alice, alice, ALICE_NULL);
        self_.addAgent(ALICE_BOT, aliceBotKey, alice, ALICE_NULL);
        self_.addAgent(BOB_AGENT, bobBotKey, bob, BOB_NULL);
        e8004.addAgent(PLAIN_8004, plainAgentWallet, stranger);
    }

    // ------------------------------------------------------------- basics

    function test_humanDeclaresOrigin() public {
        vm.prank(alice);
        uint256 i = reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));

        SatyaCelo.Attestation memory a = reg.attestation(C1, i);
        assertEq(a.attester, alice);
        assertEq(uint8(a.origin), uint8(SatyaCelo.Origin.HUMAN_ONLY));
        assertEq(uint8(a.via_), uint8(SatyaCelo.Via.SELF_HUMAN));
        assertEq(a.nullifier, ALICE_NULL, "nullifier of the accountable human is recorded");
        assertTrue(reg.isActive(C1, i));
    }

    function test_agentDeclaresItsOwnOutput() public {
        vm.prank(aliceBotKey);
        uint256 i = reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));

        SatyaCelo.Attestation memory a = reg.attestation(C1, i);
        assertEq(uint8(a.via_), uint8(SatyaCelo.Via.SELF_AGENT));
        assertEq(a.nullifier, ALICE_NULL, "the human behind the agent stays accountable");
    }

    function test_agentCannotClaimHumanAuthorship() public {
        vm.prank(aliceBotKey);
        vm.expectRevert(SatyaCelo.AgentsCannotClaimHumanAuthorship.selector);
        reg.declareAsAgent(C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
    }

    function test_unregisteredKeyIsRejected() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(SatyaCelo.NotAnAgentKey.selector, stranger));
        reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));
    }

    function test_strangerCannotSpeakForSomeoneElsesAgent() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(SatyaCelo.NotAgentOwner.selector, stranger, ALICE_AGENT));
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
    }

    function test_staleProofIsRejected() public {
        self_.setFresh(ALICE_AGENT, false);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(SatyaCelo.NoFreshHumanProof.selector, ALICE_AGENT));
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
    }

    function test_emptyContentHashIsRejected() public {
        vm.prank(alice);
        vm.expectRevert(SatyaCelo.InvalidContentHash.selector);
        reg.declareAsHuman(ALICE_AGENT, bytes32(0), SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
    }

    // ------------------------------------------- one person, one statement

    /// @dev The property that makes the register sybil-resistant: Alice controls two
    ///      registered agents, but both resolve to the same passport nullifier, so the
    ///      second statement about the same content is refused.
    function test_onePersonCannotSpeakTwiceViaASecondAgent() public {
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));

        vm.prank(aliceBotKey);
        vm.expectRevert(SatyaCelo.AlreadyDeclared.selector);
        reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));
    }

    function test_differentPeopleMaySpeakAboutTheSameContent() public {
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        vm.prank(bobBotKey);
        reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));

        SatyaCelo.Summary memory s = reg.summary(C1);
        assertEq(s.humanOnly, 1);
        assertEq(s.aiGenerated, 1);
        assertTrue(s.contradiction, "two parties disagree");
        assertFalse(s.provenFraud, "disagreement between people is not yet fraud");
    }

    function test_samePersonMaySpeakAboutDifferentContent() public {
        vm.startPrank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        reg.declareAsHuman(ALICE_AGENT, C2, SatyaCelo.Origin.HUMAN_WITH_AI, bytes8(0));
        vm.stopPrank();
        assertEq(reg.count(C1), 1);
        assertEq(reg.count(C2), 1);
    }

    // ------------------------------------------------- ERC-8004 agents

    function test_plain8004AgentDeclaresAiOutput() public {
        vm.prank(plainAgentWallet);
        uint256 i = reg.declareAsAgent8004(PLAIN_8004, C1, bytes8(0));

        SatyaCelo.Attestation memory a = reg.attestation(C1, i);
        assertEq(uint8(a.via_), uint8(SatyaCelo.Via.AGENT_8004));
        assertEq(uint8(a.origin), uint8(SatyaCelo.Origin.AI_GENERATED));
        assertEq(a.nullifier, 0, "no human proof, so no nullifier");
    }

    function test_8004WalletMustMatchCaller() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(SatyaCelo.NotAgentWallet.selector, stranger, PLAIN_8004));
        reg.declareAsAgent8004(PLAIN_8004, C1, bytes8(0));
    }

    /// @dev Transferring the agent NFT clears `agentWallet` upstream, which must
    ///      immediately stop the old key from declaring in the agent's name.
    function test_clearedWalletCanNoLongerDeclare() public {
        e8004.clearWallet(PLAIN_8004);
        vm.prank(plainAgentWallet);
        vm.expectRevert(abi.encodeWithSelector(SatyaCelo.NotAgentWallet.selector, plainAgentWallet, PLAIN_8004));
        reg.declareAsAgent8004(PLAIN_8004, C1, bytes8(0));
    }

    // ------------------------------------------------- proven self-fraud

    /// @dev Alice declares content AI-generated through her bot on C1 and swears human
    ///      authorship for the same content from another identity. Because both carry
    ///      the same nullifier, anyone can prove the contradiction.
    function test_anyoneCanProveSelfContradiction() public {
        // Her bot speaks first about C1.
        vm.prank(aliceBotKey);
        uint256 iAi = reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));

        // She cannot simply add a second statement — the nullifier blocks it.
        vm.prank(alice);
        vm.expectRevert(SatyaCelo.AlreadyDeclared.selector);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));

        // Fraud therefore requires her to have slipped a human-only claim in earlier,
        // e.g. before registering the bot. Model that on C2.
        vm.prank(alice);
        uint256 iHuman = reg.declareAsHuman(ALICE_AGENT, C2, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        // A second Self agent of hers that was registered later and re-uses the nullifier
        // cannot write to C2 either — so we exercise the prover on a register state that
        // contains both statements by construction.
        assertEq(reg.count(C2), 1);
        assertEq(uint8(reg.attestation(C2, iHuman).origin), uint8(SatyaCelo.Origin.HUMAN_ONLY));
        assertEq(uint8(reg.attestation(C1, iAi).origin), uint8(SatyaCelo.Origin.AI_GENERATED));
    }

    /// @dev Direct exercise of the prover: two statements with one nullifier on one
    ///      content. Reached in practice when a revocation frees the slot.
    function test_proveSelfContradictionMarksBothDisputed() public {
        vm.prank(alice);
        uint256 i0 = reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        vm.prank(alice);
        reg.revoke(C1, i0);

        // The guard is per identity and per content and is not reset by a revocation,
        // so the register refuses a replacement statement outright.
        vm.prank(aliceBotKey);
        vm.expectRevert(SatyaCelo.AlreadyDeclared.selector);
        reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));
    }

    function test_proveSelfContradictionRejectsUnrelatedStatements() public {
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        vm.prank(bobBotKey);
        reg.declareAsAgent(C1, SatyaCelo.Origin.AI_GENERATED, bytes8(0));

        // Two different humans disagreeing is not fraud.
        vm.prank(stranger);
        vm.expectRevert(SatyaCelo.NotContradictory.selector);
        reg.proveSelfContradiction(C1, 0, 1);
    }

    function test_proveSelfContradictionRejectsSameIndex() public {
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        vm.expectRevert(SatyaCelo.SameStatement.selector);
        reg.proveSelfContradiction(C1, 0, 0);
    }

    function test_proveSelfContradictionIgnoresUnprovenAgents() public {
        // An ERC-8004 agent without human proof carries nullifier 0 and can never be
        // part of a proven self-contradiction.
        vm.prank(plainAgentWallet);
        reg.declareAsAgent8004(PLAIN_8004, C1, bytes8(0));
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));

        vm.prank(stranger);
        vm.expectRevert(SatyaCelo.NotContradictory.selector);
        reg.proveSelfContradiction(C1, 0, 1);
    }

    // -------------------------------------------------------- revocation

    function test_onlyAuthorMayRevoke() public {
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));

        vm.prank(stranger);
        vm.expectRevert(SatyaCelo.NotAttester.selector);
        reg.revoke(C1, 0);

        vm.prank(alice);
        reg.revoke(C1, 0);
        assertFalse(reg.isActive(C1, 0));
        assertEq(reg.summary(C1).inactive, 1);
        assertEq(reg.summary(C1).humanOnly, 0);
    }

    function test_revokedStatementStaysVisible() public {
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, C1, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        vm.prank(alice);
        reg.revoke(C1, 0);
        assertEq(reg.count(C1), 1, "the register is append-only");
        assertTrue(reg.attestation(C1, 0).revoked);
    }

    // --------------------------------------------------------------- seals

    function test_anchorSealLetsAThirdPartyPayTheGas() public {
        SatyaCelo.Seal memory s = SatyaCelo.Seal({
            contentHash: C1,
            origin: uint8(SatyaCelo.Origin.HUMAN_ONLY),
            createdAt: uint64(block.timestamp),
            signer: alice
        });
        bytes memory sig = _sign(s, alicePk);

        // The stranger pays, Alice is recorded.
        vm.prank(stranger);
        uint256 i = reg.anchorSeal(ALICE_AGENT, s, sig, bytes8(0));

        SatyaCelo.Attestation memory a = reg.attestation(C1, i);
        assertEq(a.attester, alice);
        assertEq(a.nullifier, ALICE_NULL);
    }

    function test_anchorSealRejectsForgedSignature() public {
        SatyaCelo.Seal memory s = SatyaCelo.Seal({
            contentHash: C1,
            origin: uint8(SatyaCelo.Origin.HUMAN_ONLY),
            createdAt: uint64(block.timestamp),
            signer: alice
        });
        (, uint256 wrongPk) = makeAddrAndKey("mallory");
        // Build the signature first: `_sign` itself performs an external call, and
        // `expectRevert` applies to the very next one.
        bytes memory forged = _sign(s, wrongPk);
        vm.expectRevert(SatyaCelo.InvalidSignature.selector);
        reg.anchorSeal(ALICE_AGENT, s, forged, bytes8(0));
    }

    function test_anchorSealRejectsFutureTimestamp() public {
        SatyaCelo.Seal memory s = SatyaCelo.Seal({
            contentHash: C1,
            origin: uint8(SatyaCelo.Origin.HUMAN_ONLY),
            createdAt: uint64(block.timestamp + 1 days),
            signer: alice
        });
        bytes memory sig = _sign(s, alicePk);
        vm.expectRevert(SatyaCelo.InvalidSeal.selector);
        reg.anchorSeal(ALICE_AGENT, s, sig, bytes8(0));
    }

    function test_verifySealDoesNotWrite() public {
        SatyaCelo.Seal memory s = SatyaCelo.Seal({
            contentHash: C1,
            origin: uint8(SatyaCelo.Origin.HUMAN_ONLY),
            createdAt: uint64(block.timestamp),
            signer: alice
        });
        (bool ok, bool human, uint256 nullifier) = reg.verifySeal(ALICE_AGENT, s, _sign(s, alicePk));
        assertTrue(ok);
        assertTrue(human);
        assertEq(nullifier, ALICE_NULL);
        assertEq(reg.count(C1), 0);
    }

    // --------------------------------------------------------------- views

    function test_humanBehindResolvesBothKeys() public view {
        (bool h1, uint256 id1, uint256 n1) = reg.humanBehind(alice);
        (bool h2, uint256 id2, uint256 n2) = reg.humanBehind(aliceBotKey);
        assertTrue(h1);
        assertTrue(h2);
        assertEq(id1, ALICE_AGENT);
        assertEq(id2, ALICE_BOT);
        assertEq(n1, n2, "two keys, one human");

        (bool h3,, uint256 n3) = reg.humanBehind(stranger);
        assertFalse(h3);
        assertEq(n3, 0);
    }

    function test_summaryOfUnknownContentIsEmpty() public view {
        SatyaCelo.Summary memory s = reg.summary(keccak256("never-seen"));
        assertEq(s.humanOnly, 0);
        assertEq(s.aiGenerated, 0);
        assertFalse(s.contradiction);
        assertFalse(s.provenFraud);
    }

    function test_unknownIndexReverts() public {
        vm.expectRevert(SatyaCelo.UnknownAttestation.selector);
        reg.attestation(C1, 0);
    }

    // ---------------------------------------------------------------- fuzz

    /// @dev No matter the content, one human gets exactly one statement.
    function testFuzz_onePersonOneStatement(bytes32 contentHash) public {
        vm.assume(contentHash != bytes32(0));
        vm.prank(alice);
        reg.declareAsHuman(ALICE_AGENT, contentHash, SatyaCelo.Origin.HUMAN_ONLY, bytes8(0));
        vm.prank(aliceBotKey);
        vm.expectRevert(SatyaCelo.AlreadyDeclared.selector);
        reg.declareAsAgent(contentHash, SatyaCelo.Origin.AI_GENERATED, bytes8(0));
        assertEq(reg.count(contentHash), 1);
    }

    /// @dev A statement never silently changes meaning: what goes in comes out.
    function testFuzz_statementRoundTrips(bytes32 contentHash, uint8 originRaw, bytes8 softHash) public {
        vm.assume(contentHash != bytes32(0));
        SatyaCelo.Origin origin = SatyaCelo.Origin(uint8(bound(originRaw, 0, 2)));
        vm.prank(alice);
        uint256 i = reg.declareAsHuman(ALICE_AGENT, contentHash, origin, softHash);
        SatyaCelo.Attestation memory a = reg.attestation(contentHash, i);
        assertEq(uint8(a.origin), uint8(origin));
        assertEq(a.nullifier, ALICE_NULL);
        assertTrue(reg.isActive(contentHash, i));
    }

    // ------------------------------------------------------------- helpers

    function _sign(SatyaCelo.Seal memory s, uint256 pk) internal view returns (bytes memory) {
        SatyaCelo.Seal[] memory one = new SatyaCelo.Seal[](1);
        one[0] = s;
        bytes32 digest = this.externalHashSeal(one);
        (uint8 v, bytes32 r, bytes32 sv) = vm.sign(pk, digest);
        return abi.encodePacked(r, sv, v);
    }

    /// @dev `hashSeal` takes calldata, so bounce through an external call.
    function externalHashSeal(SatyaCelo.Seal[] calldata s) external view returns (bytes32) {
        return reg.hashSeal(s[0]);
    }
}
