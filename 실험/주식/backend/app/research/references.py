from __future__ import annotations


RESEARCH_REFERENCES = [
    {
        "title": "TimeSeriesSplit",
        "author": "scikit-learn developers",
        "date": "accessed 2026-06-22",
        "url": "https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html",
        "method": "시간 순서를 유지하고 미래 자료가 학습 자료로 들어가지 않게 하는 교차검증",
        "application": "월별 확장형 워크포워드 검증과 학습·보정·최종시험 분리",
        "limitation": "금융 자료의 레이블 중첩을 자동으로 제거하지 않으므로 시차·엠바고를 별도 적용해야 함",
    },
    {
        "title": "Probability calibration",
        "author": "scikit-learn developers",
        "date": "accessed 2026-06-22",
        "url": "https://scikit-learn.org/stable/modules/calibration.html",
        "method": "독립 보정 표본에서 예측 확률과 관측 빈도를 일치시키는 확률 보정",
        "application": "Brier·ECE·신뢰도 구간과 고신뢰 신호 기준 산출",
        "limitation": "표본이 적거나 시장 국면이 바뀌면 보정값도 불안정해질 수 있음",
    },
    {
        "title": "A Framework for Backtesting",
        "author": "Basel Committee on Banking Supervision",
        "date": "1996-01",
        "url": "https://www.bis.org/publ/bcbs22.htm",
        "method": "모형 예측과 실제 결과를 독립적으로 비교하는 백테스트 원칙",
        "application": "최종 시험 구간 고정, 예외·오류 기록, 모형 변경 이력 관리",
        "limitation": "시장위험 모형 중심 문서이므로 개별 종목 방향예측에 맞게 지표를 확장해야 함",
    },
    {
        "title": "Determining Optimal Trading Rules without Backtesting",
        "author": "Peter Carr, Marcos López de Prado",
        "date": "2014-08-06",
        "url": "https://arxiv.org/abs/1408.1159",
        "method": "반복 백테스트에 의한 과적합 위험을 줄이는 거래 규칙 평가",
        "application": "자동 운영 전환 금지, 후보 기준 강화, 시험 자료 반복 사용 경고",
        "limitation": "본 프로젝트의 데이터·비용 구조에 맞춘 재현 연구가 추가로 필요함",
    },
    {
        "title": "Avoiding Backtest Overfitting by Covariance-Penalties",
        "author": "Anthony Koshiyama, Nick Firoozye",
        "date": "2019-05-13",
        "url": "https://arxiv.org/abs/1905.05023",
        "method": "여러 전략을 비교할 때 발생하는 선택 편향과 백테스트 과적합 분석",
        "application": "실험 횟수·후보 수 기록, 단일 최고 정확도 대신 안정성과 보정 동시 평가",
        "limitation": "공분산 패널티 자체는 현재 MVP에 직접 구현하지 않고 운영 원칙으로 적용",
    },
    {
        "title": "Hybrid financial time series with regime switches",
        "author": "Tomas Kliegr et al.",
        "date": "2021-08-12",
        "url": "https://arxiv.org/abs/2108.05801",
        "method": "시장 국면 전환을 고려한 금융 시계열 예측",
        "application": "상승·하락·횡보 및 고변동 국면 특징과 국면별 앙상블 가중치",
        "limitation": "현재 국면 분류는 투명한 규칙형 MVP이며 은닉상태 모형은 아님",
    },
    {
        "title": "Machine Learning for Financial Market Prediction: A Survey",
        "author": "Various authors",
        "date": "2019-06-18",
        "url": "https://arxiv.org/abs/1906.07786",
        "method": "금융시장 예측의 특징·모델·평가 방법 조사",
        "application": "선형·트리·부스팅·앙상블 비교와 다중 성과지표 사용",
        "limitation": "조사 논문 결과가 이 데이터셋에서 동일하게 재현된다는 보장은 없음",
    },
]


def research_summary() -> dict:
    return {
        "principles": [
            "미래 시점 자료를 입력 특징에 포함하지 않는다.",
            "학습·확률보정·최종시험 구간을 시간 순서대로 분리한다.",
            "정확도뿐 아니라 보정, 거래비용, 낙폭, 신호 빈도를 함께 본다.",
            "후보 모델은 자동 적용하지 않고 사용자가 검증 결과를 보고 선택한다.",
        ],
        "references": RESEARCH_REFERENCES,
    }
