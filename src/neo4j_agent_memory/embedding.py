from __future__ import annotations

import os
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed(self, text: str) -> list[float]: ...


class OpenAIEmbeddingProvider:
    """Optional hosted embeddings. Constructing this provider makes no API call."""

    def __init__(self, model: str, dimensions: int):
        self.model = model
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when embedding text")
        from openai import OpenAI

        result = OpenAI(api_key=api_key).embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        vector = result.data[0].embedding
        if len(vector) != self.dimensions:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected {self.dimensions}, got {len(vector)}"
            )
        return vector
