# Como contribuir

Equipe: Kaique, Evelyn e Kauany. Ninguém manda código direto para a `main`: tudo entra por Pull Request.

## Fluxo

1. Atualize a `main` e crie uma branch a partir dela: `feat/etapa-N-nome` para trabalho de uma etapa do checklist
   ou `feat/descricao-curta` para o resto. Para correção, `fix/descricao-curta`; para texto, `docs/descricao-curta`.
2. Faça commits pequenos no formato `tipo: descrição`, em português, no presente e sem ponto final.
   Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
   Exemplo: `feat: filtra a busca por categoria`.
3. **Antes de abrir o PR**, rode na pasta `backend/` (com o venv ativo e `pip install -r requirements-dev.txt`):

   ```
   ruff check .
   python -m pytest
   ```

4. Abra o PR e preencha o modelo (`.github/pull_request_template.md`). O PR só entra com a **esteira verde**:
   Lint e testes, Testes com PostgreSQL, SAST, SCA e Segredos. Se algum job ficar vermelho, corrija na mesma branch.
5. Faça o merge, confira o deploy e apague a branch.

## Regras que não mudam

- **Mudou o banco?** Crie uma migração nova em `db/migrations/` e siga o `db/README.md`
  (desenvolvimento primeiro, backup antes de produção). Nunca edite uma migração já aplicada.
- **Código novo tem teste.** Rota que devolve dado pessoal tem teste de que o público não o vê.
- **Nenhum segredo no Git**: nada de `.env`, chave de IA, senha do banco, nem em zip, print ou comentário.
  Se vazar, siga "Rotação de chaves" em `docs/operacao.md` na hora.
- **Usou IA para gerar código?** Marque no PR, leia e entenda tudo que foi gerado, e registre a comparação em
  `docs/decisoes-ia/` (use o `modelo.md`). Não envie `.env` nem dados reais de pessoas a nenhuma ferramenta.
- **Decisão de arquitetura?** Atualize o Memory Bank e a tabela de decisões em `docs/arquitetura.md`.

## Testes com PostgreSQL (opcional no computador)

Por padrão os testes usam SQLite em memória. Para rodar os testes marcados `postgres`, aponte `TEST_DATABASE_URL`
para um PostgreSQL **local** com as migrações aplicadas. Os testes apagam os dados, então a configuração recusa
qualquer servidor que não seja local. Nunca aponte para o Supabase. A esteira já faz isso sozinha.
