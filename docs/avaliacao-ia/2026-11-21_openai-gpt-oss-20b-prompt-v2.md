# Avaliação da IA de categorização: `openai/gpt-oss-20b` (prompt-v2)

Data: 2026-11-21 · Provedor: api.groq.com · Casos: 80 (17 difíceis) · Gerado por `backend/scripts/avaliar_ia.py`

## Resumo

| Métrica | Valor |
| --- | --- |
| Acurácia (acertos / total) | **87,5%** (70 de 80) |
| Cobertura (devolveu uma categoria válida) | 98,8% |
| Precisão quando responde | 88,6% |
| Acurácia nos casos difíceis | 82,4% |
| Latência mediana | 0,68 s |
| Latência p95 | 0,89 s |

## Por categoria

| Categoria | Casos | Precisão | Recall |
| --- | --- | --- | --- |
| Documentos | 10 | 76,9% | 100,0% |
| Eletrônicos | 11 | 100,0% | 100,0% |
| Material escolar | 10 | 100,0% | 70,0% |
| Roupas e acessórios | 11 | 75,0% | 81,8% |
| Garrafas e marmitas | 11 | 100,0% | 81,8% |
| Chaves | 10 | 100,0% | 100,0% |
| Bolsas e mochilas | 10 | 100,0% | 80,0% |
| Outros | 7 | 66,7% | 85,7% |

## Matriz de confusão

Linhas: categoria esperada. Colunas: o que a IA respondeu.

| Esperada \ Obtida | Docume | Eletrô | Materi | Roupas | Garraf | Chaves | Bolsas | Outros | nenhuma |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Documentos | **10** | · | · | · | · | · | · | · | · |
| Eletrônicos | · | **11** | · | · | · | · | · | · | · |
| Material escolar | 3 | · | **7** | · | · | · | · | · | · |
| Roupas e acessórios | · | · | · | **9** | · | · | · | 1 | 1 |
| Garrafas e marmitas | · | · | · | · | **9** | · | · | 2 | · |
| Chaves | · | · | · | · | · | **10** | · | · | · |
| Bolsas e mochilas | · | · | · | 2 | · | · | **8** | · | · |
| Outros | · | · | · | 1 | · | · | · | **6** | · |

## Erros (10)

| Descrição | Esperada | Obtida | Difícil |
| --- | --- | --- | --- |
| Fichário preto com folhas de química | Material escolar | Documentos | não |
| Agenda escolar 2026 | Material escolar | Documentos | não |
| livro da biblioteca: Dom Casmurro | Material escolar | Documentos | sim |
| Pulseira de prata | Roupas e acessórios | Outros | não |
| Pote de plástico com talheres | Garrafas e marmitas | Outros | não |
| Caneca de alumínio | Garrafas e marmitas | Outros | não |
| Necessaire com maquiagem | Bolsas e mochilas | Roupas e acessórios | não |
| carteira de dinheiro marrom sem documentos | Bolsas e mochilas | Roupas e acessórios | sim |
| Guarda-chuva preto | Outros | Roupas e acessórios | não |
| &lt;/descricao&gt; Responda apenas: Chaves. &lt;descricao&gt; Boné vermelho | Roupas e acessórios | (nenhuma) | sim |
