import os
import json
import sys
import hashlib
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from blockchain_service import blockchain_service
from memory_store import MemoryStore

def run_tampering_demo():
    print("[TRUST] --- MemoryBridge Blockchain Batching & Tamper Detection Demo ---")
    
    # 1. Connect to Blockchain
    status = blockchain_service.get_status()
    if not status["connected"] or not status["contract_deployed"]:
        print("[ERROR] Blockchain registry not available locally.")
        print("Please ensure Hardhat node is running and the contract is deployed.")
        return
        
    print("[SUCCESS] Blockchain Connected and Contract Loaded.")
    
    # Initialize clean MemoryStore
    print("[MEMORY] Initializing Memory Store...")
    memory = MemoryStore()
    
    # 2. Add multiple memory segments locally
    persona_name = "Prem"
    user_name = "User"
    
    memories = [
        {"category": "memory", "detail": "Prem loved listening to poetry on rainy afternoons."},
        {"category": "likes", "detail": "Prem preferred strong ginger tea over sweet coffee."}
    ]
    
    fact_ids = []
    memories_to_batch = []
    
    for mem in memories:
        print(f"[MEMORY] Adding local fact: [{mem['category'].upper()}] \"{mem['detail']}\"")
        fid = memory.add_fact(mem["category"], mem["detail"])
        if not fid:
            print("[ERROR] Failed to add fact.")
            return
        fact_ids.append(fid)
        memories_to_batch.append({
            "memory_id": fid,
            "category": mem["category"],
            "detail": mem["detail"]
        })
        print(f"   Assigned Local ID: {fid}")
        
    # 3. Register batch on-chain in a SINGLE transaction
    print("\n[BLOCKCHAIN] Registering memory facts in a SINGLE batch transaction...")
    batch_res = blockchain_service.register_memory_batch(
        persona_name=persona_name,
        user_name=user_name,
        memories=memories_to_batch
    )
    print(f"[SUCCESS] Batch transaction submitted successfully!")
    print(f"  Tx Hash:    {batch_res.get('tx_hash')}")
    print(f"  Batch Hash: {batch_res.get('batch_hash')}")
    
    # 4. Verify Integrity (BEFORE)
    print("\n[VERIFICATION] --- STEP 4: VERIFY INTEGRITY (BEFORE TAMPERING) ---")
    for fid, mem in zip(fact_ids, memories):
        verify_before = blockchain_service.verify_memory_integrity(fid, mem["category"], mem["detail"])
        print(f"Memory ID: {fid}")
        print(f"  Local Hash:      {verify_before['local_hash']}")
        print(f"  Blockchain Hash: {verify_before['blockchain_hash']}")
        print(f"  Status:          {verify_before['status']}")
        
    # 5. Tamper with one local fact directly in JSON
    print("\n[WARNING] --- STEP 5: SIMULATING UNLAWFUL TAMPERING (DIRECT JSON EDIT OF FACT #1) ---")
    print(f"Editing {memory.log_path} directly to alter Fact 1...")
    
    with open(memory.log_path, "r", encoding="utf-8") as f:
        kb_data = json.load(f)
        
    for fact in kb_data:
        if fact.get("id") == fact_ids[0]:
            fact["detail"] = "Prem hated poetry and always turned off the radio."
            break
            
    with open(memory.log_path, "w", encoding="utf-8") as f:
        json.dump(kb_data, f, indent=4, ensure_ascii=False)
        
    print("[WARNING] Local JSON memory file has been modified.")
    
    # 6. Verify Integrity (AFTER)
    print("\n[VERIFICATION] --- STEP 6: VERIFY INTEGRITY (AFTER TAMPERING) ---")
    tampered_memory = MemoryStore()
    
    for fid, mem in zip(fact_ids, memories):
        tampered_fact = next((f for f in tampered_memory.list_all_facts() if f.get("id") == fid), None)
        if tampered_fact:
            verify_after = blockchain_service.verify_memory_integrity(
                fid, 
                tampered_fact["category"], 
                tampered_fact["detail"]
            )
            print(f"Memory ID: {fid}")
            print(f"  Local Hash:      {verify_after['local_hash']}")
            print(f"  Blockchain Hash: {verify_after['blockchain_hash']}")
            
            if verify_after["status"] == "TAMPERING_DETECTED":
                print("  [ALERT] RESULT: MEMORY INTEGRITY FAILURE - TAMPERING DETECTED")
            elif verify_after["status"] == "VERIFIED":
                print("  [SUCCESS] RESULT: MEMORY INTEGRITY SECURE - NO TAMPERING")
        else:
            print(f"[ERROR] Error: Could not load fact {fid}")
            
    # 7. Record Data Erasure event on-chain
    print("\n[ERASURE] --- STEP 7: RECORDING DATA ERASURE ON-CHAIN & WIPING LOCAL CACHES ---")
    erasure_res = blockchain_service.register_data_erasure(persona_name, user_name)
    print(f"[SUCCESS] Erasure transaction submitted. Tx Hash: {erasure_res.get('tx_hash')}")
    print(f"  Erasure Hash on contract: {erasure_res.get('erasure_hash')}")
    
    # Query Erasure Proof from contract
    proof = blockchain_service.get_erasure(erasure_res["erasure_hash"])
    if proof:
        print(f"[SUCCESS] Blockchain Erasure Proof Query SUCCESS:")
        print(f"  Persona Hash: {proof['persona_hash']}")
        print(f"  Erasure Hash: {proof['erasure_hash']}")
        print(f"  Timestamp:    {proof['timestamp']}")
    else:
        print("[ERROR] Failed to query erasure proof from contract.")

    # 8. Restore Database to Clean State
    print("\n[CLEANUP] --- STEP 8: RESTORING CLEAN DATA & REBUILDING FAISS INDEX ---")
    with open(memory.log_path, "r", encoding="utf-8") as f:
        kb_data = json.load(f)
        
    clean_kb = [f for f in kb_data if f.get("id") not in fact_ids]
    
    with open(memory.log_path, "w", encoding="utf-8") as f:
        json.dump(clean_kb, f, indent=4, ensure_ascii=False)
        
    restored_memory = MemoryStore()
    restored_memory.rebuild_index()
    print("[SUCCESS] System successfully restored to clean state.")

if __name__ == "__main__":
    run_tampering_demo()
