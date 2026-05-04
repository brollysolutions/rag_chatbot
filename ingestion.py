import os
import uuid
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, VECTOR_SIZE

# Define the folder where all your PDFs will live
DOCS_DIR = "documents"

qdrant_client = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))

def setup_collection():
    """Deletes old collection and creates a fresh one. Only run ONCE per ingestion."""
    if qdrant_client.collection_exists(COLLECTION_NAME):
        print(f"Deleting old collection: {COLLECTION_NAME}")
        qdrant_client.delete_collection(COLLECTION_NAME)

    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        ),
    )
    print(f"Created fresh collection: {COLLECTION_NAME}\n")

# Load models once globally
embedding_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    length_function=len,
    separators=["\n\n", "\n", " "]
)

def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    extracted_text = ""
    for page in doc:
        text = page.get_text()
        if text:
            clean_text = " ".join(text.split())
            extracted_text += clean_text + "\n\n"
    return extracted_text

def ingest_file(file_path: str):
    filename = os.path.basename(file_path)
    print(f"Reading: {filename}")
    
    full_text = extract_text_from_pdf(file_path)
    if not full_text.strip():
        print(f"Warning: No readable text found in {filename}. Skipping.")
        return

    print("Chunking...")
    chunks = text_splitter.split_text(full_text)
    
    print(f"Embedding {len(chunks)} chunks...")
    embeddings = embedding_model.encode(chunks, show_progress_bar=True).tolist()
    
    points = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{filename}_{i}_{chunks[i]}")),
            vector=embeddings[i],
            payload={
                "text": chunks[i],
                "chunk_index": i,
                "source": filename  # Injecting the source document name!
            }
        )
        for i in range(len(chunks))
    ]
    
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"✅ Uploaded {filename} to Qdrant.\n")

def ingest_directory(directory: str):
    # 1. Create the directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created '{directory}' folder. Please place your PDFs inside and run again.")
        return

    # 2. Find all PDFs
    pdf_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in the '{directory}' folder.")
        return

    print(f"Found {len(pdf_files)} PDF(s). Starting mass ingestion...\n")
    
    # 3. Reset the database
    setup_collection()

    # 4. Process each file
    for pdf in pdf_files:
        ingest_file(pdf)
        
    print("🎉 All documents processed successfully!")

if __name__ == "__main__":
    ingest_directory(DOCS_DIR)