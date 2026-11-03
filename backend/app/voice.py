from __future__ import annotations

import tempfile
from functools import lru_cache

from .config import settings

SUPPORTED = {"en", "hi", "kn"}


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel
    return WhisperModel(settings.whisper_model, device=settings.whisper_device,
                        compute_type=settings.whisper_compute)


def _run(path: str, language):
    segs, info = _model().transcribe(path, language=language, vad_filter=True, beam_size=5)
    return " ".join(s.text.strip() for s in segs).strip(), info.language


def transcribe(audio: bytes, language: str | None = None, fallback: str = "en", suffix: str = ".webm"):
    """Speech -> (text, lang). Swap this function for AI4Bharat IndicConformer if Kannada WER is too high."""
    with tempfile.NamedTemporaryFile(suffix=suffix) as f:
        f.write(audio)
        f.flush()
        text, lang = _run(f.name, language)
        if language is None and lang not in SUPPORTED:  # misdetected -> force user's language
            text, lang = _run(f.name, fallback)
    return text, lang