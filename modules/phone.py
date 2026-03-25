from __future__ import annotations

import phonenumbers
import pycountry
from phonenumbers import carrier, geocoder, timezone


LINE_TYPE_MAP = {
    phonenumbers.PhoneNumberType.MOBILE: "MOBILE",
    phonenumbers.PhoneNumberType.FIXED_LINE: "FIXED_LINE",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
    phonenumbers.PhoneNumberType.VOIP: "VOIP",
    phonenumbers.PhoneNumberType.TOLL_FREE: "TOLL_FREE",
}


def parse_phone_number(number_str: str):
    """
    Parses a phone number in E.164 format and validates that it is possible.
    """
    try:
        parsed = phonenumbers.parse(number_str, None)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_possible_number(parsed):
        return None

    return parsed


def _country_name(region_code: str | None) -> str | None:
    if not region_code:
        return None

    try:
        country = pycountry.countries.get(alpha_2=region_code)
        return country.name if country else region_code
    except Exception:
        return region_code


def _line_type(parsed_number) -> str:
    number_type = phonenumbers.number_type(parsed_number)
    return LINE_TYPE_MAP.get(number_type, "UNKNOWN")


def _npa_nxx(parsed_number) -> str | None:
    national_number = str(parsed_number.national_number)
    if parsed_number.country_code == 1 and len(national_number) >= 6:
        return f"{national_number[:3]}-{national_number[3:6]}"
    return None


def get_phone_info(number_str: str, lang: str = "es") -> dict:
    """
    Extracts phone metadata using phonenumbers only.
    """
    parsed = parse_phone_number(number_str)
    if not parsed:
        return {"error": "Numero invalido o formato incorrecto. Usa formato E.164, por ejemplo +573001234567."}

    if not phonenumbers.is_valid_number(parsed):
        return {"error": "El numero no es valido segun la metadata de phonenumbers."}

    region_code = phonenumbers.region_code_for_number(parsed)
    description_es = geocoder.description_for_number(parsed, "es") or None
    description_en = geocoder.description_for_number(parsed, "en") or None
    selected_description = description_es if lang.lower().startswith("es") else description_en
    carrier_es = carrier.name_for_number(parsed, "es") or None
    carrier_en = carrier.name_for_number(parsed, "en") or None
    selected_carrier = carrier_es or carrier_en

    return {
        "input_number": number_str,
        "number": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "country_code": region_code,
        "country_calling_code": parsed.country_code,
        "country": _country_name(region_code),
        "region": selected_description or _country_name(region_code),
        "description_es": description_es,
        "description_en": description_en,
        "carrier": selected_carrier,
        "carrier_es": carrier_es,
        "carrier_en": carrier_en,
        "line_type": _line_type(parsed),
        "timezones": list(timezone.time_zones_for_number(parsed)),
        "npa_nxx": _npa_nxx(parsed),
        "is_valid": True,
    }
