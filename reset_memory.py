#!/usr/bin/env python3
"""
Reset script to clean up old memory files and reinitialize for new system.
Run this once to fix mismatch issues.

Usage:
    python reset_memory.py
"""

import os

def reset_memory():
    """Clean up old files and prepare for new knowledge base system."""
    print("\n" + "="*60)
    print("🧹 RESETTING MEMORY SYSTEM")
    print("="*60 + "\n")
    
    old_files = [
        "memory_index.faiss",         # FAISS index
        "memory_log.json",            # Conversation history
        "prem_knowledge_base.json",   # Current knowledge base persistence
    ]
    
    for filename in old_files:
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"✅ Deleted: {filename}")
            except Exception as e:
                print(f"❌ Failed to delete {filename}: {e}")
        else:
            print(f"⏭️  {filename} doesn't exist (already clean)")

    # Optional: clear generated audio artifacts (non-source outputs)
    gen_audio_dir = "generated_audio"
    if os.path.isdir(gen_audio_dir):
        try:
            for name in os.listdir(gen_audio_dir):
                if name.lower().endswith(".wav"):
                    os.remove(os.path.join(gen_audio_dir, name))
            print(f"✅ Cleared: {gen_audio_dir}/*.wav")
        except Exception as e:
            print(f"⚠️ Failed to clear generated audio: {e}")
    
    print("\n" + "="*60)
    print("✅ MEMORY SYSTEM RESET COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. python setup_prem_knowledge.py   (populate knowledge base)")
    print("2. python server.py                 (start server)")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    reset_memory()
