#!/usr/bin/env python3
"""
Diagnostic script to check if model.glb exists and is accessible.
"""

import os
import sys

def check_model():
    print("\n" + "="*60)
    print("🔍 3D MODEL DIAGNOSTICS")
    print("="*60 + "\n")
    
    model_path = "static/model.glb"
    
    print(f"📁 Checking for GLB model at: {model_path}")
    
    if os.path.exists(model_path):
        size = os.path.getsize(model_path)
        print(f"✅ Model file found!")
        print(f"   Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
        print(f"   Path: {os.path.abspath(model_path)}")
        print(f"   Format: GLTF Binary (GLB)")
    else:
        print(f"⚠️  Model file NOT found at {model_path}")
        print(f"\n   Expected: {os.path.abspath(model_path)}")
        print(f"   Current dir: {os.getcwd()}")
        print("\n   Files in static/:")
        if os.path.exists("static"):
            for f in os.listdir("static"):
                print(f"     - {f}")
        return False
    
    print("\n" + "="*60)
    print("🌐 SERVER ROUTING:")
    print("="*60)
    print("\nThe server will serve model.glb from:")
    print("  Route: /model.glb")
    print("  Type: model/gltf-binary (MIME type)")
    print("\nBrowser will load from:")
    print("  fetch('/model.glb')")
    
    print("\n" + "="*60)
    print("✅ TROUBLESHOOTING:")
    print("="*60)
    print("""
If model still doesn't show in chat:
1. Restart server: python3 server.py
2. Open browser DevTools (F12)
3. Check Console tab for 3D model logs
4. Check Network tab → filter by 'model.glb' → should be 200
5. If 404: File doesn't exist, check path and filename

GLB Benefits over FBX:
- ✅ Smaller file size
- ✅ Better web browser support (standard GLTF format)
- ✅ Includes materials and textures
- ✅ Better animation support
- ✅ Loads faster

To convert FBX to GLB:
- Use Blender: File → Export as GLB
- Online: model3d.cs.technology (upload FBX, download GLB)
""")
    
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    check_model()

