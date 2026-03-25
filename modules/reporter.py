# modules/reporter.py
import os
from datetime import datetime

def generate_html_report(data, filename="report.html"):
    """
    Genera un informe HTML profesional con los datos recopilados.
    """
    
    # Formatear lista de razones para HTML
    reasons_html = "<ul>" + "".join(f"<li>{r}</li>" for r in data['risk']['reasons']) + "</ul>"
    
    # Formatear enlaces de búsqueda
    links_html = ""
    for name, url in data['deep_links'].items():
        links_html += f'<a href="{url}" target="_blank" class="btn">{name}</a> '

    # Formatear resultados de Dorking
    dorks_html = ""
    if data.get('dork_results'):
        for source, urls in data['dork_results'].items():
            if urls:
                dorks_html += f"<h4>{source.upper()}</h4><ul>"
                for url in urls:
                    dorks_html += f'<li><a href="{url}" target="_blank">{url}</a></li>'
                dorks_html += "</ul>"
    else:
        dorks_html = "<p>No se encontraron resultados públicos o Google bloqueó la búsqueda.</p>"

    # --- LÓGICA PARA MANEJAR COORDENADAS 0,0 ---
    lat = data.get('lat', 0)
    lon = data.get('lon', 0)
    
    if lat != 0 and lon != 0:
        # Si hay coordenadas reales, mostramos el mapa
        location_section = f"""
        <h2>🗺️ Ubicación Aproximada</h2>
        <div class="card">
            <p><strong>Coordenadas:</strong> {lat}, {lon}</p>
            <iframe class="map" src="https://maps.google.com/maps?q={lat},{lon}&z=5&output=embed"></iframe>
        </div>
        """
    else:
        # Si son 0,0 mostramos error de conexión
        location_section = f"""
        <h2>🗺️ Ubicación Aproximada</h2>
        <div class="card" style="background-color: #4a3333; border-left: 5px solid #ff4d4d;">
            <p style="color: #ffaaaa;"><strong>⚠️ Error de Geolocalización</strong></p>
            <p>No se pudieron obtener coordenadas. Causas comunes:</p>
            <ul>
                <li>Sin conexión a Internet o DNS fallido.</li>
                <li>Clave API de OpenCage inválida o no configurada en config.json.</li>
                <li>Firewall bloqueando a Python.</li>
            </ul>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Informe OSINT - {data['number']}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; color: #eee; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: #2d2d2d; padding: 20px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.5); }}
            h1 {{ color: #00ff9d; border-bottom: 2px solid #00ff9d; padding-bottom: 10px; }}
            h2 {{ color: #fff; margin-top: 30px; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .card {{ background: #3a3a3a; padding: 15px; border-radius: 5px; }}
            .risk-high {{ color: #ff4d4d; font-weight: bold; font-size: 1.2em; }}
            .risk-low {{ color: #00ff9d; font-weight: bold; font-size: 1.2em; }}
            .risk-med {{ color: #ffb84d; font-weight: bold; font-size: 1.2em; }}
            .btn {{ display: inline-block; padding: 10px; background: #444; color: #00ff9d; text-decoration: none; border-radius: 5px; margin: 5px; font-size: 0.9em; border: 1px solid #00ff9d;}}
            .btn:hover {{ background: #555; }}
            a {{ color: #00b3ff; }}
            .map {{ width: 100%; height: 300px; border: 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕵️ Informe OSINT: {data['number']}</h1>
            <p>Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>

            <div class="grid">
                <div class="card">
                    <h3>Información Técnica</h3>
                    <p><strong>Formato:</strong> {data['international']}</p>
                    <p><strong>País:</strong> {data['country']}</p>
                    <p><strong>Operadora:</strong> {data['carrier']}</p>
                    <p><strong>Tipo:</strong> {data['line_type']}</p>
                </div>
                
                <div class="card">
                    <h3>Análisis de Riesgo</h3>
                    <p class="risk-{data['risk']['level'].lower()}">{data['risk']['color']} {data['risk']['level']} (Score: {data['risk']['score']})</p>
                    {reasons_html}
                </div>
            </div>

            {location_section}

            <h2>🔗 Enlaces de Investigación Rápida</h2>
            <div class="card">
                {links_html}
            </div>

            <h2>🔎 Resultados de Dorking</h2>
            <div class="card">
                {dorks_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        return os.path.abspath(filename)
    except Exception as e:
        return str(e)