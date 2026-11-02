# Como trabalhar neste projeto / How we work on this project

## 🇧🇷 Português

### Pelo celular (dia a dia)
1. **App Claude → aba Code → ambiente `srv2120199`** (a VPS). Abra uma sessão na pasta deste projeto (`~/projetos/<nome>`).
2. Peça em linguagem normal. Exemplos:
   - "Qual o status do projeto e o que vem agora?"
   - "Pega a próxima tarefa do backlog e faz."
   - "Tive uma ideia nova: … vamos fazer o brainstorm." (o Claude usa o Superpowers e faz uma pergunta por vez)
3. **App GitHub Mobile** para acompanhar:
   - **Board de backlog** (link no README): Todo = próximos passos, In Progress = em andamento/em revisão, Done = feito.
   - **Pull requests**: leia o **Resumo para o negócio** no fim do PR. Se o veredito for 🟢 e a confirmação estiver toda marcada, aprove com **Squash and merge**.
4. Nada entra na `main` sem o seu merge. O merge só é liberado com o status **business-summary ✅** no PR.
5. Se você editar o texto de um PR pelo celular, peça ao Claude: "roda a verificação do PR N". A verificação roda na VPS, não no GitHub Actions.

### Pelo notebook
- `ssh vps` e depois `cc` abre a sessão tmux da VPS. Entre na pasta do projeto e rode `claude`.

### O ciclo de cada entrega
Ideia → brainstorm (spec) → plano → tarefas no board → branch → código com testes → revisão automática → PR com resumo de negócio → **você aprova** → Done.

### Onde fica cada coisa
| Pasta | O que tem |
|---|---|
| `docs/brainstorm.md` | Resultado do brainstorm inicial e o nome |
| `docs/requisitos.md` | O que o produto precisa fazer |
| `docs/arquitetura.md` | Como ele é construído |
| `docs/decisoes/` | Decisões importantes e o porquê |
| `docs/superpowers/specs/` | Especificações de cada funcionalidade |
| `docs/superpowers/plans/` | Planos de execução passo a passo |
| `scripts/` | Automação de backlog e PR |
| `CLAUDE.md` | Regras que o Claude segue neste projeto |

---

## 🇺🇸 English

### From the phone (daily)
1. **Claude app → Code tab → `srv2120199` environment** (the VPS). Open a session in this project's folder (`~/projetos/<name>`).
2. Ask in plain language: "What's the status and what's next?", "Take the next backlog task and do it.", "New idea: … let's brainstorm."
3. **GitHub Mobile**: follow the **backlog board** (link in the README) and review **pull requests** by reading the **Business summary** at the end. If the verdict is 🟢 and every confirmation item is checked, approve with **Squash and merge**.
4. Nothing reaches `main` without your merge, and merge requires the **business-summary ✅** status on the PR.
5. If you edit a PR body from the phone, ask Claude: "run the PR check for PR N". The check runs on the VPS, not on GitHub Actions.

### From the laptop
- `ssh vps`, then `cc` to attach to the VPS tmux session. Go to the project folder and run `claude`.

### Delivery cycle
Idea → brainstorm (spec) → plan → board tasks → branch → tested code → automated review → PR with business summary → **you approve** → Done.

### Where things live
See the table above: brainstorm, requirements, architecture, decisions, specs, plans, scripts, and `CLAUDE.md` (rules Claude follows here).
