from types import SimpleNamespace

import pytest

from app import speech
from app.config import get_settings


def test_rejects_empty_audio():
    with pytest.raises(ValueError, match="empty"):
        speech.validate_audio_upload("note.webm", "audio/webm", b"")


def test_rejects_unsupported_audio():
    with pytest.raises(ValueError, match="Unsupported"):
        speech.validate_audio_upload("note.txt", "text/plain", b"not audio")


def test_transcribes_with_configured_whisper_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")
    get_settings.cache_clear()
    speech._VOICE_CALL_TIMESTAMPS.clear()
    captured = {}

    class FakeTranscriptions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="Met Dr. Rao and discussed CardioPlus.")

    fake_client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=FakeTranscriptions()),
    )
    monkeypatch.setattr(speech, "_create_groq_client", lambda _: fake_client)

    result = speech.transcribe_audio("note.webm", "audio/webm", b"audio bytes")

    assert result == {
        "text": "Met Dr. Rao and discussed CardioPlus.",
        "model": "whisper-large-v3-turbo",
    }
    assert captured["model"] == "whisper-large-v3-turbo"
    assert captured["temperature"] == 0.0

    get_settings.cache_clear()
