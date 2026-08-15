import os
import json
import sys
import hashlib
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from blockchain_service import blockchain_service
from memory_store import MemoryStore

def run_tampering_demo():
    print("🔒 --- MemoryBridge Blockchain Tamper Detection Demo ---")
    
    # 1. Connect to Blockchain
    status = blockchain_service.get_status()
    if not status["connected"] or not status["contract_deployed"]:
        print("❌ ERROR: Blockchain registry not available locally.")
        print("Please ensure Hardhat node is running and the contract is deployed.")
        return
        
    print("🟢 Blockchain Connected and Contract Loaded.")
    
    # Initialize clean MemoryStore
    print("🧠 Initializing Memory Store...")
    memory = MemoryStore()
    
    # 2. Add memory segment
    category = "memory"
    detail = "Prem loved listening to poetry on rainy afternoons."
    persona_name = "Prem"
    user_name = "Maitree"
    
    print(f"➕ Adding fact: [{category.upper()}] \"{detail}\"")
    fact_id = memory.add_fact(category, detail)
    if not fact_id:
        print("❌ Failed to add fact.")
        return
        
    print(f"ℹ️ Assigned Local Memory ID: {fact_id}")
    
    # 3. Register on-chain
    print("⛓️ Registering memory hash on-chain...")
    reg_res = blockchain_service.register_memory(
        persona_name=persona_name,
        user_name=user_name,
        memory_id=fact_id,
        category=category,
        detail=detail
    )
    print(f"✓ Transaction submitted. Tx Hash: {reg_res.get('tx_hash')}")
    
    # 4. Verify Integrity (BEFORE)
    print("\n🔍 --- STEP 4: VERIFY INTEGRITY (BEFORE TAMPERING) ---")
    verify_before = blockchain_service.verify_memory_integrity(fact_id, category, detail)
    print(f"Local Hash:      {verify_before['local_hash']}")
    print(f"Blockchain Hash: {verify_before['blockchain_hash']}")
    
    if verify_before["status"] == "VERIFIED":
        print("✅ RESULT: ✓ MEMORY INTEGRITY VERIFIED")
    else:
        print(f"❌ RESULT: Unexpected status: {verify_before['status']}")
        
    # 5. Tamper with local data directly in JSON
    print("\n🛡️ --- STEP 5: SIMULATING UNLAWFUL TAMPERING (DIRECT JSON EDIT) ---")
    print(f"Editing {memory.log_path} directly to alter memory...")
    
    # Load raw JSON
    with open(memory.log_path, "r", encoding="utf-8") as f:
        kb_data = json.load(f)
        
    # Modify the fact's detail
    original_detail = None
    for fact in kb_data:
        if fact.get("id") == fact_id:
            original_detail = fact["detail"]
            fact["detail"] = "Prem hated listening to poetry and preferred silence."
            break
            
    if not original_detail:
        print("❌ Could not find fact in JSON database.")
        return
        
    # Save modified JSON
    with open(memory.log_path, "w", encoding="utf-8") as f:
        json.dump(kb_data, f, indent=4, ensure_ascii=False)
        
    print("⚠️ Local JSON memory file has been modified.")
    
    # 6. Verify Integrity (AFTER)
    print("\n🔍 --- STEP 6: VERIFY INTEGRITY (AFTER TAMPERING) ---")
    # Load facts again using a fresh MemoryStore instance to simulate server reading the file
    tampered_memory = MemoryStore()
    tampered_fact = next((f for f in tampered_memory.list_all_facts() if f.get("id") == fact_id), None)
    
    if tampered_fact:
        verify_after = blockchain_service.verify_memory_integrity(
            fact_id, 
            tampered_fact["category"], 
            tampered_fact["detail"]
        )
        print(f"Local Hash (Tampered): {verify_after['local_hash']}")
        print(f"Blockchain Hash:       {verify_after['blockchain_hash']}")
        
        if verify_after["status"] == "TAMPERING_DETECTED":
            print("🚨 RESULT: ⚠ MEMORY INTEGRITY FAILURE - TAMPERING DETECTED")
        else:
            print(f"❌ RESULT: Unexpected verification outcome: {verify_after['status']}")
    else:
        print("❌ Error: Could not load the tampered fact.")
        
    # 7. Restore Database to Clean State
    print("\n🧼 --- STEP 7: RESTORING CLEAN DATA & REBUILDING FAISS INDEX ---")
    with open(memory.log_path, "r", encoding="utf-8") as f:
        kb_data = json.load(f)
        
    # Remove the added fact entirely to revert DB state
    clean_kb = [f for f in kb_data if f.get("id") != fact_id]
    
    with open(memory.log_path, "w", encoding="utf-8") as f:
        json.dump(clean_kb, f, indent=4, ensure_ascii=False)
        
    # Force rebuild FAISS index from the cleaned JSON
    restored_memory = MemoryStore()
    restored_memory.rebuild_index()
    print("✅ System successfully restored to clean state.")

if __name__ == "__main__":
    run_tampering_demo()
