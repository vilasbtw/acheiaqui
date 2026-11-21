-- 0007_perdidos: Etapa 6 (decisões D26 e D27). Quem perdeu algo registra o item e acompanha por um link secreto.
-- O sistema sugere achados parecidos (regras + IA) e a CAE SEMPRE confirma a correspondência.
--
-- perdidos.token_hash: SHA-256 do segredo do link. O segredo em si nunca é gravado (como uma senha): quem tiver
-- acesso ao banco não consegue montar o link de ninguém.
-- perdidos.contato: obrigatório; só a CAE vê (como itens.contato_achador, D5).
-- correspondencias: guarda a nota que a IA deu a cada par (perdido, achado), para não gastar a cota de novo.
-- Só acrescenta: aplique em produção ANTES do merge.

CREATE TABLE IF NOT EXISTS perdidos (
  id            SERIAL       PRIMARY KEY,
  campus_id     INT          NOT NULL REFERENCES campi(id),
  descricao     TEXT         NOT NULL,
  local_perdido VARCHAR(100),                                 -- opcional: muita gente não sabe onde perdeu
  perdido_em    DATE         NOT NULL,                        -- dia aproximado (D7: data local, sem fuso)
  contato       VARCHAR(100) NOT NULL,
  categoria_id  INT          REFERENCES categorias(id),       -- sugerida pela IA, como nos achados (D2)
  texto_busca   TEXT,                                         -- igual a itens.texto_busca (D24)
  token_hash    CHAR(64)     NOT NULL UNIQUE,
  status        VARCHAR(20)  NOT NULL DEFAULT 'procurando'
                CHECK (status IN ('procurando', 'encontrado', 'encerrado')),
  item_id       INT          REFERENCES itens(id),            -- o achado que a CAE confirmou
  confirmado_em TIMESTAMP,
  criado_em     TIMESTAMP    DEFAULT NOW(),
  CHECK ((status = 'encontrado') = (item_id IS NOT NULL))     -- encontrado <=> tem achado confirmado
);

CREATE TABLE IF NOT EXISTS correspondencias (
  perdido_id INT         NOT NULL REFERENCES perdidos(id) ON DELETE CASCADE,
  item_id    INT         NOT NULL REFERENCES itens(id) ON DELETE CASCADE,
  nota_ia    VARCHAR(10) NOT NULL CHECK (nota_ia IN ('alta', 'media', 'baixa')),  -- falha da IA não é gravada
  criado_em  TIMESTAMP   DEFAULT NOW(),
  PRIMARY KEY (perdido_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_perdidos_campus_status_criado ON perdidos(campus_id, status, criado_em DESC);

ALTER TABLE perdidos         ENABLE ROW LEVEL SECURITY;
ALTER TABLE correspondencias ENABLE ROW LEVEL SECURITY;
