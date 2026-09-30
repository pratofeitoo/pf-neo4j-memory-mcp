from __future__ import annotations

import os
import json
import ipaddress
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed_document(self, text: str) -> list[float]: ...

    def embed_query(self, text: str) -> list[float]: ...


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

    def embed_document(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)


class OllamaEmbeddingProvider:
    """Local Nomic embeddings, with separate document and query instructions."""

    def __init__(self, model: str, dimensions: int, base_url: str, model_digest: str):
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        if parsed.scheme != "http" or not hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Ollama URL must be a loopback HTTP origin")
        try:
            loopback = hostname.lower() == "localhost" or ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            loopback = hostname.lower() == "localhost"
        if not loopback:
            raise ValueError("Ollama URL must be a loopback HTTP origin")
        if not model_digest or len(model_digest) != 64 or any(c not in "0123456789abcdef" for c in model_digest.lower()):
            raise ValueError("MEMORY_OLLAMA_MODEL_DIGEST must be a full SHA-256 digest")
        self.model_name = model
        self.model_digest = model_digest.lower()
        self.model = f"ollama:{model}@{self.model_digest}"
        self.dimensions = dimensions
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(self.base_url + path, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def _verify_model(self) -> None:
        models = self._request("/api/tags").get("models", [])
        actual = next((entry.get("digest") for entry in models if entry.get("name") == self.model_name), None)
        if actual != self.model_digest:
            raise RuntimeError(f"Ollama model {self.model_name} is missing or its digest changed; update the configured digest only after reviewing the new model")

    def _embed(self, text: str, prefix: str) -> list[float]:
        self._verify_model()
        result = self._request("/api/embed", {"model": self.model_name, "input": f"{prefix}: {text}", "truncate": False})
        vectors = result.get("embeddings", [])
        if len(vectors) != 1 or len(vectors[0]) != self.dimensions:
            raise RuntimeError(f"Ollama embedding dimension mismatch: expected {self.dimensions}")
        return vectors[0]

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text, "search_document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, "search_query")
