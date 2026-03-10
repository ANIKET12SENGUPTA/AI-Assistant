from sentence_transformers import SentenceTransformer
import chromadb
import os
from pypdf import PdfReader

model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="docs")


def load_documents():
    folder = "backend/documents"

    if not os.path.exists(folder):
        return

    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            file_path = os.path.join(folder, file)

            reader = PdfReader(file_path)
            text = ""

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text

            if text.strip() == "":
                continue

            embedding = model.encode(text).tolist()

            collection.add(
                documents=[text],
                embeddings=[embedding],
                ids=[file]
            )


def query_documents(query):
    embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=1
    )

    # Safe checking
    if (
        "documents" in results
        and len(results["documents"]) > 0
        and len(results["documents"][0]) > 0
    ):
        return results["documents"][0][0]

    return ""