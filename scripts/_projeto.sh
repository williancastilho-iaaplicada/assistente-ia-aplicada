#!/usr/bin/env bash
# 🇧🇷 Carrega a configuração do projeto (.projeto) e ajuda a achar os IDs do GitHub Projects.
# 🇺🇸 Loads project config (.projeto) and helpers to resolve GitHub Projects IDs.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091
source "$ROOT/.projeto"   # OWNER, REPO, PROJECT_NUMBER

project_id() { gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json --jq .id; }
status_field_json() { gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json --jq '.fields[] | select(.name=="Status")'; }
item_id_for_url() {
  local url="$1"
  gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --limit 500 --format json \
    --jq ".items[] | select(.content.url==\"$url\") | .id"
}
set_status() {  # set_status <issue-or-pr-url> <Todo|In Progress|Done>
  local url="$1" status="$2" item field opt
  item="$(item_id_for_url "$url")"
  [ -z "$item" ] && item="$(gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$url" --format json --jq .id)"
  field="$(status_field_json | jq -r .id)"
  opt="$(status_field_json | jq -r --arg s "$status" '.options[] | select(.name==$s) | .id')"
  [ -z "$opt" ] && { echo "Status '$status' não existe / does not exist"; exit 1; }
  gh project item-edit --id "$item" --project-id "$(project_id)" --field-id "$field" --single-select-option-id "$opt" >/dev/null
  echo "==> $url → $status"
}
