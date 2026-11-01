// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {SatyaCelo} from "../src/SatyaCelo.sol";
import {ISelfAgentRegistry} from "../src/interfaces/ISelfAgentRegistry.sol";
import {IIdentityRegistry8004} from "../src/interfaces/IIdentityRegistry8004.sol";

/// @notice Deploys SatyaCelo against the live registries of the selected chain.
///         The contract is ownerless, so deployment is the last privileged act.
///
///         forge script script/DeployCelo.s.sol --rpc-url celo_sepolia --broadcast
contract DeployCelo is Script {
    address constant SELF_AGENTS_MAINNET = 0xaC3DF9ABf80d0F5c020C06B04Cced27763355944;
    address constant SELF_AGENTS_SEPOLIA = 0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379;
    address constant ID_8004_MAINNET = 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432;
    address constant ID_8004_SEPOLIA = 0x8004A818BFB912233c491871b3d84c89A494BD9e;

    function run() external returns (SatyaCelo registry) {
        (address selfAgents, address id8004) = addressesFor(block.chainid);

        require(selfAgents.code.length > 0, "Self Agent ID not deployed on this chain");
        require(id8004.code.length > 0, "ERC-8004 identity registry not deployed on this chain");

        vm.startBroadcast();
        registry = new SatyaCelo(ISelfAgentRegistry(selfAgents), IIdentityRegistry8004(id8004));
        vm.stopBroadcast();

        console2.log("chain id        ", block.chainid);
        console2.log("SatyaCelo   ", address(registry));
        console2.log("Self Agent ID   ", selfAgents);
        console2.log("ERC-8004 idReg  ", id8004);
    }

    function addressesFor(uint256 chainId) public pure returns (address selfAgents, address id8004) {
        if (chainId == 42220) return (SELF_AGENTS_MAINNET, ID_8004_MAINNET);
        if (chainId == 11142220) return (SELF_AGENTS_SEPOLIA, ID_8004_SEPOLIA);
        revert("unsupported chain: use Celo mainnet (42220) or Celo Sepolia (11142220)");
    }
}
