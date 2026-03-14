from __future__ import annotations

from datetime import datetime
import re


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _normalize_amount(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    token = value.strip().replace(" ", "").replace("\u00a0", "")
    if "," in token and "." in token:
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif "," in token:
        token = token.replace(",", ".")
    elif token.count(".") > 1:
        parts = token.split(".")
        token = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(token)
    except ValueError:
        return None


def _normalize_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token:
        return None

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y.%m.%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_fields(data: dict) -> dict:
    normalized: dict = {
        "siren": "",
        "siret": "",
        "tva": "",
        "raison_sociale": "",
        "montants": [],
        "dates": [],
        "iban": "",
    }

    siren_raw = _digits_only(str(data.get("siren", "")))
    normalized["siren"] = siren_raw if len(siren_raw) == 9 else ""

    siret_raw = _digits_only(str(data.get("siret", "")))
    normalized["siret"] = siret_raw if len(siret_raw) == 14 else ""

    tva_raw = str(data.get("tva", "")).replace(" ", "").replace(".", "").replace("-", "")
    normalized["tva"] = tva_raw.upper()

    raison_sociale_raw = str(data.get("raison_sociale", ""))
    normalized["raison_sociale"] = _clean_text(raison_sociale_raw)

    iban_raw = str(data.get("iban", ""))
    normalized["iban"] = re.sub(r"[\s.-]", "", iban_raw).upper()

    montants_raw = data.get("montants", [])
    montants: list[float] = []
    if isinstance(montants_raw, list):
        for item in montants_raw:
            amount = _normalize_amount(item)
            if amount is not None:
                montants.append(amount)
    normalized["montants"] = montants

    dates_raw = data.get("dates", [])
    dates: list[str] = []
    seen_dates: set[str] = set()
    if isinstance(dates_raw, list):
        for item in dates_raw:
            parsed = _normalize_date(item)
            if parsed and parsed not in seen_dates:
                seen_dates.add(parsed)
                dates.append(parsed)
    normalized["dates"] = dates

    return normalized
