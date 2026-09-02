"""Pure input/output transforms for the Parcelabot Apify Actor.

Kept free of the ``apify`` SDK so it can be unit-tested without it.
"""
from __future__ import annotations


def build_payload(inp: dict) -> dict:
    """Map Actor input to the partner endpoint request body.

    Raises ``ValueError`` when no usable location/reference was provided.
    """
    payload: dict = {"language": (inp.get("language") or "en")}

    ref = inp.get("ref")
    location = inp.get("location")
    lat = inp.get("lat")
    lng = inp.get("lng")
    if isinstance(ref, str) and ref.strip():
        payload["ref"] = ref.strip()
        if inp.get("country"):
            payload["country"] = str(inp["country"]).strip().upper()
    elif isinstance(location, str) and location.strip():
        payload["location"] = location.strip()
    elif lat not in (None, "") and lng not in (None, ""):
        payload["lat"] = lat
        payload["lng"] = lng
    else:
        raise ValueError(
            "Provide 'ref' (cadastral reference), 'location' as 'lat,lng', "
            "or both 'lat' and 'lng'."
        )

    if inp.get("persist") is not None:
        payload["persist"] = bool(inp["persist"])
    return payload


def record_from_response(data: dict) -> dict:
    """Flatten the endpoint response into a dataset record."""
    meta = data.get("metadata") or {}
    loc = meta.get("location") or {}
    price = data.get("price") or {}
    return {
        "markdown": data.get("markdown"),
        "metadata": meta,
        "ref": loc.get("ref"),
        "country": loc.get("country"),
        "province": loc.get("province"),
        "municipality": loc.get("municipality"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "language": meta.get("language"),
        "chapterCount": meta.get("chapter_count"),
        "chapters": meta.get("chapters"),
        "priceAmount": price.get("amount"),
        "priceCurrency": price.get("currency"),
        "pricePlan": price.get("plan"),
    }
