import os
import json
import hashlib
import time
import logging
import threading
import uuid
from web3 import Web3

logger = logging.getLogger("voice_chat.blockchain")

# Simple dotenv loader to avoid external dependencies
def load_dotenv():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        os.environ[key] = val

load_dotenv()

class BlockchainService:
    def __init__(self):
        self.provider_url = os.environ.get("BLOCKCHAIN_PROVIDER_URL", "http://127.0.0.1:8545")
        self.private_key = os.environ.get("WALLET_PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80") # Default hardhat key
        self.config_path = "blockchain_config.json"
        self.records_path = "blockchain_records.json"
        
        self.w3 = None
        self.contract = None
        self.contract_address = None
        self.account = None
        self.connected = False
        self.tx_lock = threading.Lock()
        
        self._initialize_web3()

    def _initialize_web3(self):
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
            if self.w3.is_connected():
                self.connected = True
                logger.info(f"Connected to blockchain provider at {self.provider_url}")
                
                # Try loading contract configurations
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r") as f:
                        config = json.load(f)
                    self.contract_address = Web3.to_checksum_address(config["contract_address"])
                    self.contract = self.w3.eth.contract(address=self.contract_address, abi=config["abi"])
                    logger.info(f"Loaded contract configuration. Address: {self.contract_address}")
                else:
                    logger.warning("blockchain_config.json not found. Smart contract interactions will be disabled until contract is deployed.")
                
                # Initialize account
                if self.private_key:
                    if not self.private_key.startswith("0x"):
                        self.private_key = "0x" + self.private_key
                    self.account = self.w3.eth.account.from_key(self.private_key)
                    logger.info(f"Using wallet account: {self.account.address}")
            else:
                logger.warning(f"Failed to connect to blockchain provider at {self.provider_url}. Running in offline fallback mode.")
                self.connected = False
        except Exception as e:
            logger.warning(f"Blockchain initialization error: {e}. Running in offline fallback mode.")
            self.connected = False

    def is_healthy(self):
        if not self.connected or not self.w3:
            return False
        try:
            return self.w3.is_connected()
        except:
            return False

    def get_status(self):
        if not self.is_healthy():
            return {
                "connected": False,
                "provider_url": self.provider_url,
                "contract_address": self.contract_address or "N/A",
                "latest_block": 0,
                "chain_id": 0,
                "contract_deployed": False
            }
        
        try:
            latest_block = self.w3.eth.block_number
            chain_id = self.w3.eth.chain_id
            return {
                "connected": True,
                "provider_url": self.provider_url,
                "contract_address": self.contract_address or "N/A",
                "latest_block": latest_block,
                "chain_id": chain_id,
                "contract_deployed": self.contract is not None
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }

    # Hashing logic
    @staticmethod
    def hash_canonical(data):
        """Deterministically hashes python dictionary metadata using canonical JSON format."""
        canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return "0x" + h

    @staticmethod
    def to_bytes32(hex_str):
        if hex_str.startswith("0x"):
            hex_str = hex_str[2:]
        return bytes.fromhex(hex_str)

    # Local Audit Logger compliant with required event schema
    def log_local_record(self, event_type, status, record_hash, tx_hash=None, block_number=0, details=None):
        records = []
        if os.path.exists(self.records_path):
            try:
                with open(self.records_path, "r") as f:
                    records = json.load(f)
            except:
                records = []
        
        chain_id = 0
        if self.is_healthy():
            try:
                chain_id = self.w3.eth.chain_id
            except:
                pass

        record = {
            "event_id": f"evt_{uuid.uuid4().hex[:8]}",
            "event_type": event_type,
            "chain_id": chain_id,
            "contract_address": self.contract_address or "N/A",
            "contract_version": "1.0.0",
            "transaction_hash": tx_hash or "N/A",
            "block_number": block_number or 0,
            "record_hash": record_hash,
            "status": status,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "details": details or {}
        }
        
        records.append(record)
        try:
            with open(self.records_path, "w") as f:
                json.dump(records, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save local audit log: {e}")
        return record

    # Transactions & Writing
    def _send_transaction(self, contract_func, *args):
        if not self.is_healthy() or not self.contract or not self.account:
            return None, "offline"
            
        with self.tx_lock:
            try:
                func = contract_func(*args)
                nonce = self.w3.eth.get_transaction_count(self.account.address)
                gas_estimate = func.estimate_gas({'from': self.account.address})
                
                tx = func.build_transaction({
                    'chainId': self.w3.eth.chain_id,
                    'gas': int(gas_estimate * 1.2),
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': nonce
                })
                
                signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt.status == 1:
                    return self.w3.to_hex(tx_hash), "success"
                else:
                    return self.w3.to_hex(tx_hash), "failed"
            except Exception as e:
                logger.error(f"Smart contract transaction error: {e}")
                return None, str(e)

    def register_consent(self, persona_name, user_name, consent_type, policy_version, permitted_modes):
        metadata = {
            "persona_name": persona_name,
            "user_name": user_name,
            "consent_type": consent_type,
            "policy_version": policy_version,
            "permitted_modes": permitted_modes,
            "status": "GRANTED"
        }
        meta_hash = self.hash_canonical(metadata)
        persona_id = f"persona-{persona_name}-{user_name}"
        persona_hash = self.hash_canonical({"persona_id": persona_id})
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.registerConsent,
            self.to_bytes32(persona_hash),
            consent_type,
            0, # GRANTED
            policy_version,
            self.to_bytes32(meta_hash)
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass
        
        details = {
            "persona_name": persona_name,
            "user_name": user_name,
            "consent_type": consent_type,
            "policy_version": policy_version,
            "permitted_modes": permitted_modes
        }
        
        self.log_local_record(
            "CONSENT_GRANTED", 
            "CONFIRMED" if status == "success" else "FAILED/OFFLINE", 
            meta_hash, 
            tx_hash, 
            block_number,
            details
        )
        return {"persona_hash": persona_hash, "metadata_hash": meta_hash, "tx_hash": tx_hash, "status": status}

    def revoke_consent(self, persona_name, user_name):
        persona_id = f"persona-{persona_name}-{user_name}"
        persona_hash = self.hash_canonical({"persona_id": persona_id})
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.revokeConsent,
            self.to_bytes32(persona_hash)
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass

        self.log_local_record(
            "CONSENT_REVOKED",
            "CONFIRMED" if status == "success" else "FAILED/OFFLINE",
            persona_hash,
            tx_hash,
            block_number,
            {"persona_name": persona_name, "user_name": user_name}
        )
        return {"persona_hash": persona_hash, "tx_hash": tx_hash, "status": status}

    def register_memory(self, persona_name, user_name, memory_id, category, detail):
        persona_id = f"persona-{persona_name}-{user_name}"
        persona_hash = self.hash_canonical({"persona_id": persona_id})
        
        memory_meta = {
            "memory_id": memory_id,
            "category": category,
            "detail": detail
        }
        mem_hash = self.hash_canonical(memory_meta)
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.registerMemory,
            memory_id,
            self.to_bytes32(mem_hash),
            self.to_bytes32(persona_hash)
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass

        self.log_local_record(
            "MEMORY_REGISTERED",
            "CONFIRMED" if status == "success" else "FAILED/OFFLINE",
            mem_hash,
            tx_hash,
            block_number,
            {"memory_id": memory_id, "category": category, "persona_name": persona_name}
        )
        return {"memory_hash": mem_hash, "tx_hash": tx_hash, "status": status}

    def register_memory_batch(self, persona_name, user_name, memories):
        """Registers a batch of memory items in a single blockchain transaction."""
        persona_id = f"persona-{persona_name}-{user_name}"
        persona_hash = self.hash_canonical({"persona_id": persona_id})
        
        memory_ids = []
        memory_hashes = []
        details = []
        
        for mem in memories:
            mem_id = mem["memory_id"]
            cat = mem["category"]
            det = mem["detail"]
            
            memory_meta = {
                "memory_id": mem_id,
                "category": cat,
                "detail": det
            }
            mem_hash = self.hash_canonical(memory_meta)
            
            memory_ids.append(mem_id)
            memory_hashes.append(self.to_bytes32(mem_hash))
            details.append({
                "memory_id": mem_id,
                "category": cat,
                "hash": mem_hash
            })
            
        batch_hash_input = {"hashes": [self.w3.to_hex(h) if self.w3 else h.hex() for h in memory_hashes]}
        batch_hash = self.hash_canonical(batch_hash_input)
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.registerMemoryBatch,
            memory_ids,
            memory_hashes,
            self.to_bytes32(persona_hash)
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass

        self.log_local_record(
            "MEMORY_BATCH_REGISTERED",
            "CONFIRMED" if status == "success" else "FAILED/OFFLINE",
            batch_hash,
            tx_hash,
            block_number,
            {
                "persona_name": persona_name,
                "user_name": user_name,
                "memories": details
            }
        )
        return {"batch_hash": batch_hash, "tx_hash": tx_hash, "status": status}

    # Worker task for asynchronous Response provenance registration
    def _async_register_response_worker(self, event_id, persona_name, user_name, response_text, model_name, emotion_label, memory_version):
        persona_id = f"persona-{persona_name}-{user_name}"
        persona_hash = self.hash_canonical({"persona_id": persona_id})
        
        resp_meta = {
            "response": response_text,
            "emotion": emotion_label,
            "timestamp": str(time.time())
        }
        resp_hash = self.hash_canonical(resp_meta)
        model_hash = self.hash_canonical({"model_name": model_name})
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.registerResponse,
            self.to_bytes32(resp_hash),
            self.to_bytes32(model_hash),
            self.to_bytes32(persona_hash),
            memory_version
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass
                
        # Update the pending local log record to Confirmed/Failed
        records = []
        if os.path.exists(self.records_path):
            try:
                with open(self.records_path, "r") as f:
                    records = json.load(f)
            except:
                pass
                
        for r in records:
            if r.get("event_id") == event_id:
                r["status"] = "CONFIRMED" if status == "success" else "FAILED"
                r["transaction_hash"] = tx_hash or "N/A"
                r["block_number"] = block_number
                break
                
        try:
            with open(self.records_path, "w") as f:
                json.dump(records, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to update async record: {e}")

    def register_response(self, persona_name, user_name, response_text, model_name, emotion_label, memory_version=0):
        # 1. Generate canonical hashes & local PENDING record immediately
        resp_meta = {
            "response": response_text,
            "emotion": emotion_label,
            "timestamp": str(time.time())
        }
        resp_hash = self.hash_canonical(resp_meta)
        
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        details = {
            "model_name": model_name,
            "emotion": emotion_label,
            "memory_version": memory_version,
            "persona_name": persona_name,
            "user_name": user_name
        }
        
        records = []
        if os.path.exists(self.records_path):
            try:
                with open(self.records_path, "r") as f:
                    records = json.load(f)
            except:
                pass
                
        chain_id = 0
        if self.is_healthy():
            try:
                chain_id = self.w3.eth.chain_id
            except:
                pass
                
        record = {
            "event_id": event_id,
            "event_type": "RESPONSE_PROVENANCE_REGISTERED",
            "chain_id": chain_id,
            "contract_address": self.contract_address or "N/A",
            "contract_version": "1.0.0",
            "transaction_hash": "N/A",
            "block_number": 0,
            "record_hash": resp_hash,
            "status": "PENDING",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "details": details
        }
        records.append(record)
        try:
            with open(self.records_path, "w") as f:
                json.dump(records, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to log initial pending record: {e}")
            
        # 2. Fire non-blocking transaction thread
        t = threading.Thread(
            target=self._async_register_response_worker,
            args=(event_id, persona_name, user_name, response_text, model_name, emotion_label, memory_version)
        )
        t.daemon = True
        t.start()
        
        return {"response_hash": resp_hash, "event_id": event_id, "status": "PENDING"}

    def register_version(self, version_id, config_details):
        config_hash = self.hash_canonical(config_details)
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.registerVersion,
            version_id,
            self.to_bytes32(config_hash)
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass
        
        self.log_local_record(
            "MODEL_VERSION_REGISTERED",
            "CONFIRMED" if status == "success" else "FAILED/OFFLINE",
            config_hash,
            tx_hash,
            block_number,
            {"version_id": version_id}
        )
        return {"config_hash": config_hash, "tx_hash": tx_hash, "status": status}

    def register_data_erasure(self, persona_name, user_name, erasure_details=None):
        persona_id = f"persona-{persona_name}-{user_name}"
        persona_hash = self.hash_canonical({"persona_id": persona_id})
        
        erasure_meta = erasure_details or {
            "event": "DATA_ERASURE",
            "persona_id": persona_id,
            "timestamp": str(time.time())
        }
        erasure_hash = self.hash_canonical(erasure_meta)
        
        tx_hash, status = self._send_transaction(
            self.contract.functions.registerDataErasure,
            self.to_bytes32(persona_hash),
            self.to_bytes32(erasure_hash)
        ) if self.contract else (None, "offline")
        
        block_number = 0
        if status == "success" and tx_hash:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_number = receipt.blockNumber
            except:
                pass

        self.log_local_record(
            "DATA_ERASURE_RECORDED",
            "CONFIRMED" if status == "success" else "FAILED/OFFLINE",
            erasure_hash,
            tx_hash,
            block_number,
            {"persona_name": persona_name, "user_name": user_name, "erasure_details": erasure_meta}
        )
        return {"erasure_hash": erasure_hash, "tx_hash": tx_hash, "status": status}

    # Reading & Verifying
    def get_consent(self, persona_name, user_name):
        if not self.is_healthy() or not self.contract:
            return None
        try:
            persona_id = f"persona-{persona_name}-{user_name}"
            persona_hash = self.hash_canonical({"persona_id": persona_id})
            res = self.contract.functions.getConsent(self.to_bytes32(persona_hash)).call()
            if res[5] == 0: # timestamp is 0 means not found
                return None
            return {
                "persona_hash": "0x" + res[0].hex(),
                "consent_type": res[1],
                "status": ["GRANTED", "REVOKED", "EXPIRED"][res[2]],
                "policy_version": res[3],
                "metadata_hash": "0x" + res[4].hex(),
                "timestamp": res[5]
            }
        except Exception as e:
            logger.error(f"Error fetching consent from blockchain: {e}")
            return None

    def get_memory_version_count(self, memory_id):
        if not self.is_healthy() or not self.contract:
            return 0
        try:
            return self.contract.functions.getMemoryVersionCount(memory_id).call()
        except Exception as e:
            logger.error(f"Error fetching memory version count: {e}")
            return 0

    def get_memory(self, memory_id, version):
        if not self.is_healthy() or not self.contract:
            return None
        try:
            res = self.contract.functions.getMemory(memory_id, version).call()
            return {
                "memory_id": res[0],
                "memory_version": res[1],
                "memory_hash": "0x" + res[2].hex(),
                "timestamp": res[3],
                "persona_hash": "0x" + res[4].hex()
            }
        except Exception as e:
            logger.error(f"Error fetching memory from blockchain: {e}")
            return None

    def get_erasure(self, erasure_hash):
        if not self.is_healthy() or not self.contract:
            return None
        try:
            res = self.contract.functions.getErasure(self.to_bytes32(erasure_hash)).call()
            if res[2] == 0: # timestamp is 0
                return None
            return {
                "persona_hash": "0x" + res[0].hex(),
                "erasure_hash": "0x" + res[1].hex(),
                "timestamp": res[2]
            }
        except Exception as e:
            logger.error(f"Error fetching erasure proof from blockchain: {e}")
            return None

    def verify_memory_integrity(self, memory_id, category, detail):
        memory_meta = {
            "memory_id": memory_id,
            "category": category,
            "detail": detail
        }
        current_hash = self.hash_canonical(memory_meta)
        
        version_count = self.get_memory_version_count(memory_id)
        if version_count == 0:
            return {"status": "UNREGISTERED", "local_hash": current_hash, "blockchain_hash": None}
            
        blockchain_mem = self.get_memory(memory_id, version_count)
        if not blockchain_mem:
            return {"status": "ERROR", "local_hash": current_hash, "blockchain_hash": None}
            
        blockchain_hash = blockchain_mem["memory_hash"]
        verified = (current_hash == blockchain_hash)
        
        self.log_local_record(
            "MEMORY_VERIFIED",
            "CONFIRMED" if verified else "TAMPERING_DETECTED",
            current_hash,
            details={"memory_id": memory_id, "blockchain_hash": blockchain_hash, "local_hash": current_hash}
        )
        return {
            "status": "VERIFIED" if verified else "TAMPERING_DETECTED",
            "local_hash": current_hash,
            "blockchain_hash": blockchain_hash,
            "version": version_count
        }

    def list_audit_trail(self):
        if os.path.exists(self.records_path):
            try:
                with open(self.records_path, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

blockchain_service = BlockchainService()
