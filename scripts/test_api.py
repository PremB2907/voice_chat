import json
from server import app
import unittest
import os
from unittest.mock import patch

class TestVoiceChatAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_home_route(self):
        # We check if index.html is served (ignoring file content logic specifics, just checks 200)
        # Note: testing static_folder natively in flask sometimes returns 404 if path is empty,
        # but the route `def home(): return app.send_static_file("index.html")` should resolve.
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    @patch('server.get_tts')
    @patch('server.http_requests.post')
    def test_chat_endpoint_success(self, mock_post, mock_get_tts):
        # Mock ollama response
        mock_post.return_value.json.return_value = {
            "message": {
                "content": "I am here, Maitree."
            }
        }
        mock_post.return_value.status_code = 200
        mock_get_tts.return_value.tts_to_file.return_value = None
        
        # Test chat endpoint
        payload = {
            "message": "Hello Prem, I miss you.",
            "mbti": "INFJ",
            "generate_audio": True
        }
        response = self.client.post('/chat', data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("reply", data)
        self.assertIn("audio", data)
        self.assertEqual(data["reply"], "I am here, Maitree.")
        
        # Check if tts was called
        self.assertTrue(mock_get_tts.return_value.tts_to_file.called)

    def test_chat_endpoint_no_message(self):
        payload = {"weird_field": "hello"}
        response = self.client.post('/chat', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    # Ensure generated_audio exists
    os.makedirs("generated_audio", exist_ok=True)
    unittest.main()
