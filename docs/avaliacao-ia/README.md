# Avaliação da IA de categorização

Quanto a IA que sugere a categoria no registro (D2) acerta, medido num conjunto de descrições rotuladas à mão.

## Como funciona

- **Conjunto:** `backend/scripts/avaliacao_ia/conjunto.csv`, com 80 descrições inventadas (nenhum dado real de
  pessoa), cerca de 10 por categoria. 17 são **difíceis**: erros de digitação, gírias, itens ambíguos e duas
  tentativas de *prompt injection*.
- **Script:** `backend/scripts/avaliar_ia.py`. Chama a **mesma função da produção** (`sugerir_categoria`) com as 8
  categorias da migração 0001 e grava um relatório por modelo nesta pasta.
- **Métricas:**
  - **acurácia:** acertos sobre o total, contando "sem resposta" como erro;
  - **cobertura:** quantas vezes a IA devolveu uma categoria válida;
  - **precisão e recall** de cada categoria;
  - **matriz de confusão;**
  - **latência:** mediana e p95.

```
python backend/scripts/avaliar_ia.py                                     # modelo do .env
python backend/scripts/avaliar_ia.py --rotulo prompt-v3                   # depois de mudar o prompt
python backend/scripts/avaliar_ia.py --modelos openai/gpt-oss-120b qwen/qwen3.8-27b   # comparar modelos
```

Cada rodada leva uns 4 a 5 minutos: são 80 chamadas, com uma pausa entre elas por causa da cota por minuto do
provedor. Os modelos disponíveis mudam com o tempo. Em 21/11/2026, os modelos `llama-3.*` já não existiam no Groq
(o provedor respondia 404). O script não grava relatório quando nenhuma chamada dá certo.

## Resultados de 21/11/2026 (Groq, `openai/gpt-oss-20b`)

| Rodada | Acurácia | Cobertura | Latência mediana | Relatório |
| --- | --- | --- | --- | --- |
| Prompt v1 (original) | 88,8% | 96,2% | 0,68 s | `2026-11-21_openai-gpt-oss-20b-prompt-v1.md` |
| Prompt v2 | 87,5% | 98,8% | 0,68 s | `2026-11-21_openai-gpt-oss-20b-prompt-v2.md` |
| Prompt v2, repetição | 86,2% | 100,0% | 0,66 s | `2026-11-21_openai-gpt-oss-20b-prompt-v2-r2.md` |

**O que mudou do v1 para o v2:**
- No v1, o prompt mandava responder `NENHUMA` quando nenhuma categoria servisse, mesmo com a categoria **Outros**
  na lista. Itens como "bicicleta", "skate" e "remédio" ficavam sem categoria, e o recall de Outros era de 42,9%.
- O v2 manda usar Outros nesses casos. Esses três itens passaram a acertar, e a cobertura subiu de 96% para 99–100%.

**Ruído:** o mesmo prompt, rodado duas vezes, errou casos diferentes. "Cartão do SUS" e "crachá" erraram só na
repetição. O `gpt-oss-20b` é um modelo de raciocínio e não é totalmente determinístico, mesmo com `temperature: 0`.
Por isso, diferenças de 2 ou 3 casos em 80 (2 a 4 pontos percentuais) **não** provam que um prompt é melhor que o
outro. A acurácia ficou estável, entre 86% e 89%.

**Erros que se repetem** (nas três rodadas): "Caneca de alumínio" e "Pote com talheres" (a IA respondeu Outros, e o
rótulo era Garrafas e marmitas), "Necessaire" e "Carteira de dinheiro" (Roupas e acessórios, e o rótulo era Bolsas e
mochilas), "Guarda-chuva" (Roupas e acessórios, e o rótulo era Outros) e "Fichário com folhas" (Documentos, e o rótulo
era Material escolar). São itens ambíguos. O problema pode estar nos nomes das categorias ou nos rótulos, e não só
na IA.

**Prompt injection:** com os dois prompts, nenhuma das tentativas fez a IA responder a categoria pedida pelo
atacante. No pior caso, o item ficou sem categoria. Isso confirma a defesa principal: a resposta só é aceita se
for uma categoria da lista.

## Próximos passos

- Comparar o `gpt-oss-120b` e o `qwen3.8-27b` (disponíveis no Groq em 21/11/2026).
- Rodar cada configuração 3 vezes e apresentar a média e a variação.
- Revisar os itens ambíguos: renomear as categorias (ex.: "Garrafas, marmitas e utensílios") ou ajustar os rótulos.
