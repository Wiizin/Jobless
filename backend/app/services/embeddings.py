"""sentence-transformers wrapper for offer/profile embeddings (pgvector column)."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings

settings = get_settings()


@lru_cache
def _get_model():
    # Imported lazily so the module can be imported (e.g. by tests that mock
    # this function) without pulling in torch/sentence-transformers.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model_name)


def embed_text(text: str) -> list[float]:
    """Embed a single string. Returns a plain list[float] for pgvector."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]


def offer_embedding_text(title: str, company: str, description: str) -> str:
    """Canonical text an offer is embedded from — keep stable, changing it
    invalidates every previously-stored offer embedding."""
    return f"{title}\n{company}\n{description}"


def profile_embedding_text(summary: str, skills: list[str], experience_titles: list[str]) -> str:
    parts = [summary or "", "Skills: " + ", ".join(skills), "Experience: " + ", ".join(experience_titles)]
    return "\n".join(p for p in parts if p)
