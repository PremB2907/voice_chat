import os
import faiss
import numpy as np
import json
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger("voice_chat.memory")

class MemoryStore:
    def __init__(self, index_path="memory_index.faiss", log_path="prem_knowledge_base.json"):
        self.index_path = index_path
        self.log_path = log_path
        self.model_name = "all-MiniLM-L6-v2"
        self._model = None
        # all-MiniLM-L6-v2 embedding dimension is fixed (384)
        self.dimension = 384
        
        # Knowledge base: stores detailed information ABOUT PREM
        # Format: {"topic": description, "memory": detail, "place": significance, etc.}
        self.knowledge_base = []
        
        # Short-Term Memory (STM) - sliding window for session-specific conversational data
        self.stm_window = []
        self.stm_max_turns = 5
        
        self.index = self._load_or_create_index()
        self._load_knowledge_base()
        self._ensure_index_consistency(rebuild_if_mismatch=True)

    def _get_model(self):
        if self._model is None:
            logger.info("Loading SentenceTransformer model for memory", extra={"model": self.model_name})
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            logger.info("Loading FAISS memory index", extra={"path": self.index_path})
            return faiss.read_index(self.index_path)
        else:
            logger.info("Creating new FAISS memory index", extra={"dimension": self.dimension})
            return faiss.IndexFlatL2(self.dimension)

    def _load_knowledge_base(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
            except:
                self.knowledge_base = []
                self._initialize_default_kb()
        else:
            self._initialize_default_kb()

    def _ensure_index_consistency(self, rebuild_if_mismatch: bool = True):
        """
        Keep FAISS index rows aligned with the knowledge base list order.
        If they diverge (most common after manual file edits or older versions),
        rebuild the index from the KB.
        """
        try:
            kb_len = len(self.knowledge_base)
            idx_len = int(getattr(self.index, "ntotal", 0))
            if kb_len == idx_len:
                return

            logger.warning(
                "Memory mismatch detected",
                extra={"facts": kb_len, "faiss": idx_len, "rebuild": rebuild_if_mismatch},
            )
            if rebuild_if_mismatch:
                self.rebuild_index()
        except Exception as e:
            logger.exception("Failed index consistency check", extra={"error": str(e)})

    def rebuild_index(self):
        """
        Rebuild FAISS index from the persisted knowledge base.
        This is the canonical fix for FAISS/KB count mismatches.
        """
        kb_len = len(self.knowledge_base)
        if kb_len == 0:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.save_index()
            logger.info("Rebuilt empty FAISS index", extra={"facts": 0})
            return

        details = []
        for fact in self.knowledge_base:
            detail = fact.get("detail")
            if isinstance(detail, str) and detail.strip():
                details.append(detail.strip())
            else:
                details.append("")

        model = self._get_model()
        emb = model.encode(details, convert_to_numpy=True)
        faiss.normalize_L2(emb)

        new_index = faiss.IndexFlatL2(self.dimension)
        new_index.add(emb)
        self.index = new_index
        self.save_index()
        logger.info("Rebuilt FAISS index from knowledge base", extra={"facts": kb_len, "faiss": self.index.ntotal})

    def _initialize_default_kb(self):
        """Initialize with empty knowledge base structure"""
        self.knowledge_base = []
        self._save_knowledge_base()

    def _save_knowledge_base(self):
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, indent=4, ensure_ascii=False)
            logger.info("Knowledge base saved", extra={"facts": len(self.knowledge_base), "path": self.log_path})
        except Exception as e:
            logger.exception("Failed to save knowledge base", extra={"path": self.log_path, "error": str(e)})

    def save_index(self):
        try:
            faiss.write_index(self.index, self.index_path)
        except Exception as e:
            logger.exception("Failed to save FAISS index", extra={"path": self.index_path, "error": str(e)})

    def add_fact(self, category, detail):
        """Add a fact/detail about Prem.
        category: 'memory', 'personality', 'likes', 'dislikes', 'place', 'relationship', etc.
        detail: description of the fact
        """
        try:
            fact_dict = {
                "category": category,
                "detail": detail,
                "timestamp": str(np.datetime64('now'))
            }
            
            # Create embedding for this fact
            embedding = self._get_model().encode([detail], convert_to_numpy=True)
            faiss.normalize_L2(embedding)
            self.index.add(embedding)
            
            # Store fact in knowledge base
            self.knowledge_base.append(fact_dict)
            
            # Persist
            self.save_index()
            self._save_knowledge_base()
            logger.info(
                "Fact added",
                extra={"category": category, "total": len(self.knowledge_base)},
            )
        except Exception as e:
            logger.exception("Failed to add fact", extra={"error": str(e)})

    def get_memory_status(self):
        """Verify memory integrity - useful for debugging."""
        status = {
            "total_facts": len(self.knowledge_base),
            "faiss_index_size": self.index.ntotal,
            "mismatch": len(self.knowledge_base) != self.index.ntotal,
            "files_exist": {
                "index": os.path.exists(self.index_path),
                "kb": os.path.exists(self.log_path)
            }
        }
        if status["mismatch"]:
            logger.warning(
                "Memory mismatch",
                extra={"facts": len(self.knowledge_base), "faiss": self.index.ntotal},
            )
        return status

    def retrieve_relevant_facts(self, query, top_k=5):
        """Retrieve facts about Prem relevant to Maitree's question."""
        if self.index.ntotal == 0:
            return ""
            
        k = min(top_k, self.index.ntotal)
        
        # Encode query
        query_emb = self._get_model().encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)
        
        # Search FAISS
        distances, indices = self.index.search(query_emb, k)
        
        # Compile context string with relevant facts
        context_str = ""
        for idx in indices[0]:
            if idx < len(self.knowledge_base) and idx >= 0:
                fact = self.knowledge_base[idx]
                context_str += f"[{fact['category'].upper()}] {fact['detail']}\n"
                
        if context_str:
            return f"[ABOUT PREM - Answer authentically based on these facts]\n{context_str}\n"
        return ""

    def get_all_facts_by_category(self, category):
        """Get all facts in a specific category (e.g., all 'memories' or all 'personality' traits)."""
        return [fact for fact in self.knowledge_base if fact['category'].lower() == category.lower()]

    def list_all_facts(self):
        """Return all stored facts about Prem."""
        return self.knowledge_base

    def warmup(self):
        """Optional: pre-load embedding model to reduce first-request latency."""
        self._get_model()

    def add_conversation_turn(self, user_msg, prem_reply):
        """Add a turn to the Short-Term Memory (STM) sliding window (REMIND framework)."""
        self.stm_window.append({"user": user_msg, "prem": prem_reply})
        if len(self.stm_window) > self.stm_max_turns:
            self.stm_window.pop(0)

    def get_stm_context(self):
        """Format the STM window into a context string."""
        if not self.stm_window:
            return ""
        context = "[RECENT CONVERSATION HISTORY]\n"
        for turn in self.stm_window:
            context += f"Maitree: {turn['user']}\nPrem: {turn['prem']}\n"
        return context + "\n"

    def retrieve_hybrid_context(self, query, top_k=5):
        """REMIND Hybrid Retrieval: Combines STM context and LTM FAISS retrieval."""
        stm_context = self.get_stm_context()
        ltm_context = self.retrieve_relevant_facts(query, top_k)
        
        combined = ""
        if stm_context:
            combined += stm_context
        if ltm_context:
            combined += ltm_context
            
        return combined


if __name__ == "__main__":
    # Test script
    mem = MemoryStore()
    mem.add_fact("memory", "Prem loved watching sunsets at the lake")
    mem.add_fact("personality", "Prem was deeply empathetic and always listened")
    mem.add_fact("likes", "Prem's favorite color was blue")
    mem.add_fact("relationship", "Prem and Maitree shared an unbreakable bond of love")
    print("\n--- Test Retrieval ---")
    print(mem.retrieve_relevant_facts("What did Prem enjoy doing?"))

