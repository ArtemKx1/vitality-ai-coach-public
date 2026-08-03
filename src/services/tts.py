from __future__ import annotations

import json
import logging
import os
import re

from google.cloud import texttospeech
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

_client: texttospeech.TextToSpeechClient | None = None
_MAX_INPUT_BYTES = 4800


def _get_client() -> texttospeech.TextToSpeechClient:
    global _client
    if _client is None:
        credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if credentials_json:
            credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
            _client = texttospeech.TextToSpeechClient(credentials=credentials)
        else:
            _client = texttospeech.TextToSpeechClient()
    return _client


def detect_lang(text: str) -> str:
    return "ru-RU" if any("\u0400" <= c <= "\u04FF" for c in text) else "en-US"


_VOICE_MAP = {
    "ru-RU": {"language_code": "ru-RU", "name": "ru-RU-Wavenet-C", "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE},
    "en-US": {"language_code": "en-US", "name": "en-US-Wavenet-D", "ssml_gender": texttospeech.SsmlVoiceGender.MALE},
}


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`\n]+`", "", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"(?<!\*)\*{1,2}(?!\*)([^*]+?)\*{1,2}(?!\*)", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str) -> list[str]:
    encoded = text.encode("utf-8")
    if len(encoded) <= _MAX_INPUT_BYTES:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + _MAX_INPUT_BYTES * 2, len(text))

        candidate = text[start:end]
        while len(candidate.encode("utf-8")) > _MAX_INPUT_BYTES and len(candidate) > 1:
            candidate = candidate[: len(candidate) * 3 // 4]

        split_at = -1
        for sep in ("\n\n", "\n", ". ", "! ", "? ", ".", "! ", "?"):
            pos = candidate.rfind(sep)
            if pos > len(candidate) // 2:
                split_at = pos + len(sep)
                break

        if split_at < 0:
            candidate = candidate[: _MAX_INPUT_BYTES]
            while len(candidate.encode("utf-8")) > _MAX_INPUT_BYTES:
                candidate = candidate[: len(candidate) - 1]
            split_at = len(candidate)

        chunk = text[start : start + split_at]
        chunks.append(chunk)
        start += split_at

    return chunks


def _synthesize_one(client: texttospeech.TextToSpeechClient, text: str, voice_cfg: dict) -> bytes:
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=voice_cfg["language_code"],
            name=voice_cfg["name"],
            ssml_gender=voice_cfg["ssml_gender"],
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
        ),
    )
    return response.audio_content


def synthesize(text: str) -> bytes:
    text = _strip_markdown(text)
    client = _get_client()
    lang = detect_lang(text)
    voice_cfg = _VOICE_MAP.get(lang, _VOICE_MAP["en-US"])

    chunks = _chunk_text(text)
    if len(chunks) == 1:
        audio = _synthesize_one(client, chunks[0], voice_cfg)
        logger.info("Synthesized %d chars of TTS (%s)", len(text), lang)
        return audio

    parts = []
    for i, chunk in enumerate(chunks):
        part = _synthesize_one(client, chunk, voice_cfg)
        parts.append(part)
        logger.info("Synthesized chunk %d/%d (%d chars) of TTS (%s)", i + 1, len(chunks), len(chunk), lang)

    return b"".join(parts)
