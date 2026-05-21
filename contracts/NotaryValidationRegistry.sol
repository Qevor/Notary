// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract NotaryValidationRegistry {
    struct ValidationRecord {
        bytes32 notaryId;
        bytes32 subjectId;
        bytes32 validationHash;
        bytes32 kindHash;
        address validator;
        uint256 createdAt;
    }

    mapping(bytes32 => ValidationRecord) public validations;

    event ValidationRecorded(
        bytes32 indexed validationId,
        bytes32 indexed notaryId,
        bytes32 indexed subjectId,
        bytes32 validationHash,
        bytes32 kindHash,
        address validator
    );

    function recordValidation(
        bytes32 validationId,
        bytes32 notaryId,
        bytes32 subjectId,
        bytes32 validationHash,
        bytes32 kindHash,
        address validator
    ) external {
        require(validations[validationId].createdAt == 0, "VALIDATION_EXISTS");
        validations[validationId] = ValidationRecord({
            notaryId: notaryId,
            subjectId: subjectId,
            validationHash: validationHash,
            kindHash: kindHash,
            validator: validator,
            createdAt: block.timestamp
        });
        emit ValidationRecorded(validationId, notaryId, subjectId, validationHash, kindHash, validator);
    }
}

