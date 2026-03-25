# modules/geo.py
import requests
from opencage.geocoder import OpenCageGeocode
# Importamos la librería gratuita (Plan B)
from geopy.geocoders import Nominatim

def load_opencage_config(config: dict):
    return config["opencage"]["api_key"]

def geocode_location(location_text: str, opencage_key: str):
    """
    Estrategia de dos niveles:
    1. Intenta OpenCage (Alta precisión, requiere API Key e Internet bueno).
    2. Si falla, usa Nominatim (Gratis, sin clave, funciona con DNS lento).
    """
    
    # --- PLAN A: OpenCage (El que tienes configurado en config.json) ---
    if opencage_key and opencage_key != "TU_CLAVE_AQUI":
        try:
            # Timeout corto para no esperar mucho si falla
            geocoder = OpenCageGeocode(opencage_key, timeout=5)
            results = geocoder.geocode(location_text)
            if results:
                lat = results[0]["geometry"]["lat"]
                lon = results[0]["geometry"]["lng"]
                print(Fore.CYAN + "   [i] Geolocalización vía OpenCage (Precisa).")
                return lat, lon
        except Exception:
            # Si falla (DNS, clave mala, timeout), pasamos al Plan B silenciosamente
            pass

    # --- PLAN B: Nominatim (El original, gratuito y a prueba de fallos) ---
    try:
        # User agent obligatorio para Nominatim
        geolocator = Nominatim(user_agent="OsintPhoneTool/1.0", timeout=10)
        location = geolocator.geocode(location_text)
        if location:
            print(Fore.YELLOW + "   [!] OpenCage falló. Usando Nominatim (Plan B gratuito).")
            return location.latitude, location.longitude
    except Exception as e:
        print(Fore.RED + f"   [X] Fallo total de geolocalización: {e}")
        pass

    # Si todo falla, devolvemos None para que el reporte lo entienda
    return None, None

def numverify_lookup(number_e164: str, config: dict):
    api_key = config["numverify"].get("access_key") or config["numverify"].get("api_key")
    
    if not api_key:
        return {"error": "Falta la clave en config.json"}

    url = "https://apilayer.net/api/validate"
    number_clean = number_e164.replace("+", "")
    
    params = {
        "access_key": api_key,
        "number": number_clean,
        "format": 1
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code != 200:
            return {"error": f"Error HTTP {r.status_code}"}
            
        data = r.json()
        
        if "error" in data:
             return {"error": data["error"].get("info", "Error desconocido de API")}

        if not data.get("valid"):
             return {"error": "Número inválido según API"}
             
        return data
        
    except requests.exceptions.ConnectionError:
        return {"error": "Sin conexión a internet (DNS/Red fallido)"}
    except requests.exceptions.Timeout:
        return {"error": "Tiempo de espera agotado"}
    except Exception as e:
        return {"error": str(e)}

# Necesario para los colores dentro de este archivo
from colorama import Fore