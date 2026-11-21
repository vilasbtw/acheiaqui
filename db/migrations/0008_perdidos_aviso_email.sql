-- 0008_perdidos_aviso_email: Etapa 7 (decisão D28). Aviso por e-mail para quem perdeu, só com consentimento
-- e só depois que a CAE confirma a correspondência. O envio é em segundo plano, por API HTTP (o Render bloqueia SMTP).
--
-- email_aviso só é gravado quando a pessoa marcou o consentimento (o CHECK garante). Sem consentimento, nada de e-mail.
-- aviso_enviado_em / aviso_erro: resultado do último envio, para a CAE ver no painel e reenviar se falhou.
-- Só acrescenta (colunas que aceitam nulo ou têm padrão): aplique em produção ANTES do merge.

ALTER TABLE perdidos ADD COLUMN IF NOT EXISTS email_aviso      VARCHAR(254);
ALTER TABLE perdidos ADD COLUMN IF NOT EXISTS aviso_consentido BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE perdidos ADD COLUMN IF NOT EXISTS aviso_enviado_em TIMESTAMP;
ALTER TABLE perdidos ADD COLUMN IF NOT EXISTS aviso_erro       VARCHAR(200);

ALTER TABLE perdidos DROP CONSTRAINT IF EXISTS perdidos_aviso_check;
ALTER TABLE perdidos ADD CONSTRAINT perdidos_aviso_check CHECK (aviso_consentido = (email_aviso IS NOT NULL));
