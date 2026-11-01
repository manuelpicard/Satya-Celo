// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {ISelfAgentRegistry} from "../src/interfaces/ISelfAgentRegistry.sol";
import {SatyaHumanSBT} from "../src/credentials/SatyaHumanSBT.sol";

/// @notice Deploys Satya's ERC-5192 human credential to Celo Sepolia only.
///         Mainnet is intentionally rejected by this script.
///
///         forge script script/DeploySatyaHumanSBT.s.sol --rpc-url celo_sepolia --broadcast
contract DeploySatyaHumanSBT is Script {
    address internal constant SELF_AGENT_REGISTRY = 0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379;

    function run() external returns (SatyaHumanSBT credential) {
        require(block.chainid == 11142220, "testnet only: Celo Sepolia required");
        require(SELF_AGENT_REGISTRY.code.length > 0, "Self Agent ID registry missing");

        vm.startBroadcast();
        credential = new SatyaHumanSBT(ISelfAgentRegistry(SELF_AGENT_REGISTRY));
        vm.stopBroadcast();

        console2.log("chain id             ", block.chainid);
        console2.log("SatyaHumanSBT        ", address(credential));
        console2.log("Self Agent ID registry", SELF_AGENT_REGISTRY);
    }
}
