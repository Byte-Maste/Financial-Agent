import time

from langchain_core.messages import AIMessage

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState
from schemas.models import IngestionResult, Transaction
from services.ingestion_service import insert_transactions
from services.parsing_service import parse_csv, parse_pdf, parse_pdf_with_llm, parse_upi_text


async def ingestion_agent(state: AgentState) -> dict:
    start = time.time()
    payload = state["extracted_payload"]
    user_id = payload.get("user_id", state["user_id"])
    file_bytes = payload.get("file_bytes")
    file_type = payload.get("file_type", "text")
    text_content = payload.get("text", "")
    pdf_password = payload.get("pdf_password")

    transactions: list[Transaction] = []

    if file_bytes and file_type == "pdf":
        result = parse_pdf(file_bytes, user_id, password=pdf_password)
        transactions = result.transactions

        # Fall back to LLM if regex produced nothing and we have text
        if not transactions:
            logger.info("Regex produced 0 transactions — attempting LLM-based PDF parsing")
            transactions = await parse_pdf_with_llm(result.raw_text_by_page, user_id)

    elif file_bytes and file_type == "csv":
        transactions = parse_csv(file_bytes, user_id)

    elif text_content:
        transactions = await parse_upi_text(text_content, user_id)

    logger.info(f"Ingestion parsed | user_id={user_id} | txns_found={len(transactions)}")

    async with async_session_factory() as session:
        db_result: IngestionResult = await insert_transactions(session, user_id, transactions)

    elapsed = time.time() - start
    logger.info(
        f"Ingestion done | user_id={user_id} | "
        f"inserted={db_result.records_inserted} | skipped={db_result.duplicates_skipped} | "
        f"errors={len(db_result.errors)} | took={elapsed:.2f}s"
    )

    summary = (
        f"Ingested {db_result.records_inserted} records "
        f"({db_result.duplicates_skipped} duplicates skipped)."
    )
    return {
        "messages": [AIMessage(content=summary)],
        "extracted_payload": db_result.model_dump(),
    }
