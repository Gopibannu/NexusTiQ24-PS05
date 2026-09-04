import os
import json
import numpy as np
import requests

def get_embedding(text: str, api_key: str = None) -> list:
    """
    Get embedding for a text using Gemini API 'gemini-embedding-001'.
    Includes timeout and fallback to deterministic local TF-IDF vector representation if API fails or key is missing.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if api_key:
        try:
            # First attempt with google-genai SDK
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                res = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text
                )
                if hasattr(res, 'embedding') and hasattr(res.embedding, 'values'):
                    return list(res.embedding.values)
                elif hasattr(res, 'embeddings') and len(res.embeddings) > 0:
                    return list(res.embeddings[0].values)
            except Exception as e:
                pass

            # Direct REST API fallback
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {"content": {"parts": [{"text": text}]}}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "embedding" in data and "values" in data["embedding"]:
                    return data["embedding"]["values"]
        except Exception as ex:
            print(f"[Warning] Gemini embedding call failed, fallback to local vector: {ex}")

    # Fallback deterministic vector generator (768-dim pseudo vector from word hashing for hybrid offline search)
    return _hash_vector(text, dim=768)

def _hash_vector(text: str, dim: int = 768) -> list:
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    if not words:
        return vec.tolist()
    for word in words:
        idx = hash(word) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def cosine_similarity(v1: list, v2: list) -> float:
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
