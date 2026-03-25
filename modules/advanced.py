# modules/advanced.py
import webbrowser

def analyze_risk(numverify_data, phone_info):
    """
    Analiza los datos para determinar un nivel de riesgo.
    Retorna un diccionario con el nivel y una explicación.
    """
    risk_score = 0
    reasons = []

    # 1. Verificar si es VoIP (Virtual Number)
    # Los estafadores suelen usar números VoIP porque son fáciles de conseguir y ocultan su ubicación real.
    if numverify_data.get("line_type") == "voip":
        risk_score += 50
        reasons.append("El número es VoIP (Virtual). Usado frecuentemente en estafas o empresas de marketing.")

    # 2. Verificar inconsistencia entre Operadora Local y API
    # Si phonenumbers dice "Tigo" pero Numverify dice "VoIP", es sospechoso.
    local_carrier = phone_info.get("carrier")
    api_carrier = numverify_data.get("carrier")
    
    # Si la API dice VoIP pero la librería local decía Móvil
    if numverify_data.get("line_type") == "voip" and phone_info.get("line_type") == "Móvil":
        risk_score += 20
        reasons.append("Inconsistencia en tipo de línea detectada.")

    # 3. Número inválido según API
    if numverify_data.get("valid") is False:
        risk_score = 100
        reasons.append("El número no pasó la validación internacional.")

    # Clasificación final
    if risk_score >= 80:
        level = "ALTO"
        color = "🔴"
    elif risk_score >= 40:
        level = "MEDIO"
        color = "🟠"
    else:
        level = "BAJO"
        color = "🟢"
        reasons.append("Parece un número móvil legítimo de una operadora física.")

    return {
        "score": risk_score,
        "level": level,
        "color": color,
        "reasons": reasons
    }

def generate_deep_links(phone_number):
    """
    Genera enlaces directos a herramientas externas para investigación manual.
    """
    # Limpiamos el número
    num_clean = phone_number.replace("+", "")
    
    return {
        "WhatsApp Web": f"https://wa.me/{num_clean}",
        "TrueCaller": f"https://www.truecaller.com/search/{num_clean}",
        "Sync.ME": f"https://sync.me/?number={num_clean}",
        "Spam Calls": f"https://spamcalls.net/en/number/{num_clean}",
        "WhoCalled": f"https://whocalled.com/phone/{num_clean}",
        "Google Search": f"https://www.google.com/search?q=%2B{num_clean}"
    }