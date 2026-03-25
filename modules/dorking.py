# modules/dorking.py
import random
import time
from googlesearch import search
import webbrowser

DOMAINS = ["com", "com.tw", "co.in", "be", "de", "co.uk", "co.ma", "dz", "ru", "ca"]

def get_number_variations(full_number):

    variations = set()
    
    # 1. Número completo con +
    variations.add(full_number)
    
    # 2. Número sin el +
    num_no_plus = full_number.replace("+", "")
    variations.add(num_no_plus)
    
    # 3. Intentar extraer número local (quitar código país)
    # Si es largo > 10, asumimos que tiene código país
    if len(num_no_plus) > 10:
        # Para Colombia suele ser 57, México 52, etc.
        # Probamos quitando los primeros 2 o 3 dígitos si coincide con prefijos comunes
        # O simplemente cortamos los primeros digitos para ver el número "local"
        local_guess = num_no_plus[2:] if num_no_plus.startswith("57") else num_no_plus[3:]
        
        variations.add(local_guess)
        
        # Formato con espacios: 301 518 5270 (asumiendo 10 dígitos locales)
        if len(local_guess) == 10:
            formatted = f"{local_guess[0:3]} {local_guess[3:6]} {local_guess[6:]}"
            variations.add(formatted)
            
    return list(variations)

def build_dorks(number_list):
    """
    Construye dorks agresivos usando variaciones del número.
    """
    # Usamos el número sin + para la mayoría de búsquedas
    target = number_list[1] if len(number_list) > 1 else number_list[0]
    
    return {
        "general": f'intext:"{target}" OR intext:"{number_list[0]}"',
        "pdf": f'filetype:pdf "{target}"', # Corregido: ya no usa site:@
        "facebook": f'site:facebook.com "{target}"',
        "twitter": f'site:twitter.com "{target}"',
        "linkedin": f'site:linkedin.com "{target}"', # Agregado LinkedIn
        "instagram": f'site:instagram.com "{target}"',
        "whatsapp_groups": f'site:chat.whatsapp.com "{target}"', # Busca enlaces de grupos
        "scam_reports": f'"{target}" (scam OR estafa OR spam)', # Busca reportes de estafa
    }

def run_dorks(full_number: str, max_results: int = 5):
    """
    Ejecuta los dorks. Si falla (bloqueo de Google), devuelve enlaces manuales.
    """
    variations = get_number_variations(full_number)
    dorks = build_dorks(variations)
    results = {}
    manual_links = {}

    for name, query in dorks.items():
        results[name] = []
        try:
            # Intentamos buscar
            tld = random.choice(DOMAINS)
            # Agregamos pausa aleatoria para evitar bloqueos
            pause_time = random.uniform(2.0, 4.0) 
            
            found_urls = list(search(query, tld=tld, num=max_results, stop=max_results, pause=pause_time))
            
            if found_urls:
                results[name] = found_urls
            else:
                # Si no encuentra nada, generamos el link manual
                manual_links[name] = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                
        except Exception:
            # Si hay error (bloqueo), generamos link manual
            manual_links[name] = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        
        time.sleep(1) # Pausa entre búsquedas

    return results, manual_links