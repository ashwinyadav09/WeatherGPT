from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class LLMAdapter(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        ...
