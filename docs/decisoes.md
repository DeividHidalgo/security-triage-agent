# O que o agente fez vs. o que eu decidi

Este documento existe porque é exatamente o que a vaga pede: mostrar
onde termina o trabalho do agente e começa o julgamento humano.

## O que pedi ao agente (prompt/objetivo original)

> "Construa um agente que varra um repositório atrás de dependências
> vulneráveis e segredos expostos, grave os achados num banco, abra
> issues no GitHub para os críticos e mande um resumo executivo no
> Slack. Separe claramente coleta, priorização e notificação em módulos
> diferentes, porque eu quero poder revisar antes de qualquer ação
> externa acontecer."

## O que o agente gerou sozinho

- A estrutura inicial dos clientes de integração (`integrations/*.py`)
- A lógica de varredura de arquivos e aplicação de regex (`agent/scan.py`, `agent/secret_patterns.py`)
- O schema SQL inicial
- O script de auditoria independente (`validation/audit_findings.py`)

## O que eu revisei e mudei manualmente

- **Separação scan / priorize / notify em 3 comandos distintos**: rejeitei
  a ideia de um único fluxo automático (scan → issue → Slack sem parar),
  porque numa empresa de verdade ninguém deveria deixar um agente
  notificar diretoria sem uma etapa revisável. Pedi 3 scripts
  independentes, cada um chamado explicitamente.
- **Regras de priorização (só CRITICAL/HIGH abrem issue)**: decidi
  limitar a esses dois níveis para não gerar ruído de issue para
  MEDIUM/LOW — decisão de processo, documentada em `docs/processo-mapeado.md`.
- **Padrões de detecção de segredo**: reduzi a lista de regex para os 7
  padrões mais precisos, evitando falso-positivo.
- **Auditoria independente de propósito**: pedi que `validation/audit_findings.py`
  NÃO reaproveitasse a lógica de `scan.py`, e reconsultasse o OSV.dev do
  zero — se a auditoria chamasse as mesmas funções do scan original, um
  bug no scan nunca seria pego por ela.
- **Modo `--dry-run`**: adicionado para poder testar o pipeline inteiro
  sem realmente abrir issue/mandar mensagem, importante tanto para
  desenvolvimento quanto para CI de PR.
- **python-dotenv**: adicionei depois de perceber, ao testar de verdade,
  que exigir `export` manual das variáveis de ambiente no terminal era
  um passo de fricção desnecessário para quem fosse rodar o projeto.

## Testando de ponta a ponta (o que realmente aconteceu)

Rodei o pipeline completo em duas etapas, e documento aqui os problemas
reais que apareceram — porque "o que deu errado e como resolvi" é tão
relevante quanto "o que funcionou de primeira":

1. **Teste offline** (`samples/demo-repo`, sem GitHub/Slack reais):
   `scan` → `prioritize --dry-run` → `notify_slack --dry-run` →
   `audit_findings`. A auditoria reportou **reprovado**, corretamente —
   como tudo rodou em dry-run, nenhuma issue tinha sido de fato aberta,
   e a auditoria pegou essa inconsistência. Isso
