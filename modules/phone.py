# modules/phone.py
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import pycountry

def parse_phone_number(number_str: str):
    """
    Parsea y valida un número de teléfono con phonenumbers.
    """
    try:
        parsed = phonenumbers.parse(number_str, None)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return parsed
    except phonenumbers.NumberParseException:
        return None

def get_phone_info(number_str: str):
    """
    Devuelve un dict con información básica del número usando phonenumbers.
    """
    parsed = parse_phone_number(number_str)
    if not parsed:
        return {"error": "Número inválido o formato incorrecto."}

    # Región / país
    region_code = phonenumbers.region_code_for_number(parsed)
    country = None
    if region_code:
        try:
            country = pycountry.countries.get(alpha_2=region_code).name
        except Exception:
            country = region_code

    description = geocoder.description_for_number(parsed, "es") or None

    # Operadora (solo si hay datos)
    operadora = carrier.name_for_number(parsed, "es") or None

    # Tipo de línea
    ntype = phonenumbers.number_type(parsed)
    tipo = "Desconocido"
    if ntype in (phonenumbers.PhoneNumberType.MOBILE,
                 phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE):
        tipo = "Móvil"
    elif ntype == phonenumbers.PhoneNumberType.FIXED_LINE:
        tipo = "Fijo"
    elif ntype == phonenumbers.PhoneNumberType.VOIP:
        tipo = "VoIP"

    zonas = timezone.time_zones_for_number(parsed)

    return {
        "number": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "country_code": region_code,
        "country": country,
        "description": description,
        "carrier": operadora,
        "line_type": tipo,
        "timezones": list(zonas),
        "parsed": parsed
    }