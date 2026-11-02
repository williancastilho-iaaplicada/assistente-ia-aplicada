# Brainstorm / Brainstorm

## 🇧🇷 Português

- **Nome:** Assistente IA Aplicada (`assistente-ia-aplicada`).
- **Problema:** responder rápido e bem quem chega pelo WhatsApp no lançamento, sem perder contexto nem prometer o que não existe.
- **Público:** profissionais e empresas interessados em aplicar IA; o número é do parceiro de lançamento.
- **MVP:** atendimento em texto com roteiro aprovado, ementa em texto, coleta de dados e aviso ao Willian para marcar o encontro gratuito de 30 minutos.
- **Arquitetura avaliada:** a proposta original tinha WAHA, n8n, Postgres, Redis, Piper TTS e Qdrant. Simplificamos para Evolution API + n8n + Postgres (pgvector) + Redis: sem voz na V1, Qdrant substituído por pgvector (ou prompt direto com cache), HTTPS pelo Easypanel em vez de Cloudflare Tunnel. Ver `docs/decisoes/0001-arquitetura-v1.md`.
- **Riscos:** bloqueio do número por usar WhatsApp não oficial; custo das APIs (limites configurados nos painéis).
- **Como saber que deu certo:** os cenários da seção 14 do `prompt/ChatBot.md` passam no teste com o número pessoal e depois no número do cliente.

---

## 🇺🇸 English

- **Name:** Assistente IA Aplicada.
- **Problem:** answer launch leads on WhatsApp quickly and well, keeping context and never promising what does not exist.
- **MVP:** text assistant with an approved script, syllabus in text, lead data collection and a notification to Willian to book the free 30-minute meeting.
- **Architecture:** simplified from WAHA + n8n + Postgres + Redis + Piper TTS + Qdrant to Evolution API + n8n + Postgres (pgvector) + Redis. See `docs/decisoes/0001-arquitetura-v1.md`.
- **Risks:** number ban (unofficial WhatsApp), API costs.
- **Success:** the scenarios in section 14 of `prompt/ChatBot.md` pass on the personal number and then on the client's number.
