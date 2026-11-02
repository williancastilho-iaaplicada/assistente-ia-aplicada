---
name: backlog
description: Manter o backlog do GitHub Projects atualizado (criar tarefas, mover status, registrar próximos passos). Use ao planejar, começar, terminar ou replanejar trabalho / keep the backlog board up to date.
---

# Backlog (GitHub Projects)

🇧🇷
- O board fica no link `PROJECT_URL` do arquivo `.projeto`. Colunas: **Todo** (próximos passos), **In Progress** (em andamento ou em revisão), **Done** (feito).
- **Criar tarefa**: escreva o corpo bilíngue (Objetivo, Critérios de aceite com `- [ ]`, Contexto) num arquivo e rode `scripts/tarefa.sh "Título PT / Title EN" corpo.md "tipo:feature,prioridade:media"`.
- **Começar tarefa**: `scripts/status.sh <N> "In Progress"` e crie a branch `tipo/<N>-<resumo>`.
- **Terminar**: o PR com `Closes #N` leva a issue para "Done" quando o Willian fizer o merge.
- **Depois de cada plano** (`superpowers:writing-plans`): cada tarefa do plano vira uma issue, com link para o arquivo do plano.
- **Precisa de decisão do Willian?** Label `decisao-willian` e explique as opções na issue, recomendando uma.
- Ao fim de cada sessão de trabalho, confira se o board reflete a realidade.

🇺🇸
- Board URL is `PROJECT_URL` in `.projeto`. Columns: **Todo** (next steps), **In Progress** (in progress or in review), **Done**.
- Create a task with `scripts/tarefa.sh`, start with `scripts/status.sh <N> "In Progress"` plus a `type/<N>-<summary>` branch, finish via a PR with `Closes #N`.
- Every plan task becomes an issue. Use the `decisao-willian` label when Willian must decide. Keep the board truthful at the end of every session.
