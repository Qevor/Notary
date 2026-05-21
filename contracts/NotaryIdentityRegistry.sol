// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract NotaryIdentityRegistry {
    enum Status {
        Unknown,
        Active,
        Paused,
        Retired
    }

    struct NotaryIdentity {
        address agentWallet;
        address treasury;
        bytes32 capabilitiesHash;
        bytes32 operatingAgreementHash;
        bytes32 policyDnaHash;
        bytes32 privacyPolicyHash;
        bytes32 parentNotaryId;
        Status status;
        uint256 createdAt;
    }

    address public owner;
    mapping(bytes32 => NotaryIdentity) public identities;

    event NotaryCreated(bytes32 indexed notaryId, address indexed agentWallet, address treasury);
    event PolicyUpdated(bytes32 indexed notaryId, bytes32 policyDnaHash);
    event PrivacyPolicyUpdated(bytes32 indexed notaryId, bytes32 privacyPolicyHash);
    event TreasuryUpdated(bytes32 indexed notaryId, address treasury);
    event OperatingAgreementUpdated(bytes32 indexed notaryId, bytes32 operatingAgreementHash);
    event ChildNotarySpawned(bytes32 indexed parentNotaryId, bytes32 indexed childNotaryId);
    event NotaryStatusChanged(bytes32 indexed notaryId, Status status);

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function createNotary(
        bytes32 notaryId,
        address agentWallet,
        address treasury,
        bytes32 capabilitiesHash,
        bytes32 operatingAgreementHash,
        bytes32 policyDnaHash,
        bytes32 privacyPolicyHash,
        bytes32 parentNotaryId
    ) external onlyOwner {
        require(identities[notaryId].createdAt == 0, "NOTARY_EXISTS");
        identities[notaryId] = NotaryIdentity({
            agentWallet: agentWallet,
            treasury: treasury,
            capabilitiesHash: capabilitiesHash,
            operatingAgreementHash: operatingAgreementHash,
            policyDnaHash: policyDnaHash,
            privacyPolicyHash: privacyPolicyHash,
            parentNotaryId: parentNotaryId,
            status: Status.Active,
            createdAt: block.timestamp
        });
        emit NotaryCreated(notaryId, agentWallet, treasury);
        if (parentNotaryId != bytes32(0)) {
            emit ChildNotarySpawned(parentNotaryId, notaryId);
        }
    }

    function updatePolicy(bytes32 notaryId, bytes32 policyDnaHash) external onlyOwner {
        require(identities[notaryId].createdAt != 0, "NOT_FOUND");
        identities[notaryId].policyDnaHash = policyDnaHash;
        emit PolicyUpdated(notaryId, policyDnaHash);
    }

    function updatePrivacyPolicy(bytes32 notaryId, bytes32 privacyPolicyHash) external onlyOwner {
        require(identities[notaryId].createdAt != 0, "NOT_FOUND");
        identities[notaryId].privacyPolicyHash = privacyPolicyHash;
        emit PrivacyPolicyUpdated(notaryId, privacyPolicyHash);
    }
}

