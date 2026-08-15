const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MemoryBridgeRegistry", function () {
  let Registry;
  let registry;
  let owner;
  let addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    Registry = await ethers.getContractFactory("MemoryBridgeRegistry");
    registry = await Registry.deploy();
  });

  describe("Owner", function () {
    it("Should set the right owner", async function () {
      expect(await registry.owner()).to.equal(owner.address);
    });
  });

  describe("Consent Registration & Revocation", function () {
    it("Should register consent correctly and emit event", async function () {
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));
      const consentType = "all";
      const policyVersion = "v1";
      const metadataHash = ethers.keccak256(ethers.toUtf8Bytes("meta-1"));

      await expect(
        registry.registerConsent(personaHash, consentType, 0, policyVersion, metadataHash)
      )
        .to.emit(registry, "ConsentRecorded")
        .withArgs(personaHash, consentType, 0, policyVersion, metadataHash, anyValue => true);

      const consent = await registry.getConsent(personaHash);
      expect(consent.personaHash).to.equal(personaHash);
      expect(consent.consentType).to.equal(consentType);
      expect(consent.status).to.equal(0); // ConsentStatus.GRANTED
      expect(consent.policyVersion).to.equal(policyVersion);
      expect(consent.metadataHash).to.equal(metadataHash);
    });

    it("Should revoke consent correctly and emit event", async function () {
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));
      await registry.registerConsent(
        personaHash,
        "all",
        0,
        "v1",
        ethers.keccak256(ethers.toUtf8Bytes("meta-1"))
      );

      await expect(registry.revokeConsent(personaHash))
        .to.emit(registry, "ConsentRevoked")
        .withArgs(personaHash, anyValue => true);

      const consent = await registry.getConsent(personaHash);
      expect(consent.status).to.equal(1); // ConsentStatus.REVOKED
    });

    it("Should fail to revoke if no consent record exists", async function () {
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("non-existent"));
      await expect(registry.revokeConsent(personaHash)).to.be.revertedWith("No consent record found");
    });
  });

  describe("Memory Registration", function () {
    it("Should register memory facts and track versions", async function () {
      const memoryId = "mem-101";
      const memoryHash1 = ethers.keccak256(ethers.toUtf8Bytes("fact-v1"));
      const memoryHash2 = ethers.keccak256(ethers.toUtf8Bytes("fact-v2"));
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));

      // Version 1
      await expect(registry.registerMemory(memoryId, memoryHash1, personaHash))
        .to.emit(registry, "MemoryRegistered")
        .withArgs(memoryId, 1, memoryHash1, personaHash, anyValue => true);

      // Version 2
      await expect(registry.registerMemory(memoryId, memoryHash2, personaHash))
        .to.emit(registry, "MemoryRegistered")
        .withArgs(memoryId, 2, memoryHash2, personaHash, anyValue => true);

      expect(await registry.getMemoryVersionCount(memoryId)).to.equal(2);

      const mem1 = await registry.getMemory(memoryId, 1);
      expect(mem1.memoryVersion).to.equal(1);
      expect(mem1.memoryHash).to.equal(memoryHash1);

      const mem2 = await registry.getMemory(memoryId, 2);
      expect(mem2.memoryVersion).to.equal(2);
      expect(mem2.memoryHash).to.equal(memoryHash2);
    });
  });

  describe("AI Response Provenance", function () {
    it("Should register AI response hashes", async function () {
      const responseHash = ethers.keccak256(ethers.toUtf8Bytes("resp-1"));
      const modelHash = ethers.keccak256(ethers.toUtf8Bytes("llama-model-v1"));
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));
      const memoryVersion = 3;

      await expect(registry.registerResponse(responseHash, modelHash, personaHash, memoryVersion))
        .to.emit(registry, "ResponseRegistered")
        .withArgs(responseHash, modelHash, personaHash, memoryVersion, anyValue => true);

      const resp = await registry.getResponse(responseHash);
      expect(resp.responseHash).to.equal(responseHash);
      expect(resp.modelHash).to.equal(modelHash);
      expect(resp.personaHash).to.equal(personaHash);
      expect(resp.memoryVersion).to.equal(memoryVersion);
    });
  });

  describe("Model / Persona Versioning", function () {
    it("Should register config versions", async function () {
      const versionId = "P-001";
      const configHash = ethers.keccak256(ethers.toUtf8Bytes("config-data-1"));

      await expect(registry.registerVersion(versionId, configHash))
        .to.emit(registry, "VersionRegistered")
        .withArgs(versionId, configHash, anyValue => true);

      const ver = await registry.getVersion(versionId);
      expect(ver.versionIdentifier).to.equal(versionId);
      expect(ver.configHash).to.equal(configHash);
    });
  });

  describe("Only Owner Restriction", function () {
    it("Should revert if non-owner registers consent", async function () {
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));
      const metadataHash = ethers.keccak256(ethers.toUtf8Bytes("meta-1"));
      await expect(
        registry.connect(addr1).registerConsent(personaHash, "all", 0, "v1", metadataHash)
      ).to.be.revertedWith("Only owner can call this function");
    });
  });

  describe("Memory Batch Registration", function () {
    it("Should register batch of memories in a single transaction", async function () {
      const memoryIds = ["mem-batch-1", "mem-batch-2"];
      const memoryHashes = [
        ethers.keccak256(ethers.toUtf8Bytes("batch-fact-1")),
        ethers.keccak256(ethers.toUtf8Bytes("batch-fact-2"))
      ];
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));

      await expect(registry.registerMemoryBatch(memoryIds, memoryHashes, personaHash))
        .to.emit(registry, "MemoryBatchRegistered")
        .withArgs(memoryIds, memoryHashes, personaHash, anyValue => true);

      expect(await registry.getMemoryVersionCount("mem-batch-1")).to.equal(1);
      expect(await registry.getMemoryVersionCount("mem-batch-2")).to.equal(1);

      const mem1 = await registry.getMemory("mem-batch-1", 1);
      expect(mem1.memoryHash).to.equal(memoryHashes[0]);

      const mem2 = await registry.getMemory("mem-batch-2", 1);
      expect(mem2.memoryHash).to.equal(memoryHashes[1]);
    });

    it("Should revert if arrays length mismatch", async function () {
      const memoryIds = ["mem-batch-1"];
      const memoryHashes = [
        ethers.keccak256(ethers.toUtf8Bytes("batch-fact-1")),
        ethers.keccak256(ethers.toUtf8Bytes("batch-fact-2"))
      ];
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));

      await expect(
        registry.registerMemoryBatch(memoryIds, memoryHashes, personaHash)
      ).to.be.revertedWith("Arrays length mismatch");
    });
  });

  describe("Data Erasure Recording", function () {
    it("Should record data erasure events", async function () {
      const personaHash = ethers.keccak256(ethers.toUtf8Bytes("prem-persona-1"));
      const erasureHash = ethers.keccak256(ethers.toUtf8Bytes("wipe-event-1"));

      await expect(registry.registerDataErasure(personaHash, erasureHash))
        .to.emit(registry, "DataErasureRecorded")
        .withArgs(personaHash, erasureHash, anyValue => true);

      const erasure = await registry.getErasure(erasureHash);
      expect(erasure.personaHash).to.equal(personaHash);
      expect(erasure.erasureHash).to.equal(erasureHash);
    });
  });
});
