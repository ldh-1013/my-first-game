from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import DailyPrice, Holding, Stock
from app.services.top5_service import rank_global_market


def test_top5_ranks_market_stocks_without_using_holdings():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for index in range(6):
            stock = Stock(
                ticker=f"T{index}",
                name=f"Market {index}",
                market="US" if index % 2 else "KR",
                country="US",
                currency="USD",
                is_listed=True,
            )
            db.add(stock)
            db.flush()
            for offset in range(25):
                close = 100 + index * offset
                db.add(
                    DailyPrice(
                        stock_id=stock.id,
                        date=date.today() - timedelta(days=24 - offset),
                        open_price=close - 1,
                        high_price=close + 1,
                        low_price=close - 2,
                        close_price=close,
                        volume=1000 + index * 500,
                        change_rate=float(index),
                        ma5=close - index,
                        ma20=close - index * 2,
                        ma60=close - index * 3,
                        rsi=55,
                        volatility_20d=25,
                        volume_change_rate=index * 10,
                    )
                )
        # Only one stock is held; ranking must still contain five market stocks.
        db.add(Holding(stock_id=1, market_type="KR", currency="KRW"))
        db.commit()
        rows = rank_global_market(db)
        assert len(rows) == 5
        assert len({row["stock"].ticker for row in rows}) == 5
