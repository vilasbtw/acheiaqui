-- HISTÓRICO: este arquivo é o estado do banco no fim do MVP.
-- A fonte da verdade do banco agora são as migrações em db/migrations/ (veja db/README.md).
-- Não edite este arquivo para mudar o banco: crie uma nova migração.

-- Achei Aqui — schema do MVP (fonte da verdade do banco)
-- Rodar no SQL Editor do Supabase. Decisões: D3, D4, D7, D9, D10, D17.

CREATE TABLE categorias (
  id   SERIAL PRIMARY KEY,
  nome VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE itens (
  id               SERIAL PRIMARY KEY,
  descricao        TEXT         NOT NULL,
  categoria_id     INT          REFERENCES categorias(id),
  local_encontrado VARCHAR(100) NOT NULL,
  encontrado_em    TIMESTAMP    NOT NULL,          -- hora local digitada, sem fuso (D7)
  contato_achador  VARCHAR(100),                   -- opcional; só visível para a CAE
  foto_url         TEXT,                           -- reservado, não usado no MVP (D4)
  status           VARCHAR(20)  NOT NULL DEFAULT 'disponivel'
                   CHECK (status IN ('disponivel','devolvido')),   -- D3
  criado_em        TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE devolucoes (
  id             SERIAL PRIMARY KEY,
  item_id        INT          NOT NULL UNIQUE REFERENCES itens(id),
  nome_retirante VARCHAR(100) NOT NULL,
  data_devolucao DATE         NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX idx_itens_status        ON itens(status);
CREATE INDEX idx_itens_encontrado_em ON itens(encontrado_em);

INSERT INTO categorias (nome) VALUES
  ('Documentos'), ('Eletrônicos'), ('Material escolar'), ('Roupas e acessórios'),
  ('Garrafas e marmitas'), ('Chaves'), ('Bolsas e mochilas'), ('Outros');

-- Segurança (D17): RLS ligado e sem policies = a API REST pública do Supabase não expõe nada.
-- O backend (conexão direta no Postgres) não é afetado.
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE itens      ENABLE ROW LEVEL SECURITY;
ALTER TABLE devolucoes ENABLE ROW LEVEL SECURITY;
