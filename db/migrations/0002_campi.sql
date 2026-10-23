-- 0002_campi: base do multi-campus (Etapa 1; decisões D20 e D21).
-- Cria as tabelas campi e cae_membros, acrescenta itens.campus_id e semeia o campus de Hortolândia.
--
-- itens.campus_id nasce NULO de propósito: o código que está no ar ainda não informa o campus, e uma coluna
-- obrigatória derrubaria o registro de itens entre esta migração e o deploy. A trava NOT NULL vem em uma
-- migração posterior, depois que o backend novo estiver no ar.
-- Pode rodar de novo em banco que já tem estas tabelas: não apaga nem duplica nada.

-- Campus. `sigla` é a que aparece no endereço do site do campus (ex.: hto.ifsp.edu.br).
CREATE TABLE IF NOT EXISTS campi (
  id            SERIAL PRIMARY KEY,
  sigla         VARCHAR(10)  NOT NULL UNIQUE CHECK (sigla ~ '^[a-z]{2,10}$'),
  nome          VARCHAR(100) NOT NULL,
  cidade        VARCHAR(100) NOT NULL,
  ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
  info_retirada TEXT         NOT NULL DEFAULT ''   -- sala e horário da CAE; hoje é o INFO_CAE do frontend
);

-- Quem é da CAE de qual campus (D21). user_id é o id do usuário no Supabase Auth.
-- Sem chave estrangeira para auth.users: esse esquema só existe no Supabase, e o CI usa um PostgreSQL comum.
-- UNIQUE(user_id): uma pessoa da CAE pertence a um único campus.
CREATE TABLE IF NOT EXISTS cae_membros (
  id        SERIAL PRIMARY KEY,
  user_id   UUID      NOT NULL UNIQUE,
  campus_id INT       NOT NULL REFERENCES campi(id),
  criado_em TIMESTAMP DEFAULT NOW()
);

ALTER TABLE itens ADD COLUMN IF NOT EXISTS campus_id INT REFERENCES campi(id);

CREATE INDEX IF NOT EXISTS idx_itens_campus_status_criado ON itens(campus_id, status, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_cae_membros_campus         ON cae_membros(campus_id);

-- Campus de vocês. info_retirada com o texto genérico de hoje: troque pela sala e horário reais da CAE
-- (UPDATE campi SET info_retirada = '...' WHERE sigla = 'hto').
INSERT INTO campi (sigla, nome, cidade, info_retirada) VALUES
  ('hto', 'Hortolândia', 'Hortolândia', 'Para retirar ou entregar um item, procure a CAE.')
ON CONFLICT (sigla) DO NOTHING;

-- Os itens que já existem são de Hortolândia.
UPDATE itens SET campus_id = (SELECT id FROM campi WHERE sigla = 'hto') WHERE campus_id IS NULL;

-- Segurança (D17): toda tabela nova nasce com RLS ligado e sem policies.
ALTER TABLE campi       ENABLE ROW LEVEL SECURITY;
ALTER TABLE cae_membros ENABLE ROW LEVEL SECURITY;
