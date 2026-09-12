"""Matching slice tests.

stage2_score talks to OpenRouter (OpenAI-compatible chat completions), so
it's tested here with the client mocked — we assert the tool-call contract
(structured MatchResult), not real model behavior.
"""
import json
from unittest.mock import MagicMock, patch

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

    with patch("app.services.llm_client.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_tool_call_response(
            "submit_match_result", fake_payload
        )
        mock_get_client.return_value = mock_client

        result = await matching.stage2_score(offer, profile)

    assert isinstance(result, MatchResult)
    assert result.score == 82
    assert result.missing_skills == ["Kubernetes"]
