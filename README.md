# AI-Assistant

A modular AI assistant project built with **FastAPI**, **Ollama**, **Retrieval-Augmented Generation (RAG)**, lightweight **tool calling**, and a simple **HTML/CSS/JavaScript** frontend.

This project is designed to simulate a practical local AI assistant that can:
- answer user queries through an LLM,
- search external knowledge sources like Wikipedia, DuckDuckGo, and arXiv,
- remember prior conversation in the current runtime,
- retrieve context from local PDF documents,
- and provide responses through a simple chat interface.

It is a strong portfolio project for students and beginner-to-intermediate AI/ML developers because it combines backend APIs, local LLM usage, semantic retrieval, prompt engineering, and frontend-backend integration in one complete application.

---

## Overview

`AI-Assistant` is a full-stack assistant project organized into separate folders for backend, frontend, and local environment setup.

The backend handles:
- chat processing,
- tool routing,
- document retrieval,
- short-term memory,
- prompt construction,
- and local LLM response generation.

The frontend provides a minimal browser-based chat interface that sends user input to the backend and displays the assistant’s replies.

The system supports three main assistant behaviors:
1. **Normal chat** using a local LLM
2. **Tool-based search** using commands such as `wiki`, `search`, and `arxiv`
3. **Document-aware answering** using local PDF-based retrieval

This project is intended for local development and experimentation rather than large-scale production deployment.

---

## Key Features

- FastAPI backend for chat handling
- Ollama-powered local LLM inference
- Retrieval-Augmented Generation using local PDFs
- Semantic search with sentence embeddings
- ChromaDB-based vector storage
- Simple tool routing for:
  - Wikipedia search
  - DuckDuckGo web search
  - arXiv paper search
- In-memory conversation history
- Lightweight frontend chat UI
- Modular project structure for easier extension
- Beginner-friendly code organization

---

## Tech Stack

### Backend
- Python
- FastAPI
- Uvicorn
- Pydantic

### LLM and Retrieval
- Ollama
- Sentence Transformers
- ChromaDB
- PyPDF

### Search Tools
- Wikipedia
- DuckDuckGo Search
- arXiv

### Frontend
- HTML
- CSS
- JavaScript

---

## Project Structure

```bash
AI-Assistant/
├── backend/
│   ├── app.py
│   ├── llm.py
│   ├── prompts.py
│   ├── tools.py
│   ├── memory.py
│   ├── rag.py
│   ├── requirements.txt
│   ├── documents/
│   └── uploaded_docs/
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
└── .gitignore
```
---
How the System Works
1. User sends a message
- The frontend takes a text message from the user and sends it to the backend chat endpoint.
2. Backend receives the message
- The FastAPI backend exposes a /chat endpoint that receives the user message and decides how to process it.
3. Tool routing happens first
- If the user message starts with a command prefix, the backend routes the request directly to a tool:
    - wiki <topic> → Wikipedia summary
    - search <query> → DuckDuckGo search results
    - arxiv <topic> → arXiv paper summaries
- If a tool route is triggered, the backend returns that tool result directly.
4. RAG context is retrieved
- If the input is a normal chat message, the backend queries the local document index to fetch the most relevant PDF content.
5. Memory is updated
- The user message is added to in-memory conversation history. The assistant uses this history to preserve short-term conversational continuity during the current runtime.
6. System prompt is built
- A system prompt is created dynamically using the retrieved document context. This allows the model to use local document information when it is relevant.
7. Local LLM generates a response
- The backend sends the full message list to Ollama using the phi3:latest model and returns the generated response.
8. Assistant response is stored
- The assistant’s response is added back to memory so later turns can use the conversation history.
---
## Retrieval-Augmented Generation
- This project includes a simple RAG pipeline.
## Document loading
- At backend startup, the application scans the backend/documents/ folder for PDF files and loads their contents into a vector collection.
## Embedding generation
- The system uses the all-MiniLM-L6-v2 sentence transformer model to convert document text and user queries into embeddings.
## Retrieval
- When a normal message is sent, the backend retrieves the most relevant document content and injects it into the system prompt.
## Why this matters
- This allows the assistant to answer using local document knowledge instead of relying only on the LLM’s base model behavior.
---
<img width="708" height="516" alt="image" src="https://github.com/user-attachments/assets/b6bf0d2b-10e2-46c4-a9f5-8f768e85ae31" />

---
## Python Version Compatibility
- This project is not recommended for the latest Python versions.
- A safer choice is to use:
    - Python 3.10
    - Python 3.11
- You may face installation or compatibility issues on newer Python releases because libraries such as:
    - chromadb
    - sentence-transformers
    - torch dependencies pulled indirectly
    - and some local LLM-related tooling
- may not always behave reliably on the newest Python versions depending on your operating system and package resolution.
- Recommended setup
- Use a virtual environment with Python 3.10 for the most stable experience.
- Example:
  - python3.10 -m venv venv
  - If you already have a newer Python installed, it is better to install Python 3.10 separately and create the environment       using that version.
---
## Installation
1. Clone the repository
- git clone https://github.com/ANIKET12SENGUPTA/AI-Assistant.git
- cd AI-Assistant
2. Create a virtual environment with a supported Python version
- Windows:
  - py -3.10 -m venv venv
  - venv\Scripts\activate
- macOS / Linux
  - python3.10 -m venv venv
  - source venv/bin/activate
3. Install backend dependencies
- cd backend
- pip install -r requirements.txt
4. Install and start Ollama
- Make sure Ollama is installed on your system and that the required model is available locally.

This project currently calls: phi3:latest
- So you should ensure that model is available in your local Ollama setup before running the backend.
5. Add PDF documents
- Place your PDF files inside:
    - backend/documents/
    - These files will be loaded for retrieval when the backend starts.

---
## Running the Project
- Start the backend
- From the backend/ directory:
    - uvicorn app:app --reload
- By default, the backend should run on:
    - http://127.0.0.1:8000
- Start the frontend
- Open frontend/index.html in your browser.
- If your frontend expects the backend on localhost, make sure the backend server is running before sending any messages.
---
## Example Usage
- Normal chat:
  - What is machine learning?
  - Behavior:
    - retrieves relevant document context if available
    - adds conversation to memory
    - sends prompt to the LLM
    - returns generated response
- Tool-based query:
  - wiki Artificial intelligence
  - Behavior:
    - directly returns a Wikipedia summary
- Search query:
  - search best use cases of RAG
  - Behavior:
    - returns DuckDuckGo snippets
- Research query:
  - arxiv large language models
  - Behavior:
    - returns arXiv paper titles and summaries
---
## Use Cases
- Personal AI assistant prototype
- Beginner GenAI portfolio project
- Local document question-answering assistant
- FastAPI + Ollama integration demo
- RAG experimentation project
- Multi-tool assistant prototype
- Frontend-backend AI chat project
---
## Skills Demonstrated
- FastAPI backend development
- Local LLM integration with Ollama
- Prompt engineering
- Retrieval-Augmented Generation
- Semantic search using embeddings
- Vector database usage with ChromaDB
- PDF document ingestion
- Frontend-backend communication
- Basic memory handling for chat systems
- Tool-augmented assistant design
- Modular Python project organization
---
## License
This project is licensed under the MIT License.
