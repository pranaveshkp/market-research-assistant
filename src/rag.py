"""Step 2: Basic RAG - retrieve relevant chunks and answer with citations."""
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src import config
from src.vectorstore import get_vectorstore

SYSTEM_PROMPT = """You are a market research analyst covering the renewable energy industry.
Answer the question using ONLY the numbered context passages below.

Rules:
- Cite every factual claim with the passage number in square brackets, e.g. [2].
- Include specific figures (capacity in GW, investment in USD, growth %, year) when the context has them.
- If passages disagree, say so and cite both.
- If the context does not contain the answer, say "The sources I have don't cover this." Do not guess.

Context:
{context}"""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    # temperature 0 = consistent, factual answers
    return ChatOpenAI(model=config.OPENAI_MODEL, temperature=temperature)


def format_context(docs: list[Document]) -> str:
    parts = []
    for i, d in enumerate(docs, start=1):
        page = f", p.{d.metadata['page']}" if d.metadata.get("page") else ""
        parts.append(f"[{i}] (Source: {d.metadata.get('title', d.metadata.get('source'))}{page})\n{d.page_content}")
    return "\n\n".join(parts)


def format_sources(docs: list[Document]) -> list[dict]:
    return [
        {
            "n": i,
            "title": d.metadata.get("title"),
            "source": d.metadata.get("source"),
            "page": d.metadata.get("page"),
            "excerpt": d.page_content[:300],
        }
        for i, d in enumerate(docs, start=1)
    ]


def generate_answer(question: str, docs: list[Document]) -> str:
    chain = PROMPT | get_llm()
    return chain.invoke({"question": question, "context": format_context(docs)}).content


def answer(question: str, k: int = config.TOP_K) -> dict:
    """Single-step RAG: one retrieval, one answer."""
    docs = get_vectorstore().similarity_search(question, k=k)
    return {"answer": generate_answer(question, docs), "sources": format_sources(docs)}


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What is the global installed solar PV capacity?"
    result = answer(q)
    print(result["answer"])
    print("\nSources:")
    for s in result["sources"]:
        print(f"  [{s['n']}] {s['title']} - {s['source']}")
