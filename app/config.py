import os
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_FREE_API_KEY")

ENV = os.getenv("ENV")

LLM_MODEL = "gpt-4o-mini" if ENV == "production" else "llama-3.3-70b-versatile"
#LLM_MODEL = "gpt-4o-mini"

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

COLLECTION_NAME = "brolly_docs_v8" 
VECTOR_SIZE = 384

TOP_K = 10
SCORE_THRESHOLD = 0.05


CACHE_COLLECTION_NAME = "brolly_cache_v5"
CACHE_THRESHOLD = 0.95

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")