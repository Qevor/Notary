// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract HelixAIKarma {
    struct KarmaCheckpoint {
        uint64 accuracyBps;
        uint64 safetyBps;
        uint64 paymentReliabilityBps;
        uint64 privacyScoreBps;
        int256 arbitragePnlUsdc;
        bytes32 checkpointHash;
        address signer;
        uint256 createdAt;
    }

    address public owner;
    mapping(bytes32 => KarmaCheckpoint[]) private checkpoints;

    event KarmaCheckpointRecorded(
        bytes32 indexed notaryId,
        bytes32 indexed checkpointHash,
        uint64 accuracyBps,
        uint64 safetyBps,
        uint64 paymentReliabilityBps,
        uint64 privacyScoreBps,
        int256 arbitragePnlUsdc,
        address signer
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function recordCheckpoint(
        bytes32 notaryId,
        bytes32 checkpointHash,
        uint64 accuracyBps,
        uint64 safetyBps,
        uint64 paymentReliabilityBps,
        uint64 privacyScoreBps,
        int256 arbitragePnlUsdc,
        address signer
    ) external onlyOwner {
        require(accuracyBps <= 10_000, "BAD_ACCURACY");
        require(safetyBps <= 10_000, "BAD_SAFETY");
        require(paymentReliabilityBps <= 10_000, "BAD_PAYMENT");
        require(privacyScoreBps <= 10_000, "BAD_PRIVACY");
        checkpoints[notaryId].push(
            KarmaCheckpoint({
                accuracyBps: accuracyBps,
                safetyBps: safetyBps,
                paymentReliabilityBps: paymentReliabilityBps,
                privacyScoreBps: privacyScoreBps,
                arbitragePnlUsdc: arbitragePnlUsdc,
                checkpointHash: checkpointHash,
                signer: signer,
                createdAt: block.timestamp
            })
        );
        emit KarmaCheckpointRecorded(
            notaryId,
            checkpointHash,
            accuracyBps,
            safetyBps,
            paymentReliabilityBps,
            privacyScoreBps,
            arbitragePnlUsdc,
            signer
        );
    }

    function checkpointCount(bytes32 notaryId) external view returns (uint256) {
        return checkpoints[notaryId].length;
    }

    function latestCheckpoint(bytes32 notaryId) external view returns (KarmaCheckpoint memory) {
        require(checkpoints[notaryId].length > 0, "NO_CHECKPOINT");
        return checkpoints[notaryId][checkpoints[notaryId].length - 1];
    }
}

