import os
import json
from engine.embedding_utils import get_embedding, cosine_similarity

class RAGStore:
    def __init__(self, index_file_path: str = None):
        if not index_file_path:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
            index_file_path = os.path.join(base_dir, 'standard_positions_index.json')
        
        self.index_file_path = index_file_path
        self.rules = []
        self.load_index()

    def load_index(self):
        if os.path.exists(self.index_file_path):
            with open(self.index_file_path, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
            print(f"[RAGStore] Loaded {len(self.rules)} standard position rules from {self.index_file_path}")
        else:
            print(f"[RAGStore Warning] Index file not found at {self.index_file_path}")
            self.rules = []

    def get_all_rules(self):
        return self.rules

    def search_relevant_rules(self, text_chunk: str, top_k: int = 3, api_key: str = None) -> list:
        """
        Retrieves top-k most relevant standard position rules for a given clause/chunk.
        Uses hybrid cosine similarity matching + keyword term matching.
        """
        if not self.rules:
            return []

        chunk_emb = get_embedding(text_chunk, api_key=api_key)
        
        scored_rules = []
        for rule in self.rules:
            sim = cosine_similarity(chunk_emb, rule["embedding"])
            
            # Hybrid boost for direct keyword relevance
            text_lower = text_chunk.lower()
            if "deposit" in text_lower and rule["category"] == "deposit_range":
                sim += 0.2
            if ("notice" in text_lower or "terminate" in text_lower or "vacate" in text_lower) and rule["category"] == "notice_period":
                sim += 0.2
            if ("maintain" in text_lower or "repair" in text_lower or "hvac" in text_lower or "plumbing" in text_lower) and "rule_maintenance_responsibility" in rule["id"]:
                sim += 0.2
            if ("return" in text_lower or "refund" in text_lower) and "deposit" in text_lower and "rule_deposit_return_timeline" in rule["id"]:
                sim += 0.2
            if "automatic renewal" in text_lower or "auto-renew" in text_lower or "automatically renew" in text_lower:
                if "rule_forbidden_auto_renewal" in rule["id"]:
                    sim += 0.4
                    
            scored_rules.append((sim, rule))

        scored_rules.sort(key=lambda x: x[0], reverse=True)
        return [rule for _, rule in scored_rules[:top_k]]

# Singleton instance
rag_instance = RAGStore()
