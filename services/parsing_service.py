import hashlib
import io
import json
import re
from datetime import date
from typing import BinaryIO

import pandas as pd
import pdfplumber
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from core.logger import logger
from schemas.models import Transaction
from services.llm_service import FallbackLLM


def _generate_transaction_id(txn_date: date, amount: float, raw_merchant: str) -> str:
    raw = f"{txn_date.isoformat()}|{amount}|{raw_merchant}"
    return hashlib.sha256(raw.encode()).hexdigest()


class PDFPasswordError(Exception):
    pass


class PDFParseResult:
    """Holds both the parsed transactions and all extracted text for diagnostics."""
    def __init__(self, transactions: list[Transaction], raw_text_by_page: dict[int, str]):
        self.transactions = transactions
        self.raw_text_by_page = raw_text_by_page


def parse_pdf(file: bytes | BinaryIO, user_id: str, password: str | None = None) -> PDFParseResult:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    logger.info(f"Parsing PDF | user_id={user_id} | password_provided={bool(password)}")
    raw_text_by_page: dict[int, str] = {}
    try:
        with pdfplumber.open(file, password=password or "") as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                raw_text_by_page[i] = text or ""
    except Exception as e:
        if "password" in str(e).lower() or "PdfminerException" in type(e).__name__:
            raise PDFPasswordError("PDF is password-protected and requires a valid password to parse.") from e
        raise

    logger.info(f"PDF extracted | user_id={user_id} | pages={len(raw_text_by_page)}")

    # Quick sanity log
    total_chars = sum(len(t) for t in raw_text_by_page.values())
    sample = (list(raw_text_by_page.values()) or [""])[0][:300]
    logger.debug(f"Total extracted chars={total_chars} | sample='{sample}'")

    transactions = _parse_text_lines(raw_text_by_page, user_id)
    logger.info(f"PDF parsing complete | user_id={user_id} | total={len(transactions)}")
    return PDFParseResult(transactions, raw_text_by_page)


def parse_csv(file: BinaryIO, user_id: str) -> list[Transaction]:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    df = pd.read_csv(file)
    transactions: list[Transaction] = []
    logger.info(f"Parsing CSV | user_id={user_id} | rows={len(df)}")
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        parsed_date = pd.to_datetime(row_dict.get("date")).date()
        raw_amt = float(row_dict.get("amount", 0))
        txn_type = str(row_dict.get("transaction_type", "debit"))
        if txn_type not in ("credit", "debit"):
            txn_type = "credit" if raw_amt >= 0 else "debit"
        txn = Transaction(
            transaction_id=_generate_transaction_id(
                parsed_date,
                abs(raw_amt),
                str(row_dict.get("merchant", "")),
            ),
            user_id=user_id,
            transaction_date=parsed_date,
            amount=abs(raw_amt),
            merchant=str(row_dict.get("merchant", "")),
            raw_merchant=str(row_dict.get("merchant", "")),
            category=str(row_dict.get("category", "Uncategorized")),
            payment_mode=str(row_dict.get("payment_mode", "UPI")),
            transaction_type=txn_type,
        )
        transactions.append(txn)
    logger.info(f"CSV parsing complete | user_id={user_id} | total={len(transactions)}")
    return transactions


def _parse_text_lines(raw_text_by_page: dict[int, str], user_id: str) -> list[Transaction]:
    """
    Multi-strategy regex parser across all pages.
    """
    all_lines: list[str] = []
    for page_num, text in raw_text_by_page.items():
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        all_lines.extend(lines)

    if not all_lines:
        return []

    strategies = [
        _parse_whitespace_table,
        _parse_date_merchant_amount_patterns,
    ]
    for strategy in strategies:
        txns = strategy(all_lines, user_id)
        if txns:
            logger.debug(f"Matched {len(txns)} txns using {strategy.__name__}")
            return txns

    logger.debug("No regex strategy matched — returning empty.")
    return []


def _parse_whitespace_table(lines: list[str], user_id: str) -> list[Transaction]:
    """Columns separated by 2+ spaces: date ... amount ... merchant"""
    txns = []
    for line in lines:
        parts = re.split(r"\s{3,}", line)
        if len(parts) < 3:
            parts = re.split(r"\s{2,}", line)
        if len(parts) < 3:
            continue
        txn = _try_build_transaction(parts[0], parts[-2], parts[-1], user_id)
        if txn:
            txns.append(txn)
    return txns


_DATE_MERCHANT_AMOUNT_RE = re.compile(
    r"(\d{1,4}[-/]\d{1,2}[-/]\d{1,4})"          # date
    r".*?"                                         # anything
    r"(?:Rs\.?|₹|\$)?\s*([\d,]+\.?\d{0,2})"      # amount
    r".*?"                                         # anything
    r"([A-Za-z][\w\s&.'-]+)$"                     # merchant at end
)


def _parse_date_merchant_amount_patterns(lines: list[str], user_id: str) -> list[Transaction]:
    """Regex: extract date + amount + merchant from each line."""
    txns = []
    for line in lines:
        match = _DATE_MERCHANT_AMOUNT_RE.search(line)
        if not match:
            continue
        txn = _try_build_transaction(match.group(1), match.group(2), match.group(3), user_id)
        if txn:
            txns.append(txn)
    return txns


def _try_build_transaction(date_str: str, amount_str: str, merchant_str: str, user_id: str) -> Transaction | None:
    try:
        sep = "/" if "/" in date_str else "-"
        parts = date_str.split(sep)
        if len(parts) == 3:
            if len(parts[2]) == 4:
                y, m, d = int(parts[2]), int(parts[1]), int(parts[0])
            elif len(parts[0]) == 4:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            txn_date = date(y, m, d)
        else:
            txn_date = date.fromisoformat(date_str)

        amount = float(amount_str.replace(",", "").replace("₹", "").replace("$", "").replace("Rs.", "").strip())
        merchant = merchant_str.strip().rstrip(".")
        transaction_type = "credit" if "CR" in merchant.upper() else "debit"

        return Transaction(
            transaction_id=_generate_transaction_id(txn_date, amount, merchant),
            user_id=user_id,
            transaction_date=txn_date,
            amount=amount,
            merchant=merchant,
            raw_merchant=merchant,
            transaction_type=transaction_type,
        )
    except (ValueError, IndexError, TypeError):
        return None


async def parse_pdf_with_llm(raw_text_by_page: dict[int, str], user_id: str) -> list[Transaction]:
    """
    Fallback: use Gemini to parse all PDF text when regex strategies yield nothing.
    Sends the full text per page with a structured output schema.
    """
    all_text = "\n".join(
        f"--- Page {num+1} ---\n{text}"
        for num, text in raw_text_by_page.items()
        if text.strip()
    )
    if not all_text.strip():
        return []

    logger.debug(f"LLM PDF parsing: {len(all_text)} chars across {len(raw_text_by_page)} pages")

    llm = FallbackLLM()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a bank statement parser. Extract ALL transactions from the text below. "
         "Return a JSON array of objects with fields: transaction_date (YYYY-MM-DD), "
         "amount (float, always positive), merchant (string), raw_merchant (string), "
         "transaction_type (string, 'credit' for deposits/refunds, 'debit' for withdrawals/payments), "
         "category (string, "
         "one of: Food, Transport, Shopping, Bills, Entertainment, Healthcare, Education, Income, Uncategorized), "
         "payment_mode (string, one of: UPI, Card, NEFT, Cash, Cheque, Unknown). "
         "Return ONLY valid JSON, no markdown, no explanation."),
        ("human", "{text}"),
    ])

    try:
        max_chars = 50000
        truncated = all_text[:max_chars]
        formatted_messages = prompt.format_messages(text=truncated)
        logger.debug(f"LLM prompt (first 1000 chars): {str(formatted_messages)[:1000]}")
        response = await llm.ainvoke(formatted_messages)
        content = response.content.strip()
        logger.debug(f"LLM raw response (first 500 chars): {content[:500]}")
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # JSON parsing failed — check for safety rejection
            if "User Safety" in content or "unsafe" in content.lower():
                logger.warning(f"LLM safety rejection: {content[:200]}")
            else:
                logger.error(f"LLM returned non-JSON: {content[:200]}")
            return []
        if isinstance(data, dict):
            data = data.get("transactions", data.get("data", []))
    except Exception as e:
        logger.error(f"LLM PDF parsing failed: {e} | raw_response={content[:200] if 'content' in locals() else 'N/A'}")
        return []

    transactions = []
    for item in data:
        try:
            txn_date = date.fromisoformat(item["transaction_date"])
            raw_amount = float(item["amount"])
            transaction_type = str(item.get("transaction_type", ""))
            if transaction_type not in ("credit", "debit"):
                transaction_type = "credit" if raw_amount < 0 else "debit"
            merchant = str(item.get("merchant", "Unknown"))
            raw_merchant = str(item.get("raw_merchant", merchant))
            txn = Transaction(
                transaction_id=_generate_transaction_id(txn_date, abs(raw_amount), raw_merchant),
                user_id=user_id,
                transaction_date=txn_date,
                amount=abs(raw_amount),
                merchant=merchant,
                raw_merchant=raw_merchant,
                category=item.get("category", "Uncategorized"),
                payment_mode=item.get("payment_mode", "Unknown"),
                transaction_type=transaction_type,
            )
            transactions.append(txn)
        except (ValueError, KeyError, TypeError) as e:
            logger.debug(f"Skipping malformed LLM item: {item} — {e}")
            continue

    logger.debug(f"LLM PDF parsing produced {len(transactions)} transactions")
    return transactions


async def parse_upi_text(text: str, user_id: str) -> list[Transaction]:
    llm = FallbackLLM()
    structured_llm = llm.with_structured_output(Transaction)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    transactions: list[Transaction] = []
    system_prompt = SystemMessage(
        content="Extract a single financial transaction from the given text. "
        "Return the date, amount, merchant, raw_merchant, category, and payment_mode. "
        "If unsure, set category to 'Uncategorized' and payment_mode to 'UPI'."
    )
    for line in lines:
        try:
            result = await structured_llm.ainvoke(
                [system_prompt, HumanMessage(content=line)]
            )
            if isinstance(result, Transaction):
                result.user_id = user_id
                result.transaction_id = _generate_transaction_id(
                    result.transaction_date, result.amount, result.raw_merchant
                )
                transactions.append(result)
        except Exception:
            continue
    return transactions
