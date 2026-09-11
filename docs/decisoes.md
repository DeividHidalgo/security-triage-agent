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

## O que eu revisei e mudei manualmente

- **Separação scan / priorize / notify em 3 comandos distintos**: a
  primeira versão do agente fazia tudo numa função só (scan → issue →
  slack automaticamente). Rejeitei isso porque numa empresa de verdade
  ninguém deveria deixar um agente notificar diretoria sem um humano
  revisar antes. Pedi para separar em 3 scripts independentes.
- **Regras de priorização (só CRITICAL/HIGH abrem issue)**: o agente
  originalmente sugeriu abrir issue para qualquer achado. Decidi limitar
  a CRITICAL/HIGH para não gerar ruído — isso é uma decisão de processo,
  não técnica, e documentei o porquê em `docs/processo-mapeado.md`.
- **Padrões de detecção de segredo**: reduzi a lista de regex que o
  agente propôs inicialmente (tinha ~20 padrões, vários com alto risco
  de falso-positivo tipo "qualquer string de 8+ caracteres perto da
  palavra 'key'"). Fiquei só com os 7 padrões mais precisos.
- **O script de auditoria (`validation/audit_findings.py`) foi escrito
  para NÃO reaproveitar a lógica de `scan.py`**: pedi isso explicitamente
  ao agente. Se a auditoria chamasse as mesmas funções do scan original,
  um bug no scan nunca seria pego pela auditoria. Por isso ela reconsulta
  o OSV.dev de forma independente e usa SQL puro em vez de reusar
  `storage.py` para as checagens de negócio.
- **Modo `--dry-run`**: adicionei manualmente em `prioritize.py` e
  `notify_slack.py` depois que percebi que eu precisava de um jeito de
  testar o pipeline inteiro sem realmente abrir issues/mandar mensagens
  — importante tanto para desenvolvimento quanto para rodar em CI de PR
  (sem poluir o Slack a cada commit de teste).

## Limitação conhecida, deixada de propósito

- O agente não faz correção automática (não sobe versão de dependência,
  não remove segredo do código). Decisão consciente: isso exige contexto
  de negócio que o agente não tem (será que dá pra atualizar sem quebrar
  algo?). Prefiro um agente que erra por falta de ação a um que erra por
  excesso de autonomia numa mudança que pode quebrar produção.
