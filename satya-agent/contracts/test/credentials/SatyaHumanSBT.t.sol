// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SatyaHumanSBT} from "../../src/credentials/SatyaHumanSBT.sol";
import {ISelfAgentRegistry} from "../../src/interfaces/ISelfAgentRegistry.sol";
import {IERC5192} from "../../src/interfaces/IERC5192.sol";
import {MockSelfAgentRegistry} from "../mocks/Mocks.sol";

contract SatyaHumanSBTTest is Test {
    SatyaHumanSBT internal credential;
    MockSelfAgentRegistry internal self_;

    uint256 internal constant ALICE_AGENT = 11;
    uint256 internal constant ALICE_SECOND_AGENT = 12;
    uint256 internal constant BOB_RECOVERY_AGENT = 13;
    uint256 internal constant ALICE_NULLIFIER = 0xA11CE;
    uint256 internal constant BOB_NULLIFIER = 0xB0B;

    address internal alice = address(0xA11CE);
    address internal aliceAgentKey = address(0xA11CE01);
    address internal aliceSecondKey = address(0xA11CE02);
    address internal bob = address(0xB0B);
    address internal bobAgentKey = address(0xB0B01);

    function setUp() public {
        self_ = new MockSelfAgentRegistry();
        credential = new SatyaHumanSBT(ISelfAgentRegistry(address(self_)));
        self_.addAgent(ALICE_AGENT, aliceAgentKey, alice, ALICE_NULLIFIER);
        self_.addAgent(ALICE_SECOND_AGENT, aliceSecondKey, alice, ALICE_NULLIFIER);
        self_.addAgent(BOB_RECOVERY_AGENT, bobAgentKey, bob, ALICE_NULLIFIER);
    }

    function test_claimMintsLockedErc5192Credential() public {
        vm.prank(alice);
        uint256 tokenId = credential.claim(ALICE_AGENT);

        assertEq(credential.ownerOf(tokenId), alice);
        assertEq(credential.tokenOf(alice), tokenId);
        assertTrue(credential.locked(tokenId));
        assertTrue(credential.isHuman(alice));
        assertTrue(credential.supportsInterface(type(IERC5192).interfaceId));
        assertTrue(credential.supportsInterface(0x80ac58cd)); // ERC-721
        assertTrue(_startsWith(credential.tokenURI(tokenId), "data:application/json;base64,"));
    }

    function test_sameHumanCannotMintSecondCredentialThroughAnotherAgent() public {
        vm.prank(alice);
        uint256 first = credential.claim(ALICE_AGENT);
        vm.prank(alice);
        uint256 second = credential.claim(ALICE_SECOND_AGENT);

        assertEq(second, first);
        assertEq(credential.balanceOf(alice), 1);
        (uint256 agentId,,, bool valid) = credential.credentialDetails(first);
        assertEq(agentId, ALICE_SECOND_AGENT);
        assertTrue(valid);
    }

    function test_walletCannotClaimCredentialsForDifferentHumans() public {
        self_.addAgent(21, address(0x2100), alice, BOB_NULLIFIER);
        vm.prank(alice);
        credential.claim(ALICE_AGENT);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.WalletAlreadyHasCredential.selector, 1));
        credential.claim(21);
    }

    function test_onlyCurrentSelfAgentOwnerCanClaim() public {
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.NotAgentOwner.selector, bob, ALICE_AGENT));
        credential.claim(ALICE_AGENT);
    }

    function test_missingOrStaleProofCannotClaim() public {
        self_.setFresh(ALICE_AGENT, false);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.NoFreshHumanProof.selector, ALICE_AGENT));
        credential.claim(ALICE_AGENT);
    }

    function test_zeroNullifierCannotClaim() public {
        self_.addAgent(30, address(0x3000), alice, 0);
        self_.setHasProof(30, true);
        self_.setFresh(30, true);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.InvalidHumanNullifier.selector, 30));
        credential.claim(30);
    }

    function test_transferApprovalAndOperatorApprovalAreDisabled() public {
        vm.prank(alice);
        uint256 tokenId = credential.claim(ALICE_AGENT);

        vm.prank(alice);
        vm.expectRevert(SatyaHumanSBT.Soulbound.selector);
        credential.transferFrom(alice, bob, tokenId);

        vm.prank(alice);
        vm.expectRevert(SatyaHumanSBT.Soulbound.selector);
        credential.safeTransferFrom(alice, bob, tokenId);

        vm.prank(alice);
        vm.expectRevert(SatyaHumanSBT.Soulbound.selector);
        credential.approve(bob, tokenId);

        vm.prank(alice);
        vm.expectRevert(SatyaHumanSBT.Soulbound.selector);
        credential.setApprovalForAll(bob, true);

        assertEq(credential.ownerOf(tokenId), alice);
    }

    function test_lockedRevertsForUnknownToken() public {
        vm.expectRevert();
        credential.locked(999);
    }

    function test_recoveryMustBeExplicitAndBurnsOldToken() public {
        vm.prank(alice);
        uint256 oldTokenId = credential.claim(ALICE_AGENT);

        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.RecoveryRequired.selector, oldTokenId, alice));
        credential.claim(BOB_RECOVERY_AGENT);

        vm.prank(bob);
        uint256 newTokenId = credential.recover(BOB_RECOVERY_AGENT);

        assertGt(newTokenId, oldTokenId);
        assertEq(credential.ownerOf(newTokenId), bob);
        assertEq(credential.tokenOf(bob), newTokenId);
        assertEq(credential.tokenOf(alice), 0);
        assertEq(credential.balanceOf(alice), 0);
        assertTrue(credential.isHuman(bob));
        assertFalse(credential.isHuman(alice));
        vm.expectRevert();
        credential.ownerOf(oldTokenId);
    }

    function test_recoveryRejectsDifferentHuman() public {
        vm.prank(alice);
        credential.claim(ALICE_AGENT);
        self_.addAgent(31, address(0x3100), bob, BOB_NULLIFIER);

        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.NoCredentialToRecover.selector, 31));
        credential.recover(31);
    }

    function test_currentProofExpiresAndNoLongerCountsAsHuman() public {
        vm.prank(alice);
        uint256 tokenId = credential.claim(ALICE_AGENT);

        vm.warp(block.timestamp + 366 days);
        assertFalse(credential.isHuman(alice));
        (,,, bool currentlyValid) = credential.credentialDetails(tokenId);
        assertFalse(currentlyValid);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(SatyaHumanSBT.InvalidProofExpiry.selector, ALICE_AGENT));
        credential.claim(ALICE_AGENT);
    }

    function test_relinkedCredentialIsNotValidForOldWallet() public {
        vm.prank(alice);
        uint256 tokenId = credential.claim(ALICE_AGENT);
        self_.setOwner(ALICE_AGENT, bob);

        assertFalse(credential.isHuman(alice));
        assertEq(credential.ownerOf(tokenId), alice); // soulbound token remains attached to old wallet until recovery
    }

    function test_holderCanRenounceAndLaterReclaim() public {
        vm.prank(alice);
        uint256 oldTokenId = credential.claim(ALICE_AGENT);

        vm.prank(alice);
        credential.renounce();

        assertEq(credential.tokenOf(alice), 0);
        assertFalse(credential.isHuman(alice));
        vm.expectRevert();
        credential.ownerOf(oldTokenId);

        vm.prank(alice);
        uint256 newTokenId = credential.claim(ALICE_AGENT);
        assertGt(newTokenId, oldTokenId);
        assertTrue(credential.isHuman(alice));
    }

    function test_credentialOfAgentDoesNotExposeNullifier() public {
        vm.prank(alice);
        uint256 tokenId = credential.claim(ALICE_AGENT);
        (uint256 foundTokenId, address holder) = credential.credentialOfAgent(ALICE_SECOND_AGENT);
        assertEq(foundTokenId, tokenId);
        assertEq(holder, alice);
    }

    function _startsWith(string memory value, string memory prefix) private pure returns (bool) {
        bytes memory valueBytes = bytes(value);
        bytes memory prefixBytes = bytes(prefix);
        if (valueBytes.length < prefixBytes.length) return false;
        for (uint256 i; i < prefixBytes.length; ++i) {
            if (valueBytes[i] != prefixBytes[i]) return false;
        }
        return true;
    }
}
