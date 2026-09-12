"""Generation slice tests — focused on the no-fabrication guarantee.

If Claude's structured response references an experience ID that was never
in the profile catalog offered to it, generate_document must drop it
rather than persist a fabricated reference.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.document import GeneratedDocument


def _fake_tool_use_message(payload: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_generated_document"
    block.input = payload
    message = MagicMock()
    message.content = [block]
    return message


@pytest.mark.asyncio
async def test_generate_document_strips_unknown_experience_ids():
    from app.db.models import Experience, Offer, OfferStatus, Profile
    from app.services import generation

    real_experience_id = uuid.uuid4()
    fabricated_id = uuid.uuid4()

    profile = Profile(full_name="Jane Doe", email="jane@example.com", summary="CS student", links={})
    exp = Experience(
        id=real_experience_id,
        title="Backend Intern",
        company="Acme",
        bullets=["Shipped a Python service"],
    )
    profile.experiences = [exp]
    profile.skills = []
    profile.education = []
    profile.certifications = []

    offer = Offer(
        source="manual",
        external_id="1",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        contract_type="full-time",
        description="Write Python.",
        url="https://example.com/1",
        status=OfferStatus.new,
        missing_skills=[],
    )

    fake_payload = {
        "selected_experiences": [str(real_experience_id), str(fabricated_id)],
        "bullets": ["Shipped a Python service handling production traffic"],
        "cover_letter_sections": None,
        "qa_answers": {},
        "status": "pending_review",
    }

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_tool_use_message(fake_payload)
        mock_anthropic_cls.return_value = mock_client

        result = await generation.generate_document(offer, profile)

    assert isinstance(result, GeneratedDocument)
    assert result.selected_experiences == [real_experience_id]
    assert fabricated_id not in result.selected_experiences
