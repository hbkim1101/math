"""TTS provider abstraction — edge-tts (default) and ElevenLabs."""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path

import edge_tts
import httpx

from src.dsl.lecture_models import TtsConfig
from src.renderer.tts_utils import build_ssml, normalize_math_speech


class TtsProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, out_path: Path, cfg: TtsConfig) -> None:
        """Write speech audio for *text* to *out_path*."""


class EdgeTtsProvider(TtsProvider):
    async def synthesize(self, text: str, out_path: Path, cfg: TtsConfig) -> None:
        voice = cfg.voice
        ssml = build_ssml(
            text,
            voice,
            rate=cfg.rate,
            pitch=cfg.pitch,
            pause_ms=cfg.pause_ms,
        )
        comm = edge_tts.Communicate(ssml, voice)
        await comm.save(str(out_path))


class ElevenLabsProvider(TtsProvider):
    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")

    async def synthesize(self, text: str, out_path: Path, cfg: TtsConfig) -> None:
        if not self.api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY is not set. "
                "Export the key or use tts.provider: edge in YAML."
            )
        voice_id = cfg.elevenlabs_voice_id
        if not voice_id:
            raise RuntimeError(
                "lecture.tts.elevenlabs_voice_id is required when provider=elevenlabs"
            )

        spoken = normalize_math_speech(text)
        # SSML breaks are not supported; approximate pauses with punctuation.
        spoken = spoken.replace("<break", ".").replace("/>", "")

        payload = {
            "text": spoken,
            "model_id": cfg.elevenlabs_model or "eleven_multilingual_v2",
            "voice_settings": {
                "stability": cfg.elevenlabs_stability,
                "similarity_boost": cfg.elevenlabs_similarity,
            },
        }
        url = self.API_URL.format(voice_id=voice_id)
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)


def get_tts_provider(cfg: TtsConfig) -> TtsProvider:
    provider = (cfg.provider or "edge").lower()
    if provider == "edge":
        return EdgeTtsProvider()
    if provider == "elevenlabs":
        return ElevenLabsProvider()
    raise ValueError(f"Unknown TTS provider: {provider!r}. Use 'edge' or 'elevenlabs'.")


async def synthesize_batch(
    pairs: list[tuple[str, str]],
    out_dir: Path,
    cfg: TtsConfig,
    *,
    force: bool = False,
) -> int:
    """Generate mp3 files for (subtitle, speech) pairs. Returns count written."""
    provider = get_tts_provider(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for i, (subtitle, speech) in enumerate(pairs):
        path = out_dir / f"{i:02d}.mp3"
        if path.exists() and not force:
            continue
        print(f"  TTS [{i:02d}] {subtitle[:50]}…")
        await provider.synthesize(speech, path, cfg)
        written += 1
    return written
