# Renewable Energy Market Research Assistant

An AI research assistant that answers market questions about the renewable energy industry (solar, wind, hydro, storage) from public sources, with a citation for every claim. It also extracts 1,000+ structured market data points into PostgreSQL and visualizes them in an interactive Tableau dashboard.
[Try the research assistant](https://market-research-assistant-7gfxtezzdz6oqwcfyhhtvi.streamlit.app/)
 Live dashboard:[Renewable Energy Market Overview on Tableau Public](https://public.tableau.com/app/profile/pranavesh.kotike/viz/RenewableEnergyMarketOverview/Dashboard1?publish=yes)

[Dashboard](docs/screenshots/dashboard.png)

**Stack:** Python · LangChain · LangGraph · LangSmith · OpenAI API · Pinecone · Hugging Face embeddings · PostgreSQL · Tableau · Streamlit


## Setup (Mac)

### 1. Install Python 3.11+ and PostgreSQL
```bash
brew install python@3.11 postgresql@16
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
createdb market_research
```
(Don't have Homebrew? Install it from https://brew.sh first.)

> **Apple Silicon (M1–M4) note:** run `uname -m` in your terminal. It must say `arm64`. If it says `x86_64`, your terminal or editor is the Intel build running under Rosetta, and Homebrew will compile everything from source very slowly. Install the Apple Silicon version of your editor/terminal and make sure `which brew` shows `/opt/homebrew/bin/brew`.

### 2. Create a virtual environment and install packages
```bash
cd market-research-assistant
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Get API keys and create `.env`
```bash
cp .env.example .env
```
Then open `.env` and fill in:
- **OPENAI_API_KEY**: platform.openai.com → API keys. Add about $5 of credit; this project uses far less.
- **PINECONE_API_KEY**: app.pinecone.io → free Starter plan → API Keys. The index is created automatically.
- **LANGSMITH_API_KEY**: smith.langchain.com → free Developer plan → Settings → API Keys.

If `OPENAI_MODEL` gives a "model not found" error, check platform.openai.com/docs/models and set it to a current small model.

---

## Run it

```bash
# 1. Ingest sources into Pinecone (~2–5 min; first run downloads the embedding model)
python -m src.ingest

# 2. Try a question from the terminal
python -m src.rag "What is the global installed solar PV capacity?"
python -m src.graph "Compare offshore wind in Europe and China"

# 3. Launch the chat app
streamlit run app.py

# 4. Extract structured market data (~$0.50–2 with gpt-4o-mini)
python -m src.extract

# 5. Standardize units (MW/TW → GW, etc.) and technology names,
#    update PostgreSQL, and create data/output/market_data.xlsx
python -m src.clean

# 6. Evaluate answer quality
python -m src.evaluate
```

Then build the dashboard in Tableau Public: see **[docs/tableau_guide.md](docs/tableau_guide.md)**.

## Adding industry reports (recommended)

Wikipedia pages get you started, but real industry reports make the project much stronger. Download free PDFs from these, drop them into `data/raw/pdfs/`, and re-run `python -m src.ingest`:
- **IEA**: *Renewables* annual market report (iea.org → Reports)
- **IRENA**: *Renewable Capacity Statistics* and *Renewable Power Generation Costs* (irena.org → Publications)
- **Ember**: *Global Electricity Review* (ember-energy.org)
- **REN21**: *Renewables Global Status Report* (ren21.net)

Keep it to about 5–10 PDFs at first. Large reports can be hundreds of pages.

## Deploy (free)

1. Push to GitHub (`.env` is git-ignored, so your keys stay private).
2. Go to share.streamlit.io → New app → pick your repo → main file `app.py`.
3. In **Advanced settings → Secrets**, paste your `.env` contents in TOML format:
   ```toml
   OPENAI_API_KEY = "sk-..."
   PINECONE_API_KEY = "..."
   PINECONE_INDEX = "renewable-energy-research"
   EMBEDDING_PROVIDER = "huggingface"
   ```
   The app only needs Pinecone and OpenAI; PostgreSQL is only for the dashboard.


---


