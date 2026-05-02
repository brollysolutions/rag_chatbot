from qdrant_client import models
from app.retrieval import qdrant_client
from app.config import CACHE_COLLECTION_NAME

def setup_cache():
    VECTOR_SIZE = 384 

    print(f"Checking for cache collection: {CACHE_COLLECTION_NAME}...")
    
    if not qdrant_client.collection_exists(CACHE_COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=CACHE_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE, 
                distance=models.Distance.COSINE
            ),
        )
        print(f"✅ Cache collection '{CACHE_COLLECTION_NAME}' created successfully!")
    else:
        print(f"👍 Collection '{CACHE_COLLECTION_NAME}' already exists.")

if __name__ == "__main__":
    setup_cache()