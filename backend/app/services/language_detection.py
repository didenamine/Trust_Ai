"""Detect whether a text (CV, offer) is in French or English (US05, reusable by US09)."""

from langdetect import DetectorFactory, LangDetectException, detect_langs

from app.schemas.shared import ContentLanguage

# langdetect is random by default: make it give the same answer for the same text.
DetectorFactory.seed = 0

_SAMPLE_CHARS = 5_000


def detect_language(text: str) -> ContentLanguage | None:
    """French or English, whichever is more likely; None if the text is in neither.

    French CVs are full of English terms ("full-stack", "machine learning"), so
    the two candidates are compared with each other rather than with a threshold.
    """
    try:
        guesses = detect_langs(text[:_SAMPLE_CHARS])
    except LangDetectException:
        return None

    probabilities = {guess.lang: guess.prob for guess in guesses}
    french, english = probabilities.get("fr", 0.0), probabilities.get("en", 0.0)
    if french == english == 0.0:
        return None
    return ContentLanguage.FR if french >= english else ContentLanguage.EN
