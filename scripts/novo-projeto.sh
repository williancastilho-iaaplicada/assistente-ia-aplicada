#!/usr/bin/env bash
# 🇧🇷 Cria um projeto novo a partir do template: repositório, board de backlog, labels e proteção da main.
# 🇺🇸 Creates a new project from the template: repository, backlog board, labels and main protection.
# Uso / Usage: novo-projeto.sh <nome-do-repo> "<Título do projeto>" [public|private]
set -euo pipefail
NAME="${1:?nome do repo / repo name}"; TITLE="${2:?título / title}"; VIS="${3:-public}"
OWNER="${OWNER:-williancastilho-iaaplicada}"
TEMPLATE="${TEMPLATE:-$OWNER/template-projeto}"
DIR="${PROJETOS_DIR:-$HOME/projetos}/$NAME"

echo "==> Repositório / Repository"
gh repo create "$OWNER/$NAME" --template "$TEMPLATE" --"$VIS" --clone=false
for i in 1 2 3 4 5; do gh api "repos/$OWNER/$NAME/contents/README.md" >/dev/null 2>&1 && break; sleep 3; done
gh repo clone "$OWNER/$NAME" "$DIR"
cd "$DIR"

echo "==> Board de backlog / Backlog board"
PNUM="$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq .number)"
gh project link "$PNUM" --owner "$OWNER" --repo "$OWNER/$NAME"
PURL="https://github.com/users/$OWNER/projects/$PNUM"

echo "==> Labels"
while IFS='|' read -r n c d; do
  gh label create "$n" --repo "$OWNER/$NAME" --color "$c" --description "$d" --force >/dev/null
done <<'L'
tipo:feature|1f883d|Funcionalidade / Feature
tipo:bug|d73a4a|Erro / Bug
tipo:docs|0075ca|Documentação / Documentation
tipo:chore|cfd3d7|Manutenção / Maintenance
tipo:spec|5319e7|Especificação ou plano / Spec or plan
prioridade:alta|b60205|Prioridade alta / High priority
prioridade:media|fbca04|Prioridade média / Medium priority
prioridade:baixa|0e8a16|Prioridade baixa / Low priority
bloqueado|000000|Bloqueado, depende de algo / Blocked
decisao-willian|ff5b00|Precisa de decisão do Willian / Needs Willian's decision
L

echo "==> Configuração local / Local config"
printf 'OWNER=%s\nREPO=%s\nPROJECT_NUMBER=%s\nPROJECT_URL=%s\n' "$OWNER" "$NAME" "$PNUM" "$PURL" > .projeto
sed -i "s|{{NOME_DO_PROJETO}}|$TITLE|g; s|{{LINK_DO_PROJECT}}|$PURL|g" README.md
chmod +x scripts/*.sh
git add -A && git commit -qm "chore: bootstrap do projeto / project bootstrap" && git push -q origin main

echo "==> Configurações do repo / Repo settings"
gh repo edit "$OWNER/$NAME" --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false \
  --delete-branch-on-merge --enable-auto-merge=false >/dev/null
# 🇧🇷 Main protegida: só entra via PR, com a verificação do resumo de negócio passando.
# 🇺🇸 Protected main: changes only via PR, with the business summary check passing.
if gh api -X POST "repos/$OWNER/$NAME/rulesets" --input - >/dev/null 2>&1 <<'J'
{"name":"main protegida / protected main","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
 "rules":[{"type":"deletion"},{"type":"non_fast_forward"},
  {"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,
   "require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},
  {"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,
   "required_status_checks":[{"context":"business-summary"}]}}]}
J
then echo "    main protegida / main protected"
else echo "    ⚠️ Proteção indisponível (repo privado no plano Free). A regra do CLAUDE.md continua valendo. / Protection unavailable on private Free repos."
fi

echo
echo "✅ Pronto / Done"
echo "   Repo:    https://github.com/$OWNER/$NAME"
echo "   Board:   $PURL"
echo "   Pasta:   $DIR"
