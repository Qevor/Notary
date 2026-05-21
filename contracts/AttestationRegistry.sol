// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract AttestationRegistry {
    enum Status {
        Unknown,
        Signed,
        Submitted,
        Disputed,
        Resolved,
        Rejected
    }

    struct AttestationRecord {
        bytes32 notaryId;
        bytes32 evidenceHash;
        bytes32 reasoningTraceHash;
        bytes32 disclosurePolicyHash;
        uint64 confidenceBps;
        uint8 privacyMode;
        address signer;
        Status status;
        uint256 createdAt;
    }

    mapping(bytes32 => AttestationRecord) public attestations;
    mapping(bytes32 => bytes32) public predictions;

    event AttestationRecorded(
        bytes32 indexed attestationId,
        bytes32 indexed notaryId,
        bytes32 evidenceHash,
        bytes32 reasoningTraceHash,
        uint8 privacyMode,
        address signer
    );
    event AttestationStatusChanged(bytes32 indexed attestationId, Status status);
    event PredictionRecorded(bytes32 indexed predictionId, bytes32 indexed predictionHash);

    function recordAttestation(
        bytes32 attestationId,
        bytes32 notaryId,
        bytes32 evidenceHash,
        bytes32 reasoningTraceHash,
        bytes32 disclosurePolicyHash,
        uint64 confidenceBps,
        uint8 privacyMode,
        address signer
    ) external {
        require(attestations[attestationId].createdAt == 0, "ATTESTATION_EXISTS");
        require(confidenceBps <= 10_000, "BAD_CONFIDENCE");
        attestations[attestationId] = AttestationRecord({
            notaryId: notaryId,
            evidenceHash: evidenceHash,
            reasoningTraceHash: reasoningTraceHash,
            disclosurePolicyHash: disclosurePolicyHash,
            confidenceBps: confidenceBps,
            privacyMode: privacyMode,
            signer: signer,
            status: Status.Signed,
            createdAt: block.timestamp
        });
        emit AttestationRecorded(
            attestationId,
            notaryId,
            evidenceHash,
            reasoningTraceHash,
            privacyMode,
            signer
        );
    }

    function setStatus(bytes32 attestationId, Status status) external {
        require(attestations[attestationId].createdAt != 0, "NOT_FOUND");
        attestations[attestationId].status = status;
        emit AttestationStatusChanged(attestationId, status);
    }

    function recordPrediction(bytes32 predictionId, bytes32 predictionHash) external {
        require(predictions[predictionId] == bytes32(0), "PREDICTION_EXISTS");
        predictions[predictionId] = predictionHash;
        emit PredictionRecorded(predictionId, predictionHash);
    }
}

