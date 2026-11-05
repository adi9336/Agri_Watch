"""
Integration tests for Agri_watch FastAPI Backend and React SPA serving.
"""
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from fastapi.testclient import TestClient
from backend.app import app

class TestAgriWatchBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_spa_root_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Agri-Watch" in response.text or "root" in response.text)
        self.assertTrue("<!doctype html>" in response.text.lower())

    def test_api_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["status"], ["online", "ok"])
        self.assertIn("providers", data)

    def test_api_metadata(self):
        response = self.client.get("/api/metadata")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("crops", data)
        self.assertIn("mandis", data)
        self.assertGreater(len(data["crops"]), 0)

    def test_api_price_kalyan_chana(self):
        response = self.client.get("/api/price?crop=Gram&district=Thane")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["modal_price"], 8500)

    def test_api_token_generation(self):
        response = self.client.post("/api/token", json={"identity": "test-farmer", "room": "agriwatch-test"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["identity"], "test-farmer")
        self.assertEqual(data["room"], "agriwatch-test")
        self.assertGreater(len(data["token"]), 20)

    def test_api_chat(self):
        response = self.client.post("/api/chat", json={"message": "झांसी में गेहूं का भाव क्या है?", "session_context": {}})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("response", data)
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["response"]) > 5)

if __name__ == "__main__":
    unittest.main()

