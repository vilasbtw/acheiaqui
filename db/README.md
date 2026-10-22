# Banco de dados: migrações

O banco muda com o tempo (campus, perdidos, fotos...). Para mudar **sem arriscar os dados reais**, toda
alteração é um arquivo SQL numerado em `db/migrations/`, aplicado primeiro no banco de **desenvolvimento**
e só depois no de **produção**.

## Regras de ouro

1. **Nunca** teste uma migração direto em produção. Primeiro desenvolvimento, depois produção.
2. **Nunca edite** uma migração que já foi aplicada. Crie uma nova (o script recusa se detectar edição).
3. **Toda tabela nova precisa de `ALTER TABLE <tabela> ENABLE ROW LEVEL SECURITY;`** na mesma migração
   (decisão D17). Se faltar, o script desfaz a migração inteira.
4. **Backup antes** de aplicar em produção (o plano gratuito do Supabase não faz backup automático).
5. Segredos ficam só nos arquivos `.env*` (ignorados pelo Git). Nunca em zip, print ou commit.

## Dois ambientes, dois arquivos

| Arquivo | Aponta para | Uso |
| --- | --- | --- |
| `backend/.env` | Supabase de **desenvolvimento** | trabalho do dia a dia, testes locais |
| `backend/.env.prod` | Supabase de **produção** | só para migrações e backup em produção |

A produção do site (Render e Vercel) usa as variáveis cadastradas nos próprios painéis, e não esses arquivos.

## Rotina de qualquer mudança no banco

```
# 1. Escreva db/migrations/NNNN_descricao.sql (próximo número, minúsculas, sem acento)

# 2. Veja o estado e aplique em DESENVOLVIMENTO
python backend/scripts/aplicar_migracoes.py --env backend/.env --listar
python backend/scripts/aplicar_migracoes.py --env backend/.env

# 3. Teste o sistema contra o banco de desenvolvimento (backend local + roteiro manual)
python backend/scripts/verificar_supabase.py          # confere RLS, login e sign-up

# 4. Faça o merge do PR (testes verdes) e, SÓ ENTÃO, produção:
python backend/scripts/exportar_dados.py --env backend/.env.prod       # backup
python backend/scripts/aplicar_migracoes.py --env backend/.env.prod --listar
python backend/scripts/aplicar_migracoes.py --env backend/.env.prod
```

O script mostra em **qual servidor e banco** vai mexer e pede para você digitar `sim`. Leia essa linha.

## Primeira vez em produção (banco que já existe)

A migração `0001_baseline.sql` foi escrita para rodar em um banco novo **ou** em um que já tem as tabelas e
os dados: não apaga, não duplica e não altera nada que já existe; só registra que o banco está na versão 0001.
Faça o backup antes mesmo assim.

## Como escrever uma migração

- Nome: `NNNN_descricao_em_minusculas.sql` (4 dígitos, `_`, só letras minúsculas, números e `_`).
- Uma migração = uma mudança com um propósito (`0002_campi.sql`, `0003_arquivar_itens.sql`).
- Quando mexer em tabela que já tem dados, pense nos dados existentes: nova coluna obrigatória precisa de
  valor padrão, ou ser criada nula, preenchida e só depois marcada `NOT NULL` (em migrações separadas).
- Cada migração roda numa transação. Por isso **não use** `CREATE INDEX CONCURRENTLY` nem outros comandos
  que não rodam dentro de transação.
- Prefira `IF NOT EXISTS`/`IF EXISTS` quando fizer sentido: facilita repetir uma migração em outro ambiente.

## Backup

`exportar_dados.py` grava um CSV por tabela em `backend/backups/AAAA-MM-DD_HHMMSS/`. A pasta já nasce
protegida do Git, mas os arquivos têm **dados pessoais**: não envie a ninguém e apague quando não precisar mais.
O backup guarda os dados; a estrutura das tabelas está nas migrações.

## Problemas comuns

| Mensagem | O que fazer |
| --- | --- |
| `Nome inválido` | Renomeie para `NNNN_descricao.sql` (minúsculas, sem acento nem espaço) |
| `Número repetido` | Duas migrações com o mesmo número: renumere a mais nova |
| `foi ALTERADO depois` | Desfaça a edição (`git checkout -- arquivo`) e crie uma migração nova |
| `mais antiga que a última aplicada` | Renumere para um número maior que o último aplicado |
| `tabela(s) sem RLS` | Acrescente o `ENABLE ROW LEVEL SECURITY` na migração |
| `ERRO ao conectar` | Confira a `DATABASE_URL` (Session pooler, senha só com letras e números) |
