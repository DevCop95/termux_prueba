# phone_osint.py
import json
import sys
import argparse
from colorama import Fore, Style, init

init(autoreset=True)

from modules.phone import get_phone_info
from modules.geo import numverify_lookup, geocode_location, load_opencage_config
from modules.dorking import run_dorks

def print_banner():
    print(Fore.RED + Style.BRIGHT + "\n[ Phone OSINT Tool ]\n" + Style.RESET_ALL)

def load_config(path: str = "config.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(Fore.RED + f"[!] Error cargando configuración: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Herramienta OSINT para números de teléfono.")
    parser.add_argument("number", help="Número en formato internacional (ej: +521234567890)")
    parser.add_argument("--no-dork", action="store_true", help="No ejecutar dorking")
    args = parser.parse_args()

    print_banner()
    config = load_config()

    # 1. Info con phonenumbers
    print(Fore.YELLOW + "[+] Analizando número con phonenumbers...")
    info = get_phone_info(args.number)

    if "error" in info:
        print(Fore.RED + f"[!] {info['error']}")
        sys.exit(1)

    print(Fore.GREEN + "\n--- Información del número ---")
    print(f"  Número (E.164)    : {info['number']}")
    print(f"  Formato Int.      : {info['international']}")
    print(f"  País              : {info['country']} ({info['country_code']})")
    print(f"  Descripción       : {info['description'] or 'No disponible'}")
    print(f"  Operadora         : {info['carrier'] or 'No disponible'}")
    print(f"  Tipo de línea     : {info['line_type']}")
    print(f"  Zonas horarias    : {', '.join(info['timezones'])}")

    # 2. Info con Numverify (API externa)
    print(Fore.YELLOW + "\n[+] Consultando Numverify...")
    nv_data = numverify_lookup(info["number"], config)
    if "error" not in nv_data:
        print(Fore.GREEN + "--- Numverify ---")
        print(f"  Válido            : {nv_data.get('valid')}")
        print(f"  Número            : {nv_data.get('number')}")
        print(f"  Country code      : {nv_data.get('country_code')}")
        print(f"  Country name      : {nv_data.get('country_name')}")
        print(f"  Location          : {nv_data.get('location')}")
        print(f"  Carrier           : {nv_data.get('carrier')}")
        print(f"  Line type         : {nv_data.get('line_type')}")
    else:
        print(Fore.RED + f"[!] Error en Numverify: {nv_data['error']}")

    # 3. Geolocalización con OpenCage
    print(Fore.YELLOW + "\n[+] Geolocalizando con OpenCage...")
    opencage_key = load_opencage_config(config)
    location_text = info["description"] or info["country"]
    lat, lon = geocode_location(location_text, opencage_key)

    if lat and lon:
        print(Fore.GREEN + "--- Coordenadas aproximadas ---")
        print(f"  Latitud           : {lat}")
        print(f"  Longitud          : {lon}")
        print(f"  Maps              : https://www.google.com/maps?q={lat},{lon}")
    else:
        print(Fore.RED + "[!] No se pudieron obtener coordenadas.")

    # 4. Dorking
    if not args.no_dork:
        print(Fore.YELLOW + "\n[+] Ejecutando dorking en Google (puede tardar)...")
        dork_results = run_dorks(info["number"], max_results=5)

        for name, urls in dork_results.items():
            print(Fore.GREEN + f"\n--- Dork: {name} ---")
            if not urls:
                print("  Sin resultados.")
            for url in urls:
                print(f"  - {url}")

if __name__ == "__main__":
    main()