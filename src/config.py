"""Central settings, loaded from the .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PDF_DIR = DATA_DIR / "raw" / "pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"
SOURCES_FILE = DATA_DIR / "sources.yaml"
CHUNKS_FILE = PROCESSED_DIR / "chunks.jsonl"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "renewable-energy-research")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")
MAX_EXTRACTION_CHUNKS = int(os.getenv("MAX_EXTRACTION_CHUNKS", "300"))

# Chunking: ~1000 characters keeps one idea (a paragraph or a table row group)
# per chunk; 150 overlap stops facts being cut in half at chunk borders.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Number of chunks retrieved per question.
TOP_K = 6

# WebBaseLoader warns without a user agent.
os.environ.setdefault("USER_AGENT", "market-research-assistant/1.0 (student project)")
