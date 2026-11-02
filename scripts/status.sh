#!/usr/bin/env bash
# 🇧🇷 Move uma issue/PR no board. / 🇺🇸 Moves an issue/PR on the board.
# Uso / Usage: scripts/status.sh <numero-da-issue> "Todo|In Progress|Done"
set -euo pipefail
source "$(dirname "$0")/_projeto.sh"
N="${1:?número / number}"; S="${2:?status}"
set_status "https://github.com/$OWNER/$REPO/issues/$N" "$S"
