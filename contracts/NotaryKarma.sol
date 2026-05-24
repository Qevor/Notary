// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract NotaryKarma {
    struct KarmaCheckpoint {
        bytes32 notaryId;
        int256 delta;
        uint256 score;
        bytes32 policyDnaHash;
        address validator;
        uint256 createdAt;
    }

    mapping(bytes32 => uint256) public scores;
    mapping(bytes32 => KarmaCheckpoint) public checkpoints;

    event KarmaRecorded(
        bytes32 indexed notaryId,
        bytes32 indexed checkpointId,
        int256 delta,
        uint256 score,
        bytes32 policyDnaHash,
        address indexed validator
    );

    function recordKarma(
        bytes32 notaryId,
        bytes32 checkpointId,
        int256 delta,
        uint256 score,
        bytes32 policyDnaHash,
        address validator
    ) external {
        require(checkpoints[checkpointId].createdAt == 0, "KARMA_EXISTS");
        checkpoints[checkpointId] = KarmaCheckpoint({
            notaryId: notaryId,
            delta: delta,
            score: score,
            policyDnaHash: policyDnaHash,
            validator: validator,
            createdAt: block.timestamp
        });
        scores[notaryId] = score;
        emit KarmaRecorded(notaryId, checkpointId, delta, score, policyDnaHash, validator);
    }
}
