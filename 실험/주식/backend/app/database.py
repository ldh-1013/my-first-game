from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()
    _ensure_baseline_model_version()


def _run_lightweight_migrations() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    additions = {
        "stocks": {"tags": "TEXT NOT NULL DEFAULT '[]'"},
        "news_articles": {
            "translated_title": "VARCHAR(700)",
            "translated_summary": "TEXT",
        },
        "daily_reports": {
            "data_quality_score": "FLOAT NOT NULL DEFAULT 0",
            "decision_status": "VARCHAR(30) NOT NULL DEFAULT 'hold'",
            "surge_warning": "BOOLEAN NOT NULL DEFAULT 0",
            "surge_reason": "TEXT NOT NULL DEFAULT ''",
            "active_model_version": (
                "VARCHAR(100) NOT NULL DEFAULT 'rule-based-v2-calibrated'"
            ),
            "raw_up_probability": "FLOAT",
            "calibrated_up_probability": "FLOAT",
            "validation_sample_count": "INTEGER NOT NULL DEFAULT 0",
            "probability_bucket_observed_rate": "FLOAT",
            "confidence_basis": "TEXT NOT NULL DEFAULT '[]'",
            "market_regime": (
                "VARCHAR(40) NOT NULL DEFAULT 'sideways_low_vol'"
            ),
            "signal_status": "VARCHAR(40) NOT NULL DEFAULT 'defer'",
            "defer_reason": "TEXT NOT NULL DEFAULT ''",
        },
        "recommendations": {
            "surge_warning": "BOOLEAN NOT NULL DEFAULT 0",
            "surge_reason": "TEXT NOT NULL DEFAULT ''",
        },
        "prediction_results": {
            "horizon_days": "INTEGER NOT NULL DEFAULT 1",
            "absolute_error": "FLOAT",
            "prediction_source": "VARCHAR(30) NOT NULL DEFAULT 'live'",
            "replay_run_id": "INTEGER",
            "raw_up_probability": "FLOAT",
            "calibrated_up_probability": "FLOAT",
            "range_hit": "BOOLEAN",
            "actual_direction": "VARCHAR(10)",
            "data_quality_note": "VARCHAR(200) NOT NULL DEFAULT 'incomplete'",
            "historical_news_available": "BOOLEAN NOT NULL DEFAULT 0",
            "historical_financial_available": "BOOLEAN NOT NULL DEFAULT 0",
            "feature_snapshot": "TEXT NOT NULL DEFAULT '{}'",
            "market_regime": (
                "VARCHAR(40) NOT NULL DEFAULT 'sideways_low_vol'"
            ),
            "signal_status": "VARCHAR(40) NOT NULL DEFAULT 'defer'",
            "defer_reason": "TEXT NOT NULL DEFAULT ''",
        },
    }

    with engine.begin() as connection:
        inspector = inspect(connection)
        for table_name, columns in additions.items():
            if table_name not in inspector.get_table_names():
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}')
                    )
        _merge_duplicate_stocks(connection)
        connection.execute(
            text(
                "DELETE FROM daily_prices WHERE id NOT IN "
                "(SELECT MIN(id) FROM daily_prices GROUP BY stock_id, date)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_price_stock_date "
                "ON daily_prices(stock_id, date)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_historical_prediction_identity "
                "ON prediction_results("
                "stock_id, prediction_date, horizon_days, prediction_source, model_version"
                ") WHERE prediction_source='historical_replay'"
            )
        )


def _ensure_baseline_model_version() -> None:
    from app.models import ModelVersion

    with SessionLocal() as db:
        baseline = db.scalar(
            select(ModelVersion).where(
                ModelVersion.version_name == "rule-based-v2-calibrated"
            )
        )
        active = db.scalar(
            select(ModelVersion).where(ModelVersion.is_active.is_(True))
        )
        if baseline is None:
            baseline = ModelVersion(
                version_name="rule-based-v2-calibrated",
                model_type="baseline",
                artifact_path="",
                metadata_path="",
                feature_schema_json="[]",
                training_summary_json="{}",
                validation_summary_json="{}",
                test_summary_json="{}",
                status="active" if active is None else "baseline",
                is_active=active is None,
            )
            db.add(baseline)
        elif active is None:
            baseline.status = "active"
            baseline.is_active = True
        db.commit()


def _canonical_ticker(ticker: str) -> str:
    normalized = (ticker or "").strip().upper()
    return normalized[:-3] if normalized.endswith((".KS", ".KQ")) else normalized


def _merge_duplicate_stocks(connection) -> None:
    existing_tables = set(inspect(connection).get_table_names())
    rows = connection.execute(text("SELECT id, ticker, market FROM stocks ORDER BY id")).mappings()
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(_canonical_ticker(row["ticker"]), []).append(dict(row))

    child_tables = [
        "holdings",
        "daily_prices",
        "sentiment_scores",
        "daily_reports",
        "recommendations",
        "prediction_results",
        "financial_snapshots",
        "news_stock_links",
        "alert_events",
    ]
    for duplicates in groups.values():
        if len(duplicates) < 2:
            continue
        preferred = next(
            (row for row in duplicates if row["ticker"].upper().endswith((".KS", ".KQ"))),
            duplicates[0],
        )
        target_id = preferred["id"]
        for duplicate in duplicates:
            source_id = duplicate["id"]
            if source_id == target_id:
                continue
            if "daily_prices" in existing_tables:
                connection.execute(
                    text(
                        "DELETE FROM daily_prices WHERE stock_id=:source AND date IN "
                        "(SELECT date FROM daily_prices WHERE stock_id=:target)"
                    ),
                    {"source": source_id, "target": target_id},
                )
            if "holdings" in existing_tables:
                connection.execute(
                    text(
                        "UPDATE holdings SET is_active=0 WHERE stock_id=:source AND is_active=1 "
                        "AND EXISTS (SELECT 1 FROM holdings WHERE stock_id=:target AND is_active=1)"
                    ),
                    {"source": source_id, "target": target_id},
                )
            for table_name in child_tables:
                if table_name in existing_tables:
                    connection.execute(
                        text(
                            f"UPDATE OR IGNORE {table_name} "
                            "SET stock_id=:target WHERE stock_id=:source"
                        ),
                        {"source": source_id, "target": target_id},
                    )
            if "news_articles" in existing_tables:
                connection.execute(
                    text(
                        "UPDATE news_articles SET related_stock_id=:target "
                        "WHERE related_stock_id=:source"
                    ),
                    {"source": source_id, "target": target_id},
                )
            connection.execute(text("DELETE FROM stocks WHERE id=:source"), {"source": source_id})


def database_path() -> Path | None:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        return None
    return Path(settings.database_url.removeprefix(prefix)).resolve()
