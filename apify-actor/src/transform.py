"""Pure input/output transforms for the Parcelabot Apify Actor.

Kept free of the ``apify`` SDK so it can be unit-tested without it.
"""
from __future__ import annotations

# Machine callers get structured facts and no inlined base64 maps unless
# they ask otherwise: a single map image outweighs the whole text report.
DEFAULT_FORMAT = "json"
DEFAULT_DETAIL = "full"


def _slug_list(value) -> list[str] | None:
    """Accept a list or a comma-separated string of chapter slugs."""
    if value is None:
        return None
    if isinstance(value, str):
        slugs = [s.strip() for s in value.split(",") if s.strip()]
    elif isinstance(value, (list, tuple)):
        slugs = [str(s).strip() for s in value if str(s).strip()]
    else:
        raise ValueError(
            "Chapter lists must be an array or a comma-separated string."
        )
    return slugs or None


def build_location(inp: dict) -> dict:
    """Extract just the location keys from the Actor input.

    Raises ``ValueError`` when no usable location/reference was provided.
    """
    out: dict = {}
    ref = inp.get("ref")
    location = inp.get("location")
    lat = inp.get("lat")
    lng = inp.get("lng")
    if isinstance(ref, str) and ref.strip():
        out["ref"] = ref.strip()
        if inp.get("country"):
            out["country"] = str(inp["country"]).strip().upper()
    elif isinstance(location, str) and location.strip():
        out["location"] = location.strip()
    elif lat not in (None, "") and lng not in (None, ""):
        out["lat"] = lat
        out["lng"] = lng
    else:
        raise ValueError(
            "Provide 'ref' (cadastral reference), 'location' as 'lat,lng', "
            "or both 'lat' and 'lng'."
        )
    return out


def build_payload(inp: dict) -> dict:
    """Map Actor input to the partner endpoint request body."""
    payload: dict = {
        "language": (inp.get("language") or "en"),
        "format": (inp.get("format") or DEFAULT_FORMAT),
        "detail": (inp.get("detail") or DEFAULT_DETAIL),
        "includeImages": bool(inp.get("includeImages", False)),
        **build_location(inp),
    }

    chapters = _slug_list(inp.get("chapters"))
    if chapters:
        payload["chapters"] = chapters
    excluded = _slug_list(inp.get("excludeChapters"))
    if excluded:
        payload["excludeChapters"] = excluded

    if inp.get("persist") is not None:
        payload["persist"] = bool(inp["persist"])
    return payload


def coverage_params(inp: dict) -> dict:
    """Query parameters for the free coverage preview.

    The preview is coordinate-only, so a run that supplied only a
    cadastral reference cannot be previewed.
    """
    loc = build_location(inp)
    if "lat" in loc and "lng" in loc:
        lat, lng = loc["lat"], loc["lng"]
    elif "location" in loc:
        parts = [p.strip() for p in str(loc["location"]).split(",")]
        if len(parts) != 2:
            raise ValueError("'location' must be 'lat,lng' decimal degrees.")
        lat, lng = parts
    else:
        raise ValueError(
            "A dry run needs coordinates — pass 'location' as 'lat,lng' or "
            "'lat' and 'lng'. Cadastral references cannot be previewed."
        )
    params = {"lat": float(lat), "lng": float(lng)}
    if inp.get("radiusKm"):
        params["radius_km"] = float(inp["radiusKm"])
    return params


def record_from_response(data: dict) -> dict:
    """Flatten the endpoint response into a dataset record.

    ``summary`` is deliberately first-class: it is the part an agent
    reads to decide whether to look at anything else.
    """
    meta = data.get("metadata") or {}
    loc = meta.get("location") or {}
    price = data.get("price") or {}
    record = {
        "status": "ready",
        "cache": data.get("cache"),
        "summary": data.get("summary"),
        "chapters": data.get("chapters"),
        "metadata": meta,
        "ref": loc.get("ref"),
        "country": loc.get("country"),
        "province": loc.get("province"),
        "municipality": loc.get("municipality"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "language": meta.get("language"),
        "chapterCount": meta.get("chapter_count"),
        "chapterSlugs": meta.get("chapters"),
        "chaptersFailed": meta.get("chapters_failed"),
        "chaptersSkipped": meta.get("chapters_skipped"),
        "priceAmount": price.get("amount"),
        "priceCurrency": price.get("currency"),
        "pricePlan": price.get("plan"),
    }
    if data.get("cached_at"):
        record["cachedAt"] = data["cached_at"]
    if data.get("markdown"):
        record["markdown"] = data["markdown"]
    return record


def quota_record(data: dict) -> dict:
    """Flatten a fair-use rejection into a dataset record."""
    quota = data.get("quota") or {}
    return {
        "status": "quota_exceeded",
        "message": data.get("message"),
        "quotaWindow": quota.get("window"),
        "quotaUsed": quota.get("used"),
        "quotaLimit": quota.get("limit"),
        "quotaResetsAt": quota.get("resets_at"),
    }


def coverage_record(data: dict) -> dict:
    """Flatten a coverage preview into a dataset record."""
    return {
        "status": "preview",
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "radiusKm": data.get("radius_km"),
        "coverageLevel": data.get("coverage_level"),
        "poiTotal": data.get("poi_total"),
        "chapterCount": data.get("chapters_expected"),
        "chapters": data.get("chapters"),
        "chaptersUnavailable": data.get("chapters_unavailable"),
        "sizeEstimates": data.get("size_estimates"),
        "datasets": data.get("datasets"),
        "categories": data.get("categories"),
    }
