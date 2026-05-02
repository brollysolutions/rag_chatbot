from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from langdetect import detect, LangDetectException
from app.config import (
    QDRANT_HOST, QDRANT_PORT,
    COLLECTION_NAME, TOP_K, SCORE_THRESHOLD
)



print("Loading multilingual embedding model...")
embedding_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
print("Embedding model loaded.")

qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def detect_language(text: str) -> str:
    """Detect language of input text. Returns ISO 639-1 code."""
    try:
        lang = detect(text)
        if lang in ["te"]:
            return "te"
        elif lang in ["hi"]:
            return "hi"
        else:
            return "en"
    except LangDetectException:
        return "en"


def embed_query(query: str) -> list[float]:
    """Generate 384-dim embedding for query string."""
    return embedding_model.encode(query).tolist()




def retrieve_context(query: str) -> tuple[str, list[float]]:
    query_embed = embed_query(query)

    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embed,
        limit=TOP_K,
        score_threshold=SCORE_THRESHOLD,
        with_payload=True
    )
    if not response.points:
        return "", query_embed

    docs = []
    for hit in response.points:
        if hit.payload and "text" in hit.payload:
            docs.append(hit.payload["text"])

    return "\n\n".join(docs), query_embed