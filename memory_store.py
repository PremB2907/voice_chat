import os
import faiss
import numpy as np
import json
from sentence_transformers import SentenceTransformer

class MemoryStore:
    def __init__(self, index_path="memory_index.faiss", log_path="memory_log.json"):
        self.index_path = index_path
        self.log_path = log_path
        print("🧠 Loading SentenceTransformer model ('all-MiniLM-L6-v2') for Memory...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # In-memory storage of conversation texts to map back from FAISS indices
        self.history = []
        
        self.index = self._load_or_create_index()
        self._load_history()

    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            print("🧠 Loading FAISS memory index...")
            return faiss.read_index(self.index_path)
        else:
            print("🧠 Creating new FAISS memory index...")
            return faiss.IndexFlatL2(self.dimension)

    def _load_history(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def _save_history(self):
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=4)

    def save_index(self):
        faiss.write_index(self.index, self.index_path)

    def add_memory(self, user_text, ai_reply):
        # Format interaction
        interaction = f"Maitree: {user_text}\nPrem: {ai_reply}"
        
        # Embed and add to FAISS
        embedding = self.model.encode([interaction], convert_to_numpy=True)
        # Normalize the embedding (optional, but good for cosine similarity if using IP instead of L2, L2 is fine here)
        faiss.normalize_L2(embedding)
        self.index.add(embedding)
        
        # Add to local history list
        self.history.append(interaction)
        
        # Persist to disk
        self.save_index()
        self._save_history()

    def retrieve_context(self, query, top_k=3):
        if self.index.ntotal == 0:
            return ""
            
        # Ensure k doesn't exceed available memories
        k = min(top_k, self.index.ntotal)
        
        # Encode user query
        query_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)
        
        # Search FAISS
        distances, indices = self.index.search(query_emb, k)
        
        # Compile context string
        context_str = ""
        for idx in indices[0]:
            if idx < len(self.history) and idx >= 0:
                context_str += self.history[idx] + "\n---\n"
                
        if context_str:
            return f"Retrieved Past Conversations for Context:\n{context_str.strip()}\n"
        return ""

if __name__ == "__main__":
    # Test script
    mem = MemoryStore()
    mem.add_memory("I miss going to the lake.", "I remember the lake. The water was always so peaceful.")
    mem.add_memory("Do you remember my favorite color?", "Of course, you always loved blue.")
    print("\n--- Test Retrieval ---")
    print(mem.retrieve_context("What color did I like?"))
