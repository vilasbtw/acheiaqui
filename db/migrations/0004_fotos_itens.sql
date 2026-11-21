-- 0004_fotos_itens: foto opcional do item, enviada no registro (Etapa 5; decisões D4 e D25).
-- A imagem fica no próprio banco, numa tabela separada: a busca pública consulta `itens` e nunca carrega fotos.
-- Só a CAE do campus do item vê a foto (pela API). Com o RLS ligado e sem policies, a API REST do Supabase
-- não expõe a tabela (D17).
-- A coluna itens.foto_url continua sem uso: não é removida aqui para não restringir o banco (ver db/README.md).
-- Só acrescenta: aplique em produção ANTES do merge.

CREATE TABLE IF NOT EXISTS item_fotos (
  item_id   INT         PRIMARY KEY REFERENCES itens(id) ON DELETE CASCADE,
  tipo      VARCHAR(20) NOT NULL CHECK (tipo IN ('image/jpeg', 'image/png', 'image/webp')),
  conteudo  BYTEA       NOT NULL CHECK (octet_length(conteudo) BETWEEN 1 AND 600000),  -- mesmo limite da API
  criado_em TIMESTAMP   DEFAULT NOW()
);

ALTER TABLE item_fotos ENABLE ROW LEVEL SECURITY;
