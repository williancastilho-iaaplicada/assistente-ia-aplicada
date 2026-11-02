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
| Ver o modo | `docker exec $(docker ps -qf "name=^chatbot_db\.") psql -U postgres -d chatbot -c "select * from config"` |
| Mudar para cliente | `... -c "update config set valor='all' where chave='modo'"` |
| Voltar para teste | `... -c "update config set valor='self_only' where chave='modo'"` |
| Avisos para outro número | `... -c "update config set valor='55DDNUMERO' where chave='notificar_numero'"` (vazio = o próprio número conectado) |
| Devolver um contato ao bot | Mande `#bot` na conversa com ele (modo `all`) |
| Mudar o roteiro | Edite `prompt/` ou a base privada e rode `n8n/publicar.sh` |
| Testar filtros sem WhatsApp | `testes/simular.sh <jid> <fromMe> <id> "<texto>"` |

O modo é lido a cada mensagem: muda na hora, sem reiniciar nada.

### Agenda (Cal.com)
- O bot lê os horários livres do Cal.com (que já desconta os compromissos do seu Google Calendar), oferece até 3 opções e reserva, remarca ou cancela pelo WhatsApp. O Cal.com envia o convite e cria o evento no Google Calendar.
- Seus horários de atendimento, antecedência mínima, intervalo entre reuniões e limite de dias ficam no Cal.com: Disponibilidade e aba Limites do evento.
- O evento usado é o da chave `calcom_evento` na tabela `config` (padrão `30min`).
- Sem e-mail do contato, a reserva usa o endereço da chave `email_sem_convite` (tabela `config`) e o link vai na conversa.
- Lembretes automáticos (fluxo "Lembretes de encontro", a cada 5 minutos): às 8h do dia pedindo confirmação de presença, 1 hora antes para se preparar e 15 minutos antes com o link. Antes de cada envio o fluxo confere no Cal.com se a reserva continua ativa e no mesmo horário; lembrete atrasado não é enviado.
- A chave fica em `CALCOM_API_KEY` no `.env` da VPS. Para trocar: `~/projetos/chatbot-infra/salvar-chave.sh CALCOM_API_KEY` e depois `python3 infra/deploy.py update-n8n`.

### Trocar de número (ex.: Guilherme)
1. Abra a página de conexão. Se houver um número conectado, clique em "Desconectar / trocar número".
2. No celular novo: WhatsApp → Configurações → Dispositivos conectados → Conectar dispositivo → aponte para o QR Code.
3. Ajuste o modo (`all` para atender todo mundo) e, se quiser, `notificar_numero`.

### Arquivos privados (fora do git, só na VPS)
- `~/projetos/chatbot-infra/.env`: senhas e chaves.
- `~/projetos/chatbot-infra/conhecimento/base_conhecimento.md`: base de conhecimento.
- `~/projetos/chatbot-infra/n8n/workflows/`: fluxos gerados (incluem a base).

### Dados dos leads e briefing
- Banco Postgres na VPS (`chatbot`): tabela `leads` (cadastro, reserva, lembretes) e tabela `mensagens` (conversa completa, dos dois lados, inclusive lembretes).
- Para ver pelo navegador: Easypanel → projeto `chatbot` → serviço `db` → botão DbGate. Dá para filtrar e exportar.
- Briefing por e-mail (fluxo "Briefing por e-mail", a cada 5 minutos): um e-mail quando a reunião é marcada e outro 1 hora antes, com resumo feito pela IA, cadastro, link e conversa completa. O destinatário é a chave `email_briefing` da tabela `config`; o envio usa o Gmail (`GMAIL_USER` e `GMAIL_APP_PASSWORD` no `.env`, depois `python3 infra/deploy.py update-n8n`).

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

### Scheduling (Cal.com)
The bot reads free slots from Cal.com (which already excludes Google Calendar events), offers up to 3 options and books, reschedules or cancels over WhatsApp; Cal.com sends the invite and creates the Google Calendar event. Hours, notice, buffers and booking window are set in Cal.com. Without an email, bookings use `email_sem_convite` from `config` and the link goes to the chat. Reminders run every 5 minutes: 8am on the day (attendance confirmation), 1 hour before (prep) and 15 minutes before (link), each checked against Cal.com first; late reminders are skipped. The event slug is `calcom_evento` in `config`; the key is `CALCOM_API_KEY` in the VPS `.env`.

### Changing numbers
Open the QR Code page, disconnect the current number if any, scan with the new phone, then set the mode.

### Private files (VPS only)
`.env`, the knowledge base and the generated workflows (which embed the base) never go to git.

### Lead data and briefing
Postgres on the VPS keeps `leads` (profile, booking, reminders) and `mensagens` (full two-sided conversation). Browse it through Easypanel → `chatbot` → `db` → DbGate. A briefing email (AI summary, profile, link, full conversation) goes out when a meeting is booked and 1 hour before; recipient in `config.email_briefing`, sent through Gmail (`GMAIL_USER`, `GMAIL_APP_PASSWORD`).

### Known risks
Unofficial WhatsApp may get the number banned; API usage is pay-as-you-go, so set spending limits.
