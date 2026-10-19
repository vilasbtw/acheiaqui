Documentação Técnica e Decisões - Achei Aqui

Esta pasta centraliza os artefatos de banco de dados e os registros de decisões arquiteturais do projeto Achei Aqui, com forte foco no desenvolvimento guiado por especificações (Spec-Driven Development) e na introdução do Agente de IA.

Estrutura de Arquivos

schema.sql: Arquivo contendo as instruções SQL (DDL) para a criação das tabelas no Supabase. Ele reflete a estrutura exata necessária para armazenar usuários, itens, categorias e registros de devolução.

/decisoes-ia/: Diretório contendo os Registros de Decisão Arquitetural (ADRs) específicos para a implementação da Inteligência Artificial.

001-limite-de-requisicoes-post-itens.md: Documenta as restrições, limites de API e regras de negócio definidas para evitar custos excessivos ou uso abusivo das APIs de IA durante a criação de novos itens.

modelo.md: Template ou documentação do modelo utilizado para a tomada de decisão estruturada no projeto.

Importância

Manter o schema.sql atualizado garante que qualquer membro da equipe ou ferramenta de CI/CD possa recriar o ambiente de banco de dados do zero. Os documentos de decisões de IA servem como a "fonte da verdade" (spec-first) exigida pela disciplina, direcionando como os serviços de inteligência artificial devem se comportar na aplicação.