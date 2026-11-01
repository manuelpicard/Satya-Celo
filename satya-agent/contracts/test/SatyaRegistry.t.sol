// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IHumanRegistry} from "../src/interfaces/IHumanRegistry.sol";
import {SatyaRegistry} from "../src/SatyaRegistry.sol";
import {MockHumanRegistry} from "./mocks/MockHumanRegistry.sol";

contract SatyaRegistryTest is Test {
    MockHumanRegistry internal hmn;
    SatyaRegistry internal reg;

    address internal governance = makeAddr("governance");
    uint256 internal aliceKey = 0xA1;
    address internal alice;
    uint256 internal malloryKey = 0xBAD;
    address internal mallory;
    uint256 internal agentKey = 0xA6E7; // AI agent without HMN credential
    address internal agent;
    address internal aiProvider = makeAddr("aiProvider");

    bytes32 internal constant TEXT_HUMAN = keccak256("kafka: als gregor samsa eines morgens ...");
    bytes32 internal constant TEXT_AI = keccak256("llm output");
    bytes8 internal constant SOFT = bytes8(0x0123456789abcdef);

    function setUp() public {
        vm.warp(1_790_000_000);
        alice = vm.addr(aliceKey);
        mallory = vm.addr(malloryKey);
        agent = vm.addr(agentKey);

        hmn = new MockHumanRegistry();
        reg = new SatyaRegistry(IHumanRegistry(address(hmn)), governance);

        vm.startPrank(governance);
        reg.setProvider(aiProvider, true, "Demo-KI-Anbieter");
        vm.stopPrank();

        _verifyHuman(alice, keccak256("alice"));
        _verifyHuman(mallory, keccak256("mallory"));
    }

    function _verifyHuman(address who, bytes32 personId) internal {
        hmn.setHuman(who, personId, 2);
    }

    function _seal(uint256 key, bytes32 contentHash, uint8 aiUse)
        internal
        view
        returns (SatyaRegistry.Seal memory s, bytes memory sig)
    {
        s = SatyaRegistry.Seal({
            contentHash: contentHash, aiUse: aiUse, createdAt: uint64(block.timestamp), signer: vm.addr(key)
        });
        (uint8 v, bytes32 r, bytes32 ss) = vm.sign(key, reg.hashSeal(s));
        sig = abi.encodePacked(r, ss, v);
    }

    // ------------------------------------------------------------- humans

    function test_HumanAttestsWithoutAI() public {
        vm.prank(alice);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
        SatyaRegistry.Summary memory s = reg.summary(TEXT_HUMAN);
        assertEq(s.humanNone, 1);
        assertFalse(s.contradiction);
        SatyaRegistry.Attestation memory a = reg.attestation(TEXT_HUMAN, 0);
        assertEq(a.attester, alice);
        assertEq(a.personId, keccak256("alice"));
        assertEq(a.level, 2);
    }

    function test_RevertWhen_AiAgentAttests() public {
        vm.prank(agent);
        vm.expectRevert(abi.encodeWithSelector(SatyaRegistry.NotHuman.selector, agent));
        reg.attest(TEXT_AI, SatyaRegistry.AiUse.NONE, SOFT);
    }

    function test_RevertWhen_SamePersonAttestsTwice() public {
        vm.startPrank(alice);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
        vm.expectRevert(SatyaRegistry.AlreadyAttested.selector);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.ASSISTED, SOFT);
        vm.stopPrank();
    }

    // -------------------------------------------------------------- seals

    function test_AnchorOffchainSeal() public {
        (SatyaRegistry.Seal memory s, bytes memory sig) = _seal(aliceKey, TEXT_HUMAN, 0);
        (bool validSig, bool human, uint8 level, bytes32 pid) = reg.verifySeal(s, sig);
        assertTrue(validSig);
        assertTrue(human);
        assertEq(level, 2);
        assertEq(pid, keccak256("alice"));

        vm.prank(agent); // anyone (e.g. a relayer) may pay gas for anchoring
        reg.anchorSeal(s, sig, SOFT);
        assertEq(reg.summary(TEXT_HUMAN).humanNone, 1);
        assertEq(reg.attestation(TEXT_HUMAN, 0).attester, alice);
    }

    function test_SealOfAiAgentIsNotHuman() public {
        (SatyaRegistry.Seal memory s, bytes memory sig) = _seal(agentKey, TEXT_AI, 0);
        (bool validSig, bool human,,) = reg.verifySeal(s, sig);
        assertTrue(validSig, "signature itself is valid");
        assertFalse(human, "but signer is no verified human");
        vm.expectRevert(abi.encodeWithSelector(SatyaRegistry.NotHuman.selector, agent));
        reg.anchorSeal(s, sig, SOFT);
    }

    function test_RevertWhen_SealTampered() public {
        (SatyaRegistry.Seal memory s, bytes memory sig) = _seal(aliceKey, TEXT_HUMAN, 0);
        s.contentHash = TEXT_AI; // attacker reuses Alice's signature for other content
        vm.expectRevert(SatyaRegistry.InvalidSignature.selector);
        reg.anchorSeal(s, sig, SOFT);
    }

    function test_RevertWhen_SealFromFuture() public {
        (SatyaRegistry.Seal memory s,) = _seal(aliceKey, TEXT_HUMAN, 0);
        s.createdAt = uint64(block.timestamp + 1 days);
        (uint8 v, bytes32 r, bytes32 ss) = vm.sign(aliceKey, reg.hashSeal(s));
        vm.expectRevert(SatyaRegistry.InvalidSeal.selector);
        reg.anchorSeal(s, abi.encodePacked(r, ss, v), SOFT);
    }

    function testFuzz_ForgedSealNeverAccepted(uint256 forgerKey, bytes32 contentHash) public {
        forgerKey = bound(forgerKey, 1, 2 ** 128);
        vm.assume(forgerKey != aliceKey && forgerKey != malloryKey && contentHash != bytes32(0));
        // forger signs, but claims Alice as signer
        SatyaRegistry.Seal memory s = SatyaRegistry.Seal({
            contentHash: contentHash, aiUse: 0, createdAt: uint64(block.timestamp), signer: alice
        });
        (uint8 v, bytes32 r, bytes32 ss) = vm.sign(forgerKey, reg.hashSeal(s));
        vm.expectRevert(SatyaRegistry.InvalidSignature.selector);
        reg.anchorSeal(s, abi.encodePacked(r, ss, v), SOFT);
    }

    // ---------------------------------------------------------- providers

    function test_ProviderRegistersOutput() public {
        vm.prank(aiProvider);
        reg.attestAI(TEXT_AI, SOFT);
        assertEq(reg.summary(TEXT_AI).aiProvider, 1);
    }

    function test_RevertWhen_NonProviderRegisters() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(SatyaRegistry.NotProvider.selector, alice));
        reg.attestAI(TEXT_AI, SOFT);
    }

    function test_DeactivatedProviderNoLongerCounts() public {
        vm.prank(aiProvider);
        reg.attestAI(TEXT_AI, SOFT);
        vm.prank(governance);
        reg.setProvider(aiProvider, false, "Demo-KI-Anbieter (kompromittiert)");
        SatyaRegistry.Summary memory s = reg.summary(TEXT_AI);
        assertEq(s.aiProvider, 0);
        assertEq(s.invalid, 1);
    }

    // ------------------------------------------------ contradiction & fraud

    function test_ContradictionAndFraudBan() public {
        vm.prank(aiProvider);
        reg.attestAI(TEXT_AI, SOFT);
        vm.prank(mallory); // verified human lies: "written without AI"
        reg.attest(TEXT_AI, SatyaRegistry.AiUse.NONE, SOFT);
        assertTrue(reg.summary(TEXT_AI).contradiction);

        // governance flags the statement, HMN bans the person -> all their statements lose value
        vm.startPrank(governance);
        reg.flagFraud(TEXT_AI, 1);
        hmn.revoke(hmn.tokenOf(mallory), true);
        vm.stopPrank();

        SatyaRegistry.Summary memory s = reg.summary(TEXT_AI);
        assertFalse(s.contradiction);
        assertEq(s.invalid, 1);
        assertFalse(hmn.isHuman(mallory));
    }

    function test_BannedPersonInvalidatesAllOwnStatements() public {
        vm.prank(mallory);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
        assertTrue(reg.isValid(TEXT_HUMAN, 0));
        uint256 malloryToken = hmn.tokenOf(mallory);
        vm.prank(governance);
        hmn.revoke(malloryToken, true);
        assertFalse(reg.isValid(TEXT_HUMAN, 0));
    }

    function test_ExpiredCredentialKeepsPastStatements() public {
        vm.prank(alice);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
        vm.warp(block.timestamp + 365 days);
        assertFalse(hmn.isHuman(alice));
        assertTrue(reg.isValid(TEXT_HUMAN, 0), "statement was made while verified");
    }

    function test_AttesterCanRevoke() public {
        vm.prank(alice);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
        vm.prank(mallory);
        vm.expectRevert(SatyaRegistry.NotAttester.selector);
        reg.revoke(TEXT_HUMAN, 0);
        vm.prank(alice);
        reg.revoke(TEXT_HUMAN, 0);
        assertEq(reg.summary(TEXT_HUMAN).humanNone, 0);
    }

    function test_RecoveredWalletCannotAttestTwice() public {
        vm.prank(alice);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
        // Alice recovers to a new wallet (same personId)
        address aliceNew = makeAddr("aliceNew");
        hmn.setHuman(aliceNew, keccak256("alice"), 2);

        vm.prank(aliceNew);
        vm.expectRevert(SatyaRegistry.AlreadyAttested.selector);
        reg.attest(TEXT_HUMAN, SatyaRegistry.AiUse.NONE, SOFT);
    }

    function test_RevertWhen_NonOwnerGovernance() public {
        vm.startPrank(alice);
        vm.expectRevert();
        reg.setProvider(alice, true, "fake provider");
        vm.expectRevert();
        reg.flagFraud(TEXT_HUMAN, 0);
        vm.stopPrank();
    }
}
