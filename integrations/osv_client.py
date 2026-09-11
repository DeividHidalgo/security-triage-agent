"""
Cliente para a API pública do OSV.dev (Open Source Vulnerabilities).
Não exige autenticação. Usado para checar se um pacote/versão tem
vulnerabilidades conhecidas.

Docs: https://osv.dev/docs/
"""
from __future__ import annotations
import requests

OSV_QUERY_URL = "https://api.osv.dev/v1/query"

# Severidades reconhecidas, usadas para normalizar o que a API retorna
SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def query_package(package_name: str, version: str, ecosystem: str = "PyPI") -> list[dict]:
    """
    Consulta o OSV.dev por vulnerabilidades conhecidas de um pacote+versão.
    Retorna uma lista de vulnerabilidades (pode ser vazia).
    """
    payload = {
        "version": version,
        "package": {"name": package_name, "ecosystem": ecosystem},
    }
    resp = requests.post(OSV_QUERY_URL, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("vulns", [])


def extract_severity(vuln: dict) -> str:
    """
    O OSV nem sempre traz severidade normalizada (às vezes vem como CVSS
    vector string). Aqui fazemos uma extração best-effort; na ausência de
    dado, classificamos como MEDIUM por padrão conservador.
    """
    severities = vuln.get("severity", [])
    for sev in severities:
        score = sev.get("score", "")
        if "CVSS" in sev.get("type", ""):
            try:
                base_score = float(score.split("/")[0].split(":")[-1])
            except (ValueError, IndexError):
                continue
            if base_score >= 9.0:
                return "CRITICAL"
            if base_score >= 7.0:
                return "HIGH"
            if base_score >= 4.0:
                return "MEDIUM"
            return "LOW"

    db_specific = vuln.get("database_specific", {})
    sev = db_specific.get("severity")
    if sev and sev.upper() in SEVERITY_ORDER:
        return sev.upper()

    return "MEDIUM"
