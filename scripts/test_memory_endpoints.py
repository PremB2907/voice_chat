import json
import unittest
from unittest.mock import patch

import server


class _FakeMemory:
    def __init__(self):
        self.added = []
        self.facts = [
            {"category": "memory", "detail": "Prem loved the lake at sunrise."},
            {"category": "likes", "detail": "Prem liked mangoes."},
        ]

    def add_fact(self, category, detail):
        self.added.append((category, detail))

    def list_all_facts(self):
        return self.facts

    def get_all_facts_by_category(self, category):
        return [f for f in self.facts if f.get("category") == category]

    def get_memory_status(self):
        return {"ok": True, "facts": len(self.facts)}


class TestMemoryEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.client.testing = True

    def test_add_fact_success(self):
        fake_memory = _FakeMemory()
        with patch.object(server, "memory", fake_memory):
            res = self.client.post(
                "/add-fact",
                data=json.dumps({"category": "memory", "detail": "We watched the rain together."}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(fake_memory.added, [("memory", "We watched the rain together.")])

    def test_add_fact_missing_fields(self):
        fake_memory = _FakeMemory()
        with patch.object(server, "memory", fake_memory):
            res = self.client.post(
                "/add-fact",
                data=json.dumps({"detail": "Missing category"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 400)

    def test_get_knowledge_base_all(self):
        fake_memory = _FakeMemory()
        with patch.object(server, "memory", fake_memory):
            res = self.client.get("/get-knowledge-base")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["facts"]), 2)

    def test_get_knowledge_base_filtered(self):
        fake_memory = _FakeMemory()
        with patch.object(server, "memory", fake_memory):
            res = self.client.get("/get-knowledge-base?category=likes")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["facts"][0]["category"], "likes")

    def test_memory_status(self):
        fake_memory = _FakeMemory()
        with patch.object(server, "memory", fake_memory):
            res = self.client.get("/memory-status")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["ok"])


if __name__ == "__main__":
    unittest.main()

