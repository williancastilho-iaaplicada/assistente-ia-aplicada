# Arquitetura / Architecture

## 🇧🇷 Português

### Visão geral
Assistente de atendimento no WhatsApp, rodando inteiro na VPS do Willian, num projeto isolado do Easypanel chamado `chatbot`. São quatro contêineres numa rede interna:

| Serviço | Imagem | Papel | Exposto na internet |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | Bancos `n8n`, `evolution` e `chatbot` (configuração e dados do lead) | Não |
| `redis` | `redis:7-alpine` | Memória curta da conversa, junção de mensagens picadas, anti-loop | Não |
| `evolution` | `evoapicloud/evolution-api:v2.3.7` | Conexão com o WhatsApp por QR Code (não oficial) | Sim, HTTPS, com chave |
| `n8n` | `n8nio/n8n:2.46.4` | Orquestra o fluxo e o agente de IA | Sim, HTTPS |

IA: Claude (Anthropic) responde; OpenAI (Whisper) só transcreve áudio. A resposta é sempre em texto.

### Caminho de uma mensagem
1. A Evolution recebe a mensagem e chama o webhook interno do n8n com um cabeçalho secreto.
2. **Filtrar entrada** descarta tudo que não for conversa individual (grupos, status, listas, canais), mensagens sem texto ou áudio e o eco das respostas do próprio bot.
3. **Aplicar modo** lê o modo na tabela `config`:
   - `self_only` (teste): só a conversa do dono do número com ele mesmo;
   - `all` (cliente): qualquer conversa individual. Se o dono responder um contato manualmente, o bot pausa para esse contato; o dono manda `#bot` na conversa para devolver.
4. Anti-loop: IDs das mensagens enviadas pelo bot ficam no Redis por 1 hora, e toda resposta leva um marcador invisível.
5. Áudio é transcrito. Mensagens picadas chegam juntas: o fluxo espera 6 segundos e responde só à última.
6. O agente (Claude) recebe a base de conhecimento, o roteiro `prompt/ChatBot.md`, as regras de `prompt/operacao.md` e os dados já registrados do lead.
7. A resposta é enviada, os dados do lead são atualizados no Postgres e, quando há pedido de humano ou de encontro, o Willian recebe o resumo interno no WhatsApp.

### Número sem nada fixo no código
O número do dono é lido de cada evento (`sender` da Evolution). Trocar de número é só ler o QR Code de novo na página de conexão.

### Dados e privacidade
- A Evolution não guarda mensagens, contatos, conversas nem histórico.
- O n8n não guarda execuções que deram certo; só as com erro, para diagnóstico.
- O Postgres guarda o perfil do lead e a conversa completa (tabela `mensagens`), para o briefing e consulta do Willian pelo DbGate.
- A memória curta do agente fica no Redis por 7 dias.
- A base de conhecimento fica só na VPS (`~/projetos/chatbot-infra/conhecimento/`), fora do git.
- Segredos ficam só em `~/projetos/chatbot-infra/.env` na VPS. As chaves de IA entram no n8n por `CREDENTIALS_OVERWRITE_DATA` e não aparecem na tela.

### Arquivos deste repositório
| Caminho | O que é |
|---|---|
| `infra/deploy.py` | Cria o projeto no Easypanel pela API (`create`) e atualiza o ambiente do n8n (`update-n8n`) |
| `infra/schema.sql` | Tabelas `config` e `leads` |
| `n8n/gerar_workflows.py` | Gera os fluxos do n8n (atendimento e página de QR Code) |
| `n8n/publicar.sh` | Gera, importa, publica e reinicia o n8n |
| `n8n/credenciais.json` | Credenciais sem segredos (os valores vêm do ambiente) |
| `prompt/` | Roteiro do atendimento e regras de operação |
| `testes/simular.sh` | Simula eventos da Evolution para testar os filtros |

---

## 🇺🇸 English

### Overview
WhatsApp assistant running entirely on Willian's VPS, in an isolated Easypanel project called `chatbot`, with four containers on an internal network: `db` (Postgres with pgvector), `redis` (short-term memory, message batching, anti-loop), `evolution` (unofficial WhatsApp connection via QR Code, HTTPS with API key) and `n8n` (workflow and AI agent, HTTPS). Claude answers; OpenAI Whisper only transcribes audio. Replies are always text.

### Message path
1. Evolution calls the internal n8n webhook with a secret header.
2. Only direct chats with text or audio pass; groups, status, broadcasts, channels and the bot's own echoes are dropped.
3. Mode comes from the `config` table: `self_only` (test, owner's chat with themselves) or `all` (any direct chat; a manual reply by the owner pauses the bot for that contact, `#bot` hands it back).
4. Anti-loop: sent message IDs live in Redis for 1 hour and every reply carries an invisible marker.
5. Audio is transcribed; bursts of messages are batched (6-second wait, only the latest triggers a reply).
6. The Claude agent gets the knowledge base, `prompt/ChatBot.md`, `prompt/operacao.md` and the stored lead data.
7. The reply is sent, the lead profile is updated, and Willian gets an internal summary on human or meeting requests.

### No hardcoded number
The owner's number is read from each event. Changing numbers only requires scanning the QR Code again.

### Data and privacy
Evolution stores no messages, contacts, chats or history; n8n keeps only failed executions; Postgres keeps the lead profile and the full conversation (`mensagens`) for briefings and review via DbGate; the agent short-term memory lives in Redis for 7 days; the knowledge base and all secrets stay on the VPS, outside git.

### Files
See the table above.
