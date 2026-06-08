"""
Stage 3 & 4: Embed chunks with all-MiniLM-L6-v2 and store in ChromaDB.
Also provides the retrieve() function used by the generation stage.

Usage:
    python embed.py          — build (or rebuild) the vector store
    python embed.py --query "some question"   — test retrieval interactively
"""

import json
import argparse
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb

# ── Configuration ──────────────────────────────────────────────────────────────

CHUNKS_FILE = Path("documents/chunks.json")
CHROMA_DIR = Path("documents/chroma_db")
COLLECTION_NAME = "professor_reviews"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5           # matches planning.md

# ── Shared model + client (loaded once per process) ────────────────────────────

_model: SentenceTransformer | None = None
_collection = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL} …")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print("  Model loaded.")
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        # cosine distance makes scores directly interpretable: 0 = identical,
        # 1 = orthogonal.  all-MiniLM-L6-v2 embeddings are unit-normalised, so
        # cosine and L2 are equivalent in ranking — but cosine scores are much
        # easier to threshold (good match < 0.3, weak match > 0.5).
        _collection = client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Build: embed all chunks and store in ChromaDB ─────────────────────────────

def build_vector_store() -> None:
    """
    Reads documents/chunks.json, embeds every chunk with all-MiniLM-L6-v2,
    and upserts into the persistent ChromaDB collection.

    We call collection.add() with pre-computed embeddings rather than letting
    ChromaDB embed on its own, because we want full control over the model and
    can reuse the same SentenceTransformer instance at query time.

    Metadata stored per chunk:
      - source   : clean filename (e.g. "prof_1416958_clean.txt")
      - professor: full professor name (e.g. "Robert Hatch")
      - chunk_index: position within the full chunk list (0-based)
    """
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    model = _get_model()

    # Embed all chunk texts in one batched call — sentence-transformers
    # handles batching internally, which is faster than embedding one-by-one.
    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks …")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    print(f"  Embeddings shape: {embeddings.shape}")   # (81, 384)

    # Build parallel lists required by collection.add()
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": c["source"],
            "professor": c["professor"],
            "chunk_index": i,
        }
        for i, c in enumerate(chunks)
    ]

    collection = _get_collection()

    # Delete any existing data so a re-run produces a clean store.
    # Note: distance metric is set at collection-creation time (see
    # _get_collection), so a full delete-and-re-add is correct here.
    # collection.delete() requires ids or a where filter; deleting all
    # existing ids is the safest way to reset without dropping the collection.
    existing = collection.get(include=[])  # fetch only ids, no content
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        print(f"  Cleared {len(existing['ids'])} existing records.")

    # ChromaDB expects embeddings as a plain Python list-of-lists, not numpy.
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=metadatas,
    )
    print(f"Stored {len(ids)} chunks in ChromaDB at {CHROMA_DIR}/")
    print(f"Collection '{COLLECTION_NAME}' now has {collection.count()} records.")


# ── Retrieve: embed query, find top-k neighbours ──────────────────────────────

def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """
    Embed `query` with the same model used at index time, then return the k
    most similar chunks from ChromaDB.

    Returns a list of dicts, each with:
      - text       : the chunk text
      - source     : source filename
      - professor  : professor name
      - chunk_index: position in the full chunk list
      - distance   : L2 distance from the query embedding (lower = closer)

    ChromaDB's query() returns results as parallel lists wrapped in an outer
    list (one inner list per query — we always send exactly one query, so we
    index with [0] to unwrap the batch dimension).
    """
    model = _get_model()
    query_embedding = model.encode([query], convert_to_numpy=True)

    collection = _get_collection()
    # query_embeddings must be a list-of-lists; we pass one embedding → [[...]]
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Unwrap the batch dimension ([0]) — we sent one query, so each field is
    # a list-of-lists where the outer list has length 1.
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": doc,
            "source": meta["source"],
            "professor": meta["professor"],
            "chunk_index": meta["chunk_index"],
            "distance": round(dist, 4),
        })

    return hits


# ── CLI ────────────────────────────────────────────────────────────────────────

def _print_results(hits: list[dict]) -> None:
    for i, h in enumerate(hits, 1):
        print(f"\n{'─'*60}")
        print(f"Hit {i} | Professor: {h['professor']} | Source: {h['source']}")
        print(f"        Chunk #{h['chunk_index']} | Distance: {h['distance']}")
        print(f"{'─'*60}")
        print(h["text"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default=None,
                        help="Test a retrieval query after building the store.")
    parser.add_argument("--k", type=int, default=TOP_K,
                        help=f"Number of results to return (default {TOP_K}).")
    args = parser.parse_args()

    build_vector_store()

    if args.query:
        print(f"\n{'='*60}")
        print(f"Query: {args.query!r}  (top-{args.k})")
        print(f"{'='*60}")
        hits = retrieve(args.query, k=args.k)
        _print_results(hits)
    else:
        # Default smoke-test: run each of the 5 evaluation questions
        test_queries = [
            "What do students say about the difficulty of Robert Hatch's computer science assignments?",
            "Does Professor Khan require mandatory attendance?",
            "Does Professor Potter heavily curve his math exams?",
            "What is the grading style in Biology?",
            "Do students recommend buying the textbook for history class?",
        ]
        print(f"\n{'='*60}")
        print("SMOKE TEST — 5 evaluation queries")
        print(f"{'='*60}")
        for q in test_queries:
            print(f"\n>>> {q}")
            hits = retrieve(q, k=TOP_K)
            for h in hits:
                print(f"  [{h['distance']:.4f}] {h['professor']} | {h['source']} | chunk {h['chunk_index']}")
                print(f"    {h['text'][:120].replace(chr(10), ' ')} …")
