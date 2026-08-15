import time
import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from blockchain_service import blockchain_service

def run_benchmarks():
    print("[BENCHMARK] --- MemoryBridge Blockchain Refactored Benchmarking Suite ---")
    
    # Check blockchain status
    status = blockchain_service.get_status()
    if not status["connected"] or not status["contract_deployed"]:
        print("[ERROR] Blockchain registry not available locally.")
        print("Please ensure Hardhat node is running and contract is deployed.")
        return

    runs = 5
    simulated_llm_inference_s = 0.250 # 250ms simulated LLaMA generation time
    
    # 1. SHA-256 Hashing Latency
    print("Measuring local canonical SHA-256 hashing...")
    hash_times = []
    test_dict = {
        "persona_name": "Prem",
        "user_name": "User",
        "response": "Hello, how are you? I am checking the latency impact of blockchain hashes.",
        "timestamp": str(time.time()),
        "model": "llama3"
    }
    for _ in range(10):
        t0 = time.time()
        blockchain_service.hash_canonical(test_dict)
        hash_times.append(time.time() - t0)
    avg_hash_ms = (sum(hash_times) / 10.0) * 1000

    # 2. Chat Response Latency Comparisons
    print(f"\nEvaluating Chat Response Latency over {runs} runs:")
    
    # A. Baseline Chat (No blockchain interaction)
    print("  Measuring Baseline Chat (LLM simulation)...")
    baseline_latencies = []
    for _ in range(runs):
        t0 = time.time()
        # Simulated LLM Inference
        time.sleep(simulated_llm_inference_s)
        baseline_latencies.append(time.time() - t0)
    avg_baseline_ms = (sum(baseline_latencies) / runs) * 1000

    # B. Blockchain-Synchronous (Blocking transaction write)
    print("  Measuring Blockchain-Synchronous Chat (blocking on mine)...")
    sync_latencies = []
    for i in range(runs):
        t0 = time.time()
        # Simulated LLM Inference
        time.sleep(simulated_llm_inference_s)
        
        # Blocking blockchain registration
        persona_id = f"persona-Prem-User"
        persona_hash = blockchain_service.hash_canonical({"persona_id": persona_id})
        resp_hash = blockchain_service.hash_canonical({"response": f"Sync response {i}", "timestamp": str(time.time())})
        model_hash = blockchain_service.hash_canonical({"model_name": "llama3"})
        
        # Call the contract writer synchronously
        tx_hash, status = blockchain_service._send_transaction(
            blockchain_service.contract.functions.registerResponse,
            blockchain_service.to_bytes32(resp_hash),
            blockchain_service.to_bytes32(model_hash),
            blockchain_service.to_bytes32(persona_hash),
            0
        )
        sync_latencies.append(time.time() - t0)
    avg_sync_ms = (sum(sync_latencies) / runs) * 1000

    # C. Blockchain-Asynchronous (Non-blocking background thread)
    print("  Measuring Blockchain-Asynchronous Chat (non-blocking thread)...")
    async_latencies = []
    for i in range(runs):
        t0 = time.time()
        # Simulated LLM Inference
        time.sleep(simulated_llm_inference_s)
        
        # Non-blocking blockchain registration
        blockchain_service.register_response(
            persona_name="Prem",
            user_name="User",
            response_text=f"Async response {i}",
            model_name="llama3",
            emotion_label="neutral"
        )
        async_latencies.append(time.time() - t0)
    avg_async_ms = (sum(async_latencies) / runs) * 1000

    # 3. Memory Batching Efficiency (1 vs 4 transactions)
    print(f"\nEvaluating Memory Registration Efficiency (Individual vs. Batched)...")
    
    test_facts = [
        {"memory_id": f"fid-{i}", "category": "memory", "detail": f"Ginger tea fact {i}"}
        for i in range(4)
    ]
    
    # Individual Writes (4 separate txs)
    print("  Writing 4 memory facts individually...")
    t0 = time.time()
    for fact in test_facts:
        blockchain_service.register_memory("Prem", "User", fact["memory_id"], fact["category"], fact["detail"])
    indiv_time_ms = (time.time() - t0) * 1000

    # Batched Writes (1 batch tx)
    print("  Writing 4 memory facts in a single batch...")
    t0 = time.time()
    blockchain_service.register_memory_batch("Prem", "User", test_facts)
    batch_time_ms = (time.time() - t0) * 1000

    # 4. On-Chain Integrity Verification Read
    print(f"\nMeasuring on-chain verification lookup latency...")
    verify_times = []
    for _ in range(runs):
        t0 = time.time()
        blockchain_service.verify_memory_integrity("fid-0", "memory", "Ginger tea fact 0")
        verify_times.append(time.time() - t0)
    avg_verify_ms = (sum(verify_times) / runs) * 1000

    # 5. Local Storage Size
    local_storage_overhead_bytes = 0
    if os.path.exists("blockchain_records.json"):
        size_bytes = os.path.getsize("blockchain_records.json")
        try:
            with open("blockchain_records.json", "r") as f:
                records = json.load(f)
            if len(records) > 0:
                local_storage_overhead_bytes = size_bytes / len(records)
        except:
            local_storage_overhead_bytes = size_bytes

    # Formatted comparative output table
    print("\n=========================================================================")
    print("                     EVALUATION & BENCHMARK RESULTS                      ")
    print("=========================================================================\n")
    
    print(f"{'Chat Loop Mode':<30} | {'Average Latency (ms)':<22} | {'UX Overhead (ms)':<15}")
    print("-" * 75)
    print(f"{'Baseline Chat (No Blockchain)':<30} | {avg_baseline_ms:<22.2f} | {'0.00 ms (0.0%)':<15}")
    print(f"{'Blockchain-Synchronous (Blocking)':<30} | {avg_sync_ms:<22.2f} | {f'+{avg_sync_ms - avg_baseline_ms:.2f} ms':<15}")
    print(f"{'Blockchain-Asynchronous (Threaded)':<30} | {avg_async_ms:<22.2f} | {f'+{avg_async_ms - avg_baseline_ms:.2f} ms':<15}")
    
    print("\n" + "=" * 75 + "\n")
    print(f"{'Memory Registration Mode (4 Facts)':<35} | {'Total Latency (ms)':<22} | {'Transactions count':<15}")
    print("-" * 75)
    print(f"{'Individual Registrations':<35} | {indiv_time_ms:<22.2f} | {'4 transactions':<15}")
    print(f"{'Batched Registry':<35} | {batch_time_ms:<22.2f} | {'1 transaction':<15}")
    
    print("\n" + "=" * 75 + "\n")
    print(f"{'Verification Operation':<35} | {'Average Latency (ms)':<32}")
    print("-" * 75)
    print(f"{'SHA-256 Hash Generation':<35} | {avg_hash_ms:<32.4f} ms")
    print(f"{'On-Chain Verification Lookup':<35} | {avg_verify_ms:<32.2f} ms")
    print(f"Local Storage Log Overhead per entry: {local_storage_overhead_bytes:.1f} bytes")
    print("=========================================================================")

if __name__ == "__main__":
    run_benchmarks()
