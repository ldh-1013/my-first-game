from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import date
from functools import lru_cache

import requests
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import FinancialSnapshot, Setting, Stock
from app.utils.logger import get_logger

logger = get_logger(__name__)
_financial_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="financial-data",
)


def _number(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def collect_financial_snapshot(db: Session, stock: Stock) -> FinancialSnapshot | None:
    if not stock.is_listed or not get_settings().enable_external_data:
        return None
    current = db.scalar(
        select(FinancialSnapshot).where(
            FinancialSnapshot.stock_id == stock.id,
            FinancialSnapshot.as_of_date == date.today(),
        )
    )
    if current:
        return current
    future = _financial_executor.submit(_fetch_yfinance_info, stock.ticker)
    try:
        info = future.result(
            timeout=max(3, get_settings().request_timeout_seconds),
        )
    except TimeoutError:
        future.cancel()
        logger.warning("Financial collection timed out for %s", stock.ticker)
        return _latest_financial_snapshot(db, stock.id)
    except Exception as exc:
        logger.warning("Financial collection failed for %s: %s", stock.ticker, exc)
        return _latest_financial_snapshot(db, stock.id)

    values = {
        "revenue": _number(info.get("totalRevenue")),
        "operating_income": _number(info.get("operatingCashflow")),
        "net_income": _number(info.get("netIncomeToCommon")),
        "total_debt": _number(info.get("totalDebt")),
        "free_cash_flow": _number(info.get("freeCashflow")),
        "market_cap": _number(info.get("marketCap")),
        "trailing_pe": _number(info.get("trailingPE")),
        "price_to_book": _number(info.get("priceToBook")),
        "return_on_equity": _number(info.get("returnOnEquity")),
        "earnings_growth": _number(info.get("earningsGrowth")),
        "source": "yfinance",
        "raw_summary": str(info.get("longBusinessSummary") or "")[:3000],
    }
    snapshot = db.scalar(
        select(FinancialSnapshot).where(
            FinancialSnapshot.stock_id == stock.id,
            FinancialSnapshot.as_of_date == date.today(),
        )
    )
    if snapshot:
        for key, value in values.items():
            setattr(snapshot, key, value)
    else:
        snapshot = FinancialSnapshot(
            stock_id=stock.id,
            as_of_date=date.today(),
            **values,
        )
        db.add(snapshot)
    db.flush()
    return snapshot


def _fetch_yfinance_info(ticker: str) -> dict:
    return yf.Ticker(ticker).get_info()


def _latest_financial_snapshot(
    db: Session,
    stock_id: int,
) -> FinancialSnapshot | None:
    return db.scalar(
        select(FinancialSnapshot)
        .where(FinancialSnapshot.stock_id == stock_id)
        .order_by(FinancialSnapshot.as_of_date.desc())
    )


def _setting(db: Session, key: str) -> str:
    row = db.scalar(select(Setting).where(Setting.key == key))
    return row.value.strip() if row else ""


@lru_cache(maxsize=2)
def _dart_corp_codes(api_key: str) -> dict[str, str]:
    response = requests.get(
        "https://opendart.fss.or.kr/api/corpCode.xml",
        params={"crtfc_key": api_key},
        timeout=20,
    )
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        root = ET.fromstring(archive.read("CORPCODE.xml"))
    result: dict[str, str] = {}
    for item in root.findall("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_code = (item.findtext("corp_code") or "").strip()
        if stock_code and corp_code:
            result[stock_code] = corp_code
    return result


def dart_disclosures(db: Session, stock: Stock, limit: int = 10) -> list[dict]:
    api_key = _setting(db, "dart_api_key")
    stock_code = stock.ticker.split(".")[0]
    if not api_key or not stock_code.isdigit():
        return []
    try:
        corp_code = _dart_corp_codes(api_key).get(stock_code)
        if not corp_code:
            return []
        response = requests.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bgn_de": str(date.today().replace(year=date.today().year - 1)).replace("-", ""),
                "page_count": min(limit, 100),
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            {
                "source": "DART",
                "title": row.get("report_nm", ""),
                "date": row.get("rcept_dt", ""),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={row.get('rcept_no', '')}",
                "company": row.get("corp_name", stock.name),
            }
            for row in payload.get("list", [])[:limit]
        ]
    except Exception as exc:
        logger.warning("DART collection failed for %s: %s", stock.ticker, exc)
        return []


@lru_cache(maxsize=1)
def _sec_tickers() -> dict[str, str]:
    response = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers={"User-Agent": "Stock Insight local-research contact@example.com"},
        timeout=15,
    )
    response.raise_for_status()
    return {
        row["ticker"].upper(): str(row["cik_str"]).zfill(10)
        for row in response.json().values()
    }


def sec_filings(stock: Stock, limit: int = 10) -> list[dict]:
    if stock.market != "US":
        return []
    try:
        cik = _sec_tickers().get(stock.ticker.upper())
        if not cik:
            return []
        response = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers={"User-Agent": "Stock Insight local-research contact@example.com"},
            timeout=15,
        )
        response.raise_for_status()
        recent = response.json().get("filings", {}).get("recent", {})
        rows = []
        for index, form in enumerate(recent.get("form", [])):
            if form not in {"10-K", "10-Q", "8-K", "6-K", "20-F"}:
                continue
            accession = recent["accessionNumber"][index].replace("-", "")
            primary = recent["primaryDocument"][index]
            rows.append(
                {
                    "source": "SEC",
                    "title": f"{form} · {recent['primaryDocDescription'][index] or primary}",
                    "date": recent["filingDate"][index],
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}",
                    "company": stock.name,
                }
            )
            if len(rows) >= limit:
                break
        return rows
    except Exception as exc:
        logger.warning("SEC collection failed for %s: %s", stock.ticker, exc)
        return []


def serialize_financial(snapshot: FinancialSnapshot | None) -> dict | None:
    if not snapshot:
        return None
    return {
        "as_of_date": snapshot.as_of_date,
        "revenue": snapshot.revenue,
        "operating_income": snapshot.operating_income,
        "net_income": snapshot.net_income,
        "total_debt": snapshot.total_debt,
        "free_cash_flow": snapshot.free_cash_flow,
        "market_cap": snapshot.market_cap,
        "trailing_pe": snapshot.trailing_pe,
        "price_to_book": snapshot.price_to_book,
        "return_on_equity": snapshot.return_on_equity,
        "earnings_growth": snapshot.earnings_growth,
        "source": snapshot.source,
        "summary": snapshot.raw_summary,
    }
