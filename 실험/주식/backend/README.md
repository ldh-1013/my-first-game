# Backend

FastAPI, SQLAlchemy, SQLite 기반 API입니다.

## 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger 문서: `http://localhost:8000/docs`
- 상태 확인: `http://localhost:8000/health`

## 테스트

```powershell
pytest -q
```

외부 데이터가 필요 없는 CRUD와 분석 함수 단위 테스트를 실행합니다.

