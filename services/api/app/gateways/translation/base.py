from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TranslationAdapter(ABC):
    """Abstract interface for translation adapters."""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier of the translation provider."""
        ...

    @abstractmethod
    async def translate(
        self,
        text: str,
        src: str = "en",
        tgt: str = "hi",
        **kwargs: Any,
    ) -> str:
        """Translate text from source language code to target language code."""
        ...
