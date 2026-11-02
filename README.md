# Assistente IA Aplicada

> 🇧🇷 Assistente de atendimento no WhatsApp do Willian Castilho · IA Aplicada: orienta, explica o método e a ementa e encaminha o encontro gratuito de 30 minutos.
> 🇺🇸 WhatsApp assistant for Willian Castilho · IA Aplicada: guides leads, explains the method and syllabus, and routes the free 30-minute meeting.

[📋 Backlog / Board](https://github.com/users/williancastilho-iaaplicada/projects/4) · [🧠 Brainstorm](docs/brainstorm.md) · [📐 Requisitos / Requirements](docs/requisitos.md) · [🏗️ Arquitetura / Architecture](docs/arquitetura.md) · [🛠️ Operação / Operations](docs/operacao.md) · [📱 Como trabalhar / How we work](docs/como-trabalhar.md)

---

## 🇧🇷 Português

### O que é
Um agente de IA que atende no WhatsApp em texto, seguindo o roteiro aprovado (`prompt/ChatBot.md`) e uma base de conhecimento privada. Ele entende áudio, guarda o perfil do lead, explica a ementa e avisa o Willian quando alguém quer conversar ou marcar o encontro. Esta é a versão de validação, com WhatsApp não oficial (Evolution API); a API oficial da Meta vem depois.

### Status
O andamento em tempo real fica no **[Backlog do GitHub Projects](https://github.com/users/williancastilho-iaaplicada/projects/4)**:
- **Todo**: próximos passos
- **In Progress**: em andamento (com PR aberto quando estiver em revisão)
- **Done**: concluído

### Como rodar
Tudo roda na VPS, no projeto `chatbot` do Easypanel. Passo a passo em [docs/operacao.md](docs/operacao.md):
1. `python3 infra/deploy.py create` cria os serviços (uma vez).
2. `infra/schema.sql` cria as tabelas.
3. `n8n/publicar.sh` gera e publica os fluxos.
4. Conecte o WhatsApp pela página de QR Code.

---

## 🇺🇸 English

### What it is
An AI agent that answers on WhatsApp in text, following the approved script (`prompt/ChatBot.md`) and a private knowledge base. It understands audio, stores the lead profile, explains the syllabus and notifies Willian when someone wants to talk or book the meeting. This is the validation version using unofficial WhatsApp (Evolution API); the official Meta API comes later.

### Status
Real-time progress lives in the **[GitHub Projects backlog](https://github.com/users/williancastilho-iaaplicada/projects/4)**: Todo, In Progress, Done.

### How to run
Everything runs on the VPS in the `chatbot` Easypanel project. See [docs/operacao.md](docs/operacao.md): `python3 infra/deploy.py create`, apply `infra/schema.sql`, run `n8n/publicar.sh`, then connect WhatsApp through the QR Code page.
