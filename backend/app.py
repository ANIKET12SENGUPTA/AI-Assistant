from prompts import build_system_prompt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import generate_response
from memory import add_memory, get_memory
from rag import load_documents, query_documents
from tools import wiki_search, duck_search, arxiv_search

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    load_documents()

class Message(BaseModel):
    message: str

@app.post("/chat")
async def chat(msg: Message):

    user_input = msg.message.lower()

    # TOOL ROUTING
    if user_input.startswith("wiki "):
        result = wiki_search(user_input.replace("wiki ", ""))
        return {"response": result}

    if user_input.startswith("arxiv "):
        result = arxiv_search(user_input.replace("arxiv ", ""))
        return {"response": result}

    if user_input.startswith("search "):
        result = duck_search(user_input.replace("search ", ""))
        return {"response": result}

    # RAG
    context = query_documents(user_input)

    # MEMORY
    add_memory("user", msg.message)
    messages = get_memory()

    # SYSTEM PROMPT
    system_prompt = build_system_prompt(context)
    full_messages = [system_prompt] + messages

    full_messages = [system_prompt] + messages

    response = generate_response(full_messages)

    add_memory("assistant", response)

    return {"response": response}