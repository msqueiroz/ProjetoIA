import re
import unicodedata
from typing import Any


UNIDADES_APRESENTACAO = {
    "cubic meter per hour": "m³/h",
    "cubic meters per hour": "m³/h",
    "cubic metre per hour": "m³/h",
    "cubic metres per hour": "m³/h",
    "cubic meter per second": "m³/s",
    "cubic meters per second": "m³/s",
    "cubic meter": "m³",
    "cubic meters": "m³",
    "liter per second": "L/s",
    "liters per second": "L/s",
    "litre per second": "L/s",
    "litres per second": "L/s",
    "liter per hour": "L/h",
    "liters per hour": "L/h",
    "milligram per liter": "mg/L",
    "milligrams per liter": "mg/L",
    "kilogram per hour": "kg/h",
    "kilograms per hour": "kg/h",
    "kilowatt": "kW",
    "kilowatts": "kW",
    "kilowatt hour": "kWh",
    "degree celsius": "°C",
    "degrees celsius": "°C",
    "percent": "%",
    "percentage": "%",
    "ampere": "A",
    "amperes": "A",
    "volt": "V",
    "volts": "V",
    "revolutions per minute": "rpm",
    "revolution per minute": "rpm",
    "nephelometric turbidity unit": "NTU",
    "day": "d",
    "days": "d",
    "hour": "h",
    "hours": "h",
    "meter": "m",
    "meters": "m",
}


def _chave_unidade(unidade: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(unidade or ""))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", texto.strip().lower())


def formatar_unidade_engenharia(unidade: Any) -> str:
    """Converte nomes extensos do PI/AF para símbolos de apresentação."""

    original = str(unidade or "").strip()
    if not original:
        return ""
    return UNIDADES_APRESENTACAO.get(_chave_unidade(original), original)
