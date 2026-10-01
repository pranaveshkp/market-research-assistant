"""Embeddings + Pinecone vector store setup."""
import os

from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from src import config


def get_embeddings():
    """Return the embedding model and its vector dimension."""
    if config.EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small"), 1536

    # Free, runs locally on your laptop; good quality for semantic search.
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"), 384


def get_vectorstore(create_if_missing: bool = False) -> PineconeVectorStore:
    embeddings, dim = get_embeddings()
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    if not pc.has_index(config.PINECONE_INDEX):
        if not create_if_missing:
            raise RuntimeError(
                f"Pinecone index '{config.PINECONE_INDEX}' not found. Run `python -m src.ingest` first."
            )
        print(f"Creating Pinecone index '{config.PINECONE_INDEX}' (dim={dim})...")
        pc.create_index(
            name=config.PINECONE_INDEX,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    return PineconeVectorStore(index=pc.Index(config.PINECONE_INDEX), embedding=embeddings)
