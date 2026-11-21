Backend - Achei Aqui

Este é o módulo backend do projeto Achei Aqui, construído para gerenciar a lógica de negócios, a persistência de dados e as integrações de Inteligência Artificial do portal de achados e perdidos.

Tecnologias Utilizadas

Python & FastAPI: Framework principal para construção da API REST.

Supabase & SQLAlchemy: Gerenciamento e ORM para o banco de dados relacional.

Pytest: Framework para testes unitários e de integração.

Ruff: Linter para padronização e qualidade do código.

Estrutura de Diretórios

A arquitetura do backend é dividida em camadas para facilitar a escalabilidade e a manutenção:

/app/models/: Contém os modelos de dados do SQLAlchemy (categoria.py, devolucao.py, item.py).

/app/schemas/: Define os esquemas do Pydantic para validação de entrada e saída de dados.

/app/routers/: Concentra os endpoints da API (cae.py, categorias.py, itens.py), separando as rotas por domínio.

/app/services/: Abriga a lógica de negócios e as regras mais complexas. Destaca-se o arquivo ia_categoria.py, responsável pela integração do Agente de IA que sugere a categoria de cada item no momento do registro.

/scripts/: Scripts utilitários para validação de banco de dados e testes locais de IA (verificar_supabase.py, testar_ia.py).

/tests/: Conjunto completo de testes automatizados garantindo a estabilidade da API e do serviço de IA.

Funcionalidade de IA

O backend abriga o Agente de IA que sugere a categoria de um item a partir da descrição, no registro (POST /itens), quando quem registra não informa uma categoria. A chamada vai para qualquer provedor compatível com "chat/completions" (configurado em IA_API_KEY, IA_BASE_URL e IA_MODEL no .env), e a resposta só é aceita se for o nome de uma categoria que existe no banco.

A IA nunca bloqueia o registro (decisão D2): se ela não estiver configurada, falhar, passar de 8 s ou responder algo que não é uma categoria, o item é salvo sem categoria.

A correspondência entre itens perdidos e achados por IA ainda não existe: está planejada para a Etapa 6 (D26–D27 em docs/arquitetura.md).

Como Executar

Para rodar este módulo localmente:

Ative o ambiente virtual: venv\Scripts\activate

Instale as dependências: pip install -r requirements.txt (apenas na primeira vez)

Inicie o servidor: uvicorn app.main:app --reload