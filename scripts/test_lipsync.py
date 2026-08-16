import os
import unittest
import wave
import struct
import json
from lipsync_service import lipsync_service

class TestLipSyncService(unittest.TestCase):
    def setUp(self):
        self.test_wav = "test_speech_dummy.wav"
        self.test_json = "test_speech_dummy.json"
        
        # Create a dummy WAV file (16kHz, mono, 0.5s of silent samples)
        with wave.open(self.test_wav, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            # Write 8000 frames (0.5 seconds) of silence
            for _ in range(8000):
                wav_file.writeframes(struct.pack('<h', 0))

    def tearDown(self):
        # Clean up files
        if os.path.exists(self.test_wav):
            os.remove(self.test_wav)
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def test_rhubarb_installation(self):
        self.assertIsNotNone(lipsync_service.rhubarb_bin)
        self.assertTrue(os.path.exists(lipsync_service.rhubarb_bin))

    def test_viseme_generation(self):
        cues = lipsync_service.generate_visemes(self.test_wav)
        self.assertIsNotNone(cues)
        self.assertIn("mouthCues", cues)
        
        # Verify JSON file was created next to WAV
        self.assertTrue(os.path.exists(self.test_json))
        
        # Check standard properties
        with open(self.test_json, 'r') as f:
            data = json.load(f)
            self.assertIn("mouthCues", data)
            
            # Since the file is silent, it should typically return a sequence ending in REST (X)
            cues_list = data["mouthCues"]
            self.assertTrue(len(cues_list) > 0)
            self.assertEqual(cues_list[-1]["value"], "X")

if __name__ == '__main__':
    unittest.main()
