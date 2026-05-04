# 🤖 Digital Brolly AI Assistant

> An enterprise-grade **Retrieval-Augmented Generation (RAG) Microservice** designed for the Digital Brolly training institute.  
> This API powers a conversational AI assistant that provides accurate, context-aware information about courses, fees, internships, and placements.

Designed for high performance, this service features **semantic caching**, **conversation history compression**, **multi-query expansion**, and **dynamic language mirroring** — including full **Tenglish / Hinglish** support.

---

## 📖 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Directory Structure](#-directory-structure)
- [Environment Configuration](#-environment-configuration)
- [Deployment & Installation](#-deployment--installation)
  - [Option 1: Docker Compose (Production)](#option-1-docker-compose-production-recommended)
  - [Option 2: Local Development](#option-2-local-development-setup)
- [API Reference](#-api-reference)
  - [POST /chat](#post-chat)
- [Evaluation & Testing](#-evaluation--testing)
- [Key System Behaviors](#-key-system-behaviors)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Architecture Overview

The RAG pipeline is heavily optimized for **speed**, **cost-efficiency**, and **accuracy**.  
Below is the complete lifecycle of a single user request from input to response.

### Request Processing Flow

| Step | Stage | Description |
|:----:|-------|-------------|
| **1** | 🌐 **Language Detection & Greetings** | Detects if the user is typing in English, Telugu, Hindi, or a transliterated hybrid (Tenglish / Hinglish). Standard greetings are intercepted and resolved via shortcuts — no LLM call is triggered. |
| **2** | ⚡ **Semantic Cache Lookup** | The user's query is embedded and compared against the Qdrant cache collection. A match with **>95% similarity** returns the cached answer instantly at **zero token cost**. |
| **3** | 🔄 **Multi-Query Expansion** | On a cache miss, the LLM rewrites the original query into multiple semantic variations to maximize document recall from the vector database. |
| **4** | 🔍 **Vector Retrieval** | All expanded queries are embedded and searched against the Qdrant document collection using pure **semantic (cosine similarity) retrieval**. |
| **5** | 🗜️ **Context Assembly & History Compression** | Retrieved chunks are deduplicated and assembled. If conversation history exceeds **4 turns**, older messages are summarized via a lightweight LLM call to prevent context window overflow. |
| **6** | 🧠 **Orchestration & Sentinel Logic** | The system prompt, compressed history, and retrieved context are forwarded to the LLM. If the LLM cannot find the answer, it emits a `[NOT_FOUND]` sentinel — which the backend intercepts and replaces with a professional fallback message containing contact details. |
| **7** | 📦 **JSON Response** | The final answer is returned to the client as a clean, structured JSON payload ready for front-end consumption. |

### Architecture Diagram

```
User Query
    │
    ▼
┌─────────────────────────┐
│  Language Detection      │  ◄── Greeting Shortcut (no LLM)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Semantic Cache Lookup   │  ◄── Qdrant Cache Collection (>95% match = instant return)
└────────────┬────────────┘
             │ Cache Miss
             ▼
┌─────────────────────────┐
│  Multi-Query Expansion   │  ◄── LLM rewrites query into N variations
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Vector Retrieval        │  ◄── Qdrant Document Collection (semantic search)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Context Assembly        │  ◄── Dedup + History Compression (if >4 turns)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  LLM Orchestration       │  ◄── System Prompt + Context + History
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Sentinel Check          │  ◄── [NOT_FOUND] → Fallback message
└────────────┬────────────┘
             │
             ▼
   JSON Response → Client
```

---

## 🛠️ Tech Stack

| Layer | Component | Technology |
|-------|-----------|------------|
| **API** | Web Framework | [FastAPI](https://fastapi.tiangolo.com/) — Python 3.10 |
| **Database** | Vector Store | [Qdrant](https://qdrant.tech/) — Local / Dockerized |
| **AI (Production)** | LLM Provider | OpenAI `gpt-4o-mini` |
| **AI (Development)** | LLM Provider | [Groq](https://groq.com/) — Fast inference |
| **AI** | Embeddings | HuggingFace `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| **Testing** | Evaluation Framework | [Ragas](https://docs.ragas.io/) — Faithfulness & Answer Relevancy |
| **Infrastructure** | Containerization | Docker & Docker Compose — Multi-stage builds |

---

## 📂 Directory Structure

```
.
├── app/                          # 🚀 Core application package
│   ├── main.py                   # FastAPI app instance, route definitions & REST endpoints
│   ├── rag_service.py            # RAG pipeline orchestration, cache logic & LLM calls
│   ├── retrieval.py              # Qdrant client setup, embedding engine & multi-query logic
│   ├── prompts.py                # System prompt templates, language rules & fallback messages
│   └── config.py                 # Environment variable loading & threshold configuration
│
├── scripts/
│   └── start.sh                  # Production entrypoint — initializes DB, runs ingestion & starts Uvicorn
│
├── documents/                    # 📁 Source document directory
│   └── *.pdf                     # Drop institute PDF files here for ingestion
│
├── ingestion.py                  # Reads PDFs, chunks text, generates embeddings & indexes into Qdrant
├── init_cache.py                 # Creates and initializes the Semantic Cache collection in Qdrant
├── evaluate_rag.py               # Automated LLM-as-a-judge test suite using Ragas
│
├── requirements.txt              # Python package dependencies
├── docker-compose.yml            # Multi-container orchestration (API service + Qdrant service)
├── Dockerfile                    # Optimized multi-stage Docker build with non-root user
└── README.md                     # Project documentation (this file)
```

---

## ⚙️ Environment Configuration

### Prerequisites

Before running the application, ensure the following are available on your machine:

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Docker** | 20.x+ | Container runtime |
| **Docker Compose** | 2.x+ | Multi-container orchestration |
| **Python** | 3.10+ | Local development only |
| **OpenAI API Key** | — | Production LLM calls |
| **Groq API Key** | — | Development / fast inference |

### Setting Up Environment Variables

Create a `.env` file in the **root directory** of the project before starting the application:

```bash
# ──────────────────────────────
# API Keys
# ──────────────────────────────
OPENAI_API_KEY=sk-your-openai-api-key
GROQ_API_KEY=gsk_your-groq-api-key

# ──────────────────────────────
# Environment Toggle
# Options: development | production
# ──────────────────────────────
ENV=production

# ──────────────────────────────
# Qdrant Vector Database Config
# ──────────────────────────────
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# ──────────────────────────────
# Collection Names
# ──────────────────────────────
COLLECTION_NAME=brolly_docs_v8
CACHE_COLLECTION_NAME=brolly_cache_v1
```

> ⚠️ **Never commit your `.env` file to version control.** Add it to `.gitignore` immediately.

---

## 🚀 Deployment & Installation

### Option 1: Docker Compose (Production Recommended)

The `Dockerfile` uses a **multi-stage build** that:
- Creates a **non-root `appuser`** for container security
- Pre-downloads the **embedding model** at build time for rapid cold starts
- Minimizes the final image size by excluding build-time dependencies

The `start.sh` script automatically handles:
- Qdrant database initialization
- Document ingestion from the `documents/` folder
- Uvicorn server startup

#### Step 1 — Add Your Documents

Place your institute PDF files in the `documents/` directory:

```bash
cp /your/source/*.pdf ./documents/
```

#### Step 2 — Build & Launch

```bash
# Build images and start all containers in detached mode
docker-compose up --build -d
```

#### Step 3 — Verify the Deployment

```bash
# Stream logs from the web service to confirm ingestion completed
docker-compose logs -f web

# Check the status of all running containers
docker-compose ps
```

#### Step 4 — Access the API

| Interface | URL |
|-----------|-----|
| **REST API Base** | `http://localhost:8080` |
| **Swagger UI (Interactive Docs)** | `http://localhost:8080/docs` |
| **ReDoc Documentation** | `http://localhost:8080/redoc` |
| **Qdrant Web Dashboard** | `http://localhost:6333/dashboard` |

#### Managing Containers

```bash
# Stop all running containers
docker-compose down

# Stop containers and remove all volumes (full reset)
docker-compose down -v

# Rebuild only the web service
docker-compose up --build web
```

---

### Option 2: Local Development Setup

Use this approach for active debugging and development with hot-reload.

#### Step 1 — Start Qdrant Locally

```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

#### Step 2 — Create a Virtual Environment

```bash
python -m venv venv

# Activate on macOS / Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

#### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4 — Initialize the Cache Collection

```bash
python init_cache.py
```

#### Step 5 — Ingest Documents

Add your PDF files to the `documents/` directory, then run:

```bash
python ingestion.py
```

#### Step 6 — Start the Development Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

> 💡 The `--reload` flag enables **hot-reloading**. Any saved code changes will automatically restart the server.

---

## 📡 API Reference

### POST `/chat`

Handles a single conversational query. Pass the full conversation history on each request for multi-turn context awareness.

#### Endpoint

```
POST http://localhost:8080/chat
Content-Type: application/json
```

#### Request Schema

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `message` | `string` | ✅ Yes | The user's query. Supports English, Telugu, Hindi, Tenglish, and Hinglish. |
| `history` | `array` | ❌ No | Array of previous conversation turns. Each item must include `role` (`user` or `assistant`) and `content` (`string`). |

#### Request Body Example

```json
{
  "message": "Tell me about the BDCP course.",
  "history": [
    {
      "role": "user",
      "content": "Hi"
    },
    {
      "role": "assistant",
      "content": "Hello! I'm the Digital Brolly Assistant. How can I help you today?"
    }
  ]
}
```

#### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `response` | `string` | The assistant's answer. May contain Markdown formatting (bold, bullet lists, etc.). |

#### Response Body Example

```json
{
  "response": "The **Brolly Digital Marketing Career Program (BDCP)** is an intermediate-level course focusing on job-ready digital marketing skills.\n\n- 💰 Total Fee: **₹50,000**\n- 🗓️ Includes a **4-month internship**\n- 🎯 Features a **Placement Guarantee**\n- 🛠️ Includes **3+ Live In-house Projects**"
}
```

#### HTTP Status Codes

| Code | Status | Meaning |
|------|--------|---------|
| `200` | `OK` | Request successful, response returned |
| `422` | `Unprocessable Entity` | Request body validation failed (check field types) |
| `500` | `Internal Server Error` | Unexpected server-side error |

---

#### Example — cURL

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the placement statistics?",
    "history": []
  }'
```

#### Example — Python

```python
import requests

res = requests.post(
    "http://localhost:8080/chat",
    json={
        "message": "What courses do you offer?",
        "history": []
    }
)

print(res.json()["response"])
```

#### Example — JavaScript (fetch)

```javascript
const res = await fetch("http://localhost:8080/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "BDCP course fees enta?",
    history: []
  })
});

const data = await res.json();
console.log(data.response);
```

---

## 📊 Evaluation & Testing

This project uses the **Ragas framework** with `gpt-4o-mini` as an automated LLM judge to rigorously evaluate output quality against ground-truth data.

### Running the Evaluation Suite

```bash
python evaluate_rag.py
```

### Metrics Tracked

| Metric | Description | Target Score |
|--------|-------------|:------------:|
| **Faithfulness** | Measures whether the generated answer is fully supported by the retrieved context. Detects hallucinations — a score of 1.0 means no hallucination. | > 0.90 |
| **Answer Relevancy** | Measures how directly and completely the generated answer addresses the user's query. Penalizes vague or off-topic responses. | > 0.85 |

### Evaluation Output

Results are saved to **`rag_evaluation_report.csv`** with the following columns:

| Column | Description |
|--------|-------------|
| `question` | The test query input |
| `answer` | The generated answer from the RAG pipeline |
| `contexts` | Retrieved document chunks used as context |
| `ground_truth` | The expected correct answer |
| `faithfulness` | Faithfulness score — range 0.0 to 1.0 |
| `answer_relevancy` | Relevancy score — range 0.0 to 1.0 |

---

## 🛡️ Key System Behaviors

### ⚡ Semantic Caching

Questions are cached at the **embedding level** inside Qdrant. On every new query:

- The query is embedded and compared against all cached entries via cosine similarity
- A score **≥ 0.95** triggers an instant cache hit — the stored answer is returned immediately
- New unique Q&A pairs are automatically written to the cache for future use
- Cache hits incur **zero LLM API cost** and respond in milliseconds

**Benefits:**

| Benefit | Detail |
|---------|--------|
| ⚡ Speed | Sub-100ms responses for repeated queries |
| 💰 Cost | Eliminates token costs for common questions |
| 🔒 Consistency | Identical answers for semantically similar queries |

---

### 🌐 Dynamic Language Mirroring

The system prompt is engineered to detect and mirror the user's exact linguistic style in real time.

| User Input Style | Bot Response Style |
|------------------|--------------------|
| Formal English | Formal English |
| Casual English | Casual English |
| Telugu (Tenglish) | Localized Tenglish |
| Hindi (Hinglish) | Localized Hinglish |

**Example:**
> **User:** *"Course duration entha?"*  
> **Bot:** *"BDCP course duration 6 months undi bro, including a 4-month internship! 🎓"*

---

### 🔁 Idempotent Ingestion

The `start.sh` startup script checks whether vector points already exist in the Qdrant collection **before** running the ingestion pipeline.

This prevents:
- Duplicate documents being indexed on container restarts
- Inflated vector counts degrading retrieval quality
- Unnecessary re-processing of already-indexed PDFs

---

### 🛡️ Graceful Fallbacks (Sentinel Logic)

The LLM is strictly sandboxed to only use knowledge from ingested PDFs.

**Flow:**

```
LLM cannot answer from context
          │
          ▼
  Outputs [NOT_FOUND] sentinel
          │
          ▼
  Backend intercepts sentinel
          │
          ▼
  Returns pre-written fallback
  with phone numbers & WhatsApp links
```

This guarantees the assistant **never hallucinates** or invents course details.

---

### 🗜️ Conversation History Compression

For long conversations, raw history is expensive. The system automatically:

- Monitors conversation turn count on every request
- Summarizes all turns **beyond the 4-message threshold** using a compact LLM call
- Keeps the active context window lean and within token limits
- Retains full conversational context without truncation loss

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome.

**To contribute:**

1. Fork the repository
2. Create a new branch
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes and commit
   ```bash
   git commit -m "Add: description of your change"
   ```
4. Push to your branch
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a **Pull Request** with a clear description of the change and its motivation

> For major changes, please open an **Issue** first to discuss the proposal before investing development time.

---

## 📄 License

This project is **proprietary** to Digital Brolly.  
Unauthorized copying, distribution, or modification is strictly prohibited.

© 2024 Digital Brolly. All rights reserved.