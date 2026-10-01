"""Step 5: Evaluate answer quality.

For each test question, measures:
  - keyword_hit:  does the answer contain the expected terms?
  - has_citation: does the answer cite at least one source like [1]?
  - groundedness: LLM judge (1-5) - is every claim supported by the retrieved passages?
  - refused_correctly: for unanswerable questions, did it decline instead of guessing?

With LANGSMITH_TRACING=true every run is also traced in LangSmith, so you can
open any low-scoring answer and see exactly which chunks were retrieved.

Run:  python -m src.evaluate
"""
import re

import pandas as pd
import yaml
from pydantic import BaseModel, Field

from src import config
from src.graph import research
from src.rag import get_llm


class Judgement(BaseModel):
    score: int = Field(ge=1, le=5, description="5 = every claim supported by the passages, 1 = mostly unsupported")
    reason: str


JUDGE_PROMPT = """You are grading a research assistant's answer.
Score from 1 to 5 how well EVERY factual claim in the answer is supported by the source passages.

Question: {question}

Source passages:
{passages}

Answer:
{answer}"""

REFUSAL = re.compile(r"don't cover|do not cover|not (contain|mention|include)|no information", re.IGNORECASE)


def main():
    tests = yaml.safe_load(open(config.ROOT / "eval" / "questions.yaml"))["questions"]
    judge = get_llm().with_structured_output(Judgement)
    rows = []

    for t in tests:
        q = t["question"]
        print(f"- {q}")
        r = research(q)
        ans = r["answer"]
        passages = "\n\n".join(f"[{s['n']}] {s['excerpt']}" for s in r["sources"])
        row = {"question": q, "answer": ans, "has_citation": bool(re.search(r"\[\d+\]", ans))}

        if t.get("answerable", True):
            kws = t.get("expect_keywords", [])
            row["keyword_hit"] = all(k.lower() in ans.lower() for k in kws)
            j = judge.invoke(JUDGE_PROMPT.format(question=q, passages=passages, answer=ans))
            row["groundedness"], row["judge_reason"] = j.score, j.reason
        else:
            row["refused_correctly"] = bool(REFUSAL.search(ans))
        rows.append(row)

    df = pd.DataFrame(rows)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.OUTPUT_DIR / "eval_results.csv", index=False)

    answerable = df[df["groundedness"].notna()] if "groundedness" in df else df.iloc[0:0]
    print("\n=== Results ===")
    print(f"Avg groundedness (1-5): {answerable['groundedness'].mean():.2f}")
    print(f"Keyword hit rate:       {answerable['keyword_hit'].mean():.0%}")
    print(f"Answers with citations: {df['has_citation'].mean():.0%}")
    if "refused_correctly" in df:
        print(f"Correct refusals:       {df['refused_correctly'].dropna().mean():.0%}")
    print(f"Details: {config.OUTPUT_DIR / 'eval_results.csv'}")


if __name__ == "__main__":
    main()
