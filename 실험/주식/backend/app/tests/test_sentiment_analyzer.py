from app.services.sentiment_analyzer import analyze_sentiment


def test_positive_news():
    result = analyze_sentiment("Record revenue and profit growth after contract win")
    assert result["sentiment_label"] == "positive"
    assert result["sentiment_score"] > 0


def test_negative_news():
    result = analyze_sentiment("Guidance cut follows lawsuit and investigation")
    assert result["sentiment_label"] == "negative"
    assert result["sentiment_score"] < 0


def test_neutral_news():
    result = analyze_sentiment("Company schedules an ordinary shareholder meeting")
    assert result["sentiment_label"] == "neutral"
    assert result["sentiment_score"] == 0

