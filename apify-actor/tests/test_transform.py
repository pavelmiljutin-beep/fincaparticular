"""Unit tests for the Actor's pure transforms (no apify/network needed)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transform import (  # noqa: E402
    build_payload,
    coverage_params,
    coverage_record,
    quota_record,
    record_from_response,
)


def test_build_payload_location_string():
    payload = build_payload({"location": " 40.4,-3.7 ", "language": "es"})
    assert payload["location"] == "40.4,-3.7"
    assert payload["language"] == "es"


def test_build_payload_defaults_to_json_facts_without_images():
    payload = build_payload({"location": "40.4,-3.7"})
    assert payload["format"] == "json"
    assert payload["detail"] == "full"
    assert payload["includeImages"] is False


def test_build_payload_lat_lng():
    payload = build_payload({"lat": "40.4", "lng": "-3.7"})
    assert payload["lat"] == "40.4"
    assert payload["lng"] == "-3.7"
    assert payload["language"] == "en"


def test_build_payload_persist_flag():
    payload = build_payload({"location": "40,-3", "persist": True})
    assert payload["persist"] is True


def test_build_payload_ref():
    payload = build_payload({"ref": " 8034006VP3183C0001IH ", "country": "es"})
    assert payload["ref"] == "8034006VP3183C0001IH"
    assert payload["country"] == "ES"


def test_build_payload_ref_takes_priority_over_coords():
    payload = build_payload({"ref": "8034006VP3183C0001IH", "lat": "40", "lng": "-3"})
    assert payload["ref"] == "8034006VP3183C0001IH"
    assert "lat" not in payload


def test_build_payload_forwards_chapter_selection():
    payload = build_payload(
        {
            "location": "40,-3",
            "chapters": ["mold-risk", " flood-risk-snczi "],
            "excludeChapters": "old-maps-overlay",
        }
    )
    assert payload["chapters"] == ["mold-risk", "flood-risk-snczi"]
    assert payload["excludeChapters"] == ["old-maps-overlay"]


def test_build_payload_omits_empty_chapter_lists():
    payload = build_payload({"location": "40,-3", "chapters": []})
    assert "chapters" not in payload


def test_build_payload_missing_location_raises():
    with pytest.raises(ValueError):
        build_payload({"language": "en"})


def test_coverage_params_from_location_string():
    assert coverage_params({"location": "40.4,-3.7"}) == {"lat": 40.4, "lng": -3.7}


def test_coverage_params_accepts_radius():
    params = coverage_params({"lat": "40.4", "lng": "-3.7", "radiusKm": "8"})
    assert params["radius_km"] == 8.0


def test_coverage_params_rejects_a_reference_only_run():
    with pytest.raises(ValueError):
        coverage_params({"ref": "8034006VP3183C0001IH"})


def test_record_from_response_flattens():
    data = {
        "summary": {"overall_verdict": "mixed", "red_flags": []},
        "chapters": [{"slug": "flood-risk-snczi", "verdict": "favorable"}],
        "markdown": "# Report",
        "metadata": {
            "language": "en",
            "chapter_count": 3,
            "chapters": ["cadastral-identity", "flood-risk-snczi"],
            "chapters_failed": [],
            "chapters_skipped": ["old-maps-overlay"],
            "location": {
                "ref": "1234",
                "country": "ES",
                "province": "Madrid",
                "municipality": "Madrid",
                "lat": 40.4,
                "lng": -3.7,
            },
        },
        "price": {"amount": "3.00", "currency": "USD", "plan": "ai-agent"},
    }
    rec = record_from_response(data)
    assert rec["status"] == "ready"
    assert rec["summary"]["overall_verdict"] == "mixed"
    assert rec["chapters"][0]["slug"] == "flood-risk-snczi"
    assert rec["chapterSlugs"] == ["cadastral-identity", "flood-risk-snczi"]
    assert rec["chaptersSkipped"] == ["old-maps-overlay"]
    assert rec["ref"] == "1234"
    assert rec["chapterCount"] == 3
    assert rec["priceAmount"] == "3.00"


def test_record_omits_markdown_when_the_rail_returned_none():
    rec = record_from_response({"summary": {}, "chapters": []})
    assert "markdown" not in rec


def test_record_from_response_tolerates_missing_fields():
    rec = record_from_response({})
    assert rec["ref"] is None
    assert rec["summary"] is None


def test_coverage_record_exposes_the_size_forecast():
    rec = coverage_record(
        {
            "lat": 40.4,
            "lng": -3.7,
            "radius_km": 5.0,
            "coverage_level": "rich",
            "poi_total": 37,
            "chapters_expected": 22,
            "size_estimates": [{"format": "json", "estimated_tokens": 6600}],
        }
    )
    assert rec["status"] == "preview"
    assert rec["coverageLevel"] == "rich"
    assert rec["sizeEstimates"][0]["estimated_tokens"] == 6600


def test_record_reports_whether_the_result_was_replayed():
    rec = record_from_response(
        {"cache": "hit", "cached_at": "2026-09-01T10:00:00+00:00"}
    )
    assert rec["cache"] == "hit"
    assert rec["cachedAt"] == "2026-09-01T10:00:00+00:00"


def test_quota_record_says_when_the_allowance_returns():
    rec = quota_record(
        {
            "message": "Fair-use cap reached",
            "quota": {
                "window": "day",
                "used": 50,
                "limit": 50,
                "resets_at": "2026-09-04T00:00:00+00:00",
            },
        }
    )
    assert rec["status"] == "quota_exceeded"
    assert rec["quotaWindow"] == "day"
    assert rec["quotaUsed"] == 50
    assert rec["quotaResetsAt"] == "2026-09-04T00:00:00+00:00"
