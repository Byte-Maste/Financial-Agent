import time

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from core.logger import logger
from schemas.models import IngestionResult
from services.ingestion_service import insert_transactions
from services.parsing_service import parse_csv, parse_pdf, parse_pdf_with_llm, parse_upi_text, PDFPasswordError

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/ingest", response_model=IngestionResult)
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

    result = await insert_transactions(db, user_id, transactions)
    elapsed = time.time() - start
    logger.info(
        f"Ingest API done | user_id={user_id} | source={source} | "
        f"txns_found={len(transactions)} | inserted={result.records_inserted} | "
        f"skipped={result.duplicates_skipped} | errors={len(result.errors)} | "
        f"took={elapsed:.2f}s"
    )
    return result
