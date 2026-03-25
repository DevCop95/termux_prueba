from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from pathlib import Path

try:
    from colorama import Fore, Style, init
except ModuleNotFoundError:
    class _ColorFallback:
        CYAN = ""
        GREEN = ""
        RED = ""
        WHITE = ""
        YELLOW = ""

    class _StyleFallback:
        BRIGHT = ""
        RESET_ALL = ""

    def init(*args, **kwargs):
        return None

    Fore = _ColorFallback()
    Style = _StyleFallback()

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    tqdm = None


# Este script usa unicamente metadatos publicos del numero (prefijo, carrier, region).
# NO realiza rastreo GPS en tiempo real. La ubicacion es aproximada a nivel ciudad o region.
# Su uso debe cumplir con la normativa local de privacidad y proteccion de datos aplicable.

init(autoreset=True)
LOGGER = logging.getLogger(__name__)


def print_banner() -> None:
    """
    Prints the CLI banner.
    """
    line = "=" * 44
    print(Fore.CYAN + line)
    print(Fore.CYAN + Style.BRIGHT + " PHONE GEOLOCATOR v1.0")
    print(Fore.CYAN + line + Style.RESET_ALL)


def parse_args() -> argparse.Namespace:
    """
    Parses CLI arguments.
    """
    parser = argparse.ArgumentParser(description="Geolocalizacion aproximada y etica de numeros telefonicos.")
    parser.add_argument("number_positional", nargs="?", help="Numero en formato E.164, por ejemplo +573001234567")
    parser.add_argument("--number", help="Numero en formato E.164, por ejemplo +573001234567")
    parser.add_argument("--batch", help="Archivo .txt con un numero por linea")

    parser.add_argument("--lang", default=None, choices=["es", "en"], help="Idioma para descripciones y geocodificacion")
    parser.add_argument("--pro", action="store_true", help="Activa dorking y reporte ampliado")
    parser.add_argument("--no-map", action="store_true", help="No generar mapa Folium")
    parser.add_argument("--no-dork", action="store_true", help="No ejecutar busquedas abiertas")
    parser.add_argument("--no-report", action="store_true", help="No generar reporte HTML")
    parser.add_argument("--output", help="Ruta HTML del mapa para un numero individual")
    parser.add_argument("--report-output", help="Ruta del reporte HTML ejecutivo")
    parser.add_argument("--csv", help="Ruta CSV de salida para modo batch")
    parser.add_argument("--max-results", type=int, default=None, help="Resultados maximos por consulta abierta")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    selected_number = args.number or args.number_positional
    if bool(selected_number) == bool(args.batch):
        parser.error("debes indicar un numero o un archivo batch, pero no ambos")

    args.number = selected_number
    return args


def display_value(value, fallback: str = "No disponible") -> str:
    """
    Normalizes values for terminal output.
    """
    if value is None or value == "":
        return fallback
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else fallback
    return str(value)


def print_row(label: str, value, color: str = "") -> None:
    """
    Prints a formatted terminal row.
    """
    text = display_value(value)
    wrapped = textwrap.wrap(text, width=80) or [text]
    print(color + f"  [+] {label:<12}: {wrapped[0]}" + Style.RESET_ALL)
    for line in wrapped[1:]:
        print(color + f"  {'':<18}{line}" + Style.RESET_ALL)


def build_map_output_path(number: str, settings, output_override: str | Path | None):
    """
    Builds the HTML map path for a processed number.
    """
    if output_override:
        return Path(output_override)

    from modules.advanced import sanitize_number_for_filename

    file_name = f"map_{sanitize_number_for_filename(number)}.html"
    return settings.output_dir / file_name


def build_report_output_path(number: str, settings, output_override: str | Path | None):
    """
    Builds the HTML report path for a processed number.
    """
    if output_override:
        return Path(output_override)

    from modules.advanced import sanitize_number_for_filename

    file_name = f"report_{sanitize_number_for_filename(number)}.html"
    return settings.output_dir / file_name


def build_error_result(number: str, message: str) -> dict:
    """
    Creates a normalized error result dictionary.
    """
    return {
        "input_number": number,
        "number": "",
        "international": "",
        "national": "",
        "country": "",
        "country_code": "",
        "region": "",
        "carrier": "",
        "line_type": "",
        "timezones": [],
        "description_es": "",
        "description_en": "",
        "npa_nxx": "",
        "lat": None,
        "lon": None,
        "address": "",
        "confidence": 0,
        "map_path": "",
        "report_path": "",
        "dork_results": {},
        "manual_links": {},
        "dork_meta": {},
        "dork_summary": {"coverage_label": "No ejecutada", "public_mentions": 0},
        "investigation_links": {},
        "precision_level": "SIN_DATOS",
        "executive_summary": {"highlights": [], "recommendations": []},
        "status": "error",
        "error": message,
        "note": "No se pudo procesar el numero.",
    }


def process_number(
    number: str,
    lang: str,
    settings,
    create_map: bool,
    create_report: bool,
    run_open_source_search: bool,
    pro_mode: bool,
    max_results: int | None = None,
    output_override: str | Path | None = None,
    report_output_override: str | Path | None = None,
) -> dict:
    """
    Processes a single number end-to-end.
    """
    from modules.advanced import build_executive_summary, build_investigation_links, ensure_output_dir
    from modules.dorking import run_dorks
    from modules.geo import geocode_phone_metadata
    from modules.phone import get_phone_info
    from modules.reporter import generate_html_report, render_map

    LOGGER.info("Processing number %s", number)
    phone_info = get_phone_info(number, lang=lang)
    if "error" in phone_info:
        LOGGER.warning("Validation failed for %s: %s", number, phone_info["error"])
        return build_error_result(number, phone_info["error"])

    geo_result = geocode_phone_metadata(phone_info, settings.opencage_api_key, lang=lang)
    result = {
        **phone_info,
        **geo_result,
        "map_path": "",
        "report_path": "",
        "dork_results": {},
        "manual_links": {},
        "dork_queries": {},
        "dork_meta": {},
        "dork_summary": {"coverage": "not_run", "coverage_label": "No ejecutada", "public_mentions": 0},
        "investigation_links": build_investigation_links(phone_info["number"]),
        "status": "ok",
        "error": "",
    }

    if run_open_source_search:
        dork_results, manual_links, dork_queries, dork_meta, dork_summary = run_dorks(
            phone_info["number"],
            country=phone_info.get("country"),
            carrier=phone_info.get("carrier"),
            max_results=max_results or settings.dork_max_results,
            pro_mode=pro_mode,
        )
        result["dork_results"] = dork_results
        result["manual_links"] = manual_links
        result["dork_queries"] = dork_queries
        result["dork_meta"] = dork_meta
        result["dork_summary"] = dork_summary

    if create_map and result.get("lat") is not None and result.get("lon") is not None:
        ensure_output_dir(settings.output_dir)
        try:
            map_path = render_map(
                result,
                build_map_output_path(result["number"], settings, output_override),
                map_zoom=settings.map_zoom,
                enable_circle=settings.enable_circle,
                circle_radius_km=settings.circle_radius_km,
            )
            result["map_path"] = map_path or ""
        except Exception as exc:
            LOGGER.exception("Map rendering failed")
            result["note"] = (
                f"{result.get('note', '')} El mapa no pudo renderizarse ({exc.__class__.__name__})."
            ).strip()
    elif not create_map:
        result["note"] = f"{result.get('note', '')} Mapa omitido por --no-map.".strip()

    summary = build_executive_summary(result, pro_mode=pro_mode)
    result["precision_level"] = summary["precision_level"]
    result["executive_summary"] = summary

    if create_report:
        ensure_output_dir(settings.output_dir)
        try:
            report_path = generate_html_report(
                result,
                build_report_output_path(result["number"], settings, report_output_override),
                pro_mode=pro_mode,
            )
            result["report_path"] = report_path or ""
        except Exception as exc:
            LOGGER.exception("Report rendering failed")
            result["note"] = (
                f"{result.get('note', '')} El reporte no pudo renderizarse ({exc.__class__.__name__})."
            ).strip()

    return result


def print_result(result: dict) -> None:
    """
    Prints a single result in terminal.
    """
    if result.get("status") == "error":
        print_row("Numero", result.get("input_number"), Fore.RED)
        print_row("Error", result.get("error"), Fore.RED)
        print(Fore.CYAN + "=" * 44)
        return

    print_row("Numero", result.get("international"), Fore.GREEN)
    print_row("Pais", result.get("country"), Fore.GREEN)
    print_row("Region", result.get("region"), Fore.GREEN)
    print_row("Operador", result.get("carrier"), Fore.GREEN)
    print_row("Tipo", result.get("line_type"), Fore.GREEN)
    print_row("Zona Horaria", result.get("timezones"), Fore.GREEN)
    print_row("Latitud", result.get("lat"), Fore.GREEN)
    print_row("Longitud", result.get("lon"), Fore.GREEN)
    print_row("Direccion", result.get("address"), Fore.GREEN)
    print_row("Confianza", result.get("confidence"), Fore.GREEN)
    print_row("Precision", result.get("precision_level"), Fore.GREEN)
    print_row("NPA/NXX", result.get("npa_nxx"), Fore.GREEN)
    print_row("Cobertura", result.get("dork_summary", {}).get("coverage_label"), Fore.GREEN)
    print_row("Hallazgos", result.get("dork_summary", {}).get("public_mentions"), Fore.GREEN)
    print_row("Mapa", result.get("map_path"), Fore.GREEN)
    print_row("Reporte", result.get("report_path"), Fore.GREEN)
    print_row("Nota", result.get("note"), Fore.YELLOW)
    print(Fore.CYAN + "=" * 44)


def process_batch(
    batch_file: str,
    lang: str,
    settings,
    create_map: bool,
    create_report: bool,
    run_open_source_search: bool,
    pro_mode: bool,
    max_results: int | None,
    csv_output: str | Path | None,
) -> tuple[list[dict], str]:
    """
    Processes a batch file and exports a CSV summary.
    """
    from modules.advanced import ensure_output_dir, flatten_result_for_csv
    from modules.dorking import export_results_csv, read_batch_numbers

    numbers = read_batch_numbers(batch_file)
    results: list[dict] = []

    iterator = tqdm(numbers, desc="Procesando", unit="numero") if tqdm else numbers
    for number in iterator:
        results.append(
            process_number(
                number,
                lang,
                settings,
                create_map=create_map,
                create_report=create_report,
                run_open_source_search=run_open_source_search,
                pro_mode=pro_mode,
                max_results=max_results,
            )
        )

    ensure_output_dir(settings.output_dir)
    csv_path = Path(csv_output) if csv_output else settings.output_dir / "batch_results.csv"
    csv_file = export_results_csv([flatten_result_for_csv(item) for item in results], csv_path)
    return results, csv_file


def main() -> None:
    """
    CLI entry point.
    """
    args = parse_args()

    try:
        from modules.advanced import ensure_output_dir, load_settings, setup_logging
    except ModuleNotFoundError as exc:
        print(f"[!] Falta una dependencia de Python: {exc.name}")
        sys.exit(1)

    settings = load_settings()
    ensure_output_dir(settings.output_dir)
    log_path = setup_logging(args.log_level, settings.output_dir)
    LOGGER.info("Logger initialized at %s", log_path)

    lang = args.lang or settings.default_lang
    print_banner()

    if args.number:
        try:
            result = process_number(
                args.number,
                lang=lang,
                settings=settings,
                create_map=not args.no_map,
                create_report=not args.no_report,
                run_open_source_search=not args.no_dork,
                pro_mode=args.pro,
                max_results=args.max_results,
                output_override=args.output,
                report_output_override=args.report_output,
            )
        except ModuleNotFoundError as exc:
            print(f"[!] Falta una dependencia de Python: {exc.name}")
            print("[i] Instala requirements.txt y vuelve a ejecutar.")
            sys.exit(1)
        print_result(result)
        sys.exit(1 if result.get("status") == "error" else 0)

    try:
        results, csv_file = process_batch(
            args.batch,
            lang=lang,
            settings=settings,
            create_map=not args.no_map,
            create_report=not args.no_report,
            run_open_source_search=not args.no_dork,
            pro_mode=args.pro,
            max_results=args.max_results,
            csv_output=args.csv,
        )
    except ModuleNotFoundError as exc:
        print(f"[!] Falta una dependencia de Python: {exc.name}")
        print("[i] Instala requirements.txt y vuelve a ejecutar.")
        sys.exit(1)

    success_count = sum(1 for item in results if item.get("status") == "ok")
    print_row("Archivo batch", args.batch, Fore.GREEN)
    print_row("Procesados", len(results), Fore.GREEN)
    print_row("Exitosos", success_count, Fore.GREEN)
    print_row("CSV", csv_file, Fore.GREEN)
    print(Fore.CYAN + "=" * 44)


if __name__ == "__main__":
    main()
