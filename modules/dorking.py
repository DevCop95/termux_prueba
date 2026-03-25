from __future__ import annotations

import csv
import inspect
import random
import time
from pathlib import Path
from urllib.parse import quote_plus

try:
    from googlesearch import search
except ModuleNotFoundError:
    search = None


REGIONS = ["us", "uk", "ca", "de", "in"]
DOMAINS = ["com", "co.uk", "ca", "de", "be", "co.in", "com.tw"]


def read_batch_numbers(file_path: str | Path) -> list[str]:
    """
    Reads one phone number per line from a text file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de batch: {path}")

    numbers: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        value = raw_line.strip()
        if value:
            numbers.append(value)

    return numbers


def export_results_csv(rows: list[dict[str, str]], output_path: str | Path) -> str:
    """
    Exports processed results to CSV.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        rows = [{"status": "empty_batch"}]

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return str(path.resolve())


def get_number_variations(full_number: str) -> list[str]:
    """
    Creates search-friendly variations of the same number.
    """
    variations = [full_number]
    num_no_plus = full_number.replace("+", "")
    variations.append(num_no_plus)

    if len(num_no_plus) > 10:
        local_guess = num_no_plus[2:] if num_no_plus.startswith("57") else num_no_plus[3:]
        variations.append(local_guess)

        if len(local_guess) == 10:
            variations.append(f"{local_guess[:3]} {local_guess[3:6]} {local_guess[6:]}")
            variations.append(f"{local_guess[:3]}-{local_guess[3:6]}-{local_guess[6:]}")

    deduped: list[str] = []
    for value in variations:
        if value and value not in deduped:
            deduped.append(value)

    return deduped


def build_dorks(number_list: list[str], country: str | None = None, carrier: str | None = None, pro_mode: bool = False) -> dict[str, str]:
    """
    Builds a dork set for public-surface investigation.
    """
    exact_parts = [f'"{value}"' for value in number_list[:4]]
    exact_query = " OR ".join(exact_parts)
    scam_terms = "(scam OR estafa OR fraude OR spam OR robo)"
    carrier_hint = f' "{carrier}"' if carrier else ""
    country_hint = f' "{country}"' if country else ""

    dorks = {
        "general": exact_query,
        "social": f"(site:facebook.com OR site:instagram.com OR site:linkedin.com OR site:x.com OR site:twitter.com) ({exact_query}){country_hint}",
        "directories": f"(site:truecaller.com OR site:sync.me OR site:spamcalls.net OR site:whocalled.com OR site:tellows.com) ({exact_query})",
        "scam_reports": f"({exact_query}) {scam_terms}{country_hint}",
        "pdf": f"filetype:pdf ({exact_query}){carrier_hint}",
    }

    if pro_mode:
        dorks.update(
            {
                "messaging_groups": f'(site:chat.whatsapp.com OR site:t.me) ({exact_query})',
                "forums": f"(site:reddit.com OR site:quora.com OR site:forocoches.com) ({exact_query})",
                "marketplaces": f"(site:mercadolibre.com OR site:facebook.com/marketplace OR site:olx.com) ({exact_query}){country_hint}",
                "documents": f'(filetype:xls OR filetype:xlsx OR filetype:csv OR filetype:doc OR filetype:docx) ({exact_query})',
            }
        )

    return dorks


def _manual_link(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _coverage_label(coverage: str) -> str:
    labels = {
        "good": "Buena",
        "partial": "Parcial",
        "poor": "Pobre",
        "not_run": "No ejecutada",
    }
    return labels.get(coverage, "Desconocida")


def _search_with_compatible_signature(query: str, max_results: int, delay_seconds: float):
    if search is None:
        raise ModuleNotFoundError("googlesearch")

    params = inspect.signature(search).parameters

    if "num_results" in params:
        return list(
            search(
                query,
                num_results=max_results,
                sleep_interval=delay_seconds,
                timeout=8,
                safe="active",
                region=random.choice(REGIONS),
                unique=True,
            )
        )

    if "num" in params:
        return list(
            search(
                query,
                tld=random.choice(DOMAINS),
                num=max_results,
                stop=max_results,
                pause=delay_seconds,
            )
        )

    return list(search(query))


def run_dorks(
    full_number: str,
    country: str | None = None,
    carrier: str | None = None,
    max_results: int = 3,
    pro_mode: bool = False,
) -> tuple[dict, dict, dict, dict, dict]:
    """
    Executes automated open-source searches and prepares manual fallbacks.
    """
    variations = get_number_variations(full_number)
    dorks = build_dorks(variations, country=country, carrier=carrier, pro_mode=pro_mode)
    results: dict[str, list[str]] = {}
    manual_links: dict[str, str] = {}
    metadata: dict[str, dict[str, str | int]] = {}

    for name, query in dorks.items():
        results[name] = []
        manual_links[name] = _manual_link(query)
        metadata[name] = {
            "query": query,
            "status": "no_results",
            "count": 0,
            "error": "",
        }

        if search is None:
            metadata[name]["status"] = "error"
            metadata[name]["error"] = "Dependencia googlesearch no instalada"
            continue

        try:
            delay_seconds = random.uniform(1.5, 3.0)
            found_urls = _search_with_compatible_signature(query, max_results, delay_seconds)
            if found_urls:
                results[name] = found_urls
                metadata[name]["status"] = "hits"
                metadata[name]["count"] = len(found_urls)
        except Exception as exc:
            metadata[name]["status"] = "error"
            metadata[name]["error"] = f"{exc.__class__.__name__}: {exc}"

        time.sleep(0.5)

    queries_total = len(dorks)
    queries_with_hits = sum(1 for item in metadata.values() if item["status"] == "hits")
    queries_failed = sum(1 for item in metadata.values() if item["status"] == "error")
    queries_without_hits = queries_total - queries_with_hits - queries_failed
    public_mentions = sum(len(urls) for urls in results.values())

    if queries_total == 0:
        coverage = "not_run"
    elif queries_failed == 0:
        coverage = "good"
    elif queries_failed < queries_total:
        coverage = "partial"
    else:
        coverage = "poor"

    summary = {
        "queries_total": queries_total,
        "queries_with_hits": queries_with_hits,
        "queries_without_hits": queries_without_hits,
        "queries_failed": queries_failed,
        "public_mentions": public_mentions,
        "coverage": coverage,
        "coverage_label": _coverage_label(coverage),
    }

    return results, manual_links, dorks, metadata, summary
