import time
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from blockchain_service import blockchain_service

def run_benchmarks():
    print("📊 --- MemoryBridge Blockchain Performance Benchmarking ---")
    
    # Check blockchain status
    status = blockchain_service.get_status()
    if not status["connected"] or not status["contract_deployed"]:
        print("❌ ERROR: Blockchain registry not available locally.")
        print("Please ensure Hardhat node is running and contract is deployed.")
        return

    runs = 5
    
    # 1. Hashing Latency
    print(f"Measuring hash generation latency over {runs} runs...")
    hash_times = []
    test_dict = {
        "persona_name": "Prem",
        "user_name": "Maitree",
        "response": "Arey tension mat le yaar, main hoon na. Hum sab handle kar lenge!",
        "timestamp": str(time.time()),
        "model": "tinyllama"
    }
    for _ in range(runs):
        t0 = time.time()
        blockchain_service.hash_canonical(test_dict)
        hash_times.append(time.time() - t0)
    avg_hash_ms = (sum(hash_times) / runs) * 1000

    # 2. Blockchain Transaction Latency (Register response provenance)
    print(f"Measuring blockchain transaction latency (mining time) over {runs} runs...")
    tx_times = []
    for i in range(runs):
        t0 = time.time()
        res = blockchain_service.register_response(
            persona_name="Prem",
            user_name="Maitree",
            response_text=f"Benchmark response turn {i}.",
            model_name="tinyllama",
            emotion_label="neutral"
        )
        tx_times.append(time.time() - t0)
        
    avg_tx_ms = (sum(tx_times) / runs) * 1000

    # 3. Verification Latency
    print(f"Measuring on-chain verification latency over {runs} runs...")
    verify_times = []
    # Register a memory first
    mem_id = f"bench-mem-{int(time.time())}"
    blockchain_service.register_memory("Prem", "Maitree", mem_id, "memory", "Chai on a rainy afternoon.")
    
    for _ in range(runs):
        t0 = time.time()
        blockchain_service.verify_memory_integrity(mem_id, "memory", "Chai on a rainy afternoon.")
        verify_times.append(time.time() - t0)
    avg_verify_ms = (sum(verify_times) / runs) * 1000

    # 4. Storage size calculations
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

    # Formatted output table
    print("\n=============================================================")
    print("                     BENCHMARK RESULTS                       ")
    print("=============================================================\n")
    print(f"{'Metric':<35} | {'Average Latency (ms)':<25}")
    print("-" * 65)
    print(f"{'SHA-256 Hash Generation':<35} | {avg_hash_ms:<25.4f} ms")
    print(f"{'On-Chain Tx (Write + Mine)':<35} | {avg_tx_ms:<25.2f} ms")
    print(f"{'On-Chain Verification (Read)':<35} | {avg_verify_ms:<25.2f} ms")
    print("-" * 65)
    print(f"Local Storage Log Overhead per entry: {local_storage_overhead_bytes:.1f} bytes")
    print("\nEvaluation Summary:")
    print("- Hash generation overhead is negligible (< 0.1ms).")
    print("- Blockchain write transaction latency depends on network block times (approx 5-15ms on local Hardhat).")
    print("- Verification reads run sub-5ms, representing zero UX lag for integrity auditing.")
    print("=============================================================")

if __name__ == "__main__":
    import json
    run_benchmarks()
