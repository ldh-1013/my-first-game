import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setting
from app.schemas.setting_schema import SettingRead, SettingUpsert

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_KEYS = {
    "collection_time",
    "default_market",
    "schedule_enabled",
    "validation_schedule_enabled",
    "validation_time",
    "scoring_weights",
    "dart_api_key",
    "discord_webhook_url",
    "telegram_bot_token",
    "telegram_chat_id",
    "alert_gain_percent",
    "alert_loss_percent",
    "alert_email",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_password",
    "hidden_dashboard_tickers",
}


@router.get("", response_model=list[SettingRead])
def get_settings(db: Session = Depends(get_db)) -> list[Setting]:
    return list(db.scalars(select(Setting).order_by(Setting.key)).all())


@router.post("", response_model=SettingRead)
def upsert_setting(payload: SettingUpsert, db: Session = Depends(get_db)) -> Setting:
    if payload.key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail="지원하지 않는 설정 항목입니다.")
    if payload.key == "scoring_weights":
        try:
            values = json.loads(payload.value)
            if not isinstance(values, dict):
                raise ValueError
            for value in values.values():
                if float(value) < 0:
                    raise ValueError
        except (TypeError, ValueError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="분석 가중치 형식이 올바르지 않습니다.")
    setting = db.scalar(select(Setting).where(Setting.key == payload.key))
    if setting:
        setting.value = payload.value
    else:
        setting = Setting(key=payload.key, value=payload.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
