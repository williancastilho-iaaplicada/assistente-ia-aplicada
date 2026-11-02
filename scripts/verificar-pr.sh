#!/usr/bin/env bash
# 🇧🇷 Roda a verificação do resumo de negócio no PR e grava o resultado como status "business-summary" (sem GitHub Actions).
# 🇺🇸 Runs the business summary check on the PR and records it as the "business-summary" status (no GitHub Actions).
# Uso / Usage: scripts/verificar-pr.sh <numero-do-pr>   (rode de novo após editar o PR / run again after editing the PR)
set -euo pipefail
source "$(dirname "$0")/_projeto.sh"
N="${1:?número do PR / PR number}"
SHA="$(gh pr view "$N" --repo "$OWNER/$REPO" --json headRefOid --jq .headRefOid)"
URL="$(gh pr view "$N" --repo "$OWNER/$REPO" --json url --jq .url)"
if OUT="$(gh pr view "$N" --repo "$OWNER/$REPO" --json body --jq .body | python3 "$ROOT/scripts/verificar-resumo.py")"; then
  STATE=success; DESC="Resumo de negócio OK / Business summary OK"; RC=0
else
  STATE=failure; DESC="$(printf '%s' "$OUT" | head -1 | sed 's/^❌ //')"; RC=1
fi
gh api -X POST "repos/$OWNER/$REPO/statuses/$SHA" -f state="$STATE" -f context=business-summary \
  -f description="$DESC" -f target_url="$URL" >/dev/null
echo "$OUT"
echo "==> business-summary: $STATE"
exit "$RC"
