-- SÓ PARA O BANCO DE DESENVOLVIMENTO. NUNCA rode isto em produção.
-- Cria dois campi de teste para provar o isolamento (a CAE de um campus não pode ver o outro).
-- Rodar no SQL Editor do Supabase de desenvolvimento, depois da migração 0002. Pode rodar mais de uma vez.
-- Os nomes começam com "[TESTE]" para ninguém confundir no seletor de campus.

INSERT INTO campi (sigla, nome, cidade, info_retirada) VALUES
  ('tsta', '[TESTE] Campus A', 'Cidade A', 'Texto de retirada do campus de teste A.'),
  ('tstb', '[TESTE] Campus B', 'Cidade B', 'Texto de retirada do campus de teste B.')
ON CONFLICT (sigla) DO NOTHING;

-- Para criar a CAE de teste: crie o usuário em Authentication > Users, copie o id (UUID) dele e rode:
--   INSERT INTO cae_membros (user_id, campus_id)
--   VALUES ('COLE-O-UUID-AQUI', (SELECT id FROM campi WHERE sigla = 'tsta'));
