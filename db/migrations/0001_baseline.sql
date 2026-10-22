-- 0001_baseline: estado do banco no fim do MVP (igual ao antigo docs/schema.sql).
-- Pode rodar em banco NOVO (cria tudo) ou em banco que JÁ tem essas tabelas (não apaga nem duplica nada).

CREATE TABLE IF NOT EXISTS categorias (
  id   SERIAL PRIMARY KEY,
  nome VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS itens (
  id               SERIAL PRIMARY KEY,
  descricao        TEXT         NOT NULL,
  categoria_id     INT          REFERENCES categorias(id),
  local_encontrado VARCHAR(100) NOT NULL,
  encontrado_em    TIMESTAMP    NOT NULL,          -- hora local digitada, sem fuso (D7)
  contato_achador  VARCHAR(100),                   -- opcional; só visível para a CAE
  foto_url         TEXT,                           -- reservado, não usado no MVP (D4)
  status           VARCHAR(20)  NOT NULL DEFAULT 'disponivel'
                   CHECK (status IN ('disponivel','devolvido')),
  criado_em        TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devolucoes (
  id             SERIAL PRIMARY KEY,
  item_id        INT          NOT NULL UNIQUE REFERENCES itens(id),
  nome_retirante VARCHAR(100) NOT NULL,
  data_devolucao DATE         NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_itens_status        ON itens(status);
CREATE INDEX IF NOT EXISTS idx_itens_encontrado_em ON itens(encontrado_em);

INSERT INTO categorias (nome) VALUES
  ('Documentos'), ('Eletrônicos'), ('Material escolar'), ('Roupas e acessórios'),
  ('Garrafas e marmitas'), ('Chaves'), ('Bolsas e mochilas'), ('Outros')
ON CONFLICT (nome) DO NOTHING;

-- Segurança (D17): RLS ligado e sem policies = a API REST pública do Supabase não expõe nada.
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE itens      ENABLE ROW LEVEL SECURITY;
ALTER TABLE devolucoes ENABLE ROW LEVEL SECURITY;
