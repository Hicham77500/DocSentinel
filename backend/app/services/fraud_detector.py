from __future__ import annotations

import re


TVA_PATTERN = re.compile(r"^FR[0-9A-Z]{2}\d{9}$")


def compute_fraud_score(data: dict) -> tuple[float, list[str]]:
    anomalies: list[str] = []

    siren = str(data.get("siren", "")).strip()
    if siren and len(siren) != 9:
        anomalies.append("Invalid SIREN length.")

    siret = str(data.get("siret", "")).strip()
    if siret and len(siret) != 14:
        anomalies.append("Invalid SIRET length.")

    tva = str(data.get("tva", "")).strip().upper()
    if tva and not TVA_PATTERN.match(tva):
        anomalies.append("TVA format anomaly.")

    dates_raw = data.get("dates", [])
    if isinstance(dates_raw, list):
        unique_dates = {str(item) for item in dates_raw if str(item).strip()}
        if len(unique_dates) > 1:
            anomalies.append("Multiple inconsistent dates detected.")

    amounts_raw = data.get("montants", [])
    if isinstance(amounts_raw, list):
        for amount in amounts_raw:
            try:
                value = float(amount)
            except (TypeError, ValueError):
                continue
            if value > 1_000_000:
                anomalies.append("Unusually large amount detected.")
                break

    max_checks = 4.0
    fraud_score = min(len(anomalies) / max_checks, 1.0)
    return fraud_score, anomalies
