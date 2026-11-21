-- 0006_itens_texto_busca: Etapa 4 (decisão D24). Busca que ignora acentos e maiúsculas.
-- `texto_busca` guarda a descrição e o local em minúsculas e sem acento. A API grava a coluna em todo item novo,
-- com a mesma regra (`app/services/busca.py`, `normalizar`), e a busca compara a palavra também normalizada.
-- Assim "eletronico" encontra "Eletrônico". Sem extensão do banco (D1): o `translate` abaixo é SQL padrão.
--
-- Só ACRESCENTA (coluna que aceita nulo): aplique em produção ANTES do merge. Itens gravados pelo código antigo
-- entre a migração e o deploy ficam com a coluna nula; a busca cai para a descrição original nesses casos.
-- O mapa de acentos abaixo é conferido contra o Python por tests/test_busca_sem_acento.py.

ALTER TABLE itens ADD COLUMN IF NOT EXISTS texto_busca TEXT;

UPDATE itens
SET texto_busca = lower(translate(
  descricao || ' ' || local_encontrado,
  'ÁÀÂÃÄáàâãäÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇçÑñ',
  'AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCcNn'
))
WHERE texto_busca IS NULL;
