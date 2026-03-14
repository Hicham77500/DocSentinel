from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata


MISSING_EXPECTED_BY_TYPE: dict[str, set[str]] = {
    "invoice": {"rib", "kbis"},
    "quote": {"rib"},
    "certificate": {"kbis"},
    "rib": {"invoice"},
    "supplier_document": {"invoice", "rib"},
}


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _digits_only(value: object) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _normalize_siren(value: object) -> str:
    candidate = _digits_only(value)
    return candidate if len(candidate) == 9 else ""


def _normalize_siret(value: object) -> str:
    candidate = _digits_only(value)
    return candidate if len(candidate) == 14 else ""


def _normalize_iban(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _normalize_tva(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _normalize_raison_sociale(value: object) -> str:
    return _normalize_text(value)


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token:
        return None
    try:
        return datetime.fromisoformat(token).date()
    except ValueError:
        return None


def _extract_normalized_payload(document: dict) -> dict:
    normalized = document.get("normalized")
    if isinstance(normalized, dict):
        return normalized
    return {}


def _build_mismatch_anomaly(
    label: str,
    field_values: dict[str, tuple[str, str]],
) -> str | None:
    if len(field_values) <= 1:
        return None
    values = list(field_values.values())
    first_type = values[0][1]
    second_type = values[1][1]
    return f"{label} mismatch between {first_type} and {second_type}"


def cross_check_documents(documents: list[dict]) -> dict:
    anomalies: list[str] = []
    doc_types: list[str] = []

    siren_values: dict[str, tuple[str, str]] = {}
    siret_values: dict[str, tuple[str, str]] = {}
    raison_values: dict[str, tuple[str, str]] = {}
    iban_values: dict[str, tuple[str, str]] = {}
    tva_values: dict[str, tuple[str, str]] = {}
    all_dates: list[date] = []

    for document in documents:
        document_type = str(document.get("document_type") or "unknown")
        normalized = _extract_normalized_payload(document)
        doc_types.append(document_type)

        siren = _normalize_siren(normalized.get("siren"))
        if siren:
            siren_values.setdefault(siren, (siren, document_type))

        siret = _normalize_siret(normalized.get("siret"))
        if siret:
            siret_values.setdefault(siret, (siret, document_type))

        raison_sociale = _normalize_raison_sociale(normalized.get("raison_sociale"))
        if raison_sociale:
            raison_values.setdefault(raison_sociale, (raison_sociale, document_type))

        iban = _normalize_iban(normalized.get("iban"))
        if iban:
            iban_values.setdefault(iban, (iban, document_type))

        tva = _normalize_tva(normalized.get("tva"))
        if tva:
            tva_values.setdefault(tva, (tva, document_type))

        raw_dates = normalized.get("dates", [])
        if isinstance(raw_dates, list):
            for raw_date in raw_dates:
                parsed = _parse_date(raw_date)
                if parsed is not None:
                    all_dates.append(parsed)

    for label, values in (
        ("SIREN", siren_values),
        ("SIRET", siret_values),
        ("raison sociale", raison_values),
        ("IBAN", iban_values),
        ("TVA", tva_values),
    ):
        mismatch = _build_mismatch_anomaly(label=label, field_values=values)
        if mismatch:
            anomalies.append(mismatch)

    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        spread_days = (max_date - min_date).days
        if spread_days > 90:
            anomalies.append(
                f"Suspicious date spread across related documents ({spread_days} days)"
            )

    distinct_types = sorted({doc_type for doc_type in doc_types if doc_type})
    expected_types: set[str] = set()
    for doc_type in distinct_types:
        expected_types.update(MISSING_EXPECTED_BY_TYPE.get(doc_type, set()))
    missing_types = sorted(expected_types - set(distinct_types))
    if missing_types:
        anomalies.append(
            "Missing expected document types in bundle: "
            + ", ".join(missing_types)
        )

    return {
        "bundle_status": "inconsistent" if anomalies else "consistent",
        "anomalies": anomalies,
        "summary": {
            "document_count": len(documents),
            "document_types": distinct_types,
        },
    }
