from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# CJK: Hiragana, Katakana, CJK Unified Ideographs, Compatibility Ideographs, Hangul
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]")
_CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")

# Latin tokens that legitimately appear in Russian fitness/tech talk
_ALLOWED_LATIN = {
    "garmin", "hrv", "vo2max", "vo2", "gps", "wi-fi", "wifi", "ok", "okay",
    "app", "strava", "trainingpeaks", "m", "km", "kg", "bpm", "mp3", "us", "eu",
    "ui", "api", "tss", "ctl", "atl", "lthr", "rhr", "sos",
}


def detect_lang(text: str) -> str:
    """Return 'ru' or 'en' based on the script of the text."""
    return "ru" if _CYRILLIC_RE.search(text) else "en"


def is_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def strip_cjk(text: str) -> str:
    """Remove CJK characters from a token; returns '' if nothing remains."""
    return _CJK_RE.sub("", text)


def has_foreign(text: str, lang: str) -> bool:
    """Detect foreign-script content that should not be in a `lang` response."""
    if not text:
        return False
    if _CJK_RE.search(text):
        return True
    if lang == "ru":
        for match in _LATIN_WORD_RE.finditer(text):
            if match.group().lower() not in _ALLOWED_LATIN:
                return True
        return False
    if lang == "en":
        return bool(_CYRILLIC_RE.search(text))
    return False


def repair_text(text: str, lang: str, llm) -> str:
    """One-shot rewrite that translates foreign words, keeping proper nouns/terms.

    Falls back to the original text on any failure.
    """
    lang_name = "Russian" if lang == "ru" else "English"
    prompt = (
        f"The following text is written in {lang_name} but contains foreign words.\n"
        f"Rewrite it fixing ONLY the foreign words: translate them into {lang_name}.\n"
        "Keep proper nouns and common technical abbreviations unchanged "
        "(e.g., Garmin, HRV, VO2max, GPS, Strava, Wi-Fi, OK).\n"
        "Do not change the meaning, tone, or structure. Do not add or remove content.\n\n"
        f"Text:\n{text}\n\n"
        f"Rewritten text in pure {lang_name}:"
    )
    try:
        result = llm.invoke(prompt)
        cleaned = result.content if hasattr(result, "content") else str(result)
        cleaned = cleaned.strip()
        if cleaned:
            return cleaned
    except Exception as e:
        logger.warning("Language repair failed: %s", e)
    return text
