// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract NotaryReplication {
    struct ReplicationRecord {
        bytes32 parentNotaryId;
        bytes32 childNotaryId;
        bytes32 policyDnaHash;
        address childAgentWallet;
        uint256 createdAt;
    }

    mapping(bytes32 => ReplicationRecord) public replications;

    event ReplicationRecorded(
        bytes32 indexed replicationId,
        bytes32 indexed parentNotaryId,
        bytes32 indexed childNotaryId,
        bytes32 policyDnaHash,
        address childAgentWallet
    );

    function recordReplication(
        bytes32 replicationId,
        bytes32 parentNotaryId,
        bytes32 childNotaryId,
        bytes32 policyDnaHash,
        address childAgentWallet
    ) external {
        require(replications[replicationId].createdAt == 0, "REPLICATION_EXISTS");
        replications[replicationId] = ReplicationRecord({
            parentNotaryId: parentNotaryId,
            childNotaryId: childNotaryId,
            policyDnaHash: policyDnaHash,
            childAgentWallet: childAgentWallet,
            createdAt: block.timestamp
        });
        emit ReplicationRecorded(
            replicationId,
            parentNotaryId,
            childNotaryId,
            policyDnaHash,
            childAgentWallet
        );
    }
}
