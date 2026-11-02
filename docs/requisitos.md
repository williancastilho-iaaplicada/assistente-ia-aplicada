# Requisitos / Requirements

## 🇧🇷 Português

### Objetivo
Validar um assistente de atendimento no WhatsApp para o Willian Castilho · IA Aplicada, operado no número do parceiro de lançamento (Guilherme), antes de migrar para a API oficial da Meta.

### V1 (validação)
- Atender em texto, seguindo `prompt/ChatBot.md` e a base de conhecimento privada.
- Áudio recebido é transcrito; a resposta é sempre em texto (sem voz, sem clonagem).
- Explicar a ementa em texto (não há PDF).
- Agenda real ainda não existe: coletar e-mail, confirmar telefone e preferência de dia e período, e avisar o Willian com o resumo interno. Nunca inventar horários.
- Encaminhar ao Willian quando pedirem humano, com pausa do bot para aquele contato.
- Modo `self_only` para teste no número pessoal do Willian e modo `all` para o número do cliente.
- Conexão por página de QR Code com link secreto, sem número fixo no código.
- Ignorar grupos, status e listas; não marcar mensagens como lidas; não guardar o conteúdo das mensagens.
- Tudo em contêineres separados no projeto `chatbot` do Easypanel.

### Fora da V1
Agenda integrada (Google Calendar ou Cal.com), lembretes e retomadas automáticas, envio de PDF, API oficial do WhatsApp, subdomínios próprios.

---

## 🇺🇸 English

### Goal
Validate a WhatsApp assistant for Willian Castilho · IA Aplicada, running on the launch partner's (Guilherme) number, before moving to the official Meta API.

### V1
Text replies following `prompt/ChatBot.md` and the private knowledge base; audio transcribed, replies always text; syllabus explained in text; no real calendar yet (collect email, phone and day/period preference, notify Willian, never invent times); human hand-off with per-contact pause; `self_only` and `all` modes; QR Code page with a secret link and no hardcoded number; groups, status and broadcasts ignored, no read receipts, no message storage; everything in separate containers in the `chatbot` Easypanel project.

### Out of V1
Calendar integration, reminders and follow-ups, PDF sending, official WhatsApp API, custom subdomains.
