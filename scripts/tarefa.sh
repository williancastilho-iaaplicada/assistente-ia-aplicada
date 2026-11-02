#!/usr/bin/env bash
# 🇧🇷 Cria uma issue bilíngue e coloca no backlog (Todo).
# 🇺🇸 Creates a bilingual issue and adds it to the backlog (Todo).
# Uso / Usage: scripts/tarefa.sh "Título PT / Title EN" arquivo-corpo.md [labels]
set -euo pipefail
source "$(dirname "$0")/_projeto.sh"
TITLE="${1:?título / title}"; BODY_FILE="${2:?arquivo do corpo / body file}"; LABELS="${3:-tipo:feature}"
URL="$(gh issue create --repo "$OWNER/$REPO" --title "$TITLE" --body-file "$BODY_FILE" --label "$LABELS")"
set_status "$URL" "Todo"
echo "$URL"
