#!/usr/bin/env bash
# 🇧🇷 Gera os fluxos (com a base privada), importa no n8n, publica e reinicia o serviço.
# 🇺🇸 Generates the workflows (with the private knowledge base), imports them into n8n, publishes and restarts.
# Uso / Usage: n8n/publicar.sh   (na VPS / on the VPS)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${FLUXOS_DIR:-$HOME/projetos/chatbot-infra/n8n/workflows}"
python3 "$HERE/gerar_workflows.py" "$OUT"
C="$(docker ps -qf name=chatbot_n8n)"
docker exec "$C" mkdir -p /tmp/imp
for f in "$OUT"/*.json; do docker cp "$f" "$C:/tmp/imp/"; done
for f in "$OUT"/*.json; do
  docker exec "$C" n8n import:workflow --input="/tmp/imp/$(basename "$f")" | tail -1
  id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$f")"
  docker exec "$C" n8n publish:workflow --id="$id" | tail -1
done
docker exec "$C" rm -rf /tmp/imp
docker service update --force chatbot_n8n >/dev/null
echo "==> n8n reiniciado / restarted"
