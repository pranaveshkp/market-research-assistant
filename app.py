"""Streamlit chat UI.

Run:  streamlit run app.py
"""
import streamlit as st

from src.graph import research
from src.rag import answer

st.set_page_config(page_title="Renewable Energy Market Research Assistant", page_icon="⚡", layout="wide")

st.title("⚡ Renewable Energy Market Research Assistant")
st.caption("Ask about market size, installed capacity, growth, investment, and key players. Every answer cites its sources.")

with st.sidebar:
    st.header("Settings")
    deep = st.toggle(
        "Deep research mode",
        value=True,
        help="Breaks complex questions into sub-questions with LangGraph before answering. Slower but more thorough.",
    )
    st.divider()
    st.markdown("**Try asking:**")
    examples = [
        "What is the global installed solar PV capacity and how fast is it growing?",
        "Which countries lead in wind power capacity?",
        "Compare offshore wind development in Europe and China.",
        "What are the main challenges for grid energy storage?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander(f"Sources ({len(m['sources'])})"):
                for s in m["sources"]:
                    page = f" (p.{s['page']})" if s.get("page") else ""
                    st.markdown(f"**[{s['n']}] {s['title']}**{page} — {s['source']}")
                    st.caption(s["excerpt"] + "…")

question = st.chat_input("Ask a market research question...") or st.session_state.pop("pending", None)

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Researching..."):
            result = research(question) if deep else answer(question)
        if deep and result.get("sub_questions"):
            st.caption("Searched: " + " · ".join(result["sub_questions"]))
        st.markdown(result["answer"])
        with st.expander(f"Sources ({len(result['sources'])})"):
            for s in result["sources"]:
                page = f" (p.{s['page']})" if s.get("page") else ""
                st.markdown(f"**[{s['n']}] {s['title']}**{page} — {s['source']}")
                st.caption(s["excerpt"] + "…")

    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "sources": result["sources"]}
    )
