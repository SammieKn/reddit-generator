import sqlite3
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine

DB_NAME = "./data/askreddit.db"

# Load the embedding model
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("all-MiniLM-L6-v2").to(device)

def get_similar_questions(query, top_n=10):
    """Finds the most similar questions to the given query."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Encode query into an embedding
    query_embedding = model.encode(query, convert_to_numpy=True, device=device)

    # Retrieve stored embeddings
    cur.execute("SELECT id, vector FROM embeddings")
    rows = cur.fetchall()
    
    # Compute similarity scores
    similarities = []
    for q_id, vector_blob in rows:
        stored_embedding = np.frombuffer(vector_blob, dtype=np.float32)
        similarity = 1 - cosine(query_embedding, stored_embedding)  # Cosine similarity
        similarities.append((q_id, similarity))

    conn.close()

    # Sort by highest similarity and get top matches
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_ids = [item[0] for item in similarities[:top_n]]

    # Fetch actual questions from the database
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, text FROM questions WHERE id IN ({})".format(",".join("?" * len(top_ids))), top_ids)
    results = cur.fetchall()
    conn.close()

    # Print results
    print("\n🔍 Top Matching Questions:")
    for i, (q_id, text) in enumerate(results):
        print(f"{i+1}. {text} (ID: {q_id})")

# Run the test with the given query
if __name__ == "__main__":
    test_query = "What makes you lose all hope in the world?"
    get_similar_questions(test_query)
