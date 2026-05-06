"""
RAG retriever — cosine similarity search against the guidelines collection.
"""
from rag.ingestion import CHROMA_DIR, COLLECTION, _get_ef
import chromadb


def retrieve(query: str, top_k: int = 3) -> str:
    """
    Return the top-k most relevant guideline chunks for the query.
    Returns formatted string ready for LLM prompt injection.
    Returns empty string if collection is empty or on any error (fail-safe).
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        col    = client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=_get_ef(),
            metadata={'hnsw:space': 'cosine'},
        )
        count = col.count()
        if count == 0:
            return ''

        results = col.query(query_texts=[query], n_results=min(top_k, count))
        docs = results.get('documents', [[]])[0]
        metas = results.get('metadatas', [[]])[0]

        if not docs:
            return ''

        parts = []
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            source = meta.get('source', 'guidelines')
            parts.append(f"[{source} — excerpt {i+1}]\n{doc}")

        return '\n\n---\n\n'.join(parts)

    except Exception:
        return ''  # RAG failure must never block validation
