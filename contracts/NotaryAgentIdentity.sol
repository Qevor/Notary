// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract NotaryAgentIdentity {
    struct AgentRecord {
        address agentWallet;
        bytes32 serviceHash;
        bytes32 metadataHash;
        bytes32 capabilitiesHash;
        uint256 createdAt;
    }

    mapping(bytes32 => AgentRecord) public agents;

    event AgentRegistered(
        bytes32 indexed notaryId,
        address indexed agentWallet,
        bytes32 serviceHash,
        bytes32 metadataHash,
        bytes32 capabilitiesHash
    );

    function registerAgent(
        bytes32 notaryId,
        address agentWallet,
        bytes32 serviceHash,
        bytes32 metadataHash,
        bytes32 capabilitiesHash
    ) external {
        require(agents[notaryId].createdAt == 0, "AGENT_EXISTS");
        agents[notaryId] = AgentRecord({
            agentWallet: agentWallet,
            serviceHash: serviceHash,
            metadataHash: metadataHash,
            capabilitiesHash: capabilitiesHash,
            createdAt: block.timestamp
        });
        emit AgentRegistered(notaryId, agentWallet, serviceHash, metadataHash, capabilitiesHash);
    }
}
