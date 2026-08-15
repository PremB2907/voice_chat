import unittest
import json
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from blockchain_service import blockchain_service, BlockchainService

class TestBlockchainService(unittest.TestCase):
    def setUp(self):
        # We ensure records file is isolated
        self.original_records_path = blockchain_service.records_path
        blockchain_service.records_path = "blockchain_records_test.json"
        
        self.persona_name = "TestPrem"
        self.user_name = "TestMaitree"

    def tearDown(self):
        if os.path.exists("blockchain_records_test.json"):
            os.remove("blockchain_records_test.json")
        blockchain_service.records_path = self.original_records_path

    def test_canonical_hashing(self):
        data1 = {"a": 1, "b": [1, 2, 3], "c": {"d": "hello"}}
        data2 = {"c": {"d": "hello"}, "b": [1, 2, 3], "a": 1}
        
        hash1 = blockchain_service.hash_canonical(data1)
        hash2 = blockchain_service.hash_canonical(data2)
        
        self.assertEqual(hash1, hash2)
        self.assertTrue(hash1.startswith("0x"))
        self.assertEqual(len(hash1), 66)

    def test_blockchain_connectivity_and_status(self):
        status = blockchain_service.get_status()
        self.assertIn("connected", status)
        if status["connected"]:
            self.assertTrue(blockchain_service.is_healthy())
            self.assertIsNotNone(blockchain_service.contract_address)
        else:
            self.assertFalse(blockchain_service.is_healthy())

    def test_consent_lifecycle(self):
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain test.")

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
        
        # 2. Get Consent
        consent = blockchain_service.get_consent(self.persona_name, self.user_name)
        self.assertIsNotNone(consent)
        self.assertEqual(consent["consent_type"], "all")
        self.assertEqual(consent["status"], "GRANTED")

        # 3. Revoke Consent
        rev_res = blockchain_service.revoke_consent(self.persona_name, self.user_name)
        self.assertEqual(rev_res["status"], "success")

        # 4. Verify Revocation
        revoked = blockchain_service.get_consent(self.persona_name, self.user_name)
        self.assertEqual(revoked["status"], "REVOKED")

    def test_memory_batch_and_verification(self):
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain test.")

        memories = [
            {"memory_id": f"t-mem-1-{int(time.time())}", "category": "memory", "detail": "TestPrem detail 1"},
            {"memory_id": f"t-mem-2-{int(time.time())}", "category": "memory", "detail": "TestPrem detail 2"}
        ]

        # Register Batch
        res = blockchain_service.register_memory_batch(self.persona_name, self.user_name, memories)
        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["tx_hash"])

        # Verify Integrity
        v1 = blockchain_service.verify_memory_integrity(memories[0]["memory_id"], memories[0]["category"], memories[0]["detail"])
        self.assertEqual(v1["status"], "VERIFIED")

        v2 = blockchain_service.verify_memory_integrity(memories[1]["memory_id"], memories[1]["category"], memories[1]["detail"])
        self.assertEqual(v2["status"], "VERIFIED")

    def test_response_provenance_async(self):
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain test.")

        res = blockchain_service.register_response(
            persona_name=self.persona_name,
            user_name=self.user_name,
            response_text="Async test reply text.",
            model_name="test-model",
            emotion_label="neutral",
            memory_version=1
        )
        self.assertEqual(res["status"], "PENDING")
        self.assertIsNotNone(res["event_id"])
        
        # Wait a moment for background worker thread to execute transaction
        time.sleep(2.0)
        
        # Verify the record has updated to CONFIRMED
        trail = blockchain_service.list_audit_trail()
        record = next((r for r in trail if r.get("event_id") == res["event_id"]), None)
        
        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "CONFIRMED")
        self.assertNotEqual(record["transaction_hash"], "N/A")
        self.assertGreater(record["block_number"], 0)

    def test_data_erasure_logging(self):
        status = blockchain_service.get_status()
        if not status["connected"] or not status["contract_deployed"]:
            self.skipTest("Local Hardhat node is not available or contract not deployed. Skipping on-chain test.")

        res = blockchain_service.register_data_erasure(self.persona_name, self.user_name)
        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["tx_hash"])

        # Fetch proof from contract
        proof = blockchain_service.get_erasure(res["erasure_hash"])
        self.assertIsNotNone(proof)
        self.assertEqual(proof["erasure_hash"], res["erasure_hash"])

if __name__ == "__main__":
    unittest.main()
