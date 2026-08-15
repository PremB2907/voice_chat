// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MemoryBridgeRegistry {
    address public owner;

    enum ConsentStatus { GRANTED, REVOKED, EXPIRED }

    struct ConsentRecord {
        bytes32 personaHash;
        string consentType;
        ConsentStatus status;
        string policyVersion;
        bytes32 metadataHash;
        uint256 timestamp;
    }

    struct MemoryRecord {
        string memoryId;
        uint256 memoryVersion;
        bytes32 memoryHash;
        uint256 timestamp;
        bytes32 personaHash;
    }

    struct ResponseRecord {
        bytes32 responseHash;
        bytes32 modelHash;
        bytes32 personaHash;
        uint256 memoryVersion;
        uint256 timestamp;
    }

    struct VersionRecord {
        string versionIdentifier;
        bytes32 configHash;
        uint256 timestamp;
    }

    // Mapping from personaHash to ConsentRecord
    mapping(bytes32 => ConsentRecord) public consentRecords;

    // Mapping from memoryId to its versions (version index -> MemoryRecord)
    mapping(string => MemoryRecord[]) public memoryRecords;

    // Mapping from responseHash to ResponseRecord
    mapping(bytes32 => ResponseRecord) public responseRecords;

    // Mapping from versionIdentifier to VersionRecord
    mapping(string => VersionRecord) public versionRecords;

    // Events
    event ConsentRecorded(bytes32 indexed personaHash, string consentType, ConsentStatus status, string policyVersion, bytes32 metadataHash, uint256 timestamp);
    event ConsentRevoked(bytes32 indexed personaHash, uint256 timestamp);
    event MemoryRegistered(string indexed memoryId, uint256 indexed memoryVersion, bytes32 memoryHash, bytes32 indexed personaHash, uint256 timestamp);
    event ResponseRegistered(bytes32 indexed responseHash, bytes32 modelHash, bytes32 personaHash, uint256 memoryVersion, uint256 timestamp);
    event VersionRegistered(string versionIdentifier, bytes32 configHash, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerConsent(
        bytes32 _personaHash,
        string calldata _consentType,
        ConsentStatus _status,
        string calldata _policyVersion,
        bytes32 _metadataHash
    ) external onlyOwner {
        consentRecords[_personaHash] = ConsentRecord({
            personaHash: _personaHash,
            consentType: _consentType,
            status: _status,
            policyVersion: _policyVersion,
            metadataHash: _metadataHash,
            timestamp: block.timestamp
        });
        emit ConsentRecorded(_personaHash, _consentType, _status, _policyVersion, _metadataHash, block.timestamp);
    }

    function revokeConsent(bytes32 _personaHash) external onlyOwner {
        require(consentRecords[_personaHash].timestamp != 0, "No consent record found");
        consentRecords[_personaHash].status = ConsentStatus.REVOKED;
        consentRecords[_personaHash].timestamp = block.timestamp;
        emit ConsentRevoked(_personaHash, block.timestamp);
    }

    function registerMemory(
        string calldata _memoryId,
        bytes32 _memoryHash,
        bytes32 _personaHash
    ) external onlyOwner {
        uint256 nextVersion = memoryRecords[_memoryId].length + 1;
        MemoryRecord memory rec = MemoryRecord({
            memoryId: _memoryId,
            memoryVersion: nextVersion,
            memoryHash: _memoryHash,
            timestamp: block.timestamp,
            personaHash: _personaHash
        });
        memoryRecords[_memoryId].push(rec);
        emit MemoryRegistered(_memoryId, nextVersion, _memoryHash, _personaHash, block.timestamp);
    }

    function registerResponse(
        bytes32 _responseHash,
        bytes32 _modelHash,
        bytes32 _personaHash,
        uint256 _memoryVersion
    ) external onlyOwner {
        responseRecords[_responseHash] = ResponseRecord({
            responseHash: _responseHash,
            modelHash: _modelHash,
            personaHash: _personaHash,
            memoryVersion: _memoryVersion,
            timestamp: block.timestamp
        });
        emit ResponseRegistered(_responseHash, _modelHash, _personaHash, _memoryVersion, block.timestamp);
    }

    function registerVersion(
        string calldata _versionIdentifier,
        bytes32 _configHash
    ) external onlyOwner {
        versionRecords[_versionIdentifier] = VersionRecord({
            versionIdentifier: _versionIdentifier,
            configHash: _configHash,
            timestamp: block.timestamp
        });
        emit VersionRegistered(_versionIdentifier, _configHash, block.timestamp);
    }

    // Getters for off-chain verification
    function getConsent(bytes32 _personaHash) external view returns (
        bytes32 personaHash,
        string memory consentType,
        ConsentStatus status,
        string memory policyVersion,
        bytes32 metadataHash,
        uint256 timestamp
    ) {
        ConsentRecord memory rec = consentRecords[_personaHash];
        return (rec.personaHash, rec.consentType, rec.status, rec.policyVersion, rec.metadataHash, rec.timestamp);
    }

    function getMemoryVersionCount(string calldata _memoryId) external view returns (uint256) {
        return memoryRecords[_memoryId].length;
    }

    function getMemory(string calldata _memoryId, uint256 _version) external view returns (
        string memory memoryId,
        uint256 memoryVersion,
        bytes32 memoryHash,
        uint256 timestamp,
        bytes32 personaHash
    ) {
        require(_version > 0 && _version <= memoryRecords[_memoryId].length, "Invalid version");
        MemoryRecord memory rec = memoryRecords[_memoryId][_version - 1];
        return (rec.memoryId, rec.memoryVersion, rec.memoryHash, rec.timestamp, rec.personaHash);
    }

    function getResponse(bytes32 _responseHash) external view returns (
        bytes32 responseHash,
        bytes32 modelHash,
        bytes32 personaHash,
        uint256 memoryVersion,
        uint256 timestamp
    ) {
        ResponseRecord memory rec = responseRecords[_responseHash];
        return (rec.responseHash, rec.modelHash, rec.personaHash, rec.memoryVersion, rec.timestamp);
    }

    function getVersion(string calldata _versionIdentifier) external view returns (
        string memory versionIdentifier,
        bytes32 configHash,
        uint256 timestamp
    ) {
        VersionRecord memory rec = versionRecords[_versionIdentifier];
        return (rec.versionIdentifier, rec.configHash, rec.timestamp);
    }
}
