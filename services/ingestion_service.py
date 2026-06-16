from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from schemas.models import IngestionResult, Transaction


async def insert_transactions(
    session: AsyncSession, user_id: str, transactions: list[Transaction]
) -> IngestionResult:
    result = IngestionResult(user_id=user_id)
    logger.info(f"Inserting {len(transactions)} transactions | user_id={user_id}")
    for txn in transactions:
        exists = await session.execute(
            text("SELECT 1 FROM transactions WHERE transaction_id = :tid"),
            {"tid": txn.transaction_id},
        )
        if exists.scalar():
            result.duplicates_skipped += 1
            continue
        await session.execute(
            text(
                "INSERT INTO transactions (transaction_id, user_id, date, amount, "
                "transaction_type, merchant, raw_merchant, category, payment_mode) "
                "VALUES (:tid, :uid, :date, :amount, :tt, :merchant, :raw, :cat, :pm)"
            ),
            {
                "tid": txn.transaction_id,
                "uid": user_id,
                "date": txn.transaction_date,
                "amount": txn.amount,
                "tt": txn.transaction_type,
                "merchant": txn.merchant,
                "raw": txn.raw_merchant,
                "cat": txn.category,
                "pm": txn.payment_mode,
            },
        )
        result.records_inserted += 1
    await session.commit()
    logger.info(f"Ingestion complete | user_id={user_id} | inserted={result.records_inserted} | skipped={result.duplicates_skipped}")
    return result
