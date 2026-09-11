# Agente de Triagem de Vulnerabilidades e Reporte Executivo

Projeto construído com um agente de código (Claude Code) para automatizar
parte do processo de triagem de segurança: varrer um repositório atrás de
dependências vulneráveis e segredos expostos, priorizar o que é crítico,
abrir issues no GitHub e comunicar o risco à diretoria em linguagem
executiva — com um script independente que audita se o trabalho do
agente está correto.

## Por que este projeto

Feito para demonstrar, com código real e executável:
- Uso de agente de código de ponta a ponta (não só geração de trechos soltos)
- Entendimento de um processo de negócio (triagem de segurança) mapeado
  **antes** de automatizar — ver `docs/processo-mapeado.md`
- Integrações reais: GitHub REST API, Slack Incoming Webhook, OSV.dev
- Autonomia real com limite claro: o agente coleta e prioriza, mas nunca
  age externamente sem uma etapa explícita e revisável
- SQL/Python para conferir que o agente fez o trabalho certo — ver `validation/audit_findings.py`
- Comunicação executiva — ver o formato do resumo em `agent/notify_slack.py`

## Arquitetura

```
GitHub push ──▶ agent/scan.py ──▶ SQLite (db/findings.db)
                    │
                    ├─ consulta OSV.dev (dependências vulneráveis)
                    └─ regex scan (segredos expostos)

agent/prioritize.py ──▶ abre issues no GitHub (CRITICAL/HIGH)
agent/notify_slack.py ──▶ envia resumo executivo ao Slack

validation/audit_findings.py ──▶ reconsulta OSV.dev + SQL puro
                                  para auditar o que o agente reportou
```

Os três passos (`scan`, `prioritize`, `notify_slack`) são comandos
**separados de propósito** — ver `docs/decisoes.md` para o porquê.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha GITHUB_TOKEN, GITHUB_REPO, SLACK_WEBHOOK_URL
# o .env é carregado automaticamente (python-dotenv) — não precisa exportar nada

# 1. Varredura (funciona sem credenciais nenhuma, só consulta o OSV.dev que é público)
python -m agent.scan --path /caminho/do/repo --repo owner/nome

# 2. Priorizar e abrir issues (precisa de GITHUB_TOKEN)
python -m agent.prioritize --scan-id 1 --repo owner/nome
#   use --dry-run para só imprimir, sem chamar a API de verdade

# 3. Enviar resumo ao Slack (precisa de SLACK_WEBHOOK_URL)
python -m agent.notify_slack --scan-id 1
#   use --dry-run para só imprimir

# 4. Auditar o trabalho do agente
python -m validation.audit_findings --scan-id 1
```

Há um repositório de amostra em `samples/demo-repo` (com um segredo
propositalmente exposto) para testar o pipeline sem precisar de um repo
real:

```bash
python -m agent.scan --path samples/demo-repo --repo demo-org/demo-repo
python -m agent.prioritize --scan-id 1 --repo demo-org/demo-repo --dry-run
python -m agent.notify_slack --scan-id 1 --dry-run
python -m validation.audit_findings --scan-id 1
```

## CI automático

`.github/workflows/security-scan.yml` roda o pipeline inteiro a cada push
na `main` (requer os secrets `SLACK_WEBHOOK_URL` configurados no repo —
`GITHUB_TOKEN` já é injetado automaticamente pelo GitHub Actions).

## Estrutura

- `agent/` — lógica do agente (scan, priorização, notificação)
- `integrations/` — clientes das APIs externas (GitHub, Slack, OSV.dev)
- `db/` — schema SQLite
- `validation/` — auditoria independente do trabalho do agente
- `docs/processo-mapeado.md` — o processo de negócio mapeado antes de automatizar
- `docs/decisoes.md` — o que o agente fez sozinho vs. o que eu decidi/mudei
- `samples/demo-repo/` — repositório de teste para rodar o pipeline sem rede/credenciais reais

## Limitações conhecidas

- O agente não corrige nada sozinho (não faz upgrade de dependência, não
  remove segredo) — decisão consciente, ver `docs/decisoes.md`.
- Detecção de segredo é baseada em regex (rápida e auditável, mas não
  substitui uma ferramenta como TruffleHog para cobertura completa).
- Suporte a dependências hoje é só Python (`requirements.txt`); dá pra
  estender para `package.json` (npm/OSV ecosystem) sem mudar a arquitetura.
