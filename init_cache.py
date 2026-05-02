from qdrant_client import models
from app.retrieval import qdrant_client
from app.config import CACHE_COLLECTION_NAME, COLLECTION_NAME, VECTOR_SIZE

def setup_collections():
    print(f"Checking for collections...")
    
    # 1. Main Document Collection
    try:
        if not qdrant_client.collection_exists(COLLECTION_NAME):
            print(f"Creating document collection: {COLLECTION_NAME}...")
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE, 
                    distance=models.Distance.COSINE
                ),
            )
            print(f"✅ Collection '{COLLECTION_NAME}' created successfully!")
        else:
            print(f"👍 Collection '{COLLECTION_NAME}' already exists.")
    except Exception as e:
        if "already exists" in str(e):
            print(f"👍 Collection '{COLLECTION_NAME}' was created by another worker.")
        else:
            raise e

    # 2. Cache Collection
    try:
        if not qdrant_client.collection_exists(CACHE_COLLECTION_NAME):
            print(f"Creating cache collection: {CACHE_COLLECTION_NAME}...")
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
    except Exception as e:
        if "already exists" in str(e):
            print(f"👍 Collection '{CACHE_COLLECTION_NAME}' was created by another worker.")
        else:
            raise e

if __name__ == "__main__":
    setup_collections()