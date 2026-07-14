from __future__ import annotations

import time
from pathlib import Path

from app.config import get_settings


SUPPORTED_AUDIO_EXTENSIONS = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
SUPPORTED_AUDIO_TYPES = {
    "audio/flac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "video/mp4",
    "video/webm",
}

_VOICE_CALL_TIMESTAMPS: list[float] = []


class SpeechError(RuntimeError):
    pass


class SpeechConfigurationError(SpeechError):
    pass


class SpeechRateLimitError(SpeechError):
    pass


def validate_audio_upload(filename: str, content_type: str | None, data: bytes) -> None:
    settings = get_settings()
    extension = Path(filename).suffix.lower()
    normalized_type = (content_type or "").split(";", 1)[0].lower()

    if not data:
        raise ValueError("The recording is empty. Please record again.")
    if len(data) > settings.voice_max_upload_bytes:
        raise ValueError("The recording is larger than the 20 MB app limit. Please record a shorter note.")
    if extension not in SUPPORTED_AUDIO_EXTENSIONS and normalized_type not in SUPPORTED_AUDIO_TYPES:
        raise ValueError("Unsupported audio format. Use FLAC, MP3, MP4, M4A, OGG, WAV, or WEBM.")


def _reserve_voice_call() -> None:
    settings = get_settings()
    now = time.monotonic()
    window_start = now - 60
    _VOICE_CALL_TIMESTAMPS[:] = [stamp for stamp in _VOICE_CALL_TIMESTAMPS if stamp >= window_start]
    if len(_VOICE_CALL_TIMESTAMPS) >= settings.aivoa_voice_calls_per_minute:
        raise SpeechRateLimitError("Voice transcription budget reached. Please wait one minute and try again.")
    _VOICE_CALL_TIMESTAMPS.append(now)


def _create_groq_client(api_key: str):
    from groq import Groq

    return Groq(api_key=api_key)


def transcribe_audio(filename: str, content_type: str | None, data: bytes) -> dict[str, str]:
    validate_audio_upload(filename, content_type, data)
    settings = get_settings()
    if not settings.groq_api_key:
        raise SpeechConfigurationError("Groq API key is not configured.")

    _reserve_voice_call()
    client = _create_groq_client(settings.groq_api_key)
    try:
        result = client.audio.transcriptions.create(
            file=(filename, data),
            model=settings.groq_transcription_model,
            prompt=(
                "HCP pharmaceutical CRM interaction note. Preserve doctor names, product names, "
                "dates, times, sentiment, materials shared, and follow-up actions."
            ),
            response_format="json",
            temperature=0.0,
        )
    except Exception as exc:  # noqa: BLE001 - provider errors are translated at the API boundary
        message = str(exc)
        if "429" in message or "rate limit" in message.lower():
            raise SpeechRateLimitError("Groq's voice limit was reached. Please wait and try again.") from exc
        raise SpeechError(f"Groq could not transcribe this recording: {message[:220]}") from exc

    text = str(getattr(result, "text", "")).strip()
    if not text:
        raise SpeechError("No speech was detected. Please record again in a quieter place.")
    return {"text": text, "model": settings.groq_transcription_model}
