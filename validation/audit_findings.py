"""
Auditoria independente do trabalho do agente.

Este script NÃO reaproveita a lógica de scan.py — ele consulta o SQLite
com SQL puro e reconsulta o OSV.dev de forma independente, para responder
três perguntas que qualquer gestor faria antes de confiar no agente:

  1. Todo achado CRITICAL/HIGH tem mesmo uma issue aberta no GitHub?
  2. As vulnerabilidades reportadas realmente existem no OSV.dev (o agente
     não "alucinou" um CVE)?
  3. Existe algum achado duplicado (mesmo pacote+CVE registrado 2x)?

Uso:
    python -m validation.audit_findings --scan-id 1

Saída: relatório no terminal + código de saída != 0 se algo falhar,
para poder ser usado em CI.
"""
from __future__ import annotations
import argparse
import sys

from agent import storage
from integrations import osv_client


def check_critical_have_issues(scan_id: int) -> list[str]:
    """SQL puro: acha achados CRITICAL/HIGH sem número de issue."""
    conn = storage.get_connection()
    rows = conn.execute(
        """
        SELECT id, kind, package, file_path, severity
        FROM findings
        WHERE scan_id = ?
          AND severity IN ('CRITICAL', 'HIGH')
          AND github_issue_number IS NULL
        """,
        (scan_id,),
    ).fetchall()
    conn.close()

    problems = []
    for row in rows:
        label = row["package"] or row["file_path"]
        problems.append(f"achado #{row['id']} ({row['severity']}, {label}) é crítico/alto mas não tem issue aberta")
    return problems


def check_duplicates(scan_id: int) -> list[str]:
    """SQL puro: usa GROUP BY / HAVING para achar duplicatas exatas."""
    conn = storage.get_connection()
    rows = conn.execute(
        """
        SELECT package, vulnerability_id, COUNT(*) as n
        FROM findings
        WHERE scan_id = ? AND kind = 'dependency'
        GROUP BY package, vulnerability_id
        HAVING COUNT(*) > 1
        """,
        (scan_id,),
    ).fetchall()
    conn.close()

    return [
        f"vulnerabilidade {row['vulnerability_id']} do pacote {row['package']} aparece {row['n']}x (duplicada)"
        for row in rows
    ]


def check_vulnerabilities_are_real(scan_id: int) -> list[str]:
    """
    Reconsulta o OSV.dev, em Python, para cada dependency finding e confirma
    que o vulnerability_id gravado no banco realmente está entre os
    retornados pela API — ou seja, confere a fonte primária, não confia
    só no que o agente escreveu no banco.
    """
    conn = storage.get_connection()
    rows = conn.execute(
        "SELECT id, package, installed_version, vulnerability_id FROM findings "
        "WHERE scan_id = ? AND kind = 'dependency'",
        (scan_id,),
    ).fetchall()
    conn.close()

    problems = []
    for row in rows:
        try:
            vulns = osv_client.query_package(row["package"], row["installed_version"])
        except Exception as exc:
            problems.append(f"achado #{row['id']}: não consegui reconsultar o OSV.dev ({exc})")
            continue
        vuln_ids = {v.get("id") for v in vulns}
        if row["vulnerability_id"] not in vuln_ids:
            problems.append(
                f"achado #{row['id']}: {row['vulnerability_id']} não foi encontrado numa "
                f"nova consulta ao OSV.dev para {row['package']}=={row['installed_version']}"
            )
    return problems


def run_audit(scan_id: int) -> bool:
    print(f"=== Auditoria do scan {scan_id} ===\n")

    checks = [
        ("Achados críticos/altos têm issue aberta", check_critical_have_issues),
        ("Sem achados duplicados", check_duplicates),
        ("Vulnerabilidades reportadas existem de fato no OSV.dev", check_vulnerabilities_are_real),
    ]

    all_ok = True
    for description, check_fn in checks:
        problems = check_fn(scan_id)
        if problems:
            all_ok = False
            print(f"❌ {description} — {len(problems)} problema(s):")
            for p in problems:
                print(f"   - {p}")
        else:
            print(f"✅ {description}")
        print()

    print("RESULTADO: " + ("aprovado" if all_ok else "reprovado — ver problemas acima"))
    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditoria independente dos achados do agente")
    parser.add_argument("--scan-id", required=True, type=int)
    args = parser.parse_args()
    ok = run_audit(args.scan_id)
    sys.exit(0 if ok else 1)
