from __future__ import annotations

import os
from datetime import datetime
from html import escape
from pathlib import Path

import folium


STAMEN_TERRAIN_URL = "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png"
STAMEN_TERRAIN_ATTR = (
    '&copy; <a href="https://stadiamaps.com/" target="_blank">Stadia Maps</a> '
    '&copy; <a href="https://stamen.com/" target="_blank">Stamen Design</a> '
    '&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> '
    '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
)


def _popup_html(result: dict) -> str:
    """
    Builds popup content for the folium marker.
    """
    return (
        f"<strong>Numero:</strong> {result.get('international') or result.get('number')}<br>"
        f"<strong>Pais:</strong> {result.get('country', 'No disponible')}<br>"
        f"<strong>Region:</strong> {result.get('region', 'No disponible')}<br>"
        f"<strong>Operador:</strong> {result.get('carrier', 'No disponible')}<br>"
        f"<strong>Tipo:</strong> {result.get('line_type', 'No disponible')}<br>"
        f"<strong>Coordenadas:</strong> {result.get('lat')}, {result.get('lon')}"
    )


def _as_text(value, fallback: str = "No disponible") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value) if value else fallback
    return str(value)


def _render_list(items: list[str], empty_message: str) -> str:
    if not items:
        return f"<p class='muted'>{escape(empty_message)}</p>"
    return "<ul class='bullet-list'>" + "".join(f"<li>{escape(_as_text(item))}</li>" for item in items) + "</ul>"


def _render_link_buttons(links: dict[str, str], empty_message: str) -> str:
    if not links:
        return f"<p class='muted'>{escape(empty_message)}</p>"

    buttons = []
    for label, url in links.items():
        buttons.append(
            f"<a class='link-chip' href='{escape(url)}' target='_blank' rel='noreferrer'>{escape(label)}</a>"
        )
    return "".join(buttons)


def _render_dork_summary(summary: dict) -> str:
    if not summary:
        return "<p class='muted'>Sin resumen de cobertura.</p>"

    return f"""
    <div class="kv-grid">
        <div>
            <span class="kv-label">Cobertura</span>
            <span class="kv-value">{escape(_as_text(summary.get("coverage_label"), "No ejecutada"))}</span>
        </div>
        <div>
            <span class="kv-label">Consultas</span>
            <span class="kv-value">{escape(_as_text(summary.get("queries_total"), "0"))}</span>
        </div>
        <div>
            <span class="kv-label">Con hallazgos</span>
            <span class="kv-value">{escape(_as_text(summary.get("queries_with_hits"), "0"))}</span>
        </div>
        <div>
            <span class="kv-label">Sin hallazgos</span>
            <span class="kv-value">{escape(_as_text(summary.get("queries_without_hits"), "0"))}</span>
        </div>
        <div>
            <span class="kv-label">Fallidas</span>
            <span class="kv-value">{escape(_as_text(summary.get("queries_failed"), "0"))}</span>
        </div>
        <div>
            <span class="kv-label">Menciones</span>
            <span class="kv-value">{escape(_as_text(summary.get("public_mentions"), "0"))}</span>
        </div>
    </div>
    """


def _render_dork_results(results: dict[str, list[str]], manual_links: dict[str, str], dork_meta: dict | None = None) -> str:
    dork_meta = dork_meta or {}
    sections = []

    for source, urls in results.items():
        meta = dork_meta.get(source, {})
        heading = escape(source.replace("_", " ").title())
        status = meta.get("status", "no_results")
        error = meta.get("error", "")

        if urls:
            links = "".join(
                f"<li><a href='{escape(url)}' target='_blank' rel='noreferrer'>{escape(url)}</a></li>"
                for url in urls
            )
            body = f"<p class='muted'>Estado: coincidencias automaticas.</p><ul class='result-list'>{links}</ul>"
        else:
            fallback = manual_links.get(source)
            prefix = "Sin coincidencias automaticas. "
            if status == "error":
                prefix = "Busqueda automatica no concluyente. "

            body = f"<p class='muted'>{prefix}"
            if fallback:
                body += f"<a href='{escape(fallback)}' target='_blank' rel='noreferrer'>Abrir busqueda manual</a>."
            body += "</p>"
            if error:
                body += f"<p class='muted'>Detalle: {escape(_as_text(error))}</p>"

        sections.append(f"<section class='result-block'><h3>{heading}</h3>{body}</section>")

    if not sections:
        return "<p class='muted'>No se ejecutaron busquedas abiertas.</p>"
    return "".join(sections)


def render_map(
    result: dict,
    output_path: str | Path,
    map_zoom: int,
    enable_circle: bool,
    circle_radius_km: float,
) -> str | None:
    """
    Renders an interactive folium map for a single phone result.
    """
    if result.get("lat") is None or result.get("lon") is None:
        return None

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    phone_map = folium.Map(
        location=[result["lat"], result["lon"]],
        zoom_start=map_zoom,
        control_scale=True,
        tiles=None,
    )

    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(phone_map)
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(phone_map)
    folium.TileLayer(
        tiles=STAMEN_TERRAIN_URL,
        attr=STAMEN_TERRAIN_ATTR,
        name="Stamen Terrain",
        overlay=False,
        control=True,
    ).add_to(phone_map)

    folium.Marker(
        [result["lat"], result["lon"]],
        tooltip=result.get("number"),
        popup=folium.Popup(_popup_html(result), max_width=350),
    ).add_to(phone_map)

    if enable_circle:
        folium.Circle(
            location=[result["lat"], result["lon"]],
            radius=int(circle_radius_km * 1000),
            color="#0a9396",
            fill=True,
            fill_opacity=0.12,
            tooltip=f"Radio aproximado de {circle_radius_km} km",
        ).add_to(phone_map)

    folium.LayerControl().add_to(phone_map)
    phone_map.save(output_file)
    return str(output_file.resolve())


def generate_html_report(result: dict, output_path: str | Path, pro_mode: bool = False) -> str:
    """
    Generates a rich HTML report with metadata, map and optional dorking.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    map_path = result.get("map_path")
    report_dir = output_file.parent
    relative_map = ""
    if map_path:
        try:
            relative_map = os.path.relpath(Path(map_path).resolve(), report_dir.resolve())
        except Exception:
            try:
                relative_map = Path(map_path).name
            except Exception:
                relative_map = ""

    summary = result.get("executive_summary", {}) or {}
    dork_summary = result.get("dork_summary", {}) or {}
    dork_results = result.get("dork_results", {}) or {}
    dork_meta = result.get("dork_meta", {}) or {}
    manual_links = result.get("manual_links", {}) or {}
    quick_links = result.get("investigation_links", {}) or {}

    precision_class = {
        "PAIS": "risk-medium",
        "REGION": "risk-low",
        "APROXIMADA": "risk-medium",
        "OFFLINE": "risk-unknown",
        "SIN_DATOS": "risk-unknown",
    }.get(result.get("precision_level"), "risk-unknown")

    map_section = (
        f"<iframe class='map' src='{escape(relative_map)}' loading='lazy'></iframe>"
        if relative_map else "<p class='muted'>No se genero mapa para este resultado.</p>"
    )

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte Pro - {escape(_as_text(result.get("number")))}</title>
        <style>
            :root {{
                --bg: #0b1420;
                --panel: #152334;
                --panel-soft: #1d3047;
                --border: rgba(255,255,255,0.08);
                --text: #eef5ff;
                --muted: #9db2ca;
                --accent: #5dd3b2;
                --warning: #ffbe55;
                --danger: #ff7878;
                --safe: #83e7b0;
                --unknown: #c7a8ff;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                font-family: "Trebuchet MS", "Segoe UI", sans-serif;
                background:
                    radial-gradient(circle at top left, rgba(93,211,178,0.18), transparent 30%),
                    linear-gradient(180deg, #09111a 0%, var(--bg) 100%);
                color: var(--text);
            }}
            .shell {{
                max-width: 1180px;
                margin: 0 auto;
                padding: 28px 18px 40px;
            }}
            .hero, .panel {{
                background: linear-gradient(180deg, rgba(21,35,52,0.98), rgba(15,25,38,0.98));
                border: 1px solid var(--border);
                border-radius: 22px;
                padding: 22px;
                box-shadow: 0 18px 40px rgba(0,0,0,0.28);
            }}
            .hero {{ margin-bottom: 22px; }}
            .hero-top, .panel-head {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
                align-items: center;
                flex-wrap: wrap;
            }}
            .badge, .chip {{
                display: inline-flex;
                align-items: center;
                padding: 8px 12px;
                border-radius: 999px;
                border: 1px solid var(--border);
                background: rgba(255,255,255,0.04);
                color: var(--muted);
                font-size: 0.92rem;
            }}
            .risk-low {{ color: var(--safe); background: rgba(131,231,176,0.12); }}
            .risk-medium {{ color: var(--warning); background: rgba(255,190,85,0.12); }}
            .risk-unknown {{ color: var(--unknown); background: rgba(199,168,255,0.12); }}
            .summary-grid, .kv-grid, .content-grid {{
                display: grid;
                gap: 16px;
            }}
            .summary-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 18px; }}
            .content-grid {{ grid-template-columns: 1.1fr 0.9fr; margin-top: 22px; }}
            .stack {{ display: grid; gap: 22px; }}
            .summary-card {{
                background: var(--panel-soft);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 16px;
            }}
            .summary-card .label, .kv-label {{
                display: block;
                color: var(--muted);
                font-size: 0.84rem;
                margin-bottom: 5px;
            }}
            .summary-card strong, .kv-value {{
                font-size: 1rem;
                line-height: 1.5;
            }}
            .kv-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
            .bullet-list, .result-list {{
                margin: 0;
                padding-left: 20px;
                line-height: 1.65;
            }}
            .muted {{ color: var(--muted); line-height: 1.6; }}
            .link-chip {{
                display: inline-block;
                margin: 0 10px 10px 0;
                padding: 10px 14px;
                border-radius: 999px;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(93,211,178,0.24);
                color: var(--text);
                text-decoration: none;
            }}
            .map {{
                width: 100%;
                height: 360px;
                border: 0;
                border-radius: 16px;
                margin-top: 14px;
                background: #0d1520;
            }}
            .result-block + .result-block {{
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid var(--border);
            }}
            a {{ color: #8fd7ff; }}
            @media (max-width: 920px) {{
                .content-grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <main class="shell">
            <section class="hero">
                <div class="hero-top">
                    <div>
                        <span class="badge">Modo {"PRO" if pro_mode else "ESTANDAR"}</span>
                        <span class="badge">Generado: {escape(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))}</span>
                    </div>
                    <span class="chip {precision_class}">Precision {escape(_as_text(result.get("precision_level")))}</span>
                </div>
                <h1>Reporte telefonico {escape(_as_text(result.get("number")))}</h1>
                <p class="muted">Expediente tecnico con geolocalizacion aproximada, enlaces de verificacion y hallazgos de fuentes abiertas.</p>

                <div class="summary-grid">
                    <article class="summary-card">
                        <span class="label">Pais</span>
                        <strong>{escape(_as_text(result.get("country")))}</strong>
                    </article>
                    <article class="summary-card">
                        <span class="label">Region</span>
                        <strong>{escape(_as_text(result.get("region")))}</strong>
                    </article>
                    <article class="summary-card">
                        <span class="label">Operador</span>
                        <strong>{escape(_as_text(result.get("carrier")))}</strong>
                    </article>
                    <article class="summary-card">
                        <span class="label">Cobertura abierta</span>
                        <strong>{escape(_as_text(dork_summary.get("coverage_label"), "No ejecutada"))}</strong>
                    </article>
                </div>
            </section>

            <section class="content-grid">
                <div class="stack">
                    <section class="panel">
                        <div class="panel-head">
                            <h2>Resumen ejecutivo</h2>
                            <span class="badge">{escape(_as_text(summary.get("coverage_label"), dork_summary.get("coverage_label", "No ejecutada")))}</span>
                        </div>
                        {_render_list(summary.get("highlights", []), "Sin hallazgos ejecutivos adicionales.")}
                        <h3>Siguientes pasos</h3>
                        {_render_list(summary.get("recommendations", []), "Sin recomendaciones adicionales.")}
                    </section>

                    <section class="panel">
                        <div class="panel-head">
                            <h2>Mapa aproximado</h2>
                            <span class="badge">{escape(_as_text(result.get("provider"), "offline"))}</span>
                        </div>
                        <p class="muted">{escape(_as_text(result.get("note"), "Sin observaciones."))}</p>
                        {map_section}
                    </section>

                    <section class="panel">
                        <div class="panel-head">
                            <h2>Resultados de dorking</h2>
                            <span class="badge">{escape(_as_text(dork_summary.get("public_mentions"), "0"))} hits</span>
                        </div>
                        {_render_dork_summary(dork_summary)}
                        <div style="margin-top: 18px;">
                            {_render_dork_results(dork_results, manual_links, dork_meta)}
                        </div>
                    </section>
                </div>

                <div class="stack">
                    <section class="panel">
                        <div class="panel-head">
                            <h2>Perfil tecnico</h2>
                            <span class="badge">{escape(_as_text(result.get("line_type")))}</span>
                        </div>
                        <div class="kv-grid">
                            <div><span class="kv-label">Numero E.164</span><span class="kv-value">{escape(_as_text(result.get("number")))}</span></div>
                            <div><span class="kv-label">Internacional</span><span class="kv-value">{escape(_as_text(result.get("international")))}</span></div>
                            <div><span class="kv-label">Nacional</span><span class="kv-value">{escape(_as_text(result.get("national")))}</span></div>
                            <div><span class="kv-label">Pais</span><span class="kv-value">{escape(_as_text(result.get("country")))}</span></div>
                            <div><span class="kv-label">Codigo de region</span><span class="kv-value">{escape(_as_text(result.get("country_code")))}</span></div>
                            <div><span class="kv-label">Prefijo internacional</span><span class="kv-value">+{escape(_as_text(result.get("country_calling_code")))}</span></div>
                            <div><span class="kv-label">Zona horaria</span><span class="kv-value">{escape(_as_text(result.get("timezones")))}</span></div>
                            <div><span class="kv-label">Latitud</span><span class="kv-value">{escape(_as_text(result.get("lat")))}</span></div>
                            <div><span class="kv-label">Longitud</span><span class="kv-value">{escape(_as_text(result.get("lon")))}</span></div>
                            <div><span class="kv-label">Direccion</span><span class="kv-value">{escape(_as_text(result.get("address")))}</span></div>
                            <div><span class="kv-label">Confianza</span><span class="kv-value">{escape(_as_text(result.get("confidence")))}</span></div>
                            <div><span class="kv-label">NPA/NXX</span><span class="kv-value">{escape(_as_text(result.get("npa_nxx")))}</span></div>
                        </div>
                    </section>

                    <section class="panel">
                        <div class="panel-head">
                            <h2>Enlaces de investigacion</h2>
                            <span class="badge">Verificacion manual</span>
                        </div>
                        {_render_link_buttons(quick_links, "No se generaron accesos manuales.")}
                        <h3>Busquedas manuales</h3>
                        {_render_link_buttons(manual_links, "No se generaron consultas manuales.")}
                    </section>
                </div>
            </section>
        </main>
    </body>
    </html>
    """

    output_file.write_text(html_content, encoding="utf-8")
    return str(output_file.resolve())
