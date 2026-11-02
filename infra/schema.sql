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
