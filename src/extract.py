"""Step 4: Structured data extraction for the Power BI dashboard.

Reads the chunks saved by ingestion, keeps the ones that contain numbers or
company news, and asks the LLM to pull out structured records:
  - market_facts: capacity, investment, market size, growth rates, shares
  - company_events: funding, acquisitions, partnerships, project launches

Results are saved to CSV (data/output/) and, if DATABASE_URL is set, PostgreSQL.

Run:  python -m src.extract
"""
import json
import re
from typing import Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field

from src import config
from src.rag import get_llm


class MarketFact(BaseModel):
    metric: Literal[
        "installed_capacity", "annual_additions", "generation", "investment",
        "market_size", "growth_rate", "market_share", "cost", "other",
    ]
    technology: str = Field(description="e.g. solar, wind, offshore wind, hydro, storage, renewables overall")
    region: str = Field(description="Country or region, or 'Global'")
    company: Optional[str] = Field(default=None, description="Company name if the fact is about one company")
    year: Optional[int] = Field(default=None, description="Year the figure refers to")
    value: float
    unit: str = Field(description="e.g. GW, TWh, USD billion, %, USD/kWh")
    description: str = Field(description="One short sentence describing the fact")


class CompanyEvent(BaseModel):
    company: str
    event_type: Literal["funding", "acquisition", "partnership", "project_launch", "expansion", "other"]
    year: Optional[int] = None
    region: Optional[str] = None
    description: str = Field(description="One short sentence")


class Extraction(BaseModel):
    facts: list[MarketFact] = Field(default_factory=list)
    events: list[CompanyEvent] = Field(default_factory=list)


EXTRACTION_PROMPT = """Extract structured renewable energy market data from the text below.
Only extract figures and events that are explicitly stated. Do not estimate or infer numbers.
If nothing relevant is present, return empty lists.

Text (source: {source}):
{text}"""

# Cheap pre-filter so we only pay the LLM for chunks likely to contain data.
SIGNAL = re.compile(
    r"\b(?:GW|MW|TWh|billion|million|percent|capacity|market share)\b|\binvest|\bacquir|\bpartnership|%",
    re.IGNORECASE,
)


def load_candidate_chunks() -> list[dict]:
    if not config.CHUNKS_FILE.exists():
        raise SystemExit("No chunks found. Run `python -m src.ingest` first.")
    chunks = [json.loads(line) for line in open(config.CHUNKS_FILE)]
    candidates = [c for c in chunks if len(SIGNAL.findall(c["text"])) >= 2]
    print(f"{len(candidates)} of {len(chunks)} chunks contain market data signals.")
    return candidates[: config.MAX_EXTRACTION_CHUNKS]


def extract_all(chunks: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    extractor = get_llm().with_structured_output(Extraction)
    facts, events = [], []

    for i, c in enumerate(chunks, start=1):
        source = c["metadata"].get("source")
        try:
            result: Extraction = extractor.invoke(EXTRACTION_PROMPT.format(source=source, text=c["text"]))
        except Exception as e:
            print(f"  chunk {i}: skipped ({e})")
            continue
        facts += [{**f.model_dump(), "source": source} for f in result.facts]
        events += [{**e.model_dump(), "source": source} for e in result.events]
        if i % 20 == 0:
            print(f"  processed {i}/{len(chunks)} chunks - {len(facts)} facts, {len(events)} events")

    facts_df = pd.DataFrame(facts, columns=[*MarketFact.model_fields, "source"])
    events_df = pd.DataFrame(events, columns=[*CompanyEvent.model_fields, "source"])
    facts_df = facts_df.drop_duplicates(subset=["metric", "technology", "region", "year", "value", "unit"])
    events_df = events_df.drop_duplicates(subset=["company", "event_type", "description"])
    return facts_df, events_df


def clean_facts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["technology"] = df["technology"].str.strip().str.lower()
    df["region"] = df["region"].str.strip().str.title().replace({"World": "Global", "Worldwide": "Global"})
    df["unit"] = df["unit"].str.strip()
    # Drop implausible years (LLM occasionally mistakes a number for a year).
    df = df[df["year"].isna() | df["year"].between(1990, 2060)].copy()
    df["year"] = df["year"].astype("Int64")  # whole numbers, blanks allowed
    return df


def save(facts: pd.DataFrame, events: pd.DataFrame) -> None:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    facts.to_csv(config.OUTPUT_DIR / "market_facts.csv", index=False)
    events.to_csv(config.OUTPUT_DIR / "company_events.csv", index=False)
    print(f"Saved {len(facts)} facts and {len(events)} events to {config.OUTPUT_DIR}/")

    if config.DATABASE_URL:
        from sqlalchemy import create_engine

        engine = create_engine(config.DATABASE_URL)
        facts.to_sql("market_facts", engine, if_exists="replace", index=False)
        events.to_sql("company_events", engine, if_exists="replace", index=False)
        print("Also written to PostgreSQL tables: market_facts, company_events")


def main():
    chunks = load_candidate_chunks()
    print(f"Extracting from {len(chunks)} chunks with {config.OPENAI_MODEL}...")
    facts, events = extract_all(chunks)
    save(clean_facts(facts), events)


if __name__ == "__main__":
    main()
