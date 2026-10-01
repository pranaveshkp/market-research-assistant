"""Step 3: Multi-step research with LangGraph.

Broad questions ("Compare solar and wind growth in Asia and Europe") need facts
from several places. The graph:
    plan       -> break the question into up to 4 focused sub-questions
    retrieve   -> search Pinecone for each sub-question, de-duplicate results
    synthesize -> write one cited answer from all retrieved passages
"""
from typing import TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.rag import format_sources, generate_answer, get_llm
from src.vectorstore import get_vectorstore


class ResearchState(TypedDict, total=False):
    question: str
    sub_questions: list[str]
    docs: list[Document]
    answer: str
    sources: list[dict]


class Plan(BaseModel):
    sub_questions: list[str] = Field(
        description="1-4 short, specific search queries that together answer the question. "
        "Use 1 if the question is already simple."
    )


def plan(state: ResearchState) -> ResearchState:
    planner = get_llm().with_structured_output(Plan)
    result = planner.invoke(
        "You plan research for a renewable energy market analyst. "
        f"Break this question into focused search queries:\n\n{state['question']}"
    )
    return {"sub_questions": result.sub_questions[:4] or [state["question"]]}


def retrieve(state: ResearchState) -> ResearchState:
    vs = get_vectorstore()
    seen, docs = set(), []
    for q in state["sub_questions"]:
        for d in vs.similarity_search(q, k=4):
            key = d.page_content[:200]
            if key not in seen:
                seen.add(key)
                docs.append(d)
    return {"docs": docs[:12]}  # cap context size (cost + focus)


def synthesize(state: ResearchState) -> ResearchState:
    return {
        "answer": generate_answer(state["question"], state["docs"]),
        "sources": format_sources(state["docs"]),
    }


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("plan", plan)
    g.add_node("retrieve", retrieve)
    g.add_node("synthesize", synthesize)
    g.add_edge(START, "plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


_graph = None


def research(question: str) -> dict:
    global _graph
    if _graph is None:
        _graph = build_graph()
    result = _graph.invoke({"question": question})
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "sub_questions": result["sub_questions"],
    }


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Compare the growth of solar and wind power in China and Europe."
    r = research(q)
    print("Sub-questions:", r["sub_questions"], "\n")
    print(r["answer"])
