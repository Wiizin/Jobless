"""CV-upload import tests.

parse_cv_text goes through the OpenRouter client, so it's mocked here the
same way tests/test_matching.py and tests/test_generation.py do it — we
assert the tool-call contract and the DB writes, not real model behavior.

Real PDF binary parsing isn't covered: that's pypdf's job. What's ours is
the dispatch, the structured-output contract, and the fact that a CV with
no email can't quietly become a profile.
"""
import io
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.profile import ParsedProfile


def _fake_tool_call_response(tool_name: str, payload: dict):
    call = MagicMock()
    call.function.name = tool_name
    call.function.arguments = json.dumps(payload)
    response = MagicMock()
    response.choices[0].message.tool_calls = [call]
    return response


def _docx_bytes(paragraphs: list[str]) -> bytes:
    """A real .docx built in-memory, so extract_text is exercised end to end."""
    from docx import Document as DocxDocument

    document = DocxDocument()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_text_reads_docx_paragraphs():
    from app.services import cv_import

    content = _docx_bytes(["Jane Doe", "jane@example.com", "Backend Intern at Acme"])
    text = cv_import.extract_text("cv.docx", content)

    assert "Jane Doe" in text
    assert "jane@example.com" in text
    assert "Backend Intern at Acme" in text


def test_extract_text_reads_latex_source():
    from app.services import cv_import

    tex = rb"\section{Experience} \textbf{Backend Intern} at Acme"
    text = cv_import.extract_text("cv.tex", tex)

    assert "Backend Intern" in text


def test_extract_text_rejects_unsupported_extension():
    from app.services import cv_import

    with pytest.raises(ValueError) as exc:
        cv_import.extract_text("cv.png", b"\x89PNG\r\n")

    assert "png" in str(exc.value).lower()


def test_parse_cv_text_returns_parsed_profile():
    from app.services import cv_import

    fake_payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": None,
        "location": "Remote",
        "summary": "CS student",
        "links": {"github": "https://github.com/janedoe"},
        "experiences": [
            {
                "title": "Backend Intern",
                "company": "Acme",
                "location": "Remote",
                "start_date": "2024-06-01",
                "end_date": None,
                "is_current": True,
                "description": None,
                "bullets": ["Shipped a Python service"],
            }
        ],
        "skills": [{"name": "Python", "category": "language", "proficiency": None}],
        "education": [
            {
                "institution": "State University",
                "degree": "BSc",
                "field_of_study": "Computer Science",
                "start_date": "2022-09-01",
                "end_date": None,
                "description": None,
            }
        ],
        "certifications": [],
    }

    with patch("app.services.llm_client.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_tool_call_response(
            "submit_parsed_profile", fake_payload
        )
        mock_get_client.return_value = mock_client

        parsed = cv_import.parse_cv_text("Jane Doe\njane@example.com\nBackend Intern at Acme")

    assert isinstance(parsed, ParsedProfile)
    assert parsed.full_name == "Jane Doe"
    assert parsed.links == {"github": "https://github.com/janedoe"}
    assert [e.title for e in parsed.experiences] == ["Backend Intern"]
    assert parsed.experiences[0].start_date.isoformat() == "2024-06-01"
    assert [s.name for s in parsed.skills] == ["Python"]
    assert [e.institution for e in parsed.education] == ["State University"]
    assert parsed.certifications == []

    # The model must be pinned to the extraction tool, not left to free text.
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["tool_choice"]["function"]["name"] == "submit_parsed_profile"


class _FakeResult:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one(self):
        return self._obj


class _FakeSession:
    """Minimal AsyncSession stand-in — the models need Postgres (UUID +
    pgvector), so there's no in-memory DB to run this against."""

    def __init__(self):
        self.added = []
        self.deleted_models = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def execute(self, stmt):
        if getattr(stmt, "is_delete", False):
            self.deleted_models.append(stmt.table.name)
            return MagicMock()
        # the final eager-loaded re-select
        profile = next(o for o in self.added if type(o).__name__ == "Profile")
        return _FakeResult(profile)

    async def commit(self):
        self.commits += 1

    def expire(self, obj):
        pass


@pytest.mark.asyncio
async def test_apply_parsed_profile_creates_new_profile():
    from app.db.models import Certification, Education, Experience, Profile, Skill
    from app.services import cv_import

    parsed = ParsedProfile.model_validate(
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "location": "Remote",
            "summary": "CS student",
            "links": {"github": "https://github.com/janedoe"},
            "experiences": [
                {"title": "Backend Intern", "company": "Acme", "bullets": ["Shipped a Python service"]}
            ],
            "skills": [{"name": "Python"}],
            "education": [{"institution": "State University", "degree": "BSc"}],
            "certifications": [{"name": "AWS Cloud Practitioner"}],
        }
    )

    db = _FakeSession()
    profile = await cv_import.apply_parsed_profile(db, None, parsed)

    assert isinstance(profile, Profile)
    assert profile.full_name == "Jane Doe"
    assert profile.email == "jane@example.com"
    assert profile.links == {"github": "https://github.com/janedoe"}

    # children written from the CV, all hung off the new profile
    by_type = {}
    for obj in db.added:
        by_type.setdefault(type(obj), []).append(obj)
    assert len(by_type[Experience]) == 1
    assert by_type[Experience][0].title == "Backend Intern"
    assert len(by_type[Skill]) == 1
    assert len(by_type[Education]) == 1
    assert len(by_type[Certification]) == 1
    assert all(
        child.profile_id == profile.id
        for model in (Experience, Skill, Education, Certification)
        for child in by_type[model]
    )

    # full re-sync: every child table is cleared before the inserts
    assert set(db.deleted_models) == {"experiences", "skills", "education", "certifications"}
    assert db.commits == 1


@pytest.mark.asyncio
async def test_apply_parsed_profile_rejects_cv_without_email():
    """An email can't be invented, and Profile.email is NOT NULL — so a CV
    that didn't yield one must fail loudly rather than store a placeholder."""
    from app.services import cv_import

    parsed = ParsedProfile.model_validate({"full_name": "Jane Doe", "email": None})

    db = _FakeSession()
    with pytest.raises(ValueError) as exc:
        await cv_import.apply_parsed_profile(db, None, parsed)

    assert "email" in str(exc.value).lower()
    assert db.added == []
    assert db.commits == 0
