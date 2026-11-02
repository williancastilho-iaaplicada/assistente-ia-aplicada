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
// Joins buffered messages and adds the lead context for the agent.
const lead = $('Lead').first().json;
const base = $('Lead').first().json;
const parts = [].concat($json.buffer || []).filter(Boolean);
const agora = new Date().toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'full', timeStyle: 'short' });
const conhecido = {};
for (const [k, v] of Object.entries(lead)) {
  if (v !== null && v !== '' && !['criado_em', 'atualizado_em', 'atendimento_humano'].includes(k)) conhecido[k] = v;
}
const texto = `[contexto]\nAgora: ${agora} (horário de Brasília)\nDados registrados do lead: ${JSON.stringify(conhecido)}\n[/contexto]\n\n${parts.join('\n')}`;
return [{ json: { sessionId: 'mem:' + base.jid, chatInput: texto, jid: base.jid } }];
"""

PARSE_OUTPUT = r"""
// Splits the agent output into the WhatsApp reply and the structured data block.
const raw = String($json.output || '');
const resp = (raw.match(/<resposta>([\s\S]*?)<\/resposta>/) || [])[1];
const dados = (raw.match(/<dados>([\s\S]*?)<\/dados>/) || [])[1];
let parsed = { lead: {}, acao: 'nenhuma' };
try { if (dados) parsed = JSON.parse(dados.trim()); } catch (e) {}
const allowed = ['nome', 'email', 'telefone_preferencial', 'contato_avisos_confirmado', 'perfil', 'objetivo',
  'experiencia', 'problema', 'interesse', 'ementa', 'sabe_programar', 'duvidas_pendentes', 'preferencia_agenda', 'estado'];
const lead = {};
for (const k of allowed) if (parsed.lead && parsed.lead[k] != null && parsed.lead[k] !== '') lead[k] = String(parsed.lead[k]).slice(0, 500);
const acoes = ['nenhuma', 'encaminhar_humano', 'registrar_preferencia_agenda', 'parar_acompanhamento'];
const acao = acoes.includes(parsed.acao) ? parsed.acao : 'nenhuma';
if (acao === 'encaminhar_humano') lead.estado = 'atendimento_humano';
if (acao === 'parar_acompanhamento') lead.estado = 'acompanhamento_encerrado';
const resposta = (resp || raw.replace(/<dados>[\s\S]*<\/dados>/, '')).trim();
return [{ json: { jid: $('Montar entrada').first().json.jid, resposta, lead, acao,
  humano: acao === 'encaminhar_humano', parada: acao === 'parar_acompanhamento' } }];
"""

SUMMARY = r"""
// Builds the internal summary for Willian (knowledge base, section 9).
const l = $('Salvar lead').first().json;
const p = $('Interpretar resposta').first().json;
const v = (x, d = 'não informado') => (x === null || x === undefined || x === '') ? d : x;
const motivo = p.acao === 'encaminhar_humano' ? 'Pedido de atendimento humano' : 'Pedido de encontro de 30 minutos';
const texto = [
  `*${motivo}*`,
  `Nome: ${v(l.nome)}`,
  `Perfil: ${v(l.perfil, 'indefinido')}`,
  `E-mail do Convite: ${v(l.email, 'pendente')}`,
  `Telefone WhatsApp: +${v(l.telefone_origem)}${l.telefone_preferencial ? ' (preferencial: ' + l.telefone_preferencial + ')' : ''}`,
  `Objetivo Principal: ${v(l.objetivo)}`,
  `Experiência com IA: ${v(l.experiencia)}`,
  `Sabe Programar?: ${v(l.sabe_programar)}`,
  `Principal Gargalo/Rotina: ${v(l.problema)}`,
  `Interesse Identificado: ${v(l.interesse, 'indefinido')}`,
  `Status da Ementa: ${v(l.ementa, 'não solicitada')}`,
  `Status da Agenda: Pendente de horário${l.preferencia_agenda ? ' (preferência: ' + l.preferencia_agenda + ')' : ''}`,
  `Próximo Passo: ${p.acao === 'encaminhar_humano' ? 'responder o contato (bot pausado para ele; mande #bot na conversa para devolver)' : 'confirmar o horário com o contato'}`,
].join('\n');
const cfg = $('Config').first().json;
const destino = cfg.notificar_numero || $('Filtrar entrada').first().json.owner;
return [{ json: { destino, texto } }];
"""

f = Flow("Atendimento WhatsApp")
f.add("Entrada Evolution", "n8n-nodes-base.webhook", 2.1,
      {"httpMethod": "POST", "path": "evolution-entrada", "options": {}}, webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "evolution-entrada")))
f.add("Filtrar entrada", "n8n-nodes-base.code", 2, code(PRE_FILTER))
f.add("Config", "n8n-nodes-base.postgres", 2.8,
      sql("SELECT COALESCE(MAX(valor) FILTER (WHERE chave='modo'),'self_only') AS modo, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='instancia'),'atendimento') AS instancia, "
          "COALESCE(MAX(valor) FILTER (WHERE chave='notificar_numero'),'') AS notificar_numero FROM config", ""),
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
f.add("Montar entrada", "n8n-nodes-base.code", 2, code(BUILD_INPUT.replace("$json.buffer", "$('Ler buffer').first().json.buffer")))
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
f.add("Salvar lead", "n8n-nodes-base.postgres", 2.8,
      sql("UPDATE leads AS l SET nome = COALESCE(d.nome, l.nome), email = COALESCE(d.email, l.email), "
          "telefone_preferencial = COALESCE(d.telefone_preferencial, l.telefone_preferencial), "
          "contato_avisos_confirmado = COALESCE(d.contato_avisos_confirmado, l.contato_avisos_confirmado), "
          "perfil = COALESCE(d.perfil, l.perfil), objetivo = COALESCE(d.objetivo, l.objetivo), "
          "experiencia = COALESCE(d.experiencia, l.experiencia), problema = COALESCE(d.problema, l.problema), "
          "interesse = COALESCE(d.interesse, l.interesse), ementa = COALESCE(d.ementa, l.ementa), "
          "sabe_programar = COALESCE(d.sabe_programar, l.sabe_programar), "
          "duvidas_pendentes = COALESCE(d.duvidas_pendentes, l.duvidas_pendentes), "
          "preferencia_agenda = COALESCE(d.preferencia_agenda, l.preferencia_agenda), "
          "estado = COALESCE(d.estado, l.estado), "
          "atendimento_humano = l.atendimento_humano OR $3::boolean, pediu_parada = l.pediu_parada OR $4::boolean, "
          "atualizado_em = now() "
          "FROM jsonb_to_record($2::jsonb) AS d(nome text, email text, telefone_preferencial text, "
          "contato_avisos_confirmado text, perfil text, objetivo text, experiencia text, problema text, interesse text, "
          "ementa text, sabe_programar text, duvidas_pendentes text, preferencia_agenda text, estado text) "
          "WHERE l.jid = $1 RETURNING l.*",
          "={{ [$json.jid, JSON.stringify($json.lead), $json.humano, $json.parada] }}"),
      creds=CRED["postgres"])
f.add("Enviar resposta", "n8n-nodes-base.httpRequest", 4.2,
      evolution_send("$('Aplicar modo').first().json.jid", "$('Interpretar resposta').first().json.resposta"))
f.add("Registrar envio", "n8n-nodes-base.redis", 1,
      {"operation": "set", "key": "=sent:{{ $json.key.id }}", "value": "1", "keyType": "string", "expire": True, "ttl": SENT_TTL_SECONDS},
      creds=CRED["redis"])
f.add("Avisar Willian?", "n8n-nodes-base.if", 2.2,
      {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                      "conditions": [{"id": "a1", "leftValue": "={{ ['encaminhar_humano', 'registrar_preferencia_agenda'].includes($('Interpretar resposta').first().json.acao) }}",
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
f.chain("Ler buffer", "Limpar buffer", "Montar entrada", "Agente", "Interpretar resposta", "Salvar lead",
        "Enviar resposta", "Registrar envio", "Avisar Willian?")
f.link("Claude", "Agente", kind="ai_languageModel")
f.link("Memória da conversa", "Agente", kind="ai_memory")
f.link("Avisar Willian?", "Resumo para o Willian", 0)
f.chain("Resumo para o Willian", "Enviar resumo", "Registrar envio do resumo")

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
for flow, fname in [(f, "atendimento-whatsapp.json"), (q, "pagina-qrcode.json")]:
    (OUT / fname).write_text(json.dumps(flow.json(), ensure_ascii=False, indent=2))
    print("ok", OUT / fname, len(flow.nodes), "nós")
