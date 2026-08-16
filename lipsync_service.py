import os
import sys
import zipfile
import urllib.request
import subprocess
import json
import shutil
import logging

logger = logging.getLogger("voice_chat.lipsync")

class LipSyncService:
    def __init__(self, install_dir="bin"):
        self.install_dir = os.path.abspath(install_dir)
        self.rhubarb_dir = os.path.join(self.install_dir, "rhubarb-cli")
        self.rhubarb_bin = None
        self._ensure_rhubarb_installed()

    def _ensure_rhubarb_installed(self):
        """Check if Rhubarb CLI is installed. If not, download and configure it."""
        # Search for rhubarb executable in the rhubarb directory
        if os.path.isdir(self.rhubarb_dir):
            for root, dirs, files in os.walk(self.rhubarb_dir):
                if "rhubarb" in files:
                    potential_bin = os.path.join(root, "rhubarb")
                    # Check if it has execution permissions or try to run --version
                    try:
                        res = subprocess.run([potential_bin, "--version"], capture_output=True, text=True)
                        if res.returncode == 0 or "Rhubarb Lip Sync" in res.stdout:
                            self.rhubarb_bin = potential_bin
                            logger.info(f"Rhubarb CLI binary found: {self.rhubarb_bin}")
                            return
                    except Exception:
                        pass

        # If not found or run failed, download it
        logger.info("Rhubarb CLI not found or invalid. Initializing automatic download...")
        os.makedirs(self.install_dir, exist_ok=True)
        
        # Download Linux ZIP release (Rhubarb v1.13.0)
        zip_url = "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/Rhubarb-Lip-Sync-1.13.0-Linux.zip"
        zip_path = os.path.join(self.install_dir, "rhubarb_linux.zip")
        
        try:
            print(f"📥 Downloading Rhubarb Lip Sync from: {zip_url}")
            with urllib.request.urlopen(zip_url) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            print("📦 Extracting Rhubarb Lip Sync binary...")
            
            # Extract ZIP
            if os.path.exists(self.rhubarb_dir):
                shutil.rmtree(self.rhubarb_dir)
            os.makedirs(self.rhubarb_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.rhubarb_dir)
            
            os.remove(zip_path) # Clean up zip
            
            # Locate binary and chmod +x
            for root, dirs, files in os.walk(self.rhubarb_dir):
                if "rhubarb" in files:
                    bin_path = os.path.join(root, "rhubarb")
                    # Make executable
                    os.chmod(bin_path, 0o755)
                    # Also make files in bin/ folder executable if they exist (sometimes dynamic libs or helpers are present)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o755)
                    self.rhubarb_bin = bin_path
                    print(f"✅ Rhubarb Lip Sync installed successfully at: {self.rhubarb_bin}")
                    return
            
            raise RuntimeError("Rhubarb executable not found in the extracted files.")
            
        except Exception as e:
            logger.error(f"Failed to install Rhubarb Lip Sync: {e}")
            print(f"❌ Failed to install Rhubarb Lip Sync: {e}")
            self.rhubarb_bin = None

    def generate_visemes(self, audio_path):
        """Analyze a WAV audio file and generate viseme mouth cue json logs."""
        if not self.rhubarb_bin:
            logger.warning("Rhubarb binary not available. Cannot generate visemes.")
            return None

        if not os.path.exists(audio_path):
            logger.error(f"Audio file does not exist: {audio_path}")
            return None

        # Output JSON target path next to WAV file
        base_path, _ = os.path.splitext(audio_path)
        json_path = base_path + ".json"

        # If already cached, load and return
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cached visemes from {json_path}: {e}")

        # Run Rhubarb CLI
        logger.info(f"Running Rhubarb Lip Sync on: {audio_path}")
        try:
            # Command: rhubarb -f json -o output.json input.wav
            cmd = [self.rhubarb_bin, "-f", "json", "-o", json_path, audio_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if res.returncode != 0:
                logger.error(f"Rhubarb execution failed (code {res.returncode}): {res.stderr}")
                return None
                
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Viseme generation complete: {len(data.get('mouthCues', []))} cues generated.")
                return data
                
        except subprocess.TimeoutExpired:
            logger.error(f"Rhubarb lip sync timed out for: {audio_path}")
        except Exception as e:
            logger.error(f"Error during Rhubarb Viseme generation: {e}")

        return None

# Singleton Instance
lipsync_service = LipSyncService()
