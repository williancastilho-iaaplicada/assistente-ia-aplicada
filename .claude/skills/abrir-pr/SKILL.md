---
name: abrir-pr
description: Abrir pull request neste projeto com o template bilíngue e o resumo de negócio para o Willian aprovar. Use sempre que for publicar trabalho / open a PR.
---

# Abrir PR / Open a PR

🇧🇷 Passo a passo (siga na ordem):
1. Confirme que está numa branch `tipo/<issue>-<resumo>`, nunca na `main`.
2. Rode os testes e verificações do projeto. Use `superpowers:verification-before-completion`. Se algo falhar, conserte antes.
3. Rode `superpowers:requesting-code-review` e resolva o que for relevante.
4. Escreva o corpo do PR num arquivo temporário seguindo `.github/pull_request_template.md`, **sem apagar nenhum título**:
   - Técnico em PT-BR e EN.
   - **Resumo para o negócio** em PT-BR e EN, para alguém que não é técnico: o que aborda, o que foi feito, impacto no projeto, como desfazer.
   - Marque `[x]` só nos itens de confirmação que você realmente conferiu. Se algum não puder ser marcado, explique no Veredito e use 🟡 ou 🔴.
   - `Closes #N` para cada issue resolvida.
5. Título: `tipo: resumo em PT / summary in EN` (Conventional Commits).
6. Rode `scripts/abrir-pr.sh "<título>" <arquivo>`. Ele publica a branch, abre o PR, põe no board como "In Progress" e roda `scripts/verificar-pr.sh`, que grava o status `business-summary` (✅/❌) no PR. A `main` só aceita merge com ✅. Se falhar, corrija o corpo com `gh pr edit <N> --body-file <arquivo>` e rode `scripts/verificar-pr.sh <N>` de novo.
   - Sempre que o corpo do PR for editado (inclusive pelo Willian no celular), rode `scripts/verificar-pr.sh <N>` de novo: a verificação não roda sozinha (não usamos GitHub Actions).
7. Mande ao Willian o link do PR e o resumo de negócio em 3 linhas. **Não faça merge.**

🇺🇸 Same steps in English: be on a feature branch; run tests and `superpowers:verification-before-completion`; run `superpowers:requesting-code-review`; write the PR body from the template keeping every heading, with the business summary in PT-BR and EN and only truly verified items checked; title `type: PT summary / EN summary`; run `scripts/abrir-pr.sh` (it also runs `scripts/verificar-pr.sh`, which sets the required `business-summary` status; rerun it after any PR body edit, since there is no GitHub Actions); send Willian the link and a 3-line business summary. **Never merge.**
