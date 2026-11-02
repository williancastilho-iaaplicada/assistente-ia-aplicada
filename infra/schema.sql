-- Chatbot runtime config and lead profile. Message content is never stored here.
CREATE TABLE IF NOT EXISTS config (
  chave text PRIMARY KEY,
  valor text NOT NULL,
  atualizado_em timestamptz NOT NULL DEFAULT now()
);
INSERT INTO config (chave, valor) VALUES
  ('modo', 'self_only'),
  ('instancia', 'atendimento'),
  ('notificar_numero', '')
ON CONFLICT (chave) DO NOTHING;

CREATE TABLE IF NOT EXISTS leads (
  jid text PRIMARY KEY,
  telefone_origem text,
  nome text,
  email text,
  telefone_preferencial text,
  contato_avisos_confirmado text,
  perfil text,
  objetivo text,
  experiencia text,
  problema text,
  interesse text,
  ementa text,
  duvidas_pendentes text,
  preferencia_agenda text,
  estado text NOT NULL DEFAULT 'novo',
  atendimento_humano boolean NOT NULL DEFAULT false,
  pediu_parada boolean NOT NULL DEFAULT false,
  criado_em timestamptz NOT NULL DEFAULT now(),
  atualizado_em timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS sabe_programar text;

-- Agenda (Cal.com). The event slug is configurable; no ids hardcoded in the flow.
INSERT INTO config (chave, valor) VALUES ('calcom_evento', '30min') ON CONFLICT (chave) DO NOTHING;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reserva_uid text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reserva_inicio timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reserva_status text;

-- Booking extras and day-of reminders (08:00, 1 hour and 15 minutes before).
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reserva_link text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reserva_criada_em timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lembrete_8h_em timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lembrete_1h_em timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lembrete_15m_em timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ultimo_lembrete text;
-- Address used by Cal.com when the contact gives no email (the link goes to the chat instead).
INSERT INTO config (chave, valor) VALUES ('email_sem_convite', 'willianpcastilho+whatsapp@outlook.com') ON CONFLICT (chave) DO NOTHING;

-- Conversation history (both sides) for briefings and later review. Kept until deleted on request.
CREATE TABLE IF NOT EXISTS mensagens (
  id bigserial PRIMARY KEY,
  jid text NOT NULL,
  direcao text NOT NULL CHECK (direcao IN ('entrada', 'saida')),
  texto text NOT NULL,
  criado_em timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS mensagens_jid_idx ON mensagens (jid, id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS briefing_reserva_em timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS briefing_1h_em timestamptz;
-- Briefing recipient (set the real address directly in the database).
INSERT INTO config (chave, valor) VALUES ('email_briefing', '') ON CONFLICT (chave) DO NOTHING;
