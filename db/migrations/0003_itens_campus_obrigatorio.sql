-- 0003_itens_campus_obrigatorio: fecha a Etapa 1. Todo item passa a ter campus.
-- Os itens gravados sem campus (no intervalo entre a 0002 e o deploy do backend novo) ficam com Hortolândia,
-- e só então a coluna vira NOT NULL. Se o campus hto não existir, o UPDATE não preenche nada, o NOT NULL falha
-- e a migração inteira é desfeita (roda numa transação): nada fica pela metade.

UPDATE itens SET campus_id = (SELECT id FROM campi WHERE sigla = 'hto') WHERE campus_id IS NULL;

ALTER TABLE itens ALTER COLUMN campus_id SET NOT NULL;
