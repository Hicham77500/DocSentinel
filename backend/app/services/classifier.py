from __future__ import annotations

import re
import unicodedata


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


CLASSIFICATION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "invoice",
        (
            "facture",
            "invoice",
            "montant ttc",
            "total ttc",
            "date de facture",
        ),
    ),
    (
        "quote",
        (
            "devis",
            "quotation",
            "estimation",
        ),
    ),
    (
        "certificate",
        (
            "attestation",
            "certificate",
            "assurance",
            "responsabilite civile",
        ),
    ),
    (
        "rib",
        (
            "rib",
            "releve d identite bancaire",
            "iban",
            "bic",
        ),
    ),
    (
        "kbis",
        (
            "kbis",
            "extrait kbis",
            "registre du commerce",
            "rcs",
        ),
    ),
    (
        "supplier_document",
        (
            "fournisseur",
            "vendor",
            "supplier",
        ),
    ),
)


def classify_document(text: str, filename: str | None = None) -> str:
    normalized_text = _normalize_text(text or "")
    normalized_filename = _normalize_text(filename or "")
    searchable = f"{normalized_text} {normalized_filename}".strip()

    for document_type, keywords in CLASSIFICATION_RULES:
        if any(keyword in searchable for keyword in keywords):
            return document_type

    return "unknown"
