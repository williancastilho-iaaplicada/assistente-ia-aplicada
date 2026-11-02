#!/usr/bin/env python3
"""Generates the n8n workflow JSON files for the WhatsApp assistant.

Usage: python3 gerar_workflows.py <output-dir>
The system prompt is the private knowledge base (outside git, path in BASE_CONHECIMENTO)
plus ../prompt/ChatBot.md and ../prompt/operacao.md.
No secrets live here: they come from n8n env vars and credential overwrites.
The generated JSON embeds the knowledge base, so the output dir must stay out of git.
"""
import json
import os
import pathlib
import sys
import uuid

HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "workflows")
BASE = pathlib.Path(os.environ.get("BASE_CONHECIMENTO", "~/projetos/chatbot-infra/conhecimento/base_conhecimento.md")).expanduser()
if not BASE.is_file():
    sys.exit(f"Base de conhecimento não encontrada / knowledge base not found: {BASE}")
PROMPT = "\n\n---\n\n".join([
    "# Base de conhecimento\n\n" + BASE.read_text(),
    "# Especificação do atendimento\n\n" + (HERE.parent / "prompt" / "ChatBot.md").read_text(),
    (HERE.parent / "prompt" / "operacao.md").read_text(),
])

MODEL = "claude-sonnet-5-5"
DEBOUNCE_SECONDS = 6
MEMORY_TTL_SECONDS = 7 * 24 * 3600
SENT_TTL_SECONDS = 3600
# Invisible marker appended to every bot message, so its own echo is never processed.
MARKER = "⁣"

CRED = {
    "postgres": {"postgres": {"id": "chatbotPostgres01", "name": "Postgres chatbot"}},
    "redis": {"redis": {"id": "chatbotRedis00001", "name": "Redis chatbot"}},
    "anthropic": {"anthropicApi": {"id": "chatbotAnthropic1", "name": "Anthropic chatbot"}},
    "openai": {"openAiApi": {"id": "chatbotOpenAi0001", "name": "OpenAI chatbot"}},
}

EVO_HEADERS = {"parameters": [{"name": "apikey", "value": "={{ $env.EVOLUTION_API_KEY }}"}]}


class Flow:
    def __init__(self, name):
        self.name, self.nodes, self.conn, self.x = name, [], {}, 0

    def add(self, name, type_, version, params, pos=None, creds=None, **extra):
        self.x += 220
        node = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.name + name)), "name": name, "type": type_,
                "typeVersion": version, "position": pos or [self.x, 300], "parameters": params}
        if creds:
            node["credentials"] = creds
        node.update(extra)
        self.nodes.append(node)
        return name

    def link(self, a, b, out=0, kind="main", inp=0):
        outs = self.conn.setdefault(a, {}).setdefault(kind, [])
        while len(outs) <= out:
            outs.append([])
        outs[out].append({"node": b, "type": kind, "index": inp})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def json(self):
        return {"name": self.name, "nodes": self.nodes, "connections": self.conn, "active": False,
                "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "none",
                             "saveManualExecutions": False, "timezone": "America/Sao_Paulo"},
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.name)).replace("-", "")[:16]}


def code(js):
    return {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js}


def sql(query, values):
    return {"operation": "executeQuery", "query": query, "options": {"queryReplacement": values}}


def cond(left, op, right=None, type_="string"):
    c = {"id": str(uuid.uuid4()), "leftValue": left, "operator": {"type": type_, "operation": op}}
    if right is not None:
        c["rightValue"] = right
    if op in ("empty", "notEmpty", "true", "false"):
        c["operator"]["singleValue"] = True
    return {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                           "conditions": [c], "combinator": "and"}, "options": {}}


def evolution_send(number_expr, text_expr):
    return {"method": "POST", "url": "={{ $env.EVOLUTION_URL }}/message/sendText/{{ $('Config').first().json.instancia }}",
            "sendHeaders": True, "headerParameters": EVO_HEADERS, "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ number: " + number_expr + ", text: " + text_expr + " + '" + MARKER + "' }) }}",
            "options": {}}


# ---------------------------------------------------------------- Atendimento
PRE_FILTER = r"""
// Validates the Evolution webhook and keeps only direct-chat messages. Drops everything else.
const MARKER = '⁣';
const out = [];
for (const item of $input.all()) {
  const h = item.json.headers || {};
  if (h['x-webhook-secret'] !== $env.WEBHOOK_SECRET) continue;
  const b = item.json.body || {};
  if (b.event !== 'messages.upsert') continue;
  const d = b.data || {};
  const key = d.key || {};
  const jid = key.remoteJid || '';
  if (!/@(s\.whatsapp\.net|lid)$/.test(jid)) continue; // no groups, status, broadcast, newsletters
  const m = d.message || {};
  const text = m.conversation || (m.extendedTextMessage && m.extendedTextMessage.text) || '';
  const audio = m.audioMessage ? (m.base64 || d.base64 || '') : '';
  if (!text && !audio) continue;
  if (text.endsWith(MARKER)) continue; // the bot's own reply echoing back
  const digits = s => String(s || '').split('@')[0].split(':')[0].replace(/\D/g, '');
  const owner = digits(b.sender);
  const alt = key.remoteJidAlt || key.senderPn || '';
  const selfChat = !!owner && (digits(jid) === owner || (alt && digits(alt) === owner));
  const entry = { json: {
    jid, numero: digits(alt && jid.endsWith('@lid') ? alt : jid), msgId: key.id, fromMe: !!key.fromMe,
    selfChat, owner, nome: d.pushName || '', texto: text, audio: !!audio,
    audioMime: (m.audioMessage && m.audioMessage.mimetype) || 'audio/ogg',
  } };
  if (audio) entry.binary = { data: { data: audio, mimeType: 'audio/ogg', fileName: 'audio.ogg' } };
  out.push(entry);
}
return out;
"""

DECIDE = r"""
// Applies the instance mode. self_only: only the owner's chat with itself. all: any direct chat.
// In "all" mode a manual message from the owner to a contact pauses the bot for that contact;
// the owner sends "#bot" in that chat to hand it back.
const cfg = $('Config').first().json;
const out = [];
for (const item of $('Filtrar entrada').all()) {
  const m = item.json;
  let rota = 'descartar';
  if (cfg.modo === 'self_only') {
    if (m.fromMe && m.selfChat) rota = 'atender';
  } else if (cfg.modo === 'all') {
    if (!m.fromMe || m.selfChat) rota = 'atender';
    else if (m.texto.trim().toLowerCase() === '#bot') rota = 'liberar_humano';
    else rota = 'pausar_humano';
  }
  if (rota !== 'descartar') out.push(item.binary ? { json: { ...m, rota }, binary: item.binary } : { json: { ...m, rota } });
}
return out;
"""

BUILD_INPUT = r"""
// Joins buffered messages and adds the lead context and Willian's free slots (Cal.com) for the agent.
const lead = $('Lead').first().json;
const parts = [].concat($('Ler buffer').first().json.buffer || []).filter(Boolean);
const TZ = 'America/Sao_Paulo';
const agora = new Date().toLocaleString('pt-BR', { timeZone: TZ, dateStyle: 'full', timeStyle: 'short' });
const conhecido = {};
for (const [k, v] of Object.entries(lead)) {
  if (v !== null && v !== '' && !['criado_em', 'atualizado_em', 'atendimento_humano'].includes(k)) conhecido[k] = v;
}
let agenda = 'Agenda indisponível no momento: não ofereça horários; registre a preferência de dia e período.';
let eventTypeId = null;
try {
  const cfg = $('Config').first().json;
  const h = { Authorization: 'Bearer ' + $env.CALCOM_API_KEY };
  const et = await this.helpers.httpRequest({ url: 'https://api.cal.com/v2/event-types',
    headers: { ...h, 'cal-api-version': '2024-06-14' }, json: true });
  const ev = (et.data || []).find(e => e.slug === (cfg.calcom_evento || '30min'));
  if (ev) {
    eventTypeId = ev.id;
    const dia = d => d.toISOString().slice(0, 10);
    const ini = new Date(), fim = new Date(Date.now() + 14 * 864e5);
    const sl = await this.helpers.httpRequest({ url: `https://api.cal.com/v2/slots?eventTypeId=${ev.id}&start=${dia(ini)}&end=${dia(fim)}&timeZone=${TZ}`,
      headers: { ...h, 'cal-api-version': '2024-09-04' }, json: true });
    const linhas = [];
    for (const [d, lista] of Object.entries(sl.data || {}).slice(0, 10)) {
      const hs = lista.map(x => x.start.slice(11, 16));
      const faixas = [];
      for (const hh of hs) {
        const [H, M] = hh.split(':').map(Number);
        const last = faixas[faixas.length - 1];
        const prev = last && last[1].split(':').map(Number);
        if (last && (H * 60 + M) - (prev[0] * 60 + prev[1]) === ev.lengthInMinutes) last[1] = hh;
        else faixas.push([hh, hh]);
      }
      const nomeDia = new Date(d + 'T12:00:00-03:00').toLocaleDateString('pt-BR', { timeZone: TZ, weekday: 'short', day: '2-digit', month: '2-digit' });
      linhas.push(`${nomeDia} (${d}): início às ` + faixas.map(f => f[0] === f[1] ? f[0] : `${f[0]}–${f[1]}`).join(', '));
    }
    agenda = linhas.length
      ? `Horários livres para o encontro de ${ev.lengthInMinutes} min (horário de Brasília; inícios a cada ${ev.lengthInMinutes} min dentro de cada faixa):\n` + linhas.join('\n')
      : 'Sem horários livres nos próximos 14 dias: registre a preferência de dia e período e encaminhe ao Willian.';
  }
} catch (e) {}
const perguntas = { objetivo: 'objetivo principal com IA', experiencia: 'como usa IA hoje', sabe_programar: 'se sabe programar',
  problema: 'atividade repetitiva que mais consome tempo', interesse: 'interesse (mentoria em grupo, 1:1, in-company, implementação ou dúvida)' };
const faltam = Object.keys(perguntas).filter(k => !lead[k]).map(k => perguntas[k]);
const qualif = faltam.length ? `Qualificação pendente, nesta ordem: ${faltam.join('; ')}.` : 'Qualificação completa.';
const emailInfo = lead.email ? '' : (lead.email_solicitado ? 'E-mail já foi pedido uma vez: não peça de novo.' : 'E-mail ainda não foi pedido.');
const texto = `[contexto]\nAgora: ${agora} (horário de Brasília)\nDados registrados do lead: ${JSON.stringify(conhecido)}\n${qualif} ${emailInfo}\n${agenda}\n[/contexto]\n\n${parts.join('\n')}`;
return [{ json: { sessionId: 'mem:' + lead.jid, chatInput: texto, jid: lead.jid, eventTypeId } }];
"""

PARSE_OUTPUT = r"""
// Splits the agent output into the WhatsApp reply and the structured data block.
const raw = String($json.output || '');
const resp = (raw.match(/<resposta>([\s\S]*?)<\/resposta>/) || [])[1];
const dados = (raw.match(/<dados>([\s\S]*?)<\/dados>/) || [])[1];
let parsed = { lead: {}, acao: 'nenhuma' };
try { if (dados) parsed = JSON.parse(dados.trim()); } catch (e) {}
const allowed = ['nome', 'email', 'telefone_preferencial', 'contato_avisos_confirmado', 'perfil', 'objetivo',
  'experiencia', 'problema', 'interesse', 'ementa', 'sabe_programar', 'duvidas_pendentes', 'preferencia_agenda', 'estado',
  'email_solicitado'];
const lead = {};
for (const k of allowed) if (parsed.lead && parsed.lead[k] != null && parsed.lead[k] !== '') lead[k] = String(parsed.lead[k]).slice(0, 500);
const acoes = ['nenhuma', 'encaminhar_humano', 'registrar_preferencia_agenda', 'parar_acompanhamento',
  'reservar', 'remarcar', 'cancelar_reserva'];
const acao = acoes.includes(parsed.acao) ? parsed.acao : 'nenhuma';
if (acao === 'encaminhar_humano') lead.estado = 'atendimento_humano';
if (acao === 'parar_acompanhamento') lead.estado = 'acompanhamento_encerrado';
const resposta = (resp || raw.replace(/<dados>[\s\S]*<\/dados>/, '')).trim();
const inicio = parsed.agenda && parsed.agenda.inicio ? String(parsed.agenda.inicio) : null;
return [{ json: { jid: $('Montar entrada').first().json.jid, resposta, lead, acao, inicio,
  humano: acao === 'encaminhar_humano', parada: acao === 'parar_acompanhamento' } }];
"""

SUMMARY = r"""
// Builds the internal summary for Willian (knowledge base, section 9).
const l = $('Salvar lead').first().json;
const p = $('Executar agenda').first().json;
const v = (x, d = 'não informado') => (x === null || x === undefined || x === '') ? d : x;
const motivos = { encaminhar_humano: 'Pedido de atendimento humano', registrar_preferencia_agenda: 'Pedido de encontro (sem horário reservado)',
  reservar: 'Encontro reservado', remarcar: 'Encontro remarcado', cancelar_reserva: 'Encontro cancelado' };
const motivo = motivos[p.acao] || 'Atualização do atendimento';
const quando = l.reserva_inicio ? new Date(l.reserva_inicio).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';
const texto = [
  `*${motivo}*`,
  `Nome: ${v(l.nome)}`,
  `Perfil: ${v(l.perfil, 'indefinido')}`,
  `E-mail do Convite: ${v(l.email, l.reserva_status === 'reservado' ? 'não informado (link enviado no WhatsApp)' : 'pendente')}`,
  `Telefone WhatsApp: +${v(l.telefone_origem)}${l.telefone_preferencial ? ' (preferencial: ' + l.telefone_preferencial + ')' : ''}`,
  `Objetivo Principal: ${v(l.objetivo)}`,
  `Experiência com IA: ${v(l.experiencia)}`,
  `Sabe Programar?: ${v(l.sabe_programar)}`,
  `Principal Gargalo/Rotina: ${v(l.problema)}`,
  `Interesse Identificado: ${v(l.interesse, 'indefinido')}`,
  `Status da Ementa: ${v(l.ementa, 'não solicitada')}`,
  `Status da Agenda: ${l.reserva_status === 'reservado' ? 'Reservado em ' + quando + (l.reserva_link ? ' · ' + l.reserva_link : '') : l.reserva_status === 'cancelado' ? 'Cancelado' : 'Pendente de horário'}${l.preferencia_agenda ? ' (preferência: ' + l.preferencia_agenda + ')' : ''}`,
  `Próximo Passo: ${p.acao === 'encaminhar_humano' ? 'responder o contato (bot pausado para ele; mande #bot na conversa para devolver)' : (p.acao === 'registrar_preferencia_agenda' ? 'confirmar o horário com o contato' : 'nenhuma ação necessária; o convite saiu pelo Cal.com')}`,
].join('\n');
const cfg = $('Config').first().json;
const destino = cfg.notificar_numero || $('Filtrar entrada').first().json.owner;
return [{ json: { destino, texto } }];
"""


AGENDA = r"""
// Books, reschedules or cancels on Cal.com. Only a confirmed API result produces a confirmation message.
const p = $json;
const out = { ...p, lead: { ...p.lead }, avisar: ['encaminhar_humano', 'registrar_preferencia_agenda'].includes(p.acao) };
const TZ = 'America/Sao_Paulo';
const antes = $('Lead').first().json;
const lead = { ...antes, ...p.lead };
const cfg = $('Config').first().json;
if (!['reservar', 'remarcar', 'cancelar_reserva'].includes(p.acao)) {
  if (p.lead.email && !antes.email && antes.reserva_uid && antes.reserva_status === 'reservado' && new Date(antes.reserva_inicio) > new Date()) {
    try {
      await this.helpers.httpRequest({ method: 'POST', url: `https://api.cal.com/v2/bookings/${antes.reserva_uid}/guests`, json: true,
        headers: { Authorization: 'Bearer ' + $env.CALCOM_API_KEY, 'cal-api-version': '2024-08-13' },
        body: { guests: [{ email: p.lead.email, name: lead.nome || 'Convidado' }] } });
      out.resposta = `${out.resposta}\n\nPronto, enviei o convite do encontro também para ${p.lead.email}.`.trim();
    } catch (e) {}
  }
  return [{ json: out }];
}
const eventTypeId = $('Montar entrada').first().json.eventTypeId;
const h = { Authorization: 'Bearer ' + $env.CALCOM_API_KEY, 'cal-api-version': '2024-08-13' };
const quando = iso => new Date(iso).toLocaleString('pt-BR', { timeZone: TZ, weekday: 'long', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
const falha = 'Não consegui concluir a reserva desse horário. Posso consultar novas opções ou encaminhar seu pedido ao Willian.';
try {
  if (p.acao === 'cancelar_reserva') {
    if (!lead.reserva_uid) throw new Error('sem reserva');
    await this.helpers.httpRequest({ method: 'POST', url: `https://api.cal.com/v2/bookings/${lead.reserva_uid}/cancel`, headers: h,
      body: { cancellationReason: 'Cancelado pelo contato no WhatsApp' }, json: true });
    out.lead.reserva_status = 'cancelado'; out.lead.estado = 'cancelado';
    out.resposta = 'Pronto, cancelei o seu encontro com o Willian. Se quiser marcar outro horário, é só me avisar por aqui.';
    out.avisar = true;
    return [{ json: out }];
  }
  if (!p.inicio || isNaN(new Date(p.inicio))) throw new Error('sem horário');
  const semEmail = !lead.email;
  const emailReserva = lead.email || cfg.email_sem_convite;
  if (!emailReserva) throw new Error('sem e-mail');
  let r;
  if (p.acao === 'remarcar' && lead.reserva_uid && lead.reserva_status === 'reservado') {
    r = await this.helpers.httpRequest({ method: 'POST', url: `https://api.cal.com/v2/bookings/${lead.reserva_uid}/reschedule`, headers: h,
      body: { start: new Date(p.inicio).toISOString(), reschedulingReason: 'Remarcado pelo contato no WhatsApp' }, json: true });
  } else {
    if (lead.reserva_uid && lead.reserva_status === 'reservado' && new Date(lead.reserva_inicio) > new Date()) {
      out.resposta = `Você já tem um encontro marcado para ${quando(lead.reserva_inicio)} (horário de Brasília). Quer remarcar para outro horário?`;
      out.acao = 'nenhuma'; return [{ json: out }];
    }
    const fone = String(lead.telefone_preferencial || lead.telefone_origem || '').replace(/\D/g, '');
    // Name and phone go into the attendee name so they show up in the calendar event title.
    const foneBR = fone.length === 13 && fone.startsWith('55') ? `+55 ${fone.slice(2, 4)} ${fone.slice(4, 9)}-${fone.slice(9)}` : (fone ? '+' + fone : '');
    const nomeTitulo = [lead.nome || 'Contato WhatsApp', foneBR].filter(Boolean).join(' · ');
    r = await this.helpers.httpRequest({ method: 'POST', url: 'https://api.cal.com/v2/bookings', headers: h, json: true, body: {
      start: new Date(p.inicio).toISOString(), eventTypeId,
      attendee: { name: nomeTitulo, email: emailReserva, timeZone: TZ, language: 'pt', ...(fone ? { phoneNumber: '+' + fone } : {}) },
      metadata: { origem: 'whatsapp' } } });
  }
  const b = r.data || {};
  const link = b.meetingUrl || (typeof b.location === 'string' && b.location.startsWith('http') ? b.location : '');
  out.lead.reserva_uid = b.uid; out.lead.reserva_inicio = b.start; out.lead.reserva_status = 'reservado'; out.lead.estado = 'reservado';
  out.lead.reserva_link = link; out.lead.reserva_criada_em = new Date().toISOString();
  if (p.acao === 'reservar' && lead.ementa !== 'enviada' && cfg.ementa_resumo) out.lead.ementa = 'enviada';
  const convite = semEmail ? 'Como não tenho seu e-mail, o acesso fica aqui na conversa' : `o convite foi enviado para ${lead.email}`;
  out.resposta = [
    `Combinado${lead.nome ? ', ' + lead.nome : ''}! ${p.acao === 'remarcar' ? 'Remarquei para' : 'Marcado para'} ${quando(b.start)} (horário de Brasília). Seu encontro com o Willian terá 30 minutos e ${convite}.`,
    link ? `Acesso: ${link}` : 'O link de acesso chega por aqui 15 minutos antes.',
    'No dia, às 8h, eu confirmo sua presença; 1 hora antes, lembro você de se preparar; e 15 minutos antes, envio o link de novo.',
    ...(p.acao === 'reservar' && lead.ementa !== 'enviada' && cfg.ementa_resumo ? [cfg.ementa_resumo] : []),
    'Traga suas dúvidas e uma visão geral da rotina que deseja melhorar. Se precisar remarcar, é só avisar por aqui!',
  ].join('\n\n');
  out.avisar = true;
} catch (e) {
  out.resposta = falha; out.acao = 'nenhuma'; out.avisar = false;
}
return [{ json: out }];
"""

f = Flow("Atendimento WhatsApp")
f.add("Entrada Evolution", "n8n-nodes-base.webhook", 2.1,
      {"httpMethod": "POST", "path": "evolution-entrada", "options": {}}, webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "evolution-entrada")))
f.add("Filtrar entrada", "n8n-nodes-base.code", 2, code(PRE_FILTER))
f.add("Config", "n8n-nodes-base.postgres", 2.8,
      sql("SELECT COALESCE(MAX(valor) FILTER (WHERE chave='modo'),'self_only') AS modo, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='instancia'),'atendimento') AS instancia, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='notificar_numero'),'') AS notificar_numero, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='calcom_evento'),'30min') AS calcom_evento, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='email_sem_convite'),'') AS email_sem_convite, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='ementa_resumo'),'') AS ementa_resumo FROM config", ""),
      creds=CRED["postgres"], executeOnce=True)
f.add("Aplicar modo", "n8n-nodes-base.code", 2, code(DECIDE))
f.add("Atender?", "n8n-nodes-base.if", 2.2, cond("={{ $json.rota }}", "equals", "atender"))
f.add("Pausar ou liberar humano", "n8n-nodes-base.postgres", 2.8,
      sql("INSERT INTO leads (jid, telefone_origem, atendimento_humano, estado) VALUES ($1, $2, $3::boolean, "
          "CASE WHEN $3::boolean THEN 'atendimento_humano' ELSE 'orientacao' END) "
          "ON CONFLICT (jid) DO UPDATE SET atendimento_humano = EXCLUDED.atendimento_humano, "
          "estado = EXCLUDED.estado, atualizado_em = now()",
          "={{ [$json.jid, $json.numero, $json.rota === 'pausar_humano'] }}"),
      creds=CRED["postgres"], pos=[1320, 520])
f.add("Já enviado pelo bot?", "n8n-nodes-base.redis", 1,
      {"operation": "get", "propertyName": "enviadoPeloBot", "key": "=sent:{{ $json.msgId }}", "keyType": "string", "options": {}},
      creds=CRED["redis"])
f.add("Mensagem nova?", "n8n-nodes-base.if", 2.2, cond("={{ $json.enviadoPeloBot }}", "empty"))
f.add("Lead", "n8n-nodes-base.postgres", 2.8,
      sql("INSERT INTO leads (jid, telefone_origem, nome) VALUES ($1, $2, NULLIF($3, '')) "
          "ON CONFLICT (jid) DO UPDATE SET atualizado_em = now() RETURNING *",
          "={{ [$('Aplicar modo').item.json.jid, $('Aplicar modo').item.json.numero, $('Aplicar modo').item.json.nome] }}"),
      creds=CRED["postgres"])
f.add("Bot ativo para o contato?", "n8n-nodes-base.if", 2.2, cond("={{ $json.atendimento_humano }}", "false", type_="boolean"))
f.add("É áudio?", "n8n-nodes-base.if", 2.2, cond("={{ $('Aplicar modo').item.json.audio }}", "true", type_="boolean"))
f.add("Recuperar áudio", "n8n-nodes-base.code", 2,
      code("const a = $('Aplicar modo').first();\nreturn [{ json: { jid: a.json.jid }, binary: a.binary }];"), pos=[2420, 160])
f.add("Transcrever áudio", "n8n-nodes-base.httpRequest", 4.2, {
    "method": "POST", "url": "https://api.openai.com/v1/audio/transcriptions",
    "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
    "sendBody": True, "contentType": "multipart-form-data",
    "bodyParameters": {"parameters": [
        {"parameterType": "formBinaryData", "name": "file", "inputDataFieldName": "data"},
        {"name": "model", "value": "whisper-1"}, {"name": "language", "value": "pt"}]},
    "options": {}}, creds=CRED["openai"], pos=[2640, 160])
f.add("Texto do áudio", "n8n-nodes-base.set", 3.4, {"mode": "manual", "assignments": {"assignments": [
    {"id": "t1", "name": "textoFinal", "type": "string", "value": "=[áudio transcrito] {{ $json.text }}"}]}, "options": {}}, pos=[2860, 160])
f.add("Texto da mensagem", "n8n-nodes-base.set", 3.4, {"mode": "manual", "assignments": {"assignments": [
    {"id": "t2", "name": "textoFinal", "type": "string", "value": "={{ $('Aplicar modo').item.json.texto }}"}]}, "options": {}}, pos=[2860, 420])
f.x = 2860
f.add("Guardar no buffer", "n8n-nodes-base.redis", 1,
      {"operation": "push", "list": "=buf:{{ $('Aplicar modo').item.json.jid }}", "messageData": "={{ $json.textoFinal }}", "tail": True},
      creds=CRED["redis"])
f.add("Marcar última mensagem", "n8n-nodes-base.redis", 1,
      {"operation": "set", "key": "=last:{{ $('Aplicar modo').item.json.jid }}", "value": "={{ $('Aplicar modo').item.json.msgId }}",
       "keyType": "string", "expire": True, "ttl": 120}, creds=CRED["redis"])
f.add("Aguardar mensagens picadas", "n8n-nodes-base.wait", 1.1,
      {"resume": "timeInterval", "amount": DEBOUNCE_SECONDS, "unit": "seconds"}, webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "debounce")))
f.add("Ler última mensagem", "n8n-nodes-base.redis", 1,
      {"operation": "get", "propertyName": "ultima", "key": "=last:{{ $('Aplicar modo').item.json.jid }}", "keyType": "string", "options": {}},
      creds=CRED["redis"])
f.add("É a mais recente?", "n8n-nodes-base.if", 2.2,
      cond("={{ $json.ultima }}", "equals", "={{ $('Aplicar modo').item.json.msgId }}"))
f.add("Ler buffer", "n8n-nodes-base.redis", 1,
      {"operation": "get", "propertyName": "buffer", "key": "=buf:{{ $('Aplicar modo').item.json.jid }}", "keyType": "list", "options": {}},
      creds=CRED["redis"])
f.add("Limpar buffer", "n8n-nodes-base.redis", 1,
      {"operation": "delete", "key": "=buf:{{ $('Aplicar modo').item.json.jid }}"}, creds=CRED["redis"])
f.add("Montar entrada", "n8n-nodes-base.code", 2, code(BUILD_INPUT))
f.add("Agente", "@n8n/n8n-nodes-langchain.agent", 3.1,
      {"promptType": "define", "text": "={{ $json.chatInput }}", "options": {"systemMessage": PROMPT, "maxIterations": 3}})
f.add("Claude", "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.6,
      {"model": {"__rl": True, "mode": "id", "value": MODEL},
       "options": {"maxTokensToSample": 1024, "temperature": 0.4, "promptCaching": "5m"}},
      creds=CRED["anthropic"], pos=[f.x, 520])
f.add("Memória da conversa", "@n8n/n8n-nodes-langchain.memoryRedisChat", 1.6,
      {"sessionIdType": "customKey", "sessionKey": "={{ $('Montar entrada').first().json.sessionId }}",
       "sessionTTL": MEMORY_TTL_SECONDS, "contextWindowLength": 20}, creds=CRED["redis"], pos=[f.x + 20, 520])
f.add("Interpretar resposta", "n8n-nodes-base.code", 2, code(PARSE_OUTPUT))
f.add("Executar agenda", "n8n-nodes-base.code", 2, code(AGENDA))
f.add("Salvar lead", "n8n-nodes-base.postgres", 2.8,
      sql("UPDATE leads AS l SET nome = COALESCE(d.nome, l.nome), email = COALESCE(d.email, l.email), "
          "telefone_preferencial = COALESCE(d.telefone_preferencial, l.telefone_preferencial), "
          "contato_avisos_confirmado = COALESCE(d.contato_avisos_confirmado, l.contato_avisos_confirmado), "
          "perfil = COALESCE(d.perfil, l.perfil), objetivo = COALESCE(d.objetivo, l.objetivo), "
          "experiencia = COALESCE(d.experiencia, l.experiencia), problema = COALESCE(d.problema, l.problema), "
          "interesse = COALESCE(d.interesse, l.interesse), ementa = COALESCE(d.ementa, l.ementa), "
          "sabe_programar = COALESCE(d.sabe_programar, l.sabe_programar), "
          "email_solicitado = l.email_solicitado OR COALESCE(d.email_solicitado IN ('sim', 'true'), false), "
          "duvidas_pendentes = COALESCE(d.duvidas_pendentes, l.duvidas_pendentes), "
          "preferencia_agenda = COALESCE(d.preferencia_agenda, l.preferencia_agenda), "
          "estado = COALESCE(d.estado, l.estado), reserva_uid = COALESCE(d.reserva_uid, l.reserva_uid), "
          "reserva_inicio = COALESCE(d.reserva_inicio::timestamptz, l.reserva_inicio), "
          "reserva_status = COALESCE(d.reserva_status, l.reserva_status), "
          "reserva_link = COALESCE(d.reserva_link, l.reserva_link), "
          "reserva_criada_em = COALESCE(d.reserva_criada_em::timestamptz, l.reserva_criada_em), "
          "lembrete_8h_em = CASE WHEN d.reserva_inicio IS NOT NULL THEN NULL ELSE l.lembrete_8h_em END, "
          "briefing_reserva_em = CASE WHEN d.reserva_inicio IS NOT NULL THEN NULL ELSE l.briefing_reserva_em END, "
          "briefing_1h_em = CASE WHEN d.reserva_inicio IS NOT NULL THEN NULL ELSE l.briefing_1h_em END, "
          "lembrete_1h_em = CASE WHEN d.reserva_inicio IS NOT NULL THEN NULL ELSE l.lembrete_1h_em END, "
          "lembrete_15m_em = CASE WHEN d.reserva_inicio IS NOT NULL THEN NULL ELSE l.lembrete_15m_em END, "
          "atendimento_humano = l.atendimento_humano OR $3::boolean, pediu_parada = l.pediu_parada OR $4::boolean, "
          "atualizado_em = now() "
          "FROM jsonb_to_record($2::jsonb) AS d(nome text, email text, telefone_preferencial text, "
          "contato_avisos_confirmado text, perfil text, objetivo text, experiencia text, problema text, interesse text, "
          "ementa text, sabe_programar text, email_solicitado text, duvidas_pendentes text, preferencia_agenda text, estado text, "
          "reserva_uid text, reserva_inicio text, reserva_status text, reserva_link text, reserva_criada_em text) "
          "WHERE l.jid = $1 RETURNING l.*",
          "={{ [$json.jid, JSON.stringify($json.lead), $json.humano, $json.parada] }}"),
      creds=CRED["postgres"])
f.add("Enviar resposta", "n8n-nodes-base.httpRequest", 4.2,
      evolution_send("$('Aplicar modo').first().json.jid", "$('Executar agenda').first().json.resposta"))
f.add("Registrar envio", "n8n-nodes-base.redis", 1,
      {"operation": "set", "key": "=sent:{{ $json.key.id }}", "value": "1", "keyType": "string", "expire": True, "ttl": SENT_TTL_SECONDS},
      creds=CRED["redis"])
f.add("Registrar conversa", "n8n-nodes-base.postgres", 2.8,
      sql("INSERT INTO mensagens (jid, direcao, texto) VALUES ($1, 'entrada', $2), ($1, 'saida', $3)",
          "={{ [$('Lead').first().json.jid, [].concat($('Ler buffer').first().json.buffer || []).join('\\n'), "
          "$('Executar agenda').first().json.resposta] }}"),
      creds=CRED["postgres"])
f.add("Avisar Willian?", "n8n-nodes-base.if", 2.2,
      {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                      "conditions": [{"id": "a1", "leftValue": "={{ $('Executar agenda').first().json.avisar }}",
                                      "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                      "combinator": "and"}, "options": {}})
f.add("Resumo para o Willian", "n8n-nodes-base.code", 2, code(SUMMARY))
f.add("Enviar resumo", "n8n-nodes-base.httpRequest", 4.2, evolution_send("$json.destino", "$json.texto"))
f.add("Registrar envio do resumo", "n8n-nodes-base.redis", 1,
      {"operation": "set", "key": "=sent:{{ $json.key.id }}", "value": "1", "keyType": "string", "expire": True, "ttl": SENT_TTL_SECONDS},
      creds=CRED["redis"])

f.chain("Entrada Evolution", "Filtrar entrada", "Config", "Aplicar modo", "Atender?")
f.link("Atender?", "Já enviado pelo bot?", 0)
f.link("Atender?", "Pausar ou liberar humano", 1)
f.chain("Já enviado pelo bot?", "Mensagem nova?")
f.link("Mensagem nova?", "Lead", 0)
f.chain("Lead", "Bot ativo para o contato?")
f.link("Bot ativo para o contato?", "É áudio?", 0)
f.link("É áudio?", "Recuperar áudio", 0)
f.link("É áudio?", "Texto da mensagem", 1)
f.chain("Recuperar áudio", "Transcrever áudio", "Texto do áudio", "Guardar no buffer")
f.link("Texto da mensagem", "Guardar no buffer")
f.chain("Guardar no buffer", "Marcar última mensagem", "Aguardar mensagens picadas", "Ler última mensagem", "É a mais recente?")
f.link("É a mais recente?", "Ler buffer", 0)
f.chain("Ler buffer", "Limpar buffer", "Montar entrada", "Agente", "Interpretar resposta", "Executar agenda", "Salvar lead",
        "Enviar resposta", "Registrar envio", "Registrar conversa", "Avisar Willian?")
f.link("Claude", "Agente", kind="ai_languageModel")
f.link("Memória da conversa", "Agente", kind="ai_memory")
f.link("Avisar Willian?", "Resumo para o Willian", 0)
f.chain("Resumo para o Willian", "Enviar resumo", "Registrar envio do resumo")


# ---------------------------------------------------------------- Reminders
LEMBRETES_SQL = (
    "SELECT * FROM (SELECT jid, nome, reserva_uid, reserva_inicio, reserva_link, "
    "CASE "
    "WHEN lembrete_15m_em IS NULL AND now() >= reserva_inicio - interval '15 minutes' AND now() < reserva_inicio + interval '5 minutes' THEN '15m' "
    "WHEN lembrete_1h_em IS NULL AND now() >= reserva_inicio - interval '60 minutes' AND now() < reserva_inicio - interval '15 minutes' THEN '1h' "
    "WHEN lembrete_8h_em IS NULL "
    "AND (now() AT TIME ZONE 'America/Sao_Paulo')::date = (reserva_inicio AT TIME ZONE 'America/Sao_Paulo')::date "
    "AND (now() AT TIME ZONE 'America/Sao_Paulo')::time >= time '08:00' AND now() < reserva_inicio - interval '70 minutes' "
    "AND (reserva_criada_em IS NULL OR (reserva_criada_em AT TIME ZONE 'America/Sao_Paulo') < "
    "((reserva_inicio AT TIME ZONE 'America/Sao_Paulo')::date + time '08:00')) THEN '8h' "
    "END AS tipo FROM leads WHERE reserva_status = 'reservado' AND reserva_inicio > now() - interval '10 minutes') x "
    "WHERE tipo IS NOT NULL"
)

SEND_REMINDERS = r"""
// Checks each booking on Cal.com, then sends the due reminder. Missed windows are skipped, never sent late.
const MARKER = '⁣', TZ = 'America/Sao_Paulo';
const cfg = $('Config lembretes').first().json;
const h = { Authorization: 'Bearer ' + $env.CALCOM_API_KEY, 'cal-api-version': '2024-08-13' };
const out = [];
for (const it of $input.all()) {
  const r = it.json;
  if (!r.tipo) continue;
  let b;
  try { b = (await this.helpers.httpRequest({ url: `https://api.cal.com/v2/bookings/${r.reserva_uid}`, headers: h, json: true })).data; }
  catch (e) { continue; }
  if (!b || b.status !== 'accepted') { out.push({ json: { jid: r.jid, tipo: 'cancelado' } }); continue; }
  if (new Date(b.start).getTime() !== new Date(r.reserva_inicio).getTime()) { out.push({ json: { jid: r.jid, tipo: 'novo_inicio', inicio: b.start } }); continue; }
  const link = b.meetingUrl || r.reserva_link || '';
  const hora = new Date(b.start).toLocaleTimeString('pt-BR', { timeZone: TZ, hour: '2-digit', minute: '2-digit' });
  const nome = r.nome ? ', ' + r.nome : '';
  const textos = {
    '8h': `Bom dia${nome}! Hoje, às ${hora} (horário de Brasília), é o seu encontro de 30 minutos com o Willian. Você confirma sua presença?`,
    '1h': `Olá${nome}! Falta 1 hora para o seu encontro com o Willian, às ${hora}. Separe suas dúvidas e uma visão geral da rotina que você quer melhorar. Daqui a pouco envio o link por aqui.`,
    '15m': `Seu encontro com o Willian começa em 15 minutos, às ${hora}.` + (link ? ` Acesse por aqui: ${link}` : ' O link está no convite.'),
  };
  const texto = textos[r.tipo];
  try {
    await this.helpers.httpRequest({ method: 'POST', url: `${$env.EVOLUTION_URL}/message/sendText/${cfg.instancia}`,
      headers: { apikey: $env.EVOLUTION_API_KEY }, json: true, body: { number: r.jid, text: texto + MARKER } });
    out.push({ json: { jid: r.jid, tipo: r.tipo, texto } });
  } catch (e) {}
}
return out;
"""

lb = Flow("Lembretes de encontro")
lb.add("A cada 5 minutos", "n8n-nodes-base.scheduleTrigger", 1.2,
       {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}})
lb.add("Config lembretes", "n8n-nodes-base.postgres", 2.8,
       sql("SELECT COALESCE(MAX(valor) FILTER (WHERE chave='instancia'),'atendimento') AS instancia FROM config", ""),
       creds=CRED["postgres"], executeOnce=True)
lb.add("Lembretes devidos", "n8n-nodes-base.postgres", 2.8, sql(LEMBRETES_SQL, ""), creds=CRED["postgres"],
       alwaysOutputData=False)
lb.add("Conferir e enviar", "n8n-nodes-base.code", 2, code(SEND_REMINDERS))
lb.add("Registrar lembrete", "n8n-nodes-base.postgres", 2.8,
       sql("WITH log AS (INSERT INTO mensagens (jid, direcao, texto) SELECT $1, 'saida', $3 WHERE $3 IS NOT NULL) "
           "UPDATE leads SET "
           "lembrete_8h_em = CASE WHEN $2 = '8h' THEN now() ELSE lembrete_8h_em END, "
           "lembrete_1h_em = CASE WHEN $2 = '1h' THEN now() ELSE lembrete_1h_em END, "
           "lembrete_15m_em = CASE WHEN $2 = '15m' THEN now() ELSE lembrete_15m_em END, "
           "ultimo_lembrete = CASE WHEN $2 IN ('8h', '1h', '15m') THEN $3 ELSE ultimo_lembrete END, "
           "reserva_status = CASE WHEN $2 = 'cancelado' THEN 'cancelado' ELSE reserva_status END, "
           "estado = CASE WHEN $2 = 'cancelado' THEN 'cancelado' ELSE estado END, "
           "reserva_inicio = CASE WHEN $2 = 'novo_inicio' THEN $4::timestamptz ELSE reserva_inicio END, "
           "atualizado_em = now() WHERE jid = $1",
           "={{ [$json.jid, $json.tipo, $json.texto || null, $json.inicio || null] }}"),
       creds=CRED["postgres"])
lb.chain("A cada 5 minutos", "Config lembretes", "Lembretes devidos", "Conferir e enviar", "Registrar lembrete")


# ---------------------------------------------------------------- Briefing by email
BRIEFING_SQL = (
    "SELECT * FROM (SELECT l.*, (SELECT valor FROM config WHERE chave = 'email_briefing') AS email_briefing, "
    "CASE WHEN l.briefing_reserva_em IS NULL AND now() < l.reserva_inicio - interval '60 minutes' THEN 'reserva' "
    "WHEN l.briefing_1h_em IS NULL AND now() >= l.reserva_inicio - interval '60 minutes' AND now() < l.reserva_inicio THEN '1h' END AS tipo_briefing, "
    "(SELECT COALESCE(json_agg(json_build_object('direcao', m.direcao, 'texto', m.texto, "
    "'em', to_char(m.criado_em AT TIME ZONE 'America/Sao_Paulo', 'DD/MM HH24:MI')) ORDER BY m.id), '[]'::json) "
    "FROM (SELECT * FROM mensagens WHERE jid = l.jid ORDER BY id DESC LIMIT 80) m) AS conversa "
    "FROM leads l WHERE l.reserva_status = 'reservado' AND l.reserva_inicio > now()) x "
    "WHERE tipo_briefing IS NOT NULL AND COALESCE(email_briefing, '') <> ''"
)

BRIEF_REQUEST = r"""
// Builds the Claude request that turns the lead profile and conversation into a meeting briefing.
const l = $json;
const perfil = {};
for (const k of ['nome', 'email', 'telefone_origem', 'telefone_preferencial', 'perfil', 'objetivo', 'experiencia', 'sabe_programar',
  'problema', 'interesse', 'ementa', 'duvidas_pendentes', 'preferencia_agenda', 'estado']) if (l[k]) perfil[k] = l[k];
const conversa = (l.conversa || []).map(m => `[${m.em}] ${m.direcao === 'entrada' ? 'Contato' : 'Assistente'}: ${m.texto}`).join('\n');
return { json: { body: {
  model: 'MODEL_ID', max_tokens: 1200,
  system: 'Você prepara o Willian Castilho (mentor de IA aplicada) para um encontro gratuito de 30 minutos com um lead que veio pelo WhatsApp. Escreva em português, direto, em tópicos curtos, só com fatos da conversa e do cadastro; quando algo não foi dito, escreva "não informado". Nunca invente.',
  messages: [{ role: 'user', content: `Cadastro:\n${JSON.stringify(perfil, null, 1)}\n\nConversa:\n${conversa || '(sem mensagens registradas)'}\n\nResponda só com HTML simples (h3, p, ul, li, b), com estas seções: Quem é; Objetivo e contexto; Dores e rotina que quer melhorar; O que perguntou ou demonstrou interesse; Pontos de atenção; Sugestão de condução do encontro (3 a 5 tópicos).` }],
} } };
""".replace("MODEL_ID", MODEL)

BRIEF_EMAIL = r"""
// Assembles the briefing email: AI summary, profile table, meeting link and the full conversation.
const l = $('Briefings devidos').item.json;
const resumo = (($json.content || [])[0] || {}).text || '<p>(resumo indisponível)</p>';
const esc = t => String(t ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const quando = new Date(l.reserva_inicio).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', weekday: 'long', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
const campos = [['Nome', l.nome], ['Telefone', l.telefone_origem && '+' + l.telefone_origem], ['Telefone preferencial', l.telefone_preferencial],
  ['E-mail', l.email], ['Perfil', l.perfil], ['Objetivo', l.objetivo], ['Experiência com IA', l.experiencia], ['Sabe programar', l.sabe_programar],
  ['Gargalo / rotina', l.problema], ['Interesse', l.interesse], ['Ementa', l.ementa], ['Dúvidas pendentes', l.duvidas_pendentes], ['Estado', l.estado]];
const tabela = campos.map(([k, v]) => `<tr><td style="padding:4px 8px;color:#555">${k}</td><td style="padding:4px 8px"><b>${esc(v || 'não informado')}</b></td></tr>`).join('');
const conversa = (l.conversa || []).map(m => `<p style="margin:4px 0"><span style="color:#888">[${m.em}]</span> <b>${m.direcao === 'entrada' ? 'Contato' : 'Assistente'}:</b> ${esc(m.texto).replace(/\n/g, '<br>')}</p>`).join('');
const titulo = l.tipo_briefing === '1h' ? 'Começa em 1 hora' : 'Nova reunião marcada';
const html = `<div style="font-family:Arial,sans-serif;max-width:680px">
<h2>${titulo}: ${esc(l.nome || 'Contato WhatsApp')}</h2>
<p><b>Quando:</b> ${quando} (horário de Brasília)${l.reserva_link ? `<br><b>Link:</b> <a href="${l.reserva_link}">${l.reserva_link}</a>` : ''}</p>
<h3>Briefing</h3>${resumo}
<h3>Cadastro</h3><table style="border-collapse:collapse">${tabela}</table>
<h3>Conversa completa</h3>${conversa || '<p>(sem mensagens registradas)</p>'}
</div>`;
return { json: { para: l.email_briefing, assunto: `[Briefing] ${titulo} · ${l.nome || 'Contato'} · ${quando}`, html, jid: l.jid, tipo: l.tipo_briefing } };
"""

br = Flow("Briefing por e-mail")
br.add("A cada 5 minutos (briefing)", "n8n-nodes-base.scheduleTrigger", 1.2,
       {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}})
br.add("Briefings devidos", "n8n-nodes-base.postgres", 2.8, sql(BRIEFING_SQL, ""), creds=CRED["postgres"])
br.add("Montar pedido", "n8n-nodes-base.code", 2, {"mode": "runOnceForEachItem", "language": "javaScript", "jsCode": BRIEF_REQUEST})
br.add("Claude resume", "n8n-nodes-base.httpRequest", 4.2, {
    "method": "POST", "url": "https://api.anthropic.com/v1/messages",
    "authentication": "predefinedCredentialType", "nodeCredentialType": "anthropicApi",
    "sendHeaders": True, "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
    "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {}},
    creds=CRED["anthropic"])
br.add("Montar e-mail", "n8n-nodes-base.code", 2, {"mode": "runOnceForEachItem", "language": "javaScript", "jsCode": BRIEF_EMAIL})
br.add("Enviar e-mail", "n8n-nodes-base.httpRequest", 4.2, {
    "method": "POST", "url": "https://api.resend.com/emails",
    "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Authorization", "value": "=Bearer {{ $env.RESEND_API_KEY }}"}]},
    "sendBody": True, "specifyBody": "json",
    "jsonBody": "={{ JSON.stringify({ from: $env.RESEND_FROM || 'Assistente IA Aplicada <onboarding@resend.dev>', to: [$json.para], subject: $json.assunto, html: $json.html }) }}",
    "options": {}})
br.add("Registrar briefing", "n8n-nodes-base.postgres", 2.8,
       sql("UPDATE leads SET briefing_reserva_em = CASE WHEN $2 = 'reserva' THEN now() ELSE briefing_reserva_em END, "
           "briefing_1h_em = CASE WHEN $2 = '1h' THEN now() ELSE briefing_1h_em END WHERE jid = $1",
           "={{ [$('Montar e-mail').item.json.jid, $('Montar e-mail').item.json.tipo] }}"),
       creds=CRED["postgres"])
br.chain("A cada 5 minutos (briefing)", "Briefings devidos", "Montar pedido", "Claude resume", "Montar e-mail", "Enviar e-mail", "Registrar briefing")

# ---------------------------------------------------------------- QR page
PAGE = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Conectar WhatsApp</title>
<style>
body{font-family:system-ui,sans-serif;background:#f4f6f8;color:#1d2733;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center}
main{background:#fff;border-radius:16px;box-shadow:0 4px 24px #0001;padding:32px;max-width:420px;width:calc(100% - 32px);text-align:center}
h1{font-size:1.3rem;margin:0 0 8px}p{color:#4a5868;line-height:1.5}
#qr{width:280px;height:280px;margin:16px auto;display:flex;align-items:center;justify-content:center}
#qr img{width:100%;height:100%}.ok{color:#1f883d;font-size:1.2rem;font-weight:600}
button{background:#b42318;color:#fff;border:0;border-radius:8px;padding:10px 16px;font-size:1rem;cursor:pointer}
small{color:#6b7785}
</style></head><body><main>
<h1>Conectar o WhatsApp do atendimento</h1>
<div id="box"><p>Carregando…</p></div>
<small>A página se atualiza sozinha.</small>
</main><script>
const t = new URLSearchParams(location.search).get('t');
const base = location.pathname.replace(/\/conectar$/, '');
async function load() {
  try {
    const r = await fetch(base + '/conectar-status?t=' + encodeURIComponent(t), { cache: 'no-store' });
    const s = await r.json();
    const box = document.getElementById('box');
    if (s.estado === 'open') {
      box.innerHTML = '<p class="ok">✅ Conectado</p><p>Número: +' + (s.numero || '') +
        '</p><p>O assistente já está atendendo neste número.</p><p><button id="sair">Desconectar / trocar número</button></p>';
      document.getElementById('sair').onclick = async () => {
        if (!confirm('Desconectar este número do atendimento?')) return;
        await fetch(base + '/conectar-sair?t=' + encodeURIComponent(t), { method: 'POST' });
        load();
      };
    } else if (s.qr) {
      box.innerHTML = '<p>No celular: WhatsApp → <b>Configurações</b> → <b>Dispositivos conectados</b> → <b>Conectar dispositivo</b> e aponte para o código.</p><div id="qr"><img alt="QR Code" src="' + s.qr + '"></div>';
    } else {
      box.innerHTML = '<p>Gerando o QR Code…</p>';
    }
  } catch (e) { document.getElementById('box').innerHTML = '<p>Sem conexão com o servidor. Tentando de novo…</p>'; }
}
load(); setInterval(load, 5000);
</script></body></html>"""

STATUS = r"""
// Returns the connection state; when disconnected, asks Evolution for a fresh QR code.
const base = $env.EVOLUTION_URL, inst = 'atendimento';
const h = { apikey: $env.EVOLUTION_API_KEY };
const st = await this.helpers.httpRequest({ url: `${base}/instance/connectionState/${inst}`, headers: h, json: true });
const estado = st.instance && st.instance.state;
if (estado === 'open') {
  const list = await this.helpers.httpRequest({ url: `${base}/instance/fetchInstances?instanceName=${inst}`, headers: h, json: true });
  const owner = (list[0] && list[0].ownerJid) || '';
  return [{ json: { estado, numero: owner.split('@')[0].split(':')[0] } }];
}
const c = await this.helpers.httpRequest({ url: `${base}/instance/connect/${inst}`, headers: h, json: true });
return [{ json: { estado: estado || 'close', qr: c.base64 || null } }];
"""

LOGOUT = r"""
const base = $env.EVOLUTION_URL;
await this.helpers.httpRequest({ method: 'DELETE', url: `${base}/instance/logout/atendimento`,
  headers: { apikey: $env.EVOLUTION_API_KEY }, json: true }).catch(() => null);
return [{ json: { ok: true } }];
"""

q = Flow("Página de conexão (QR Code)")
token_ok = cond("={{ $json.query.t }}", "equals", "={{ $env.QR_PAGE_TOKEN }}")
not_found = {"respondWith": "text", "responseBody": "Não encontrado", "options": {"responseCode": 404}}
for i, (path, method, kind) in enumerate([("conectar", "GET", "page"), ("conectar-status", "GET", "status"), ("conectar-sair", "POST", "logout")]):
    y = 200 + i * 260
    q.x = 0
    w = q.add(f"Rota {path}", "n8n-nodes-base.webhook", 2.1,
              {"httpMethod": method, "path": path, "responseMode": "responseNode", "options": {}},
              pos=[0, y], webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, path)))
    ok = q.add(f"Token válido? ({path})", "n8n-nodes-base.if", 2.2, token_ok, pos=[220, y])
    deny = q.add(f"Negar ({path})", "n8n-nodes-base.respondToWebhook", 1.4, not_found, pos=[440, y + 100])
    if kind == "page":
        resp = q.add("Responder página", "n8n-nodes-base.respondToWebhook", 1.4,
                     {"respondWith": "text", "responseBody": PAGE,
                      "options": {"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"},
                                                                  {"name": "Cache-Control", "value": "no-store"}]}}},
                     pos=[440, y])
        q.chain(w, ok)
        q.link(ok, resp, 0)
    else:
        act = q.add("Consultar conexão" if kind == "status" else "Desconectar número", "n8n-nodes-base.code", 2,
                    code(STATUS if kind == "status" else LOGOUT), pos=[440, y])
        resp = q.add(f"Responder ({path})", "n8n-nodes-base.respondToWebhook", 1.4,
                     {"respondWith": "json", "responseBody": "={{ JSON.stringify($json) }}",
                      "options": {"responseHeaders": {"entries": [{"name": "Cache-Control", "value": "no-store"}]}}},
                     pos=[660, y])
        q.chain(w, ok)
        q.link(ok, act, 0)
        q.link(act, resp)
    q.link(ok, deny, 1)

OUT.mkdir(parents=True, exist_ok=True)
for flow, fname in [(f, "atendimento-whatsapp.json"), (lb, "lembretes.json"), (br, "briefing-email.json"), (q, "pagina-qrcode.json")]:
    (OUT / fname).write_text(json.dumps(flow.json(), ensure_ascii=False, indent=2))
    print("ok", OUT / fname, len(flow.nodes), "nós")
