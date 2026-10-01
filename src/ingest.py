"""Step 1: Ingestion pipeline.

Loads web pages (data/sources.yaml) and PDFs (data/raw/pdfs/), cleans the text,
splits it into overlapping chunks, embeds them, and stores them in Pinecone.
Also saves the chunks to data/processed/chunks.jsonl for the extraction step.

Run:  python -m src.ingest
"""
import hashlib
import json
import re

import yaml
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config
from src.vectorstore import get_vectorstore

# Wikipedia/web boilerplate we don't want in the index.
NOISE_PATTERNS = [
    r"\[\d+\]",                 # citation markers like [12]
    r"\[citation needed\]",
    r"\[edit\]",
    r"Jump to navigation|Jump to search",
]


def clean_text(text: str) -> str:
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def load_web_pages() -> list[Document]:
    urls = yaml.safe_load(config.SOURCES_FILE.read_text()).get("urls", [])
    docs = []
    for url in urls:
        try:
            loaded = WebBaseLoader(url).load()
            for d in loaded:
                d.metadata = {"source": url, "title": d.metadata.get("title", url), "type": "web"}
            docs.extend(loaded)
            print(f"  loaded  {url}")
        except Exception as e:  # keep going if one site fails
            print(f"  FAILED  {url}: {e}")
    return docs


def load_pdfs() -> list[Document]:
    docs = []
    for pdf in sorted(config.RAW_PDF_DIR.glob("*.pdf")):
        try:
            pages = PyPDFLoader(str(pdf)).load()
            for p in pages:
                p.metadata = {
                    "source": pdf.name,
                    "title": pdf.stem.replace("_", " "),
                    "page": p.metadata.get("page", 0) + 1,
                    "type": "pdf",
                }
            docs.extend(pages)
            print(f"  loaded  {pdf.name} ({len(pages)} pages)")
        except Exception as e:
            print(f"  FAILED  {pdf.name}: {e}")
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    for d in docs:
        d.page_content = clean_text(d.page_content)
    docs = [d for d in docs if len(d.page_content) > 200]  # drop near-empty pages

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = i
    return chunks


def chunk_id(chunk: Document) -> str:
    """Deterministic ID so re-running ingestion overwrites instead of duplicating."""
    key = f"{chunk.metadata['source']}|{chunk.metadata.get('page', '')}|{chunk.page_content[:200]}"
    return hashlib.sha1(key.encode()).hexdigest()


def save_chunks(chunks: list[Document]) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.CHUNKS_FILE, "w") as f:
        for c in chunks:
            f.write(json.dumps({"text": c.page_content, "metadata": c.metadata}) + "\n")


def main():
    print("Loading sources...")
    docs = load_web_pages() + load_pdfs()
    if not docs:
        raise SystemExit("No documents loaded. Check data/sources.yaml or add PDFs to data/raw/pdfs/.")

    chunks = chunk_documents(docs)
    print(f"Split {len(docs)} documents into {len(chunks)} chunks.")
    save_chunks(chunks)

    print("Embedding and uploading to Pinecone (first run downloads the embedding model)...")
    vs = get_vectorstore(create_if_missing=True)
    vs.add_documents(chunks, ids=[chunk_id(c) for c in chunks], batch_size=64)
    print(f"Done. {len(chunks)} chunks stored in index '{config.PINECONE_INDEX}'.")


if __name__ == "__main__":
    main()
