import re


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_html = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", without_html).strip()

