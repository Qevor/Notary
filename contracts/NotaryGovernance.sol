// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract NotaryGovernance {
    struct GovernanceRecord {
        bytes32 operatingAgreementHash;
        bytes32 permittedActionPolicyHash;
        bytes32 privacyPolicyHash;
        bytes32 replicationPolicyHash;
        address swarmManager;
        uint256 updatedAt;
    }

    address public owner;
    mapping(bytes32 => GovernanceRecord) public records;

    event GovernanceUpdated(
        bytes32 indexed notaryId,
        bytes32 operatingAgreementHash,
        bytes32 permittedActionPolicyHash,
        bytes32 privacyPolicyHash,
        bytes32 replicationPolicyHash,
        address swarmManager
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function updateGovernance(
        bytes32 notaryId,
        bytes32 operatingAgreementHash,
        bytes32 permittedActionPolicyHash,
        bytes32 privacyPolicyHash,
        bytes32 replicationPolicyHash,
        address swarmManager
    ) external onlyOwner {
        records[notaryId] = GovernanceRecord({
            operatingAgreementHash: operatingAgreementHash,
            permittedActionPolicyHash: permittedActionPolicyHash,
            privacyPolicyHash: privacyPolicyHash,
            replicationPolicyHash: replicationPolicyHash,
            swarmManager: swarmManager,
            updatedAt: block.timestamp
        });
        emit GovernanceUpdated(
            notaryId,
            operatingAgreementHash,
            permittedActionPolicyHash,
            privacyPolicyHash,
            replicationPolicyHash,
            swarmManager
        );
    }
}

