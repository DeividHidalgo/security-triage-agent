"""
Decide o que fazer com os achados de um scan: quais viram issue no GitHub.

Regra de negócio (documentada em docs/processo-mapeado.md, seção "critérios
de priorização"): abrimos issue automaticamente só para CRITICAL e HIGH.
MEDIUM/LOW entram no resumo executivo mas não geram ruído de issue —
essa é uma decisão de processo, não uma limitação técnica.

Uso:
    python -m agent.prioritize --scan-id 1 --repo owner/nome
"""
from __future__ import annotations
import argparse

from dotenv import load_dotenv

from agent import storage
from integrations.github_client import GitHubClient

load_dotenv()  # lê o arquivo .env, se existir, e popula os.environ

AUTO_ISSUE_SEVERITIES = {"CRITICAL", "HIGH"}


def build_issue_body(finding: dict) -> str:
    if finding["kind"] == "dependency":
        return (
            f"**Tipo:** Dependência vulnerável\n"
            f"**Pacote:** `{finding['package']}=={finding['installed_version']}`\n"
            f"**Vulnerabilidade:** {finding['vulnerability_id']}\n"
            f"**Severidade:** {finding['severity']}\n"
            f"**Descrição:** {finding['description']}\n"
            f"**Referência:** {finding['source_url']}\n\n"
            f"_Achado automaticamente pelo agente de triagem de segurança._"
        )
    return (
        f"**Tipo:** Segredo potencialmente exposto\n"
        f"**Padrão detectado:** {finding['description']}\n"
        f"**Arquivo:** `{finding['file_path']}` (linha {finding['line_number']})\n"
        f"**Severidade:** {finding['severity']}\n\n"
        f"_Achado automaticamente pelo agente de triagem de segurança. "
        f"Revogue e rotacione a credencial antes de fechar esta issue._"
    )


def prioritize_and_file_issues(scan_id: int, repo: str, dry_run: bool = False) -> list[dict]:
    conn = storage.get_connection()
    rows = conn.execute(
        "SELECT * FROM findings WHERE scan_id = ? AND github_issue_number IS NULL",
        (scan_id,),
    ).fetchall()
    conn.close()

    filed = []
    client = None if dry_run else GitHubClient(repo=repo)

    for row in rows:
        finding = dict(row)
        if finding["severity"] not in AUTO_ISSUE_SEVERITIES:
            continue

        title = (
            f"[Security] {finding['severity']} - "
            + (finding["package"] if finding["kind"] == "dependency" else finding["file_path"])
        )
        body = build_issue_body(finding)

        if dry_run:
            print(f"[dry-run] abriria issue: {title}")
            filed.append({"finding_id": finding["id"], "title": title, "issue_number": None})
            continue

        issue = client.create_issue(title=title, body=body, labels=["security", finding["severity"].lower()])
        storage.set_issue_number(finding["id"], issue["number"])
        filed.append({"finding_id": finding["id"], "title": title, "issue_number": issue["number"]})
        print(f"issue #{issue['number']} criada: {title}")

    return filed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prioriza achados e abre issues no GitHub")
    parser.add_argument("--scan-id", required=True, type=int)
    parser.add_argument("--repo", required=True, help="owner/nome")
    parser.add_argument("--dry-run", action="store_true", help="Não chama a API do GitHub, só imprime")
    args = parser.parse_args()
    prioritize_and_file_issues(args.scan_id, args.repo, dry_run=args.dry_run)
