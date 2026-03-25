# phone_osint.py
import sys
import argparse
import webbrowser
import json  # Necesario para leer config.json
from colorama import Fore, Style, init

init(autoreset=True)

# Importamos los módulos
from modules.phone import get_phone_info
from modules.geo import numverify_lookup, geocode_location, load_opencage_config
from modules.dorking import run_dorks
from modules.advanced import analyze_risk, generate_deep_links
from modules.reporter import generate_html_report

def print_banner():
    # Banner limpio y agresivo centrado en DEVYHB
    print(Fore.RED + """
    
    ██████╗ ███████╗██╗   ██╗
    ██╔══██╗██╔════╝██║   ██║
    ██║  ██║█████╗  ██║   ██║
    ██║  ██║██╔══╝  ╚██╗ ██╔╝
    ██████╔╝███████╗ ╚████╔╝ 
    ╚═════╝ ╚══════╝  ╚═══╝  
    """ + Style.RESET_ALL)

def load_config(path: str = "config.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(Fore.RED + f"[!] Error crítico cargando configuración: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="DEVYHB OSINT Tool.")
    parser.add_argument("number", help="Número en formato internacional (ej: +521234567890)")
    parser.add_argument("--no-report", action="store_true", help="No generar archivo HTML")
    args = parser.parse_args()

    print_banner()
    config = load_config()
    
    report_data = {}

    # 1. Análisis Estructural
    print(Fore.YELLOW + "[+] Analizando estructura del número...")
    info = get_phone_info(args.number)

    if "error" in info:
        print(Fore.RED + f"[!] {info['error']}")
        sys.exit(1)

    print(Fore.GREEN + "\n--- Datos Técnicos ---")
    print(f"  Número          : {info['international']}")
    print(f"  País            : {info['country']}")
    print(f"  Operadora       : {info['carrier']}")
    print(f"  Tipo de línea   : {info['line_type']}")
    report_data.update(info)

    # 2. Consulta Global
    print(Fore.YELLOW + "\n[+] Consultando base de datos global...")
    nv_data = numverify_lookup(info["number"], config)
    
    if "error" not in nv_data:
        print(Fore.GREEN + "--- Validación Externa ---")
        print(f"  Válido          : {nv_data.get('valid')}")
        print(f"  Carrier Global  : {nv_data.get('carrier')}")
        print(f"  Tipo Global     : {nv_data.get('line_type')}")
        report_data['numverify'] = nv_data
    else:
        print(Fore.RED + f"[!] Advertencia: {nv_data['error']}")
        nv_data = {"valid": True, "line_type": info['line_type'], "carrier": info['carrier']}
        report_data['numverify'] = nv_data

    # 3. Análisis de Riesgo
    print(Fore.YELLOW + "\n[+] Evaluando nivel de riesgo...")
    risk_analysis = analyze_risk(nv_data, info)
    print(f"  Nivel de Riesgo : {risk_analysis['color']} {risk_analysis['level']} (Score: {risk_analysis['score']})")
    print(f"  Diagnóstico     : {risk_analysis['reasons'][0]}")
    report_data['risk'] = risk_analysis

    # 4. Geolocalización
    print(Fore.YELLOW + "\n[+] Geolocalizando objetivo...")
    opencage_key = load_opencage_config(config)
    location_text = info["description"] or info["country"]
    lat, lon = geocode_location(location_text, opencage_key)

    if lat and lon:
        print(f"  Coordenadas     : {lat}, {lon}")
        print(f"  Maps            : https://www.google.com/maps?q={lat},{lon}")
        report_data['lat'] = lat
        report_data['lon'] = lon
    else:
        report_data['lat'] = 0
        report_data['lon'] = 0
        print(Fore.RED + "  [!] Ubicación no determinada.")

    # 5. Enlaces Profundos
    print(Fore.CYAN + "\n[+] Generando enlaces de infiltración...")
    deep_links = generate_deep_links(info["number"])
    print("  Enlaces generados para investigación profunda.")
    report_data['deep_links'] = deep_links

    # 6. Dorking
    print(Fore.YELLOW + "\n[+] Ejecutando Dorking en la web profunda...")
    dork_results, manual_links = run_dorks(info["number"], max_results=2)
    report_data['dork_results'] = dork_results
    
    found_urls = [url for sublist in dork_results.values() for url in sublist]
    if found_urls:
        print(Fore.GREEN + f"  ¡Alerta! Se encontraron {len(found_urls)} menciones públicas.")
    else:
        print(Fore.RED + "  Objetivo limpio en superficies públicas.")

    # 7. Generación de Reporte
    if not args.no_report:
        print(Fore.YELLOW + "\n[+] Compilando expediente final...")
        filename = f"report_{info['number'].replace('+', '')}.html"
        file_path = generate_html_report(report_data, filename)
        
        print(Fore.GREEN + f"\n✅ EXPEDIENTE GENERADO EXITOSAMENTE")
        print(Fore.CYAN + f"📄 Archivo: {file_path}")
        
        try:
            webbrowser.open('file://' + file_path)
        except:
            pass

if __name__ == "__main__":
    main()