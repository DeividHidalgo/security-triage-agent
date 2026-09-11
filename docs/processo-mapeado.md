# Processo mapeado: triagem de vulnerabilidades de segurança

Antes de escrever qualquer linha de código, mapeei como esse processo
normalmente funciona num time de segurança/engenharia, para o agente
automatizar a coisa certa — não só "gerar código".

## Como funciona hoje (processo manual típico)

1. **Gatilho**: alguém (dev, scanner de CI, ferramenta tipo Dependabot)
   identifica uma dependência desatualizada ou um segredo commitado.
2. **Triagem**: um engenheiro de segurança verifica se a vulnerabilidade
   é real e se aplica ao contexto do projeto (nem todo CVE de uma lib é
   explorável no jeito que a lib é usada).
3. **Priorização**: severidade + exposição (está em produção? é
   internet-facing?) definem se vira P0 (corrige hoje) ou entra no backlog.
4. **Ação**: abre-se um ticket/issue, atribui-se a um responsável, define-se
   prazo (SLA) proporcional à severidade.
5. **Comunicação**: para itens críticos, alguém do time de segurança avisa
   a liderança — em linguagem de risco/negócio, não em CVE/CVSS.
6. **Fechamento**: a correção é validada (a vulnerabilidade não está mais
   presente) antes de fechar o ticket.

## Onde o agente entra

O agente automatiza os passos 1–3 e parte do 4 e 5:
- Gatilho: `agent/scan.py`, rodado a cada push (`.github/workflows/security-scan.yml`)
- Triagem: consulta o OSV.dev (base pública de vulnerabilidades) em vez de
  confiar em heurística própria
- Priorização: `agent/prioritize.py` — regra: CRITICAL/HIGH abrem issue
  automaticamente, MEDIUM/LOW só entram no resumo
- Ação: abre issue no GitHub com o contexto já preenchido
- Comunicação: `agent/notify_slack.py` gera o resumo em linguagem executiva

## Onde o agente **não** entra (decisão consciente)

- O agente não decide se um achado é falso-positivo — isso fica para quem
  revisa a issue.
- O agente não corrige o código sozinho (não faz bump de versão nem remove
  o segredo) — corrigir requer contexto de negócio (será que dá pra
  atualizar a lib sem quebrar algo?) que o agente não tem.
- O passo 6 (validar que a correção realmente resolveu) é manual, por design.

## Critérios de priorização usados

| Severidade | Ação automática | Racional |
|---|---|---|
| CRITICAL | Abre issue automaticamente | Risco de exploração imediata |
| HIGH | Abre issue automaticamente | Risco relevante, mas não crítico |
| MEDIUM | Aparece só no resumo | Evita ruído de issue para itens de baixo risco imediato |
| LOW | Aparece só no resumo | Idem |
