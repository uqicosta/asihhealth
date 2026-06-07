"""
Base classes for TTS providers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .utils import _split_text_into_chunks, _concat_mp3_chunks_ffmpeg


class TTSProvider(ABC):
    """Abstract base for all TTS providers."""

    @abstractmethod
    def generate(self, script_text: str, output_name: Optional[str] = None) -> Path:
        """Generate audio from text and return the output Path."""
        pass


class BaseChunkedTTSProvider(TTSProvider):
    """
    Base for cloud providers that split long text and concatenate results
    (OpenAI and ElevenLabs share this pattern).
    """

    def _get_chunk_max_chars(self) -> int:
        return 4000

    @abstractmethod
    def _generate_single_chunk(self, text: str, **kwargs) -> bytes:
        """Subclasses implement this: return raw audio bytes for one chunk."""
        pass

    def generate_chunked(
        self,
        cleaned_text: str,
        output_path: Path,
        provider_name: str,
        **kwargs
    ) -> Path:
        max_chars = self._get_chunk_max_chars()
        chunks = _split_text_into_chunks(cleaned_text, max_chars=max_chars)

        from .. import logger  # avoid circular if needed, but we'll import inside

        logger.info(
            f"Generating {provider_name} TTS — {len(chunks)} chunk(s), "
            f"total {len(cleaned_text)} chars"
        )

        if len(chunks) == 1:
            audio_bytes = self._generate_single_chunk(chunks[0], **kwargs)
            output_path.write_bytes(audio_bytes)
        else:
            chunk_files: list[Path] = []
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                for idx, chunk in enumerate(chunks):
                    audio_bytes = self._generate_single_chunk(chunk, **kwargs)
                    chunk_path = tmpdir_path / f"tts_chunk_{idx:03d}.mp3"
                    chunk_path.write_bytes(audio_bytes)
                    chunk_files.append(chunk_path)
                    logger.info(f"  Chunk {idx+1}/{len(chunks)} synthesized ({len(chunk)} chars)")

                _concat_mp3_chunks_ffmpeg(chunk_files, output_path)
                logger.info(f"  Concatenated {len(chunks)} chunks with FFmpeg → final audio")

        file_size = output_path.stat().st_size
        if file_size < 100:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"{provider_name} TTS mengembalikan audio kosong / terlalu kecil.")

        logger.info(f"{provider_name} TTS voiceover saved: {output_path} ({file_size} bytes)")
        return output_path
