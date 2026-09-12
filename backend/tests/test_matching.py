"""Matching slice tests.

stage2_score talks to the Anthropic API, so it's tested here with the
client mocked — we assert the tool-use contract (structured MatchResult),
not real model behavior.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.match import MatchResult


def _fake_tool_use_message(payload: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_match_result"
    block.input = payload
    message = MagicMock()
    message.content = [block]
    return message


@pytest.mark.asyncio
async def test_stage2_score_parses_tool_use_response():
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

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_tool_use_message(fake_payload)
        mock_anthropic_cls.return_value = mock_client

        result = await matching.stage2_score(offer, profile)

    assert isinstance(result, MatchResult)
    assert result.score == 82
    assert result.missing_skills == ["Kubernetes"]
