import json

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Holding, Stock
from app.schemas.holding_schema import HoldingCreate, HoldingRead, HoldingUpdate

router = APIRouter(prefix="/holdings", tags=["holdings"])


def _normalize_ticker(ticker: str, market_type: str) -> str:
    normalized = ticker.strip().upper()
    if market_type == "KR" and normalized.isdigit() and len(normalized) == 6:
        return f"{normalized}.KS"
    return normalized


def _serialize(holding: Holding) -> HoldingRead:
    return HoldingRead(
        id=holding.id,
        stock_id=holding.stock_id,
        name=holding.stock.name,
        ticker=holding.stock.ticker,
        market_type=holding.market_type,
        asset_type=holding.asset_type,
        avg_buy_price=holding.avg_buy_price,
        quantity=holding.quantity,
        currency=holding.currency,
        investment_memo=holding.investment_memo,
        interest_level=holding.interest_level,
        risk_tolerance=holding.risk_tolerance,
        is_active=holding.is_active,
        tags=json.loads(holding.stock.tags or "[]"),
        created_at=holding.created_at,
        updated_at=holding.updated_at,
    )


def _get_holding(db: Session, holding_id: int) -> Holding:
    holding = db.scalar(
        select(Holding)
        .options(joinedload(Holding.stock))
        .where(Holding.id == holding_id)
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding


@router.get("", response_model=list[HoldingRead])
def list_holdings(db: Session = Depends(get_db)) -> list[HoldingRead]:
    holdings = db.scalars(
        select(Holding)
        .options(joinedload(Holding.stock))
        .where(Holding.is_active.is_(True))
        .order_by(Holding.interest_level.desc(), Holding.created_at.desc())
    ).all()
    return [_serialize(holding) for holding in holdings]


@router.post("", response_model=HoldingRead, status_code=status.HTTP_201_CREATED)
def create_holding(payload: HoldingCreate, db: Session = Depends(get_db)) -> HoldingRead:
    ticker = _normalize_ticker(payload.ticker, payload.market_type)
    stock = db.scalar(select(Stock).where(Stock.ticker == ticker))
    if stock is None:
        stock = Stock(
            ticker=ticker,
            name=payload.name.strip(),
            market=payload.market_type,
            country="KR" if payload.market_type == "KR" else "US",
            asset_type=payload.asset_type,
            is_listed=payload.asset_type != "PRIVATE",
            currency=payload.currency or ("KRW" if payload.market_type == "KR" else "USD"),
            data_source="unavailable" if payload.asset_type == "PRIVATE" else "yfinance",
            tags=json.dumps(payload.tags, ensure_ascii=False),
        )
        db.add(stock)
        db.flush()
    else:
        stock.name = payload.name.strip()
        stock.tags = json.dumps(payload.tags, ensure_ascii=False)
        active = db.scalar(
            select(Holding).where(Holding.stock_id == stock.id, Holding.is_active.is_(True))
        )
        if active:
            raise HTTPException(status_code=409, detail="Ticker is already in holdings")

    holding = Holding(
        stock_id=stock.id,
        asset_type=payload.asset_type,
        market_type=payload.market_type,
        avg_buy_price=payload.avg_buy_price,
        quantity=payload.quantity,
        currency=payload.currency or stock.currency,
        investment_memo=payload.investment_memo,
        interest_level=payload.interest_level,
        risk_tolerance=payload.risk_tolerance,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    holding.stock = stock
    return _serialize(holding)


@router.put("/{holding_id}", response_model=HoldingRead)
def update_holding(
    holding_id: int,
    payload: HoldingUpdate,
    db: Session = Depends(get_db),
) -> HoldingRead:
    holding = _get_holding(db, holding_id)
    values = payload.model_dump(exclude_unset=True)
    name = values.pop("name", None)
    tags = values.pop("tags", None)
    if name is not None:
        holding.stock.name = name.strip()
    if tags is not None:
        holding.stock.tags = json.dumps(tags, ensure_ascii=False)
    for key, value in values.items():
        setattr(holding, key, value)
    if payload.market_type is not None:
        holding.stock.market = payload.market_type
    if payload.asset_type is not None:
        holding.stock.asset_type = payload.asset_type
        holding.stock.is_listed = payload.asset_type != "PRIVATE"
    db.commit()
    db.refresh(holding)
    return _serialize(holding)


@router.delete("/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(holding_id: int, db: Session = Depends(get_db)) -> Response:
    holding = _get_holding(db, holding_id)
    holding.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
