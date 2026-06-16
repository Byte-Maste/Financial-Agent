# Implementation Plan: Autonomous Financial Wellness Agent

## Target Stack
- **Backend:** Python 3.13+, FastAPI, LangChain + LangGraph, SQLAlchemy (async), PostgreSQL
- **LLM:** Groq API — `llama-3.3-70b-versatile` via raw `groq.Groq` SDK
- **Embeddings:** Voyage AI — `voyage-3-lite` (512-dim), stored as JSONB
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
│   ├── budget_agent.py
│   └── advisor_agent.py
├── api/v1/
│   ├── ingestion.py         # POST /api/v1/ingest (full pipeline)
│   ├── chat.py              # POST /chat (orchestrator)
│   └── advisor.py           # GET /api/v1/advice/{user_id}
├── core/
│   ├── config.py            # pydantic-settings (groq + voyage)
│   ├── database.py          # async engine + sessions
│   ├── deps.py              # DI helpers
│   └── llm_logger.py        # Prompt/response dump to logs/llm/
├── db/
│   ├── setup.sql            # Local DB bootstrap (3 tables)
│   └── supabase_setup.sql   # Supabase variant
├── schemas/
│   ├── models.py            # Transaction (with transaction_type), AnalyticsReport, etc.
│   ├── state.py             # AgentState TypedDict
│   └── routing.py           # OrchestratorRoutingContract
├── services/
│   ├── parsing_service.py   # PDF (pdfplumber), CSV (pandas), UPI text (Groq structured)
│   ├── ingestion_service.py # SHA256 dedup + batch DB insert
│   ├── embedding_service.py # Voyage AI -> JSONB
│   ├── category_service.py  # Cosine > 0.75 -> reuse; else -> Groq classification
│   ├── analytics.py         # FHS formula: 30*Sr + 20*(1-Dr) + 20*Cs + 30*min(1,EF/6)
│   ├── anomaly_service.py   # Rolling Z-score + 60s duplicate detection
│   ├── forecaster.py        # 30-day cash flow projection
│   ├── subscription_service.py # Recurring charge detection + inactivity flags
│   ├── notification_service.py # Build alerts from anomalies + forecast
│   └── llm_service.py       # FallbackLLM wrapping raw groq.AsyncGroq
├── logs/llm/                # Auto-created; full prompt/response dumps
├── frontend/
├── tests/
├── main.py                  # FastAPI entrypoint
├── requirements.txt
├── .env.example
├── CONTRIBUTING.md
└── PLAN.md
```

## Key Fixes Applied

| Issue | Fix |
|-------|-----|
| Savings rate always zero | `analysis_agent.py` now filters by `transaction_type` (credit vs debit) |
| `users.monthly_income` never read | `analysis_agent.py` queries it; passed to `compute_health_score` |
| `current_balance=0` hardcoded | `analysis_agent.py` now queries real balance from `users` table |
| No income/expense distinction | Added `transaction_type` column to schema + `Transaction` model |
| `anomaly_agent.py` orphaned | Added to orchestrator graph + routing (`action: "anomaly"`) |
| `notification_service.py` disconnected | Wired into `ingestion.py` pipeline + orchestrator `notify` node |
| No Budget Management Agent | Created `agents/budget_agent.py` with 50/30/20 rule |
| `requirements.txt` had wrong deps | Removed `langchain-google-genai`, `google-generativeai`, `langchain-ollama`, `pgvector`; added `groq`, `langchain-groq`, `voyageai` |
| `.env.example` outdated | Updated to `GROQ_API_KEY` + `VOYAGE_API_KEY` |
| `PLAN.md` referenced Gemini | Updated to Groq + Voyage |
