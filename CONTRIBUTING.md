# Contributing

## LLM Provider Rules

- **Only Groq** — all LLM calls use the raw `groq.Groq` SDK via `services.llm_service.FallbackLLM`
- API key loaded from `.env` as `GROQ_API_KEY` (must start with `gsk_`)
- No Gemini, no OpenRouter, no Ollama, no OpenAI

## Embeddings

- Use **Voyage AI** (`voyageai` package) for embeddings
- API key loaded from `.env` as `VOYAGE_API_KEY`
- Merchant categorization uses Voyage embeddings for vector similarity lookup, with Groq LLM as fallback

## Code Style

- `FallbackLLM` in `services/llm_service.py` is the single entry point for all LLM calls
- `get_embedding()` in `services/embedding_service.py` is the single entry point for embeddings
- No hardcoded API keys — always use `core.config.settings`
- All LLM output requiring structure must use `with_structured_output(PydanticModel)`
