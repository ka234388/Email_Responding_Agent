import os
import fitz
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def load_knowledge_base(kb_folder="knowledge_base"):
    all_chunks = []
    for filename in os.listdir(kb_folder):
        filepath = os.path.join(kb_folder, filename)
        if filename.endswith(".pdf"):
            print(f"Loading PDF: {filename}")
            text = extract_text_from_pdf(filepath)
            chunks = chunk_text(text)
            all_chunks.extend(chunks)
        elif filename.endswith(".txt"):
            print(f"Loading TXT: {filename}")
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
            all_chunks.extend(chunks)
    print(f"Total chunks loaded: {len(all_chunks)}")
    return all_chunks

def build_faiss_index(docs):
    embeddings = model.encode(docs, convert_to_numpy=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index, embeddings

def search_kb(query, docs, index, top_k=3):
    query_vec = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vec, top_k)
    results = [docs[i] for i in indices[0] if i < len(docs)]
    return "\n\n".join(results)