# Arquitetura do Achei Aqui

Portal de achados e perdidos para campi do IFSP. Qualquer pessoa registra e busca itens sem conta; a CAE
(Comissão de Assistência Estudantil) entra com login para ver o contato de quem achou e registrar a devolução.

## As 3 camadas

```mermaid
flowchart LR
    U["Pessoa (celular ou PC)"] --> F
    C["CAE (logada)"] --> F
    subgraph c1["Camada 1: Frontend"]
        F["HTML + CSS + JS puro<br/>Vercel"]
    end
    subgraph c2["Camada 2: API"]
        A["FastAPI + SQLAlchemy<br/>Render"]
    end
    subgraph c3["Camada 3: Dados"]
        D[("PostgreSQL<br/>Supabase")]
        S["Supabase Auth<br/>login da CAE"]
    end
    F -- "JSON via HTTPS" --> A
    F -- "só o login (supabase-js)" --> S
    A -- "conexão direta (Session pooler)" --> D
    A -- "valida o token" --> S
    A -. "só no registro, 8 s de limite" .-> IA["Provedor de IA<br/>chat/completions"]
    M["Monitor de ping"] -. "GET /saude" .-> A
```

| Camada | Onde | O que faz | Pasta |
| --- | --- | --- | --- |
| Frontend | Vercel (sem build) | Telas públicas (`index` com busca e filtro por categoria, `registrar`, `item` com o detalhe e o botão Compartilhar) e da CAE (`cae/login`, `cae/painel`). Verde do IFSP e Open Sans. Seletor de campus no cabeçalho (`js/campus.js`): vem de `?campus=` ou da última escolha guardada no navegador; com um só campus ativo, já vem escolhido. Endereços em `js/config.js`. Só fala com a API; usa o Supabase apenas para o login | `frontend/` |
| API | Render | Regras, validação, busca, chamada à IA, autorização da CAE. Camadas internas: `routers` → `services` → `models` (+ `schemas` para entrada e saída) | `backend/app/` |
| Dados | Supabase | Tabelas `campi`, `cae_membros`, `categorias`, `itens`, `item_fotos`, `devolucoes`, `perdidos`, `correspondencias` (+ `schema_migrations`) e o Auth. RLS ligado, sem policies: a API REST do Supabase não expõe nada | `db/migrations/` |

## Fluxos principais

1. **Escolher o campus** (público): `GET /campi` lista os ativos, com o texto de retirada de cada um (D20, D22).
2. **Registrar achado** (público): `POST /itens` exige o `campus` (sigla) e recusa campus inexistente ou inativo antes
   de chamar a IA. Valida os campos, recusa data no futuro e, se não veio categoria,
   pede uma à IA. Se a IA falhar, demorar mais de 8 s ou responder algo que não é uma categoria, o item é salvo
   sem categoria (D2). A foto é opcional: o navegador a converte num JPEG de até 500 KB (sem EXIF) e manda no
   mesmo JSON; a API confere a assinatura do arquivo (JPEG, PNG ou WebP, até 600 KB) antes de chamar a IA e grava
   em `item_fotos` (D4, D25).
3. **Buscar** (público): `GET /itens?campus=&q=` é o feed de um campus: só itens `disponivel` daquele campus, sem
   contato (D1, D5, D22). Ignora acentos e maiúsculas (D24). `GET /itens/{id}` informa o campus do item.
4. **Login da CAE**: o `supabase-js` faz o login e o frontend envia `Authorization: Bearer <token>`. A API pergunta
   ao Supabase se o token vale (D6) e procura a pessoa em `cae_membros` (D21). Sem token válido: 401; logado mas
   sem linha em `cae_membros`: 403. Todas as rotas `/cae/*` exigem isso e só enxergam o campus da pessoa
   (`GET /cae/campus` diz qual é). Item de outro campus responde 404, como se não existisse.
5. **Devolução** (CAE): `POST /cae/itens/{id}/devolucao` grava a devolução e muda o status na mesma transação.
   Duas devoluções simultâneas do mesmo item: a segunda recebe 409 (`UNIQUE` em `devolucoes.item_id`).
   `GET /cae/itens` informa `tem_foto`; a imagem vem de `GET /cae/itens/{id}/foto`, só para a CAE do campus do item.
   Registro falso: `POST /cae/itens/{id}/arquivar` tira o item da busca sem apagar; `/desarquivar` desfaz (D23).
6. **Item perdido** (público): `POST /perdidos` (contato obrigatório, categoria pela IA, mesmos limites do registro)
   devolve um segredo uma única vez. O site monta `perdido.html#t=<segredo>`: o que vem depois do `#` não sai do
   navegador. `POST /perdidos/acompanhar` (segredo no corpo) mostra só o status (D27); o banco guarda o SHA-256.
7. **Correspondência** (CAE): `GET /cae/perdidos/{id}/sugestoes`. Regras escolhem os achados disponíveis do campus
   (data compatível, palavras e categoria em comum) e a IA dá nota ALTA, MEDIA ou BAIXA aos 5 melhores (gravada em
   `correspondencias`, para não gastar cota de novo). A CAE confirma (`/confirmar`), encerra ou reabre.
   Quando a CAE registra a devolução do achado confirmado, o pedido vira `entregue` (migração 0009) e o link
   mostra "Item entregue". Entregue não reabre.
8. **Aviso por e-mail** (Etapa 7): ao confirmar, se quem perdeu marcou o consentimento, o e-mail sai em segundo
   plano pelo Brevo. O painel mostra enviado, falhou (com o motivo) ou pendente, e a CAE pode reenviar.
6. **Saúde**: `GET /saude` executa `SELECT 1` no banco. O monitor de ping chama isso (D11).

## Decisões

Cada decisão tem um número (`D##`) que aparece nos comentários do código. O texto completo fica no Memory Bank.

| ID | Decisão | Situação |
| --- | --- | --- |
| D1 | Busca por palavras-chave, sem extensão do banco nem API externa | Em uso (sem acento desde a Etapa 4, D24) |
| D2 | IA só sugere a categoria no registro; nunca bloqueia o registro. A sugestão fica em `categoria_ia_id` e a CAE pode corrigir a categoria no painel (migração 0010), o que dá a acurácia real | Em uso |
| D3 | Status do item: `disponivel`, `devolvido` ou `arquivado` (D23) | Em uso |
| D4 | Foto opcional no registro, guardada no próprio banco (tabela `item_fotos`, migração 0004), e não no Storage: sem chave secreta nova nem serviço novo. `foto_url` fica sem uso | Em uso |
| D5 | Contato de quem achou só aparece para a CAE | Em uso |
| D6 | Login da CAE pelo Supabase Auth; cadastro desativado, contas criadas à mão | Em uso (com `cae_membros` desde a Etapa 1) |
| D7 | Horário guardado como hora local de Brasília, sem fuso, sem conversão na exibição | Em uso |
| D11 | Monitor externo chama `/saude` para manter API e banco acordados | **Pendente**: monitor ainda não configurado. Em 21/11/2026 os dois projetos do Supabase estavam pausados por falta de uso |
| D17 | Toda tabela nasce com RLS ligado; o script de migração desfaz a que esquecer | Em uso |
| D18 | Migrações em SQL numerado com runner próprio, sem Alembic | Em uso |
| D19 | Projeto Supabase só para desenvolvimento, separado da produção | Em uso: `backend/.env` aponta para o de desenvolvimento e `backend/.env.prod` para o de produção. Toda migração passa pelo de desenvolvimento antes (`db/README.md`) |
| D20–D22 | Tabela `campi`; CAE = logado e presente em `cae_membros` (outro campus = 404); público escolhe o campus por `?campus=` | Em uso |
| D23 | Spam vira `status = 'arquivado'` (migração 0005): some da busca pública, continua no histórico da CAE e pode ser desarquivado. Item arquivado não pode ser devolvido | Em uso |
| D24 | Busca sem acento: coluna `itens.texto_busca` (descrição + local, minúsculas, sem acento; migração 0006), preenchida pela API em todo item novo. Nome da categoria comparado sem acento em Python. Sem extensão do banco | Em uso |
| D25 | Foto comprimida no navegador (JPEG, sem EXIF/GPS); **só a CAE vê qualquer foto**, de qualquer categoria. O público não vê foto nenhuma | Em uso |
| D26–D27 | Tabela `perdidos` com link secreto (só o hash no banco; contato obrigatório, só a CAE vê). Quem perdeu vê só o status. Correspondência: regras filtram, a IA dá nota aos 5 melhores, a CAE sempre confirma (migração 0007) | Em uso |
| D28 | E-mail em segundo plano (BackgroundTasks), só depois da confirmação da CAE e só com consentimento (o e-mail nem é gravado sem ele; CHECK na migração 0008). Brevo por API HTTP, com remetente verificado (sem domínio próprio). Texto puro. Resultado no painel, com "Reenviar aviso" | Em uso |

D8, D9, D10 e D12 a D16 não aparecem no repositório. Copiar do Memory Bank para esta tabela quando ele for para `docs/`.

## Limites do plano gratuito

Render e Supabase conferidos nas páginas oficiais em 22/10/2026; Vercel e GitHub Actions ainda por conferir
nas páginas deles. Os planos mudam: reconferir antes de cada etapa.

| Serviço | Limite | Efeito no projeto |
| --- | --- | --- |
| Render (API) | Dorme após 15 min sem tráfego; volta em cerca de 1 min; 750 h por mês por workspace; 1 instância; disco apagado a cada reinício; portas de saída 25, 465 e 587 bloqueadas | Primeira visita depois de uma pausa demora. Sem SMTP: o e-mail da Etapa 7 deve usar API HTTP do provedor |
| Supabase (banco e login) | 2 projetos ativos; 500 MB de banco; 1 GB de arquivos; 5 GB de tráfego; 50 mil usuários ativos; **pausa após 1 semana sem atividade**; **sem backup automático** | Precisa de ping e de backup manual (`exportar_dados.py`). Dois projetos: um de produção e um de desenvolvimento, sem sobrar vaga |
| Vercel (frontend) | Plano Hobby: só uso pessoal e não comercial; limite mensal de banda | Adequado a projeto acadêmico |
| Provedor de IA | Cota por minuto e por dia, conforme o provedor e o modelo | Estourou a cota: o item é salvo sem categoria. Registrar provedor e limite no Memory Bank |
| Brevo (e-mail) | Cota diária de envios no plano gratuito (confira o valor atual no painel do Brevo); remetente sem domínio próprio pode cair no spam | Um e-mail por confirmação, então o uso é baixo. Se falhar, o painel mostra o motivo e a CAE reenvia |
| GitHub Actions | Minutos gratuitos por mês (sem limite em repositório público) | CI e DAST rodam a cada PR, a cada push na `main` e toda segunda |

## Como escala

A API não guarda nada em disco nem em memória entre requisições, então crescer é trocar de plano, não reescrever.

1. **Primeiro gargalo: o sono do Render e as 750 h.** Plano pago do Render e do Supabase resolve sem mudar o código.
2. **Mais campi** (Etapa 1): uma coluna `campus_id` e a tabela `campi`, no mesmo banco. Não cria um banco por campus.
3. **Busca**: `LIKE '%palavra%'` em `texto_busca` percorre os itens do campus (o índice por campus e status filtra antes). Com muitos milhares de itens, acrescentar um índice `pg_trgm` em `texto_busca` (extensão do PostgreSQL, que o Supabase oferece).
4. **Mais de uma instância**: o limite por IP da decisão 001 fica na memória, então cada instância teria o seu (e ele zera quando o Render reinicia). Os limites diários contam no banco e continuam valendo. Com mais instâncias, mover o limite por IP para o banco ou para um Redis.
5. **IA**: a chamada é síncrona e pode segurar o registro por até 8 s. Se o volume crescer, mover para segundo plano.
6. **Banco**: as fotos ficam no banco (D4), até 600 KB cada (em média bem menos, uns 100 a 300 KB). Com os 500 MB do plano gratuito, cabem alguns milhares de itens com foto. Se apertar, mover `item_fotos` para o Storage do Supabase: só a API lê e grava as fotos, então o frontend não muda. O limite de 60 fotos por dia (decisão 001) segura o pior caso em uns 36 MB por dia.

## Qualidade e segurança na esteira

`ci.yml` (a cada PR, push na `main` e toda segunda): Lint e testes (Ruff, pytest, cobertura), Testes com PostgreSQL 16,
SAST (Bandit e Semgrep), SCA (`pip-audit`) e Segredos (Gitleaks). `dast.yml`: OWASP ZAP contra uma cópia
descartável da API com SQLite, sem tocar no Supabase. Dependabot semanal para `pip` e GitHub Actions.

Na aplicação: a API manda cabeçalhos de segurança em toda resposta (`nosniff`, `X-Frame-Options`, CSP, `no-store`
e outros, com teste no CI), e o site tem CSP e cabeçalhos próprios em `frontend/vercel.json`. Detalhes em
`docs/operacao.md`, seção "Cabeçalhos de segurança e CSP".
