# Operação do Achei Aqui

Guia para quem mantém o sistema no ar. **Nunca escreva valores de senha ou chave neste arquivo**, só os nomes.

- API: `https://acheiaqui-api.onrender.com` (Render)
- Frontend: `https://acheiaqui-frontend.vercel.app` (Vercel)
- Banco e login: Supabase (um projeto de produção e, quando criado, um de desenvolvimento)

## Variáveis

Backend, cadastradas no painel do Render (local: `backend/.env`, modelo em `backend/.env.example`):

| Nome | Para que serve | Obrigatória |
| --- | --- | --- |
| `DATABASE_URL` | Conexão com o Postgres (Session pooler do Supabase; senha só com letras e números) | Sim |
| `SUPABASE_URL` | Endereço do projeto Supabase, usado para validar o token da CAE | Sim |
| `SUPABASE_ANON_KEY` | Chave pública (publishable) do Supabase | Sim |
| `FRONTEND_URL` | Endereços do frontend liberados no CORS, separados por vírgula, sem `/` no final. Em produção, o endereço da Vercel | Sim |
| `IA_API_KEY` | Chave do provedor de IA | Não |
| `IA_BASE_URL` | Endereço do provedor (compatível com `chat/completions`) | Não |
| `IA_MODEL` | Nome do modelo | Não |

As três `IA_*` vão juntas. Se faltar qualquer uma, o sistema funciona normalmente, só sem categoria automática.

Outras variáveis:

- `TEST_DATABASE_URL`: só em testes (esteira e computador). Aceita apenas banco local.
- `PORT`: o Render define sozinho. Não cadastrar.
- Frontend: **não usa variáveis**. O endereço da API está em `frontend/js/api.js` (escolhe local ou produção sozinho)
  e o endereço do Supabase com a chave pública está em `frontend/js/auth.js`.

## Deploy

O deploy sai do GitHub: ao entrar código na `main`, Render e Vercel publicam sozinhos (confirmar em cada painel
que o deploy automático está ligado).

| | Render (API) | Vercel (frontend) |
| --- | --- | --- |
| Pasta raiz | `backend` | `frontend` |
| Build | `pip install -r requirements.txt` | nenhum |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | páginas estáticas |
| Python | Mesmo da esteira (3.12) | não se aplica |

Depois de cada deploy, confira: `GET /saude` responde `{"status":"ok"}` e `GET /categorias` devolve as 8 categorias.
Depois abra o site, registre um item de teste e veja se ele aparece na busca.

**Deploy com mudança no banco:** o código novo entra no ar assim que chega à `main`. Migração que **acrescenta**
(tabela nova, coluna nula) vai para produção **antes** do merge; migração que **restringe** (`NOT NULL`, apagar
coluna) vai **depois** que o código novo estiver no ar. Sempre com backup antes e passando pelo banco de
desenvolvimento. Detalhes e exemplos em `db/README.md`, seção "Ordem com o deploy".

## Cabeçalhos de segurança e CSP

- **API:** `backend/app/main.py` acrescenta os cabeçalhos de segurança em toda resposta (inclusive erros e CORS).
  O `/docs` fica sem a CSP estrita, senão o Swagger não abre. O `tests/test_cabecalhos_seguranca.py` quebra o CI
  se alguém remover o middleware.
- **Site:** `frontend/vercel.json` define a CSP, a lista de endereços de onde o navegador aceita carregar e para onde
  aceita enviar dados. Hoje são: o próprio site, a API do Render, o Supabase, o jsDelivr (supabase-js) e o Google
  Fonts.
- **Usou um serviço novo no site** (outra API, outro CDN, as fotos do Supabase Storage na Etapa 5)? Acrescente o
  endereço na diretiva certa do `vercel.json`: `script-src` para scripts, `connect-src` para `fetch`, `img-src`
  para imagens, `style-src` e `font-src` para CSS e fontes. Se esquecer, o navegador bloqueia e o console mostra
  `Refused to ... because it violates the following Content Security Policy directive`.
- **Trocou o endereço da API ou o projeto do Supabase?** Atualize também o `connect-src`.
- O `vercel.json` só vale na Vercel: com `python -m http.server` local não há CSP. Depois do deploy, confira no
  DevTools (aba Console) que não aparece nenhum `Refused to`.

## Ping (manter a API e o banco acordados)

O Render dorme após 15 minutos sem visita, e o Supabase pausa o projeto após 1 semana sem atividade.

1. Crie um monitor no cron-job.org ou no UptimeRobot: `GET https://acheiaqui-api.onrender.com/saude`, a cada 10 minutos.
2. `/saude` consulta o banco (`SELECT 1`). Resposta `503` significa que o banco não respondeu.
3. Atenção à conta: um serviço ligado o mês todo gasta de 720 a 744 das 750 horas gratuitas do Render, que valem para
   o workspace inteiro. **Não crie um segundo serviço gratuito no mesmo workspace.**
4. Em uma semana de funcionamento, confira no painel do Supabase se o projeto continua ativo. Se pausar mesmo
   com o ping, o monitor não está contando como atividade: veja a próxima seção.
5. Antes de uma apresentação, abra o site 5 minutos antes para acordar a API (a primeira resposta leva cerca de 1 minuto).

## Se o Supabase pausar

Sintomas: a busca mostra erro, `/saude` responde `503` ("Banco de dados indisponível") e a CAE não consegue entrar.

1. Entre no painel do Supabase, abra o projeto e clique em **Restore project**. Espere voltar para o status ativo.
2. Se a conexão não voltar, copie de novo a connection string (Session pooler) e compare com `DATABASE_URL` no Render.
   Se mudou, atualize e deixe o Render reiniciar.
3. Confira `GET /saude`, a busca no site e o login da CAE. Se quiser, rode `python backend/scripts/verificar_supabase.py`.
4. Projeto pausado por muito tempo pode deixar de ser restaurável (confira o prazo no painel). Por isso, faça o
   backup em CSV (`exportar_dados.py`) de vez em quando e antes de qualquer migração.

## Rotação de chaves

Regra geral: **gere a nova, atualize o Render, confira `/saude`, só então revogue a antiga.** Se a chave
vazou (Git, print, zip, conversa), faça isso na hora e depois descubra como vazou.

| O que | Onde gerar | Onde atualizar | Conferir |
| --- | --- | --- | --- |
| Senha do banco | Supabase, Project Settings, Database, redefinir a senha (só letras e números) | `DATABASE_URL` no Render e nos arquivos `backend/.env` e `backend/.env.prod` | `/saude` |
| Chave da IA | Painel do provedor: criar a nova e apagar a antiga | `IA_API_KEY` no Render e em `backend/.env` | `python backend/scripts/testar_ia.py` |
| Chave pública do Supabase (`SUPABASE_ANON_KEY`) | Supabase, Project Settings, API | `SUPABASE_ANON_KEY` no Render **e** a constante em `frontend/js/auth.js` (novo deploy na Vercel) | Login da CAE |
| Chaves secretas do Supabase (`service_role` e semelhantes) | O sistema **não usa**. Se alguma aparecer no Git, gere outra no painel | Nenhum lugar | Gitleaks verde |
| Senha de uma conta da CAE | Supabase, Authentication, Users | A pessoa recebe a nova | Login |

A chave pública não é segredo, mas só vale com RLS ligado em todas as tabelas (D17). Confira com
`python backend/scripts/verificar_supabase.py`. Se um segredo foi para o Git, apagar o commit não basta: troque a
chave primeiro.

## Contas da CAE e campus

Desde a Etapa 1, ter login **não basta**: a API só libera o painel para quem tem uma linha em `cae_membros`, que diz
de qual campus a pessoa é (D21). Sem essa linha, o painel recebe 403.

1. Crie a conta em Authentication, Users (o cadastro livre continua desativado) e copie o **User UID** dela.
2. No SQL Editor do mesmo projeto:

   ```sql
   INSERT INTO cae_membros (user_id, campus_id)
   VALUES ('COLE-O-UUID-AQUI', (SELECT id FROM campi WHERE sigla = 'hto'));
   ```

3. Para tirar o acesso: `DELETE FROM cae_membros WHERE user_id = '...';` (e, se for o caso, apague a conta no Auth).

Uma pessoa pertence a um campus só (`UNIQUE`). Para mudar de campus, faça um `UPDATE` na linha dela.
**No deploy da Etapa 1**, as contas da CAE que já existem em produção precisam dessa linha antes de o backend novo
entrar no ar; senão, ninguém da CAE consegue abrir o painel.

## Como recriar o banco

Serve para voltar de um desastre ou para criar o projeto de desenvolvimento.

1. Crie um projeto no Supabase (o plano gratuito permite 2 ativos).
2. Em Authentication, desative o cadastro livre de usuários (D6) e crie à mão as contas da CAE (depois das
   migrações, vincule cada uma ao campus: seção "Contas da CAE e campus").
3. Copie a connection string (Session pooler) para um arquivo novo, por exemplo `backend/.env.novo`, com `DATABASE_URL`
   (o `.gitignore` já ignora `.env.*`).
4. Crie as tabelas: `python backend/scripts/aplicar_migracoes.py --env backend/.env.novo`. A `0001` cria tabelas,
   as 8 categorias e liga o RLS. Leia a linha que mostra o servidor e digite `sim`.
5. Se for restaurar dados de um backup (`backend/backups/AAAA-MM-DD_HHMMSS/*.csv`), **não há script de importação**.
   Importe pelo Table Editor do Supabase, na ordem `itens` e depois `devolucoes`. Não precisa importar `categorias`: a `0001` já
   criou as mesmas 8, com os mesmos números. Depois acerte o contador dos números automáticos, no SQL Editor:

   ```sql
   SELECT setval(pg_get_serial_sequence('itens', 'id'), (SELECT MAX(id) FROM itens));
   SELECT setval(pg_get_serial_sequence('devolucoes', 'id'), (SELECT MAX(id) FROM devolucoes));
   ```

6. Se for um projeto novo de **produção**: atualize `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_ANON_KEY` no Render
   e as constantes de `frontend/js/auth.js` (novo deploy na Vercel). O endereço do projeto é diferente em cada projeto.
7. Confira com `python backend/scripts/verificar_supabase.py` (lê o `backend/.env`; coloque ali os valores do projeto novo
   enquanto testa), depois `/saude`, busca, login da CAE e uma devolução de teste.

## Problemas comuns

| O que aparece | Causa provável | O que fazer |
| --- | --- | --- |
| "Não foi possível conectar ao servidor" na primeira visita | API dormindo | Esperar cerca de 1 minuto e tentar de novo |
| Erro de CORS no console do navegador | `FRONTEND_URL` sem o endereço da Vercel, ou com `/` no final | Corrigir no Render |
| `/saude` responde 503 | Banco pausado ou `DATABASE_URL` errada | Seção "Se o Supabase pausar" |
| Itens novos sem categoria | IA desligada ou sem cota. No log do Render aparece `achei_aqui.ia` com o motivo | Conferir as 3 variáveis `IA_*` e a cota do provedor |
| Painel da CAE devolve 401 | Sessão expirada, ou `SUPABASE_URL`/`SUPABASE_ANON_KEY` diferentes do projeto usado no login | Entrar de novo; conferir as variáveis |
| Painel da CAE devolve 403 ("não está vinculada à CAE") | Login certo, mas a conta não tem linha em `cae_membros` | Seção "Contas da CAE e campus" |
| Algo do site parou só na Vercel, e o console mostra `Refused to ...` | A CSP do `frontend/vercel.json` não libera aquele endereço | Seção "Cabeçalhos de segurança e CSP" |
| Migração recusada | Ver a tabela "Problemas comuns" em `db/README.md` | |

Os logs da API ficam na aba Logs do serviço no Render.
