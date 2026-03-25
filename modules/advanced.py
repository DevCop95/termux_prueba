from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "on", "si"}


@dataclass(slots=True)
class AppSettings:
    """
    Runtime settings loaded from environment variables and .env.
    """

    opencage_api_key: str
    default_lang: str = "es"
    map_zoom: int = 9
    enable_circle: bool = True
    circle_radius_km: float = 50.0
    dork_max_results: int = 3
    output_dir: Path = Path("output")


def load_env_file(env_path: str | Path = ".env") -> dict[str, str]:
    """
    Loads a simple .env file without introducing extra dependencies.
    """
    path = Path(env_path)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip('"').strip("'")

    return values


def load_legacy_config(config_path: str | Path = "config.json") -> dict:
    """
    Loads the legacy JSON config if it exists.
    """
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_settings(env_path: str | Path = ".env") -> AppSettings:
    """
    Builds application settings from environment variables, .env and legacy config.json.
    """
    env_values = load_env_file(env_path)
    legacy_config = load_legacy_config()

    def env_value(name: str, default: str) -> str:
        return os.getenv(name, env_values.get(name, default))

    opencage_key = env_value("OPENCAGE_API_KEY", "")
    if not opencage_key:
        opencage_key = legacy_config.get("opencage", {}).get("api_key", "")

    output_dir = Path(env_value("OUTPUT_DIR", "output"))
    return AppSettings(
        opencage_api_key=opencage_key,
        default_lang=env_value("DEFAULT_LANG", "es"),
        map_zoom=int(env_value("MAP_ZOOM", "9")),
        enable_circle=env_value("ENABLE_CIRCLE", "true").strip().lower() in TRUE_VALUES,
        circle_radius_km=float(env_value("CIRCLE_RADIUS_KM", "50")),
        dork_max_results=int(env_value("DORK_MAX_RESULTS", "3")),
        output_dir=output_dir,
    )


def ensure_output_dir(path: str | Path) -> Path:
    """
    Ensures that an output directory exists and returns it as Path.
    """
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def setup_logging(level_name: str, output_dir: str | Path) -> Path:
    """
    Configures file logging for the CLI.
    """
    ensure_output_dir(output_dir)
    log_path = Path(output_dir) / "phone_geolocator.log"
    level = getattr(logging, level_name.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
    return log_path


def sanitize_number_for_filename(number: str) -> str:
    """
    Removes characters that are inconvenient for file names.
    """
    return "".join(char for char in number if char.isdigit())


def flatten_result_for_csv(result: dict) -> dict[str, str]:
    """
    Normalizes a result dictionary for CSV export.
    """
    return {
        "input_number": str(result.get("input_number", "")),
        "number": str(result.get("number", "")),
        "country": str(result.get("country", "")),
        "country_code": str(result.get("country_code", "")),
        "region": str(result.get("region", "")),
        "carrier": str(result.get("carrier", "")),
        "line_type": str(result.get("line_type", "")),
        "timezones": ", ".join(result.get("timezones", [])) if isinstance(result.get("timezones"), list) else str(result.get("timezones", "")),
        "description_es": str(result.get("description_es", "")),
        "description_en": str(result.get("description_en", "")),
        "npa_nxx": str(result.get("npa_nxx", "")),
        "lat": str(result.get("lat", "")),
        "lon": str(result.get("lon", "")),
        "address": str(result.get("address", "")),
        "confidence": str(result.get("confidence", "")),
        "map_path": str(result.get("map_path", "")),
        "report_path": str(result.get("report_path", "")),
        "precision_level": str(result.get("precision_level", "")),
        "coverage": str(result.get("dork_summary", {}).get("coverage_label", "")),
        "public_mentions": str(result.get("dork_summary", {}).get("public_mentions", "")),
        "status": str(result.get("status", "")),
        "error": str(result.get("error", "")),
        "note": str(result.get("note", "")),
    }


def build_investigation_links(number: str) -> dict[str, str]:
    """
    Creates quick-access links for manual verification.
    """
    clean_number = sanitize_number_for_filename(number)
    encoded_number = number.replace("+", "%2B")
    return {
        "WhatsApp": f"https://wa.me/{clean_number}",
        "Truecaller": f"https://www.truecaller.com/search/{clean_number}",
        "Sync.ME": f"https://sync.me/?number={clean_number}",
        "Tellows": f"https://www.tellows.com/basic/num/{clean_number}",
        "SpamCalls": f"https://spamcalls.net/en/number/{clean_number}",
        "Google exact": f"https://www.google.com/search?q=%22{encoded_number}%22",
        "Bing exact": f"https://www.bing.com/search?q=%22{encoded_number}%22",
        "Google News": f"https://www.google.com/search?tbm=nws&q=%22{clean_number}%22",
    }


def summarize_precision(result: dict) -> str:
    """
    Labels the precision level of the geolocation result.
    """
    region = (result.get("region") or "").strip().lower()
    country = (result.get("country") or "").strip().lower()
    status = result.get("status")

    if status == "error":
        return "SIN_DATOS"
    if result.get("lat") is None or result.get("lon") is None:
        return "OFFLINE"
    if region and country and region == country:
        return "PAIS"
    if result.get("confidence", 0) >= 7:
        return "REGION"
    return "APROXIMADA"


def build_executive_summary(result: dict, pro_mode: bool) -> dict[str, object]:
    """
    Builds high-level summary fields for console and HTML report.
    """
    precision_level = summarize_precision(result)
    dork_summary = result.get("dork_summary", {}) or {}
    coverage = dork_summary.get("coverage_label", "No ejecutada")
    public_mentions = dork_summary.get("public_mentions", 0)

    highlights: list[str] = []
    recommendations: list[str] = []

    if precision_level == "PAIS":
        highlights.append("La geolocalizacion solo llego a nivel pais.")
        recommendations.append("No interpretar las coordenadas como ubicacion puntual del abonado.")
    elif precision_level == "REGION":
        highlights.append("La geolocalizacion llego a una referencia regional razonable.")
    elif precision_level == "OFFLINE":
        highlights.append("Solo hay metadata offline; no hubo geocodificacion efectiva.")

    if pro_mode:
        if dork_summary.get("coverage") == "good" and public_mentions:
            highlights.append(f"Se detectaron {public_mentions} menciones publicas en fuentes abiertas.")
        elif dork_summary.get("coverage") == "good":
            highlights.append("No se detectaron menciones publicas automaticas en la cobertura ejecutada.")
        elif dork_summary.get("coverage") in {"partial", "poor"}:
            highlights.append("La cobertura automatica de busquedas abiertas fue limitada.")
            recommendations.append("Revisar los enlaces manuales del reporte para completar la verificacion.")

    if result.get("carrier"):
        highlights.append(f"Operador detectado: {result['carrier']}.")

    if not recommendations:
        recommendations.append("Usar este resultado como referencia aproximada y no como prueba de localizacion exacta.")

    return {
        "precision_level": precision_level,
        "coverage_label": coverage,
        "highlights": highlights,
        "recommendations": recommendations,
    }
