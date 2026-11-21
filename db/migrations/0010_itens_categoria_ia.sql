-- 0010_itens_categoria_ia: a CAE corrige a categoria que a IA errou, e o sistema guarda o que a IA sugeriu.
-- Assim dá para medir a acurácia da IA com dados REAIS (docs/avaliacao-ia/README.md tem a consulta):
--   categoria_ia_id       o que a IA sugeriu no registro (nulo se a pessoa escolheu ou se a IA não respondeu)
--   categoria_corrigida_em quando a CAE trocou a categoria (nulo = nunca corrigida)
-- Itens antigos ficam com as duas nulas: não sabemos se a categoria deles veio da IA.
-- Só acrescenta: aplique em produção ANTES do merge.

ALTER TABLE itens ADD COLUMN IF NOT EXISTS categoria_ia_id        INT REFERENCES categorias(id);
ALTER TABLE itens ADD COLUMN IF NOT EXISTS categoria_corrigida_em TIMESTAMP;
