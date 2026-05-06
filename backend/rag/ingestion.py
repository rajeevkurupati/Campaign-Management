"""
RAG ingestion — loads .md and .txt files from backend/guidelines/ into ChromaDB.
Called at startup; only re-ingests files that have changed (MD5 hash check).
"""
import os, hashlib
import chromadb
from chromadb.utils import embedding_functions

GUIDELINES_DIR = os.path.join(os.path.dirname(__file__), '..', 'guidelines')
CHROMA_DIR     = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
COLLECTION     = 'guidelines'


def _get_ef():
    """OpenAI embeddings if key available, else ChromaDB local default."""
    try:
        import config
        if config.OPENAI_API_KEY:
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=config.OPENAI_API_KEY,
                model_name='text-embedding-3-small',
            )
    except Exception:
        pass
    return embedding_functions.DefaultEmbeddingFunction()


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=_get_ef(),
        metadata={'hnsw:space': 'cosine'},
    )


def _chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks, respecting paragraph boundaries.
    Keeps markdown section headers attached to their content.
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks, current = [], ''
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + '\n\n' + para).strip()
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if len(current) > overlap else current
            current = (tail + '\n\n' + para).strip() if tail else para
    if current:
        chunks.append(current)
    return [c for c in chunks if len(c) > 40]


def _file_hash(path: str) -> str:
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def ingest_guidelines(force: bool = False) -> int:
    """
    Scan guidelines/ for .md and .txt files. Ingest new/changed files into ChromaDB.
    Returns total chunk count in the collection after ingestion.
    """
    os.makedirs(GUIDELINES_DIR, exist_ok=True)
    if not os.listdir(GUIDELINES_DIR):
        print('[RAG] guidelines/ folder is empty — skipping ingestion')
        return 0

    col   = _get_collection()
    files = [f for f in os.listdir(GUIDELINES_DIR) if f.endswith(('.md', '.txt'))]

    ingested = 0
    for fname in sorted(files):
        fpath = os.path.join(GUIDELINES_DIR, fname)
        fhash = _file_hash(fpath)

        existing = col.get(where={'source': fname})
        if existing['ids']:
            if existing['metadatas'][0].get('hash') == fhash and not force:
                continue
            col.delete(where={'source': fname})

        with open(fpath, encoding='utf-8') as f:
            text = f.read()

        chunks = _chunk_text(text)
        if not chunks:
            continue

        col.add(
            documents=chunks,
            ids=[f"{fname}::chunk::{i}" for i in range(len(chunks))],
            metadatas=[{'source': fname, 'hash': fhash, 'chunk_index': i}
                       for i in range(len(chunks))],
        )
        ingested += len(chunks)
        print(f'[RAG] Ingested {len(chunks)} chunks from {fname}')

    total = col.count()
    if ingested == 0 and total > 0:
        print(f'[RAG] Guidelines up to date — {total} chunks in store')
    return total
