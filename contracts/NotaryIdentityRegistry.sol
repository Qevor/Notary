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
        bytes32 accountabilityPolicyHash;
        bytes32 privacyPolicyHash;
        Status status;
        uint256 createdAt;
    }

    address public owner;
    mapping(bytes32 => NotaryIdentity) public identities;

    event NotaryCreated(bytes32 indexed notaryId, address indexed agentWallet, address treasury);
    event AccountabilityPolicyUpdated(bytes32 indexed notaryId, bytes32 accountabilityPolicyHash);
    event PrivacyPolicyUpdated(bytes32 indexed notaryId, bytes32 privacyPolicyHash);
    event TreasuryUpdated(bytes32 indexed notaryId, address treasury);
    event OperatingAgreementUpdated(bytes32 indexed notaryId, bytes32 operatingAgreementHash);
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
        bytes32 accountabilityPolicyHash,
        bytes32 privacyPolicyHash
    ) external onlyOwner {
        require(identities[notaryId].createdAt == 0, "NOTARY_EXISTS");
        identities[notaryId] = NotaryIdentity({
            agentWallet: agentWallet,
            treasury: treasury,
            capabilitiesHash: capabilitiesHash,
            operatingAgreementHash: operatingAgreementHash,
            accountabilityPolicyHash: accountabilityPolicyHash,
            privacyPolicyHash: privacyPolicyHash,
            status: Status.Active,
            createdAt: block.timestamp
        });
        emit NotaryCreated(notaryId, agentWallet, treasury);
    }

    function updateAccountabilityPolicy(
        bytes32 notaryId,
        bytes32 accountabilityPolicyHash
    ) external onlyOwner {
        require(identities[notaryId].createdAt != 0, "NOT_FOUND");
        identities[notaryId].accountabilityPolicyHash = accountabilityPolicyHash;
        emit AccountabilityPolicyUpdated(notaryId, accountabilityPolicyHash);
    }

    function updatePrivacyPolicy(bytes32 notaryId, bytes32 privacyPolicyHash) external onlyOwner {
        require(identities[notaryId].createdAt != 0, "NOT_FOUND");
        identities[notaryId].privacyPolicyHash = privacyPolicyHash;
        emit PrivacyPolicyUpdated(notaryId, privacyPolicyHash);
    }
}
