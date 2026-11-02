# Operação e continuidade / Operations and continuity

## 🇧🇷 Português

### Como retomar pelo celular
1. App Claude → aba Code → ambiente `srv2120199` (a VPS) → sessão na pasta `~/projetos/assistente-ia-aplicada`.
2. Peça, por exemplo: "Qual o status do assistente?", "Troca o modo para all", "Mostra os últimos leads", "Ajusta o roteiro para…".
3. Acompanhe no GitHub Mobile o board e os PRs (resumo de negócio no fim de cada PR).

### Links
- n8n: https://chatbot-n8n.fakvga.easypanel.host
- Evolution API: https://chatbot-evolution.fakvga.easypanel.host (pede a chave)
- Página de conexão por QR Code: `https://chatbot-n8n.fakvga.easypanel.host/webhook/conectar?t=<QR_PAGE_TOKEN>`. O token fica só no `.env` da VPS; peça o link ao Claude.

### Tarefas do dia a dia (na VPS)
| O que | Como |
|---|---|
| Ver o modo | `docker exec $(docker ps -qf name=chatbot_db) psql -U postgres -d chatbot -c "select * from config"` |
| Mudar para cliente | `... -c "update config set valor='all' where chave='modo'"` |
| Voltar para teste | `... -c "update config set valor='self_only' where chave='modo'"` |
| Avisos para outro número | `... -c "update config set valor='55DDNUMERO' where chave='notificar_numero'"` (vazio = o próprio número conectado) |
| Devolver um contato ao bot | Mande `#bot` na conversa com ele (modo `all`) |
| Mudar o roteiro | Edite `prompt/` ou a base privada e rode `n8n/publicar.sh` |
| Testar filtros sem WhatsApp | `testes/simular.sh <jid> <fromMe> <id> "<texto>"` |

O modo é lido a cada mensagem: muda na hora, sem reiniciar nada.

### Trocar de número (ex.: Guilherme)
1. Abra a página de conexão. Se houver um número conectado, clique em "Desconectar / trocar número".
2. No celular novo: WhatsApp → Configurações → Dispositivos conectados → Conectar dispositivo → aponte para o QR Code.
3. Ajuste o modo (`all` para atender todo mundo) e, se quiser, `notificar_numero`.

### Arquivos privados (fora do git, só na VPS)
- `~/projetos/chatbot-infra/.env`: senhas e chaves.
- `~/projetos/chatbot-infra/conhecimento/base_conhecimento.md`: base de conhecimento.
- `~/projetos/chatbot-infra/n8n/workflows/`: fluxos gerados (incluem a base).

### Riscos conhecidos
- WhatsApp não oficial: o número pode ser bloqueado pelo WhatsApp. Use para validação; a API oficial fica para depois.
- Saldo das APIs: Anthropic e OpenAI são pagas por uso. Configure limites de gasto nos painéis.

---

## 🇺🇸 English

### Resuming from the phone
Claude app → Code tab → `srv2120199` environment → session in `~/projetos/assistente-ia-aplicada`. Ask in plain language ("assistant status?", "switch mode to all", "show latest leads"). Follow the board and PRs in GitHub Mobile.

### Links
n8n and Evolution URLs above. The QR Code page URL needs `QR_PAGE_TOKEN`, which lives only in the VPS `.env`; ask Claude for the link.

### Daily tasks
Mode, notification number and `#bot` hand-back are described in the table above. The mode is read on every message, so changes apply immediately. Prompt changes: edit `prompt/` or the private base and run `n8n/publicar.sh`.

### Changing numbers
Open the QR Code page, disconnect the current number if any, scan with the new phone, then set the mode.

### Private files (VPS only)
`.env`, the knowledge base and the generated workflows (which embed the base) never go to git.

### Known risks
Unofficial WhatsApp may get the number banned; API usage is pay-as-you-go, so set spending limits.
