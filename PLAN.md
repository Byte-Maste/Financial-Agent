# Implementation Plan: Autonomous Financial Wellness Agent

## Target Stack
- **Backend:** Python 3.13+, FastAPI, LangChain + LangGraph, SQLAlchemy (async), PostgreSQL + pgvector
- **LLM:** Gemini API — `gemini-2.0-flash` (routing/advice), `text-embedding-004` (768-dim embeddings)
- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **Validation:** Pydantic (backend), Zod (frontend)

## Directory Structure
```
financial_agentic_system/
├── agents/                  # LangGraph nodes
│   ├── orchestrator.py      # Master Selector + compiled graph
│   ├── ingestion_agent.py
│   ├── categorization_agent.py
│   ├── analysis_agent.py
│   ├── anomaly_agent.py
│   ├── forecast_agent.py
│   └── advisor_agent.py
├── api/v1/
│   ├── ingestion.py         # POST /api/v1/ingest
│   ├── chat.py              # WS /api/v1/ws (streams graph)
│   └── advisor.py           # GET /api/v1/advice/{user_id}
├── core/
│   ├── config.py            # pydantic-settings
│   ├── database.py          # async engine + sessions
│   └── deps.py              # DI helpers
├── db/migrations/
│   ├── 001_schema.sql       # users + transactions tables
│   └── 002_pgvector.sql     # merchant_embeddings + HNSW index
├── schemas/
│   ├── models.py            # Transaction, UserState, IngestionResult
│   ├── state.py             # AgentState TypedDict
│   └── routing.py           # OrchestratorRoutingContract
├── services/
│   ├── parsing_service.py   # PDF (pdfplumber), CSV (pandas), UPI text (Gemini structured)
│   ├── ingestion_service.py # SHA256 dedup + batch DB insert
│   ├── embedding_service.py # text-embedding-004 -> pgvector upsert
│   ├── category_service.py  # cosine >85% -> reuse; else -> Gemini classification
│   ├── analytics.py         # FHS formula: 30*Sr + 20*(1-Dr) + 20*Cs + 30*min(1,EF/6)
│   ├── anomaly_service.py   # Rolling Z-score (90d) + 60s duplicate detection
│   ├── forecaster.py        # 30-day cash flow projection
│   └── subscription_service.py # Recurring charge detection + inactivity flags
├── frontend/
├── tests/
├── main.py                  # FastAPI entrypoint
├── requirements.txt
├── .env.example
├── CONTRIBUTING.md
└── PLAN.md
```

## Phases

| Phase | What | Key Files |
|-------|------|-----------|
| 1 | Scaffold + venv + deps | `requirements.txt`, `.venv/` |
| 2 | Core config + DB + schemas | `core/config.py`, `core/database.py`, `schemas/*` |
| 3 | DB migrations | `db/migrations/001_schema.sql`, `002_pgvector.sql` |
| 4 | Ingestion pipeline | `services/parsing_service.py`, `ingestion_service.py`, `api/v1/ingestion.py`, `agents/ingestion_agent.py` |
| 5 | Master Orchestrator | `agents/orchestrator.py`, `schemas/state.py`, `schemas/routing.py` |
| 6 | Categorization Engine | `services/embedding_service.py`, `category_service.py`, `agents/categorization_agent.py` |
| 7 | Analytics + Anomaly | `services/analytics.py`, `anomaly_service.py`, `agents/analysis_agent.py`, `anomaly_agent.py` |
| 8 | Forecast + Subs | `services/forecaster.py`, `subscription_service.py`, `agents/forecast_agent.py` |
| 9 | Advisor + WS | `agents/advisor_agent.py`, `services/notification_service.py`, `api/v1/chat.py` |
| 10 | Frontend | React + Vite + Tailwind scaffold |
| 11 | Tests | `tests/conftest.py`, `tests/test_*.py` |

## Design Rules (from CONTRIBUTING.md)

| Rule | Enforcement |
|------|-------------|
| **1. No Swiss-Army Agents** | `master_selector` -> conditional edges -> single worker per turn. Workers never call workers. |
| **2. Strict Data Contracts** | All LLM output via `with_structured_output(PydanticModel)`. Validation errors caught. |
| **3. Lean Context Windows** | Aggregates in pandas/numpy first. Only summary reports passed to LLM. |
| **4. Async Everything** | FastAPI routes async. DB via `asyncpg` + `AsyncSession`. |
| **5. Gemini API** | `ChatGoogleGenerativeAI(model="gemini-2.0-flash")`, `text-embedding-004` (768-dim). |
