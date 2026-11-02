#!/usr/bin/env bash
# 🇧🇷 Publica a branch atual e abre o PR com o corpo já preenchido (seguindo o template).
# 🇺🇸 Pushes the current branch and opens the PR with a filled body (following the template).
# 🇧🇷 No fim roda scripts/verificar-pr.sh (status "business-summary"). / 🇺🇸 Ends by running scripts/verificar-pr.sh.
# Uso / Usage: scripts/abrir-pr.sh "tipo: título PT / title EN" corpo-do-pr.md
set -euo pipefail
source "$(dirname "$0")/_projeto.sh"
TITLE="${1:?título / title}"; BODY_FILE="${2:?arquivo do corpo / body file}"
BRANCH="$(git branch --show-current)"
[ "$BRANCH" = "main" ] && { echo "❌ Não abra PR a partir da main / Do not open a PR from main"; exit 1; }
python3 "$ROOT/scripts/verificar-resumo.py" < "$BODY_FILE" || { echo "❌ Corrija o corpo do PR antes de abrir / Fix the PR body before opening"; exit 1; }
git push -u origin "$BRANCH"
URL="$(gh pr create --repo "$OWNER/$REPO" --base main --head "$BRANCH" --title "$TITLE" --body-file "$BODY_FILE" --assignee "@me")"
gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$URL" >/dev/null || true
set_status "$URL" "In Progress"
echo "$URL"
"$(dirname "$0")/verificar-pr.sh" "${URL##*/}"
