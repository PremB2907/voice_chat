import os
import faiss
import numpy as np
import json
from sentence_transformers import SentenceTransformer

class MemoryStore:
    def __init__(self, index_path="memory_index.faiss", log_path="prem_knowledge_base.json"):
        self.index_path = index_path
        self.log_path = log_path
        print("🧠 Loading SentenceTransformer model ('all-MiniLM-L6-v2') for Memory...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Knowledge base: stores detailed information ABOUT PREM
        # Format: {"topic": description, "memory": detail, "place": significance, etc.}
        self.knowledge_base = []
        
        self.index = self._load_or_create_index()
        self._load_knowledge_base()

    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            print("🧠 Loading FAISS memory index...")
            return faiss.read_index(self.index_path)
        else:
            print("🧠 Creating new FAISS memory index...")
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

    def _initialize_default_kb(self):
        """Initialize with empty knowledge base structure"""
        self.knowledge_base = []
        self._save_knowledge_base()

    def _save_knowledge_base(self):
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, indent=4, ensure_ascii=False)
            print(f"✅ Prem's Knowledge Base saved ({len(self.knowledge_base)} facts)")
        except Exception as e:
            print(f"❌ Failed to save knowledge base: {e}")

    def save_index(self):
        try:
            faiss.write_index(self.index, self.index_path)
        except Exception as e:
            print(f"❌ Failed to save FAISS index: {e}")

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
            embedding = self.model.encode([detail], convert_to_numpy=True)
            faiss.normalize_L2(embedding)
            self.index.add(embedding)
            
            # Store fact in knowledge base
            self.knowledge_base.append(fact_dict)
            
            # Persist
            self.save_index()
            self._save_knowledge_base()
            print(f"✅ Fact added: {category} - {detail[:50]}... (Total: {len(self.knowledge_base)})")
        except Exception as e:
            print(f"❌ Failed to add fact: {e}")

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
            print(f"⚠️ MEMORY MISMATCH: {len(self.knowledge_base)} facts vs {self.index.ntotal} in FAISS!")
        else:
            print(f"✅ Memory intact: {len(self.knowledge_base)} facts about Prem stored")
        return status

    def retrieve_relevant_facts(self, query, top_k=5):
        """Retrieve facts about Prem relevant to Maitree's question."""
        if self.index.ntotal == 0:
            return ""
            
        k = min(top_k, self.index.ntotal)
        
        # Encode query
        query_emb = self.model.encode([query], convert_to_numpy=True)
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


if __name__ == "__main__":
    # Test script
    mem = MemoryStore()
    mem.add_fact("memory", "Prem loved watching sunsets at the lake")
    mem.add_fact("personality", "Prem was deeply empathetic and always listened")
    mem.add_fact("likes", "Prem's favorite color was blue")
    mem.add_fact("relationship", "Prem and Maitree shared an unbreakable bond of love")
    print("\n--- Test Retrieval ---")
    print(mem.retrieve_relevant_facts("What did Prem enjoy doing?"))

