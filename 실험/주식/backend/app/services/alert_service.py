from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AlertEvent, DailyPrice, Holding, Setting
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _settings(db: Session) -> dict[str, str]:
    return {row.key: row.value for row in db.scalars(select(Setting)).all()}


def create_portfolio_alerts(db: Session) -> list[AlertEvent]:
    settings = _settings(db)
    gain_threshold = float(settings.get("alert_gain_percent", "10") or 10)
    loss_threshold = float(settings.get("alert_loss_percent", "-8") or -8)
    events: list[AlertEvent] = []
    holdings = db.scalars(select(Holding).where(Holding.is_active.is_(True))).all()
    for holding in holdings:
        if holding.avg_buy_price <= 0 or holding.quantity <= 0:
            continue
        latest = db.scalar(
            select(DailyPrice)
            .where(DailyPrice.stock_id == holding.stock_id, DailyPrice.close_price.is_not(None))
            .order_by(DailyPrice.date.desc())
        )
        if not latest or latest.close_price is None:
            continue
        rate = (latest.close_price / holding.avg_buy_price - 1) * 100
        alert_type = ""
        if rate >= gain_threshold:
            alert_type = "target_gain"
        elif rate <= loss_threshold:
            alert_type = "stop_loss"
        if not alert_type:
            continue
        title = f"{holding.stock.ticker} 목표 기준 도달"
        message = f"현재 수익률 {rate:.2f}% · 현재가 {latest.close_price:,.2f}"
        duplicate = db.scalar(
            select(AlertEvent).where(
                AlertEvent.stock_id == holding.stock_id,
                AlertEvent.alert_type == alert_type,
                AlertEvent.message == message,
            )
        )
        if duplicate:
            continue
        event = AlertEvent(
            stock_id=holding.stock_id,
            alert_type=alert_type,
            title=title,
            message=message,
        )
        db.add(event)
        db.flush()
        _deliver(db, event, settings)
        events.append(event)
    db.commit()
    return events


def _deliver(db: Session, event: AlertEvent, settings: dict[str, str]) -> None:
    text = f"📈 {event.title}\n{event.message}"
    delivered: list[str] = []
    discord = settings.get("discord_webhook_url", "").strip()
    if discord:
        try:
            requests.post(discord, json={"content": text}, timeout=10).raise_for_status()
            delivered.append("discord")
        except Exception as exc:
            logger.warning("Discord alert failed: %s", exc)
    telegram_token = settings.get("telegram_bot_token", "").strip()
    telegram_chat = settings.get("telegram_chat_id", "").strip()
    if telegram_token and telegram_chat:
        try:
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": telegram_chat, "text": text},
                timeout=10,
            ).raise_for_status()
            delivered.append("telegram")
        except Exception as exc:
            logger.warning("Telegram alert failed: %s", exc)
    if settings.get("smtp_host") and settings.get("alert_email"):
        try:
            message = EmailMessage()
            message["Subject"] = event.title
            message["From"] = settings.get("smtp_user") or settings["alert_email"]
            message["To"] = settings["alert_email"]
            message.set_content(event.message)
            with smtplib.SMTP(settings["smtp_host"], int(settings.get("smtp_port", "587"))) as smtp:
                smtp.starttls()
                if settings.get("smtp_user"):
                    smtp.login(settings["smtp_user"], settings.get("smtp_password", ""))
                smtp.send_message(message)
            delivered.append("email")
        except Exception as exc:
            logger.warning("Email alert failed: %s", exc)
    event.channel = ",".join(delivered) if delivered else "in_app"
    event.delivery_status = "delivered" if delivered else "created"


def list_alerts(db: Session, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": row.id,
            "stock_id": row.stock_id,
            "alert_type": row.alert_type,
            "title": row.title,
            "message": row.message,
            "channel": row.channel,
            "delivery_status": row.delivery_status,
            "created_at": row.created_at,
        }
        for row in rows
    ]
