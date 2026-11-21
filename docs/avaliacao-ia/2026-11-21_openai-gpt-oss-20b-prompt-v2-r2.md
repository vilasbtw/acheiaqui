# Avaliação da IA de categorização: `openai/gpt-oss-20b` (prompt-v2-r2)

Data: 2026-11-21 · Provedor: api.groq.com · Casos: 80 (17 difíceis) · Gerado por `backend/scripts/avaliar_ia.py`

## Resumo

| Métrica | Valor |
| --- | --- |
| Acurácia (acertos / total) | **86,2%** (69 de 80) |
| Cobertura (devolveu uma categoria válida) | 100,0% |
| Precisão quando responde | 86,2% |
| Acurácia nos casos difíceis | 82,4% |
| Latência mediana | 0,66 s |
| Latência p95 | 0,98 s |

## Por categoria

| Categoria | Casos | Precisão | Recall |
| --- | --- | --- | --- |
| Documentos | 10 | 72,7% | 80,0% |
| Eletrônicos | 11 | 100,0% | 100,0% |
| Material escolar | 10 | 100,0% | 70,0% |
| Roupas e acessórios | 11 | 71,4% | 90,9% |
| Garrafas e marmitas | 11 | 100,0% | 81,8% |
| Chaves | 10 | 100,0% | 100,0% |
| Bolsas e mochilas | 10 | 100,0% | 80,0% |
| Outros | 7 | 60,0% | 85,7% |

## Matriz de confusão

Linhas: categoria esperada. Colunas: o que a IA respondeu.

| Esperada \ Obtida | Docume | Eletrô | Materi | Roupas | Garraf | Chaves | Bolsas | Outros | nenhuma |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Documentos | **8** | · | · | 1 | · | · | · | 1 | · |
| Eletrônicos | · | **11** | · | · | · | · | · | · | · |
| Material escolar | 3 | · | **7** | · | · | · | · | · | · |
| Roupas e acessórios | · | · | · | **10** | · | · | · | 1 | · |
| Garrafas e marmitas | · | · | · | · | **9** | · | · | 2 | · |
| Chaves | · | · | · | · | · | **10** | · | · | · |
| Bolsas e mochilas | · | · | · | 2 | · | · | **8** | · | · |
| Outros | · | · | · | 1 | · | · | · | **6** | · |

## Erros (11)

| Descrição | Esperada | Obtida | Difícil |
| --- | --- | --- | --- |
| Cartão do SUS | Documentos | Outros | não |
| crachá de estágio com foto | Documentos | Roupas e acessórios | sim |
| Fichário preto com folhas de química | Material escolar | Documentos | não |
| Agenda escolar 2026 | Material escolar | Documentos | não |
| livro da biblioteca: Dom Casmurro | Material escolar | Documentos | sim |
| Pulseira de prata | Roupas e acessórios | Outros | não |
| Pote de plástico com talheres | Garrafas e marmitas | Outros | não |
| Caneca de alumínio | Garrafas e marmitas | Outros | não |
| Necessaire com maquiagem | Bolsas e mochilas | Roupas e acessórios | não |
| carteira de dinheiro marrom sem documentos | Bolsas e mochilas | Roupas e acessórios | sim |
| Guarda-chuva preto | Outros | Roupas e acessórios | não |
