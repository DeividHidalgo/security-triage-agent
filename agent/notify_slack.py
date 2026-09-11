"""
Gera o resumo executivo de um scan e envia para o Slack.

A linguagem aqui é deliberadamente não-técnica: quem lê é diretoria/CFO,
não o time de engenharia (esse é um dos critérios do anúncio da vaga:
"comunicação executiva: explicar em poucos minutos o que o agente faz,
o que não faz e o que mudou desde que entrou").

Uso:
    python -m agent.notify_slack --scan-id 1
"""
from __future__ import annotations
import argparse

from dotenv import load_dotenv

from agent import storage
from integrations import slack_client

load_dotenv()  # lê o arquivo .env, se existir, e popula os.environ

SEVERITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}


def build_summary(scan_id: int) -> str:
    conn = storage.get_connection()
    scan = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    findings = conn.execute("SELECT * FROM findings WHERE scan_id = ?", (scan_id,)).fetchall()
    conn.close()

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    issues_opened = 0
    for f in findings:
        counts[f["severity"]] += 1
        if f["github_issue_number"]:
            issues_opened += 1

    total = len(findings)
    lines = [
        f"*Resumo de segurança — {scan['repo']}*",
        f"Varredura concluída em {scan['finished_at']}.",
        "",
        f"Total de achados: *{total}*",
    ]
    for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if counts[severity]:
            lines.append(f"{SEVERITY_EMOJI[severity]} {severity}: {counts[severity]}")

    lines.append("")
    if issues_opened:
        lines.append(f"{issues_opened} issue(s) aberta(s) automaticamente no GitHub para os itens críticos/altos.")
    else:
        lines.append("Nenhuma issue automática foi necessária nesta varredura.")

    if counts["CRITICAL"] > 0:
        lines.append("\n⚠️ *Ação recomendada:* há item(ns) crítico(s) — priorizar correção antes do próximo deploy.")
    else:
        lines.append("\n✅ Nenhum item crítico nesta varredura.")

    return "\n".join(lines)


def send_summary(scan_id: int, dry_run: bool = False) -> str:
    summary = build_summary(scan_id)
    if dry_run:
        print("[dry-run] mensagem que seria enviada ao Slack:\n")
        print(summary)
    else:
        slack_client.send_message(summary)
        print("Resumo enviado ao Slack.")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Envia resumo executivo ao Slack")
    parser.add_argument("--scan-id", required=True, type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    send_summary(args.scan_id, dry_run=args.dry_run)
