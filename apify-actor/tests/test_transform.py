"""Unit tests for the Actor's pure transforms (no apify/network needed)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transform import build_payload, record_from_response  # noqa: E402


def test_build_payload_location_string():
    payload = build_payload({"location": " 40.4,-3.7 ", "language": "es"})
    assert payload == {"language": "es", "location": "40.4,-3.7"}


def test_build_payload_lat_lng():
    payload = build_payload({"lat": "40.4", "lng": "-3.7"})
    assert payload["lat"] == "40.4"
    assert payload["lng"] == "-3.7"
    assert payload["language"] == "en"


def test_build_payload_persist_flag():
    payload = build_payload({"location": "40,-3", "persist": True})
    assert payload["persist"] is True


def test_build_payload_missing_location_raises():
    with pytest.raises(ValueError):
        build_payload({"language": "en"})


def test_record_from_response_flattens():
    data = {
        "markdown": "# Report",
        "metadata": {
            "language": "en",
            "chapter_count": 3,
            "chapters": ["cadastral-identity", "flood-risk-snczi"],
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
    assert rec["markdown"] == "# Report"
    assert rec["ref"] == "1234"
    assert rec["country"] == "ES"
    assert rec["chapterCount"] == 3
    assert rec["priceAmount"] == "3.00"
    assert rec["priceCurrency"] == "USD"


def test_record_from_response_tolerates_missing_fields():
    rec = record_from_response({})
    assert rec["markdown"] is None
    assert rec["ref"] is None
    assert rec["chapters"] is None
