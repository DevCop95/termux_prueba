from __future__ import annotations

import logging
import time
from typing import Any

import requests
from opencage.geocoder import OpenCageGeocode


LOGGER = logging.getLogger(__name__)


def _best_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Picks the result with the highest confidence score.
    """
    if not results:
        return None

    return max(
        results,
        key=lambda item: (
            int(item.get("confidence", 0)),
            len(str(item.get("formatted", ""))),
        ),
    )


def _should_retry(exc: Exception) -> bool:
    """
    Decides whether the error is transient enough to retry.
    """
    if isinstance(exc, requests.exceptions.RequestException):
        return True

    name = exc.__class__.__name__.lower()
    return any(token in name for token in ("rate", "timeout", "temporary", "quota", "network"))


def _call_with_backoff(action, attempts: int = 3, base_delay: float = 1.0):
    """
    Executes a callable with exponential backoff.
    """
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            return action()
        except Exception as exc:
            last_error = exc
            if attempt == attempts - 1 or not _should_retry(exc):
                break

            delay = base_delay * (2 ** attempt)
            LOGGER.warning("Retrying OpenCage call after %s (%ss)", exc.__class__.__name__, delay)
            time.sleep(delay)

    if last_error:
        raise last_error

    raise RuntimeError("OpenCage call failed without a concrete exception.")


def _candidate_queries(phone_info: dict, lang: str) -> list[str]:
    """
    Builds geocoding queries from phone metadata.
    """
    candidates = [
        phone_info.get("region"),
        phone_info.get("description_es"),
        phone_info.get("description_en"),
        phone_info.get("country"),
    ]

    if lang.lower().startswith("en"):
        candidates = [
            phone_info.get("description_en"),
            phone_info.get("description_es"),
            phone_info.get("region"),
            phone_info.get("country"),
        ]

    deduped: list[str] = []
    for item in candidates:
        if item and item not in deduped:
            deduped.append(item)

    return deduped


def geocode_phone_metadata(phone_info: dict, api_key: str, lang: str = "es") -> dict:
    """
    Resolves approximate coordinates from phone metadata using OpenCage.
    """
    if not api_key:
        return {
            "lat": None,
            "lon": None,
            "address": phone_info.get("region") or phone_info.get("country"),
            "confidence": 0,
            "provider": "offline",
            "note": "OpenCage API key no configurada. Usando solo metadata offline.",
            "query": phone_info.get("region") or phone_info.get("country"),
            "status": "offline_only",
        }

    queries = _candidate_queries(phone_info, lang)
    if not queries:
        return {
            "lat": None,
            "lon": None,
            "address": None,
            "confidence": 0,
            "provider": "offline",
            "note": "No hay suficientes metadatos geograficos para consultar OpenCage.",
            "query": None,
            "status": "offline_only",
        }

    best_match: dict[str, Any] | None = None
    best_query: str | None = None

    try:
        geocoder = OpenCageGeocode(api_key)

        for query in queries:
            results = _call_with_backoff(
                lambda current_query=query: geocoder.geocode(
                    current_query,
                    language=lang,
                    no_annotations=1,
                    limit=5,
                )
            )
            candidate = _best_result(results or [])
            if candidate and (
                best_match is None
                or int(candidate.get("confidence", 0)) > int(best_match.get("confidence", 0))
            ):
                best_match = candidate
                best_query = query

        if not best_match:
            return {
                "lat": None,
                "lon": None,
                "address": phone_info.get("region") or phone_info.get("country"),
                "confidence": 0,
                "provider": "OpenCage",
                "note": "OpenCage no encontro resultados suficientes para estos metadatos.",
                "query": queries[0],
                "status": "no_results",
            }

        lat = best_match["geometry"]["lat"]
        lon = best_match["geometry"]["lng"]
        reverse_results = _call_with_backoff(
            lambda: geocoder.reverse_geocode(lat, lon, language=lang, no_annotations=1)
        )
        reverse_match = _best_result(reverse_results or [])
        address = None
        if reverse_match:
            address = reverse_match.get("formatted")
        if not address:
            address = best_match.get("formatted")

        return {
            "lat": lat,
            "lon": lon,
            "address": address,
            "confidence": int(best_match.get("confidence", 0)),
            "provider": "OpenCage",
            "note": "Ubicacion aproximada obtenida por geocodificacion de metadatos telefonicos.",
            "query": best_query,
            "status": "ok",
        }

    except Exception as exc:
        LOGGER.exception("OpenCage geocoding failed")
        return {
            "lat": None,
            "lon": None,
            "address": phone_info.get("region") or phone_info.get("country"),
            "confidence": 0,
            "provider": "offline",
            "note": f"No fue posible consultar OpenCage ({exc.__class__.__name__}). Se conservaron solo datos offline.",
            "query": queries[0],
            "status": "offline_only",
        }
