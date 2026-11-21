# Avaliação da IA de categorização: `openai/gpt-oss-20b` (prompt-v1)

Data: 2026-11-21 · Provedor: api.groq.com · Casos: 80 (17 difíceis) · Gerado por `backend/scripts/avaliar_ia.py`

## Resumo

| Métrica | Valor |
| --- | --- |
| Acurácia (acertos / total) | **88,8%** (71 de 80) |
| Cobertura (devolveu uma categoria válida) | 96,2% |
| Precisão quando responde | 92,2% |
| Acurácia nos casos difíceis | 94,1% |
| Latência mediana | 0,68 s |
| Latência p95 | 0,90 s |

## Por categoria

| Categoria | Casos | Precisão | Recall |
| --- | --- | --- | --- |
| Documentos | 10 | 90,9% | 100,0% |
| Eletrônicos | 11 | 100,0% | 100,0% |
| Material escolar | 10 | 100,0% | 90,0% |
| Roupas e acessórios | 11 | 78,6% | 100,0% |
| Garrafas e marmitas | 11 | 100,0% | 81,8% |
| Chaves | 10 | 100,0% | 100,0% |
| Bolsas e mochilas | 10 | 100,0% | 80,0% |
| Outros | 7 | 60,0% | 42,9% |

## Matriz de confusão

Linhas: categoria esperada. Colunas: o que a IA respondeu.

| Esperada \ Obtida | Docume | Eletrô | Materi | Roupas | Garraf | Chaves | Bolsas | Outros | nenhuma |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Documentos | **10** | · | · | · | · | · | · | · | · |
| Eletrônicos | · | **11** | · | · | · | · | · | · | · |
| Material escolar | 1 | · | **9** | · | · | · | · | · | · |
| Roupas e acessórios | · | · | · | **11** | · | · | · | · | · |
| Garrafas e marmitas | · | · | · | · | **9** | · | · | 2 | · |
| Chaves | · | · | · | · | · | **10** | · | · | · |
| Bolsas e mochilas | · | · | · | 2 | · | · | **8** | · | · |
| Outros | · | · | · | 1 | · | · | · | **3** | 3 |

## Erros (9)

| Descrição | Esperada | Obtida | Difícil |
| --- | --- | --- | --- |
| Fichário preto com folhas de química | Material escolar | Documentos | não |
| Pote de plástico com talheres | Garrafas e marmitas | Outros | não |
| Caneca de alumínio | Garrafas e marmitas | Outros | não |
| Necessaire com maquiagem | Bolsas e mochilas | Roupas e acessórios | não |
| carteira de dinheiro marrom sem documentos | Bolsas e mochilas | Roupas e acessórios | sim |
| Guarda-chuva preto | Outros | Roupas e acessórios | não |
| Skate com rodinhas verdes | Outros | (nenhuma) | não |
| Remédio em cartela | Outros | (nenhuma) | não |
| bicicleta azul | Outros | (nenhuma) | não |
