import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx

from app.rag_service import get_answer
from app.prompts import CONTACT_INFO
from app.config import APPS_SCRIPT_URL
from init_cache import setup_collections

app = FastAPI(root_path="/rag_chatbot")

@app.on_event("startup")
async def startup_event():
    setup_collections()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = []

class ChatResponse(BaseModel):
    answer: str
    contact_info: Optional[dict] = None

class LeadInfo(BaseModel):
    name: str
    email: str
    phone: str

@app.get("/")
def home():
    return {"message": "Digital Brolly RAG Chatbot API Running"}

@app.post("/chat")
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        return ChatResponse(answer="Please enter your question.")
    
    question = request.message
    history = request.history
    
    answer = get_answer(question, history)
    
    contact_info = None
    if "whatsapp" in answer.lower() or "call" in answer.lower():
        contact_info = {
            "phone_numbers": CONTACT_INFO['phone_numbers'],
            "whatsapp": f"https://wa.me/{CONTACT_INFO['whatsapp_number'].replace('+', '')}",
            "call_link": f"tel:{CONTACT_INFO['phone_numbers'][0]}"
        }
        
    return ChatResponse(answer=answer, contact_info=contact_info)

@app.post("/submit-lead")
async def submit_lead(lead: LeadInfo):
    if not APPS_SCRIPT_URL:
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    try:
        async with httpx.AsyncClient(verify=True, timeout=20.0, follow_redirects=True) as client:
            response = await client.post(APPS_SCRIPT_URL, json=lead.dict())
            
            if not response.text.strip().startswith('{'):
                raise Exception("Unexpected response from Apps Script")
                
            result = response.json()
            if result.get("status") == "error":
                raise Exception(result.get("message"))
                
            return {"status": "success", "message": "Lead saved"}
            
    except Exception as e:
        print(f"Lead submission error: {repr(e)}")
        raise HTTPException(status_code=500, detail="Failed to save lead.")