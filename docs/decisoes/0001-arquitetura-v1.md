# 0001 · Arquitetura da V1 / V1 architecture

## 🇧🇷 Português
**Decisão:** Evolution API v2 + n8n + Postgres (pgvector) + Redis, num projeto isolado do Easypanel; Claude no agente e Whisper só para transcrição.

**Por quê:**
- Evolution API é open source completa e envia mídia sem plano pago.
- Sem voz na V1: o Piper TTS sai.
- A base de conhecimento cabe no prompt com cache; pgvector fica disponível se crescer.
- O Easypanel já entrega HTTPS e subdomínio, então o Cloudflare Tunnel não é necessário.
- Uma instância só (`atendimento`) com o modo numa tabela (`self_only`/`all`): trocar de teste para cliente não exige mudar código.

**Consequências:** WhatsApp não oficial pode bloquear o número; a migração para a API oficial troca só a entrada e a saída do fluxo.

## 🇺🇸 English
**Decision:** Evolution API v2 + n8n + Postgres (pgvector) + Redis in an isolated Easypanel project; Claude as the agent, Whisper only for transcription.

**Why:** Evolution is fully open source; no voice in V1; the knowledge base fits in a cached prompt; Easypanel provides HTTPS; a single instance with the mode in a table means switching from test to client needs no code change.

**Consequences:** unofficial WhatsApp may ban the number; moving to the official API only replaces the flow's input and output.
