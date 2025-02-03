"""
A script that generates embeddings for questions and saves them to a database.
"""

from sentence_transformers import SentenceTransformer
import sqlite3
import numpy as np
import torch
import tqdm
import time

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("all-MiniLM-L6-v2").to(device)
DB_NAME = "./data/askreddit.db"

def create_embeddings_table():
    """Creates the embeddings table if it does not exist."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id TEXT PRIMARY KEY,
            vector BLOB
        )
    """)
    conn.commit()
    conn.close()

from tqdm import tqdm
import time

def generate_embeddings(questions, batch_size=64):
    """Generates sentence embeddings efficiently using GPU batch processing with a progress bar."""
    texts = [q[1] for q in questions]  # Extract question texts
    ids = [q[0] for q in questions]    # Extract question IDs

    print(f"Generating embeddings for {len(texts)} questions...")
    start_time = time.time()

    # Encode in batches with a progress bar
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Processing Batches"):
        batch_texts = texts[i : i + batch_size]
        batch_embeddings = model.encode(
            batch_texts, 
            batch_size=batch_size, 
            convert_to_numpy=True, 
            device=device
        )
        embeddings.extend(batch_embeddings)

    elapsed_time = time.time() - start_time
    print(f"✅ Embeddings generated in {elapsed_time:.2f} seconds.")

    return list(zip(ids, embeddings))  # Return (id, embedding) tuples


def save_embeddings(embeddings):
    """Saves generated embeddings into the SQLite database."""
    create_embeddings_table()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for q_id, emb in embeddings:
        cur.execute("INSERT OR REPLACE INTO embeddings (id, vector) VALUES (?, ?)", 
                    (q_id, np.array(emb).tobytes()))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    """Fetches questions, generates embeddings, and stores them in the database."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Fetch all questions
    cur.execute("SELECT id, text FROM questions")
    questions = cur.fetchall()
    conn.close()

    if not questions:
        print("No questions found in the database.")
    else:
        print(f"Generating embeddings for {len(questions)} questions...")

        # Generate and save embeddings
        embeddings = generate_embeddings(questions)
        save_embeddings(embeddings)

        print("Embeddings saved successfully.")
