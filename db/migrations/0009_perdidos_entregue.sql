-- 0009_perdidos_entregue: fecha o ciclo da Etapa 6. Quando a CAE registra a devolução de um achado que estava
-- confirmado para um item perdido, o pedido passa para `entregue`. Antes, o link de quem perdeu continuava
-- mostrando "Pode estar na CAE, vá retirar" mesmo depois da retirada.
--
-- `entregue` mantém o achado (item_id), como `encontrado`. Por isso as duas regras de status são refeitas.
-- Só AFROUXA as regras (aceita um valor a mais): o código antigo nunca grava `entregue`. Produção ANTES do merge.
--
-- As regras da 0007 não têm nome fixo (o PostgreSQL inventa). O bloco apaga todo CHECK de `perdidos` que fale de
-- `status` e cria de novo com nome conhecido. O CHECK do e-mail (perdidos_aviso_check, 0008) não fala de status e fica.

DO $$
DECLARE
  regra record;
BEGIN
  FOR regra IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'perdidos'::regclass AND contype = 'c' AND pg_get_constraintdef(oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE perdidos DROP CONSTRAINT %I', regra.conname);
  END LOOP;
END $$;

ALTER TABLE perdidos ADD CONSTRAINT perdidos_status_check
  CHECK (status IN ('procurando', 'encontrado', 'entregue', 'encerrado'));
ALTER TABLE perdidos ADD CONSTRAINT perdidos_achado_check
  CHECK ((status IN ('encontrado', 'entregue')) = (item_id IS NOT NULL));  -- com achado <=> tem item_id
