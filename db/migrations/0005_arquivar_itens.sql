-- 0005_arquivar_itens: Etapa 3 (decisão D23). A CAE pode arquivar um registro falso (spam) sem apagá-lo.
-- `arquivado` some da busca pública, como `devolvido`, e volta a `disponivel` se a CAE desarquivar.
--
-- Só AFROUXA a regra (aceita um valor a mais): o código antigo nunca grava `arquivado`.
-- Aplique em produção ANTES do merge.
--
-- O CHECK original (0001) não tem nome fixo: o PostgreSQL inventa um. Por isso o bloco abaixo procura qualquer
-- CHECK de `itens` que fale de `status`, apaga e cria de novo com nome conhecido. Pode rodar mais de uma vez.

DO $$
DECLARE
  regra record;
BEGIN
  FOR regra IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'itens'::regclass AND contype = 'c' AND pg_get_constraintdef(oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE itens DROP CONSTRAINT %I', regra.conname);
  END LOOP;
END $$;

ALTER TABLE itens ADD CONSTRAINT itens_status_check CHECK (status IN ('disponivel', 'devolvido', 'arquivado'));
