import unittest
import json
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from blockchain_service import blockchain_service, BlockchainService

class TestBlockchainService(unittest.TestCase):
    def setUp(self):
        # We ensure records file is isolated or we back it up
        self.original_records_path = blockchain_service.records_path
        blockchain_service.records_path = "blockchain_records_test.json"
        
        self.persona_name = "TestPrem"
        self.user_name = "TestMaitree"

    def tearDown(self):
        if os.path.exists("blockchain_records_test.json"):
            os.remove("blockchain_records_test.json")
        blockchain_service.records_path = self.original_records_path

    def test_canonical_hashing(self):
        # Deterministic hashing test
        data1 = {"a": 1, "b": [1, 2, 3], "c": {"d": "hello"}}
        data2 = {"c": {"d": "hello"}, "b": [1, 2, 3], "a": 1}
        
        hash1 = blockchain_service.hash_canonical(data1)
        hash2 = blockchain_service.hash_canonical(data2)
        
        self.assertEqual(hash1, hash2)
        self.assertTrue(hash1.startswith("0x"))
        self.assertEqual(len(hash1), 66) # 0x + 64 hex characters

    def test_blockchain_connectivity_and_status(self):
        status = blockchain_service.get_status()
        self.assertIn("connected", status)
        if status["connected"]:
            self.assertTrue(blockchain_service.is_healthy())
            self.assertIsNotNone(blockchain_service.contract_address)
            self.assertIsNotNone(blockchain_service.contract)
        else:
            self.assertFalse(blockchain_service.is_healthy())

    def test_consent_lifecycle(self):
        # If blockchain is offline, this test skips or runs in offline mode
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain lifecycle test.")

        # 1. Register Consent
        res = blockchain_service.register_consent(
            persona_name=self.persona_name,
            user_name=self.user_name,
            consent_type="all",
            policy_version="v1",
            permitted_modes="Text & Voice"
        )
        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["tx_hash"])
        
        # 2. Get Consent from Blockchain
        consent = blockchain_service.get_consent(self.persona_name, self.user_name)
        self.assertIsNotNone(consent)
        self.assertEqual(consent["consent_type"], "all")
        self.assertEqual(consent["status"], "GRANTED")
        self.assertEqual(consent["policy_version"], "v1")

        # 3. Revoke Consent
        rev_res = blockchain_service.revoke_consent(self.persona_name, self.user_name)
        self.assertEqual(rev_res["status"], "success")
        self.assertIsNotNone(rev_res["tx_hash"])

        # 4. Verify Revocation State
        revoked_consent = blockchain_service.get_consent(self.persona_name, self.user_name)
        self.assertEqual(revoked_consent["status"], "REVOKED")

    def test_memory_provenance_and_verification(self):
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain lifecycle test.")

        memory_id = f"test-mem-{int(time.time())}"
        category = "memory"
        detail = "TestPrem loved walking in the autumn leaves."

        # Register Memory
        res = blockchain_service.register_memory(
            persona_name=self.persona_name,
            user_name=self.user_name,
            memory_id=memory_id,
            category=category,
            detail=detail
        )
        self.assertEqual(res["status"], "success")

        # Verify Integrity
        verify_res = blockchain_service.verify_memory_integrity(memory_id, category, detail)
        self.assertEqual(verify_res["status"], "VERIFIED")
        self.assertEqual(verify_res["version"], 1)

        # Tampering Simulation
        tampered_detail = "TestPrem hated walking in the autumn leaves."
        tampered_verify_res = blockchain_service.verify_memory_integrity(memory_id, category, tampered_detail)
        self.assertEqual(tampered_verify_res["status"], "TAMPERING_DETECTED")

    def test_response_provenance(self):
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain lifecycle test.")

        response_text = "I am always with you, Maitree."
        model_name = "test-model-1"
        emotion_label = "joy"
        
        res = blockchain_service.register_response(
            persona_name=self.persona_name,
            user_name=self.user_name,
            response_text=response_text,
            model_name=model_name,
            emotion_label=emotion_label,
            memory_version=1
        )
        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["tx_hash"])

if __name__ == "__main__":
    unittest.main()
