#!/usr/bin/env bash
# 🇧🇷 Envia eventos falsos da Evolution para o webhook do n8n, para testar filtros sem WhatsApp conectado.
# 🇺🇸 Posts fake Evolution events to the n8n webhook to test filters without a connected WhatsApp.
# Uso / Usage: testes/simular.sh <remoteJid> <fromMe 0|1> <id> "<texto>" [sender]
set -euo pipefail
set -a; . "$HOME/projetos/chatbot-infra/.env"; set +a
URL="${WEBHOOK_URL:-https://chatbot-n8n.fakvga.easypanel.host/webhook/evolution-entrada}"
BODY="$(python3 - "$@" <<'PY'
import json, sys
jid, from_me, mid, text = sys.argv[1:5]
sender = sys.argv[5] if len(sys.argv) > 5 else "5500000000001@s.whatsapp.net"
print(json.dumps({"event": "messages.upsert", "instance": "atendimento", "sender": sender,
                  "data": {"key": {"remoteJid": jid, "fromMe": from_me == "1", "id": mid},
                           "pushName": "Teste", "message": {"conversation": text}}}))
PY
)"
curl -s -X POST "$URL" -H "Content-Type: application/json" -H "x-webhook-secret: $WEBHOOK_SECRET" -d "$BODY"
echo
