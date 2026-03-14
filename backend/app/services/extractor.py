from __future__ import annotations

from datetime import datetime
import re
import unicodedata


def _normalize_text(text: str) -> str:
    return text.replace("\u00a0", " ")


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _find_siren(text: str) -> str:
    pattern = re.compile(r"(?<!\d)(\d(?:[\s.-]?\d){8})(?!\d)")
    for match in pattern.finditer(text):
        candidate = re.sub(r"\D", "", match.group(1))
        if len(candidate) == 9:
            return candidate
    return ""


def _find_siret(text: str) -> str:
    pattern = re.compile(r"(?<!\d)(\d(?:[\s.-]?\d){13})(?!\d)")
    for match in pattern.finditer(text):
        candidate = re.sub(r"\D", "", match.group(1))
        if len(candidate) == 14:
            return candidate
    return ""


def _find_tva(text: str) -> str:
    pattern = re.compile(r"\b(FR[\s-]?[0-9A-Z]{2}[\s-]?\d(?:[\s.-]?\d){8})\b", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return ""
    return re.sub(r"[\s.-]", "", match.group(1)).upper()


def _find_iban(text: str) -> str:
    pattern = re.compile(r"\b(FR\d{2}(?:[\s.-]?[A-Z0-9]){23})\b", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return ""
    return re.sub(r"[\s.-]", "", match.group(1)).upper()


def _find_raison_sociale(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    key_pattern = re.compile(
        r"(raison\s+sociale|denomination|societe|entreprise|company)",
        re.IGNORECASE,
    )

    for idx, line in enumerate(lines):
        ascii_line = _strip_accents(line).lower()
        if key_pattern.search(ascii_line):
            if ":" in line:
                value = line.split(":", 1)[1].strip(" -\t")
                if value:
                    return value
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip(" -\t")
                if next_line:
                    return next_line

    for line in lines:
        cleaned = line.strip(" -\t")
        if len(cleaned.split()) >= 2 and sum(ch.isdigit() for ch in cleaned) <= 3:
            return cleaned

    return ""


def _parse_amount_token(token: str) -> float | None:
    value = token.strip().replace(" ", "").replace("\u00a0", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    elif value.count(".") > 1:
        parts = value.split(".")
        value = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(value)
    except ValueError:
        return None


def _find_amounts(text: str) -> list[float]:
    pattern = re.compile(r"(?<!\d)(\d{1,3}(?:[ .]\d{3})*[.,]\d{2}|\d+[.,]\d{2})(?!\d)")
    amounts: list[float] = []
    seen: set[float] = set()

    for match in pattern.finditer(text):
        value = _parse_amount_token(match.group(1))
        if value is None:
            continue
        if value not in seen:
            seen.add(value)
            amounts.append(value)

    return amounts


def _parse_date_token(token: str) -> str | None:
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%Y.%m.%d",
    ):
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _find_dates(text: str) -> list[str]:
    pattern = re.compile(r"\b(\d{4}[-/.]\d{2}[-/.]\d{2}|\d{2}[-/.]\d{2}[-/.]\d{2,4})\b")
    dates: list[str] = []
    seen: set[str] = set()

    for match in pattern.finditer(text):
        parsed = _parse_date_token(match.group(1))
        if parsed and parsed not in seen:
            seen.add(parsed)
            dates.append(parsed)

    return dates


def extract_fields(text: str) -> dict:
    normalized = _normalize_text(text or "")
    return {
        "siren": _find_siren(normalized),
        "siret": _find_siret(normalized),
        "tva": _find_tva(normalized),
        "raison_sociale": _find_raison_sociale(normalized),
        "montants": _find_amounts(normalized),
        "dates": _find_dates(normalized),
        "iban": _find_iban(normalized),
    }
