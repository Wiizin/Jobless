"""Matching slice tests.

stage2_score talks to OpenRouter (OpenAI-compatible chat completions), so
it's tested here with the client mocked — we assert the tool-call contract
(structured MatchResult), not real model behavior.

Redis is patched out too: without that, the result depends on whether the
developer happens to have a local Redis holding a cached score. Patching it
to None pins the test to the cache-miss path, where the LLM is actually
called.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.match import MatchResult


def _fake_tool_call_response(tool_name: str, payload: dict):
    call = MagicMock()
    call.function.name = tool_name
    call.function.arguments = json.dumps(payload)
    response = MagicMock()
    response.choices[0].message.tool_calls = [call]
    return response


@pytest.mark.asyncio
async def test_stage2_score_parses_tool_call_response():
    from app.db.models import Offer, OfferStatus
    from app.db.models import Profile
    from app.services import matching

    offer = Offer(
        source="manual",
        external_id="1",
        title="Backend Intern",
        company="Acme",
        location="Remote",
        contract_type="internship",
        description="Write Python.",
        url="https://example.com/1",
        status=OfferStatus.new,
    )
    profile = Profile(full_name="Jane Doe", email="jane@example.com", summary="CS student", links={})
    profile.skills = []
    profile.experiences = []
    profile.education = []
    profile.certifications = []

    fake_payload = {
        "score": 82,
        "reasoning": "Strong Python overlap.",
        "missing_skills": ["Kubernetes"],
        "dealbreakers": [],
    }

    with patch("app.services.llm_client.get_client") as mock_get_client, \
         patch("app.services.cache.get_redis", return_value=None):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_tool_call_response(
            "submit_match_result", fake_payload
        )
        mock_get_client.return_value = mock_client

        result = await matching.stage2_score(offer, profile)

    assert isinstance(result, MatchResult)
    assert result.score == 82
    assert result.missing_skills == ["Kubernetes"]
    # cache miss => exactly one LLM call, no silent retry or double-scoring
    assert mock_client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_stage2_score_returns_cached_result_without_calling_llm():
    """A cache hit must short-circuit the paid call entirely."""
    from app.db.models import Offer, OfferStatus, Profile
    from app.services import matching

    offer = Offer(
        source="manual",
        external_id="1",
        title="Backend Intern",
        company="Acme",
        location="Remote",
        contract_type="internship",
        description="Write Python.",
        url="https://example.com/1",
        status=OfferStatus.new,
    )
    profile = Profile(full_name="Jane Doe", email="jane@example.com", summary="CS student", links={})
    profile.skills = []
    profile.experiences = []
    profile.education = []
    profile.certifications = []

    cached_json = MatchResult(
        score=64, reasoning="cached", missing_skills=["Go"], dealbreakers=[]
    ).model_dump_json()

    with patch("app.services.llm_client.get_client") as mock_get_client, \
         patch("app.services.matching.cache_get", AsyncMock(return_value=cached_json)):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = await matching.stage2_score(offer, profile)

    assert result.score == 64
    assert result.reasoning == "cached"
    assert mock_client.chat.completions.create.call_count == 0
