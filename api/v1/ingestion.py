import time

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from agents.advisor_agent import advisor_agent
from agents.categorization_agent import categorization_agent
from core.deps import get_db
from core.logger import logger
from schemas.models import IngestionResult
from schemas.state import AgentState
from services.ingestion_service import insert_transactions
from services.parsing_service import parse_csv, parse_pdf, parse_pdf_with_llm, parse_upi_text, PDFPasswordError
from services.pipeline_service import run_full_pipeline

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/ingest")
async def ingest_file(
    user_id: str = Form(...),
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    password: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    start = time.time()
    transactions: list = []
    source = "none"
    if file:
        content = await file.read()
        file_type = file.content_type or ""
        try:
            if "pdf" in file_type or file.filename and file.filename.endswith(".pdf"):
                source = "pdf"
                pdf_result = parse_pdf(content, user_id, password=password)
                transactions = pdf_result.transactions
                if not transactions:
                    logger.info("Regex found 0 transactions — trying LLM-based PDF parsing")
                    transactions = await parse_pdf_with_llm(pdf_result.raw_text_by_page, user_id)
            elif "csv" in file_type or file.filename and file.filename.endswith(".csv"):
                source = "csv"
                transactions = parse_csv(content, user_id)
        except PDFPasswordError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if text:
        source = "text"
        text_txns = await parse_upi_text(text, user_id)
        transactions.extend(text_txns)

    ingest_result = await insert_transactions(db, user_id, transactions)

    pipeline_results: dict[str, object] = {}
    state = AgentState(
        messages=[AIMessage(content="")],
        user_id=user_id,
        active_route="",
        extracted_payload={},
    )

    if ingest_result.records_inserted > 0:
        logger.info("Starting post-ingestion pipeline: categorize → analyze → anomaly → forecast → budget → advise")

        cat = await categorization_agent(state)
        pipeline_results["categorization"] = cat.get("extracted_payload", {})

        payload = await run_full_pipeline(user_id)
        pipeline_results["analysis"] = payload.get("analytics", {})
        pipeline_results["anomaly"] = {"outliers": payload.get("outliers", []), "duplicates": payload.get("duplicates", [])}
        pipeline_results["forecast"] = payload.get("forecast", {})
        pipeline_results["alerts"] = payload.get("alerts", [])

        state["extracted_payload"] = payload
        adv = await advisor_agent(state)
        pipeline_results["advice"] = adv.get("messages", [AIMessage(content="")])[-1].content

        logger.info(f"Post-ingestion pipeline complete | alerts={len(pipeline_results['alerts'])}")

    elapsed = time.time() - start
    logger.info(
        f"Ingest API done | user_id={user_id} | source={source} | "
        f"txns_found={len(transactions)} | inserted={ingest_result.records_inserted} | "
        f"skipped={ingest_result.duplicates_skipped} | errors={len(ingest_result.errors)} | "
        f"took={elapsed:.2f}s"
    )

    return {
        "records_inserted": ingest_result.records_inserted,
        "duplicates_skipped": ingest_result.duplicates_skipped,
        "errors": ingest_result.errors,
        "pipeline": pipeline_results,
    }
