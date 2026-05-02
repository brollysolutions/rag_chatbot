
# """
# Using Ollama as Embeddings - test2
# """
# import os
# # import chromadb
# # from groq import Groq
# from sentence_transformers import SentenceTransformer
# from openai import OpenAI
# from dotenv import load_dotenv
# from app.config import OPENAI_API_KEY
# from app.prompts import FALLBACK_MESSAGE, SYSTEM_PROMPT, CONTACT_INFO

# """-----------------------------------------------------------------------"""
# from qdrant_client import QdrantClient


# load_dotenv()

# # Initialize Groq Client
# # groq_client = Groq(api_key=GROQ_API_KEY)
# openai_client = OpenAI(api_key=OPENAI_API_KEY)

# # Initialize ChromaDB Client
# # vector_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_db_ollama")
# # client = chromadb.PersistentClient(path=vector_db_path)
# # collection = client.get_or_create_collection("brolly_docs_v3", metadata={"hnsw:space": "cosine"})


# qdrant_host = os.getenv("QDRANT_HOST")
# qdrant_port = int(os.getenv("QDRANT_PORT"))
# qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
# COLLECTION_NAME = "brolly_docs_v5"

# # Initialize SentenceTransformer (Downloads the ~500MB model on the first run)
# print("Loading Embedding Model...")
# embedding_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
# print("Model Loaded Successfully!")


# def get_answer(question):

#     greetings = ["hi", "hello", "hey", "namaste", "hallo", "hi hello"]
    
#     if question.lower().strip() in greetings:
#         return "Hello! I'm the Digital Brolly Assistant. I can help you with details about our Digital Marketing and AI courses, fees, and placements. How can I assist you today?"
        
#     try:
#         query_embedding = embedding_model.encode(f"search_query: {question}").tolist()
#     except Exception as e:
#         print(f"Error generating embedding: {e}")
#         return FALLBACK_MESSAGE

#     try:
#         response = qdrant_client.query_points(
#             collection_name=COLLECTION_NAME,
#             query=query_embedding,  
#             limit=5,
#             with_payload=True
#         )
#         search_result = response.points  
        
#     except Exception as e:
#         print(f"Error querying Qdrant: {e}")
#         return FALLBACK_MESSAGE

#     if not search_result:
#         return FALLBACK_MESSAGE

#     docs = [hit.payload["text"] for hit in search_result if hit.payload and "text" in hit.payload]
#     context = "\n\n".join(docs)


#     # --- DEBUG BLOCK ---
#     # print("\n" + "="*40)
#     # print("DEBUG: EXACT CONTEXT SENT TO LLM:")
#     # print(context)
#     # print("="*40 + "\n")
#     # -------------------------------

#     user_prompt = f"""You are a helpful assistant for Digital Brolly. Use the following context to answer the user's question.

#     --- DOCUMENT CONTEXT START ---
#     {context}
#     --- DOCUMENT CONTEXT END ---

#     If the answer cannot be found in the context, do NOT try to make up an answer. Instead, reply EXACTLY with this message:
#     {FALLBACK_MESSAGE}

#     User Question: {question}"""

#     try:
#         completion = openai_client.chat.completions.create(
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": user_prompt}
#             ],
#             model="gpt-4o-mini",
#             stream=True,
#             stop=None,
#             temperature=0
#         )

#         full_response = ""
#         for chunk in completion:
#             if chunk.choices and chunk.choices[0].delta.content:
#                 content = chunk.choices[0].delta.content
#                 full_response += content

#         return full_response if full_response else FALLBACK_MESSAGE

#     except Exception as e:
#         print(f"Error calling OpenAI API: {e}")
#         return FALLBACK_MESSAGE



from groq import Groq
from openai import OpenAI
from app.config import OPENAI_API_KEY, GROQ_API_KEY, LLM_MODEL, ENV
from app.prompts import SYSTEM_PROMPT, FALLBACK_MESSAGE, CONTACT_INFO
from app.retrieval import retrieve_context, detect_language

openai_client = OpenAI(api_key=OPENAI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

GREETINGS = {
    "hi", "hello", "hey", "namaste", "hallo",
    "హాయ్", "నమస్కారం",
    "नमस्ते", "हेलो"
}

def _call_llm(messages: list[dict]) -> str:
    """Route LLM call to Groq (dev) or OpenAI (prod) based on ENV."""
    try:
        if ENV == "production":
            response = openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=1024
            )
        else:
            response = groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=1024
            )
        raw_text = response.choices[0].message.content or FALLBACK_MESSAGE
        import re
        clean_text = re.sub(r'\[detected_language:.*?\]\n*', '', raw_text).strip()
        return clean_text
    except Exception as e:
        return FALLBACK_MESSAGE

def get_answer(question: str, history: list[dict] = None) -> str:
    """
    Full RAG pipeline:
    1. detect language
    2. check greeting shortcut
    3. retrieve text from Qdrant
    4. build prompt with history + context
    5. call LLM
    """
    history = history or []
    detected_lang = detect_language(question)
    if question.lower().strip() in GREETINGS:
        return (
            "Hello! I'm the Digital Brolly Assistant.\n\n"
            "I can help you with details about our Digital Marketing and AI courses, "
            "fees, placements, and more. How can I assist you today?"
        )

    context, _ = retrieve_context(question)

    print("--- RETRIEVED CONTEXT ---")
    print(context)
    
    if not context:
        return FALLBACK_MESSAGE
    user_prompt = (
        f"[detected_language: {detected_lang}]\n\n"
        f"--- DOCUMENT CONTEXT START ---\n"
        f"{context}\n"
        f"--- DOCUMENT CONTEXT END ---\n\n"
        f"If the answer is not in the context above, return exactly:\n"
        f"{FALLBACK_MESSAGE}\n\n"
        f"User Question: {question}"
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    return _call_llm(messages)