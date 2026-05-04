from groq import Groq
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY, GROQ_API_KEY, LLM_MODEL, ENV,
    CACHE_COLLECTION_NAME, CACHE_THRESHOLD 
)
from app.prompts import SYSTEM_PROMPT, FALLBACK_MESSAGE, CONTACT_INFO
from app.retrieval import retrieve_context_with_vector, detect_language, embed_query, qdrant_client

openai_client = OpenAI(api_key=OPENAI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

GREETINGS = {
    "hi", "hello", "hey", "namaste", "hallo", "hi hello",
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
        print(f"\n🚨 API CRASH REASON: {e}\n")
        return FALLBACK_MESSAGE


def check_cache(query_vector: list[float]):
    """Look for a similar query in the cache collection."""
    results = qdrant_client.query_points(
        collection_name=CACHE_COLLECTION_NAME,
        query=query_vector,
        limit=1,
        score_threshold=CACHE_THRESHOLD
    ).points
    
    if results:
        return results[0].payload.get("cached_answer")
    return None

def save_to_cache(query_vector: list[float], question: str, answer: str):
    """Store the query vector and LLM answer for future hits."""
    import uuid
    point_id = str(uuid.uuid4())
    qdrant_client.upsert(
        collection_name=CACHE_COLLECTION_NAME,
        points=[{
            "id": point_id,
            "vector": query_vector,
            "payload": {"question": question, "cached_answer": answer}
        }]
    )

def compress_history(history: list[dict]) -> list[dict]:
    """
    Auto-compress old history on context overflow to save tokens[cite: 1].
    Keeps the most recent 2 turns (4 messages) verbatim and summarizes the rest.
    """
    if len(history) <= 4:
        return history
    recent_history = history[-4:]
    old_history = history[:-4]

    convo_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in old_history])

    summary_prompt = (
        "Briefly summarize the following conversation history. "
        "Focus on the user's core intent, the courses they asked about, and any key details provided. "
        "Do not answer questions, just summarize.\n\n"
        f"History:\n{convo_text}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0,
            max_tokens=150
        )
        summary = response.choices[0].message.content
        return [{"role": "system", "content": f"Previous conversation summary: {summary}"}] + recent_history
        
    except Exception as e:
        print(f"\n🚨 HISTORY COMPRESSION FAILED: {e}\n")
        return recent_history

def get_query_variants(question: str) -> list[str]:
    """Uses LLM to generate search variations, automatically injecting context for short queries."""
    prompt = (
        "You are a search query generator for 'Digital Brolly', an AI Digital Marketing Institute in Hyderabad. "
        "Rewrite the following user query into 2 different, highly specific search queries for a vector database. "
        "CRITICAL: If the user's query is very short or vague (like 'address?', 'location', or 'fees'), "
        "you MUST expand it to explicitly include the institute's name (e.g., 'Digital Brolly institute address location'). "
        "Return ONLY the 2 queries separated by a newline.\n\n"
        f"User Query: {question}"
    )
    
    try:
        client = openai_client if ENV == "production" else groq_client
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50
        )
        variants = response.choices[0].message.content.strip().split('\n')
        return [v.strip('- "123.') for v in variants if v.strip()]
    except Exception as e:
        print(f"Variant generation failed: {e}")
        return []

def get_answer(question: str, history: list[dict] = None) -> str:
    """
    Enhanced RAG pipeline with Semantic Caching & Multi-Query Expansion:
    1. Language detection
    2. Greeting shortcut
    3. Semantic Cache lookup (if no history)
    4. Multi-Query Expansion & Retrieval from Qdrant[cite: 1]
    5. Call LLM & Update Cache
    """
    history = history or []
    detected_lang = detect_language(question)
    

    if question.lower().strip() in GREETINGS:
        return (
            "Hello! I'm the Digital Brolly Assistant.\n\n"
            "I can help you with details about our Digital Marketing and AI courses, "
            "fees, placements, and more. How can I assist you today?"
        )

    query_vector = embed_query(question)

    if not history:
        cached_response = check_cache(query_vector)
        if cached_response:
            print("--- SEMANTIC CACHE HIT ---")
            return cached_response

    variants = get_query_variants(question)
    
    unique_chunks = set()
    
    original_ctx, _ = retrieve_context_with_vector(query_vector)
    if original_ctx:
        for chunk in original_ctx.split('\n\n'):
            if chunk.strip():
                unique_chunks.add(chunk.strip())
                
    for var_q in variants:
        var_vec = embed_query(var_q)
        var_ctx, _ = retrieve_context_with_vector(var_vec)
        if var_ctx:
            for chunk in var_ctx.split('\n\n'):
                if chunk.strip():
                    unique_chunks.add(chunk.strip())

    context = "\n\n".join(list(unique_chunks)[:6])
    
    if not context:
        return FALLBACK_MESSAGE

    # 5. LLM ORCHESTRATION
    user_prompt = (
        f"[detected_language: {detected_lang}]\n\n"
        f"--- DOCUMENT CONTEXT START ---\n"
        f"{context}\n"
        f"--- DOCUMENT CONTEXT END ---\n\n"
        f"If the answer is not in the context above, return exactly:\n"
        f"{FALLBACK_MESSAGE}\n\n"
        f"User Question: {question}"
    )

    compressed_history = compress_history(history)
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(compressed_history)
    messages.append({"role": "user", "content": user_prompt})

    final_answer = _call_llm(messages)

    # 6. UPDATE CACHE
    if not history and final_answer != FALLBACK_MESSAGE:
        save_to_cache(query_vector, question, final_answer)

    return final_answer