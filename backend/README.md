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

/app/services/: Abriga a lógica de negócios e as regras mais complexas. Destaca-se o arquivo ia_categoria.py, responsável pela integração do Agente de IA para classificação e matching automático de itens.

/scripts/: Scripts utilitários para validação de banco de dados e testes locais de IA (verificar_supabase.py, testar_ia.py).

/tests/: Conjunto completo de testes automatizados garantindo a estabilidade da API e do serviço de IA.

Funcionalidade de IA

O backend abriga a lógica do Agente de IA responsável por analisar as descrições dos itens registrados e sugerir potenciais matches (correspondências) para a Comissão de Assistência Estudantil (CAE), otimizando a devolução de itens perdidos.

Como Executar

Para rodar este módulo localmente:

Ative o ambiente virtual: venv\Scripts\activate

Instale as dependências: pip install -r requirements.txt (apenas na primeira vez)

Inicie o servidor: uvicorn app.main:app --reload