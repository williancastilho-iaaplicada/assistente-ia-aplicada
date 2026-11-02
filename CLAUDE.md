# Regras do projeto / Project rules

> 🇧🇷 Este arquivo é lido pelo Claude em toda sessão. Vale para todo trabalho neste repositório.
> 🇺🇸 Claude reads this file in every session. It applies to all work in this repository.

## 🇧🇷 Português

### Quem é quem
- **Willian** é o dono do projeto. Ele aprova tudo pelo celular (app Claude + GitHub Mobile).
- **Claude** executa tudo: código, docs, issues, PRs. O Willian só fornece acessos e decide.

### Regras de ouro
1. **Nunca** fazer commit ou push direto na `main`. Todo trabalho vai numa branch e vira PR.
2. **Nunca** fazer merge de PR. Quem faz o merge é o Willian, depois de revisar.
3. **Tudo que vai pro GitHub é bilíngue**: primeiro PT-BR, depois EN (docs, README, PRs, issues, specs, planos). Código e nomes de variáveis em inglês; comentários de código em inglês.
4. **Todo PR** usa `.github/pull_request_template.md` e termina com o **Resumo para o negócio** em linguagem não técnica, com todos os itens de confirmação marcados de verdade (só marque o que conferiu).
5. **Backlog sempre atualizado** no GitHub Projects (ver skill `backlog`): o que foi feito, o que está em andamento e os próximos passos.
6. Nunca versionar segredos (`.env`, chaves, tokens). Usar `.env.example`.
7. Antes de algo destrutivo ou difícil de desfazer, explicar e pedir ok.

### Fluxo de trabalho (Superpowers)
1. **Ideia nova ou mudança grande** → skill `superpowers:brainstorming` (perguntas uma de cada vez). Resultado salvo em `docs/superpowers/specs/AAAA-MM-DD-<tema>.md` (bilíngue).
2. **Plano** → `superpowers:writing-plans`. Salvo em `docs/superpowers/plans/`. Cada tarefa do plano vira uma issue no backlog (`scripts/tarefa.sh`).
3. **Execução** → branch `tipo/<issue>-<resumo>` (ex.: `feat/12-login`), `superpowers:subagent-driven-development` ou `executing-plans`, com TDD (`superpowers:test-driven-development`).
4. **Revisão** → `superpowers:requesting-code-review` antes de abrir o PR, e `superpowers:verification-before-completion` antes de dizer que terminou.
5. **PR** → skill `abrir-pr`. Mover a issue para "In Progress" ao começar; o PR fecha a issue com `Closes #N` e o GitHub move para "Done" no merge.
6. Decisões importantes → `docs/decisoes/NNNN-titulo.md` (bilíngue).

### Comunicação com o Willian
- Português, direto, sem jargão quando o assunto for negócio.
- Ao terminar algo, mandar o link do PR e um resumo de 3 linhas.

---

## 🇺🇸 English

### Who is who
- **Willian** owns the project. He approves everything from his phone (Claude app + GitHub Mobile).
- **Claude** does all the work: code, docs, issues, PRs. Willian only provides access and makes decisions.

### Golden rules
1. **Never** commit or push directly to `main`. All work goes on a branch and becomes a PR.
2. **Never** merge a PR. Willian merges after reviewing.
3. **Everything on GitHub is bilingual**: PT-BR first, then EN (docs, README, PRs, issues, specs, plans). Code and identifiers in English; code comments in English.
4. **Every PR** uses `.github/pull_request_template.md` and ends with the **Business summary** in non-technical language, with every confirmation item truly checked (only check what you verified).
5. **Backlog always up to date** in GitHub Projects (see the `backlog` skill): what is done, what is in progress, and next steps.
6. Never commit secrets (`.env`, keys, tokens). Use `.env.example`.
7. Before anything destructive or hard to undo, explain and ask for approval.

### Workflow (Superpowers)
1. **New idea or big change** → `superpowers:brainstorming` (one question at a time). Output saved in `docs/superpowers/specs/YYYY-MM-DD-<topic>.md` (bilingual).
2. **Plan** → `superpowers:writing-plans`. Saved in `docs/superpowers/plans/`. Each plan task becomes a backlog issue (`scripts/tarefa.sh`).
3. **Execution** → branch `type/<issue>-<summary>` (e.g. `feat/12-login`), `superpowers:subagent-driven-development` or `executing-plans`, with TDD (`superpowers:test-driven-development`).
4. **Review** → `superpowers:requesting-code-review` before opening the PR, and `superpowers:verification-before-completion` before claiming it is done.
5. **PR** → `abrir-pr` skill. Move the issue to "In Progress" when starting; the PR closes the issue with `Closes #N` and GitHub moves it to "Done" on merge.
6. Important decisions → `docs/decisoes/NNNN-title.md` (bilingual).

### Talking to Willian
- Portuguese, direct, no jargon on business topics.
- When something is done, send the PR link and a 3-line summary.
