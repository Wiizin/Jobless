"""Ingestion slice tests: source adapters' to_common_dict + normalizer + deduplicator.

Each is independently testable with seeded/mocked input, per the project's
task-ownership boundaries. No network calls here — fetch_* functions are
adapter I/O and are covered separately with httpx mocking if/when real
credentials are wired up.
"""
from datetime import datetime, timezone

from app.schemas.offer import Offer
from app.services.deduplicator import dedupe_batch
from app.services.normalizer import normalize
from app.services.sources import agency_api, aggregator_api, ats_boards


def _offer(**overrides) -> Offer:
    base = dict(
        source="manual",
        external_id="1",
        title="Software Engineer Intern",
        company="Acme Corp",
        location="Remote",
        contract_type="internship",
        description="Build things.",
        url="https://example.com/job/1",
        posted_date=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return Offer(**base)


def test_agency_api_to_common_dict_maps_fields():
    raw = {
        "id": 42,
        "title": "Backend Developer",
        "company": {"name": "Acme"},
        "location": "Tunis",
        "contract_type": "full-time",
        "description": "Do backend things.",
        "url": "https://example.com/42",
        "posted_date": "2026-01-01T00:00:00Z",
    }
    common = agency_api.to_common_dict(raw)
    assert common["source"] == "agency_api"
    assert common["external_id"] == "42"
    assert common["company"] == "Acme"


def test_aggregator_api_to_common_dict_maps_fields():
    raw = {
        "id": 7,
        "title": "Data Analyst",
        "company": {"display_name": "BigCo"},
        "location": {"display_name": "Paris"},
        "contract_time": "full_time",
        "description": "Analyze data.",
        "redirect_url": "https://example.com/7",
        "created": "2026-02-01T00:00:00Z",
    }
    common = aggregator_api.to_common_dict(raw)
    assert common["source"] == "aggregator_api"
    assert common["company"] == "BigCo"
    assert common["location"] == "Paris"


def test_ats_boards_greenhouse_to_common_dict():
    raw = {
        "_board_token": "acme",
        "id": 99,
        "title": "Platform Engineer",
        "location": {"name": "Remote"},
        "content": "<p>Do platform things.</p>",
        "absolute_url": "https://boards.greenhouse.io/acme/jobs/99",
        "updated_at": "2026-03-01T00:00:00Z",
    }
    common = ats_boards.to_common_dict(raw)
    assert common["source"] == "ats_boards"
    assert common["external_id"] == "greenhouse:99"
    assert common["company"] == "acme"


def test_normalize_fills_blank_required_fields():
    raw = {
        "id": 1,
        "title": "Intern",
        "company": {"name": "Acme"},
        "location": "",
        "contract_type": "",
        "description": "",
        "url": "https://example.com/1",
        "posted_date": None,
    }
    offer = normalize("agency_api", raw)
    assert offer.location == "Unspecified"
    assert offer.contract_type == "Unspecified"


def test_dedupe_drops_exact_source_id_match():
    existing = [_offer(source="agency_api", external_id="1")]
    candidates = [
        _offer(source="agency_api", external_id="1"),
        _offer(source="agency_api", external_id="2", title="Data Engineer Intern", company="Other Co"),
    ]
    unique = dedupe_batch(candidates, existing_offers=existing)
    assert len(unique) == 1
    assert unique[0].external_id == "2"


def test_dedupe_drops_fuzzy_cross_source_match():
    existing = [_offer(source="agency_api", external_id="1", company="Acme Corp", title="Software Engineer Intern")]
    candidates = [
        _offer(source="aggregator_api", external_id="99", company="Acme Corp", title="Software Engineer Intern ")
    ]
    unique = dedupe_batch(candidates, existing_offers=existing)
    assert unique == []


def test_dedupe_keeps_distinct_offers():
    candidates = [
        _offer(source="agency_api", external_id="1", title="Backend Engineer"),
        _offer(source="agency_api", external_id="2", title="Frontend Engineer", company="Other Co"),
    ]
    unique = dedupe_batch(candidates)
    assert len(unique) == 2
