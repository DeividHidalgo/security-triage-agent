"""
Orquestrador principal do agente de triagem de segurança.

Uso:
    python -m agent.scan --path /caminho/do/repo --repo owner/nome

O que ele faz, em ordem:
  1. Lê requirements.txt do repositório alvo e consulta o OSV.dev
     por vulnerabilidades conhecidas de cada dependência.
  2. Varre os arquivos de texto do repositório atrás de padrões de
     segredo expostos (agent/secret_patterns.py).
  3. Grava cada achado no SQLite (agent/storage.py).
  4. Devolve a lista de achados para quem chamou (prioritize.py decide
     o que vira issue e o que vai no resumo).

Decisão de design (documentada em docs/decisoes.md):
  - O agente NUNCA abre issue nem manda Slack sozinho a partir daqui.
    Este módulo só coleta e persiste. A ação de notificar/abrir issue
    fica em prioritize.py / notify_slack.py, chamados explicitamente.
    Isso foi uma escolha manual minha, não sugestão do agente: eu quis
    poder revisar os achados antes de qualquer ação externa acontecer.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from agent import storage
from agent.secret_patterns import SECRET_PATTERNS, SCANNABLE_EXTENSIONS, IGNORED_DIRS
from integrations import osv_client


def scan_dependencies(repo_path: Path, scan_id: int) -> list[dict]:
    requirements = repo_path / "requirements.txt"
    findings = []
    if not requirements.exists():
        return findings

    for line in requirements.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        package, version = line.split("==", 1)
        package, version = package.strip(), version.strip()

        try:
            vulns = osv_client.query_package(package, version)
        except Exception as exc:  # rede indisponível, pacote não encontrado etc.
            print(f"  [aviso] não foi possível checar {package}=={version}: {exc}", file=sys.stderr)
            continue

        for vuln in vulns:
            severity = osv_client.extract_severity(vuln)
            finding_id = storage.add_finding(
                scan_id,
                kind="dependency",
                package=package,
                installed_version=version,
                vulnerability_id=vuln.get("id"),
                severity=severity,
                file_path="requirements.txt",
                description=(vuln.get("summary") or "")[:500],
                source_url=f"https://osv.dev/vulnerability/{vuln.get('id')}",
            )
            findings.append({"id": finding_id, "kind": "dependency", "package": package,
                              "severity": severity, "vulnerability_id": vuln.get("id")})
    return findings


def scan_secrets(repo_path: Path, scan_id: int) -> list[dict]:
    findings = []
    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in file_path.parts):
            continue
        if file_path.suffix not in SCANNABLE_EXTENSIONS:
            continue

        try:
            text = file_path.read_text(errors="ignore")
        except Exception:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern_name, pattern, severity in SECRET_PATTERNS:
                if pattern.search(line):
                    finding_id = storage.add_finding(
                        scan_id,
                        kind="secret",
                        severity=severity,
                        file_path=str(file_path.relative_to(repo_path)),
                        line_number=line_number,
                        description=pattern_name,
                    )
                    findings.append({"id": finding_id, "kind": "secret",
                                      "pattern": pattern_name, "severity": severity,
                                      "file_path": str(file_path.relative_to(repo_path)),
                                      "line_number": line_number})
    return findings


def run_scan(repo_path: str, repo_label: str) -> int:
    storage.init_db()
    path = Path(repo_path)
    scan_id = storage.start_scan(repo_label)
    print(f"[scan {scan_id}] iniciando varredura de {repo_label} em {path}")

    dep_findings = scan_dependencies(path, scan_id)
    print(f"[scan {scan_id}] {len(dep_findings)} vulnerabilidade(s) de dependência encontradas")

    secret_findings = scan_secrets(path, scan_id)
    print(f"[scan {scan_id}] {len(secret_findings)} segredo(s) potencial(is) encontrados")

    storage.finish_scan(scan_id, status="completed")
    print(f"[scan {scan_id}] concluído")
    return scan_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente de triagem de segurança")
    parser.add_argument("--path", required=True, help="Caminho local do repositório a varrer")
    parser.add_argument("--repo", required=True, help="Identificador do repo, ex: owner/nome")
    args = parser.parse_args()
    run_scan(args.path, args.repo)
