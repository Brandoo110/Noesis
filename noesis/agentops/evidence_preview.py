import re

MAX_PREVIEW_CHARS = 420
MAX_PREVIEW_SENTENCES = 2

LOW_QUALITY_PREVIEW = "正文抽取质量低，请查看来源确认。"

BOILERPLATE_MARKERS = (
    "skip to content",
    "got a tip",
    "let us know",
    "send us an email",
    "anonymous form",
    "advertisement",
    "subscribe",
    "sign in",
    "log in",
    "privacy policy",
    "cookie",
    "purchase licensing rights",
    "read next",
    "businesscategory",
    "technologycategory",
    "legalcategory",
)


def clean_evidence_preview(snippet: str, title: str | None = None) -> str:
    lines = [_clean_line(line) for line in re.split(r"[\r\n]+", snippet)]
    content_lines = [line for line in lines if _is_content_line(line)]
    text = " ".join(content_lines).strip()
    if not text:
        return title or LOW_QUALITY_PREVIEW
    return _limit_preview(_first_sentences(text))


def _clean_line(line: str) -> str:
    cleaned = re.sub(r"\s+", " ", line).strip()
    cleaned = re.sub(r"^[>\-\u2022\s]+", "", cleaned)
    cleaned = re.sub(r"^[a-zA-Z]\.\s+", "", cleaned)
    cleaned = re.sub(r"\s+>\s*", " ", cleaned)
    return cleaned.strip()


def _is_content_line(line: str) -> bool:
    if not line:
        return False
    lower = line.lower()
    if any(marker in lower for marker in BOILERPLATE_MARKERS):
        return False
    return len(line) >= 12


def _first_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", text)
    selected = [sentence.strip() for sentence in sentences if sentence.strip()]
    return " ".join(selected[:MAX_PREVIEW_SENTENCES]) if selected else text


def _limit_preview(text: str) -> str:
    if len(text) <= MAX_PREVIEW_CHARS:
        return text
    truncated = text[:MAX_PREVIEW_CHARS].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."
