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
        "memory_index.faiss",      # Old FAISS index
        "memory_log.json",         # Old conversation history
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
    
    print("\n" + "="*60)
    print("✅ MEMORY SYSTEM RESET COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. python setup_prem_knowledge.py   (populate knowledge base)")
    print("2. python3 server.py                (start server)")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    reset_memory()
