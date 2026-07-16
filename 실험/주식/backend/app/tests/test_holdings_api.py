def test_holdings_crud(client):
    payload = {
        "ticker": "005930.KS",
        "name": "삼성전자",
        "market_type": "KR",
        "asset_type": "LISTED_STOCK",
        "avg_buy_price": 72000,
        "quantity": 10,
        "investment_memo": "반도체 업황 관찰",
        "interest_level": 5,
        "risk_tolerance": "medium",
    }

    created = client.post("/holdings", json=payload)
    assert created.status_code == 201
    holding_id = created.json()["id"]
    assert created.json()["ticker"] == "005930.KS"

    listed = client.get("/holdings")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/holdings/{holding_id}",
        json={"avg_buy_price": 70000, "interest_level": 4},
    )
    assert updated.status_code == 200
    assert updated.json()["avg_buy_price"] == 70000
    assert updated.json()["interest_level"] == 4

    deleted = client.delete(f"/holdings/{holding_id}")
    assert deleted.status_code == 204
    assert client.get("/holdings").json() == []


def test_duplicate_active_holding_is_rejected(client):
    payload = {
        "ticker": "NVDA",
        "name": "NVIDIA",
        "market_type": "US",
        "asset_type": "LISTED_STOCK",
    }
    assert client.post("/holdings", json=payload).status_code == 201
    assert client.post("/holdings", json=payload).status_code == 409


def test_korean_numeric_ticker_is_normalized(client):
    response = client.post(
        "/holdings",
        json={
            "ticker": "005930",
            "name": "삼성전자",
            "market_type": "KR",
            "asset_type": "LISTED_STOCK",
        },
    )
    assert response.status_code == 201
    assert response.json()["ticker"] == "005930.KS"


def test_holding_tags_are_saved_and_searchable(client):
    response = client.post(
        "/holdings",
        json={
            "ticker": "TAG",
            "name": "Tag Company",
            "market_type": "US",
            "asset_type": "LISTED_STOCK",
            "tags": ["반도체", "장기"],
        },
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["반도체", "장기"]
    assert client.get("/holdings").json()[0]["tags"] == ["반도체", "장기"]


def test_single_ticker_analysis_handles_missing_external_data(client, monkeypatch):
    import pandas as pd

    from app.services import analysis_runner

    created = client.post(
        "/holdings",
        json={
            "ticker": "TEST",
            "name": "Test Company",
            "market_type": "US",
            "asset_type": "LISTED_STOCK",
        },
    )
    assert created.status_code == 201
    monkeypatch.setattr(analysis_runner, "fetch_daily_prices", lambda _: pd.DataFrame())
    monkeypatch.setattr(analysis_runner, "fetch_news_for_ticker", lambda *_: [])

    analyzed = client.post("/analyze/ticker/TEST")
    assert analyzed.status_code == 200
    assert analyzed.json()["success"] is True
    assert analyzed.json()["data_available"] is False


def test_dashboard_report_can_be_hidden_and_restored(client, monkeypatch):
    import pandas as pd

    from app.services import analysis_runner

    created = client.post(
        "/holdings",
        json={
            "ticker": "HIDE",
            "name": "Hidden Company",
            "market_type": "US",
            "asset_type": "LISTED_STOCK",
        },
    )
    assert created.status_code == 201
    monkeypatch.setattr(analysis_runner, "fetch_daily_prices", lambda _: pd.DataFrame())
    monkeypatch.setattr(analysis_runner, "fetch_news_for_ticker", lambda *_: [])
    assert client.post("/analyze/ticker/HIDE").status_code == 200
    assert len(client.get("/reports/daily").json()) == 1

    hidden = client.post("/reports/dashboard/HIDE/hide")
    assert hidden.status_code == 200
    assert client.get("/reports/daily").json() == []

    restored = client.delete("/reports/dashboard/HIDE/hide")
    assert restored.status_code == 200
    assert len(client.get("/reports/daily").json()) == 1


def test_intraday_endpoint_returns_minute_candles(client, monkeypatch):
    import pandas as pd

    from app.api import stocks

    created = client.post(
        "/holdings",
        json={
            "ticker": "LIVE",
            "name": "Live Company",
            "market_type": "US",
            "asset_type": "LISTED_STOCK",
        },
    )
    assert created.status_code == 201
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.5],
            "close": [101.0, 102.5],
            "volume": [1000, 1500],
        },
        index=pd.date_range("2026-06-19 09:30", periods=2, freq="min", tz="UTC"),
    )
    frame.attrs["resolved_ticker"] = "LIVE"
    monkeypatch.setattr(stocks, "fetch_intraday_prices", lambda _: frame)

    response = client.get("/stocks/LIVE/intraday")
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == "1m"
    assert body["refresh_seconds"] == 30
    assert body["latest_price"] == 102.5
    assert len(body["points"]) == 2
