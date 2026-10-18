# Decisão 001: limitar o uso abusivo do POST /itens

Data: ____/10/2026
Quem decidiu: ________
PR ou issue relacionado: ________

## Problema
`POST /itens` é público (sem login) e não tem limite de requisições. Quando a categoria não vem
preenchida, a API chama um provedor de IA externo com cota gratuita. Um uso abusivo (script
mandando milhares de registros) pode lotar o banco do plano gratuito e esgotar a cota da IA.
O problema foi identificado por leitura do código (seção 2 do documento da esteira).

Trecho relevante (`backend/app/routers/itens.py`):

```python
@router.post("", response_model=ItemPublico, status_code=201)
def registrar_item(dados: ItemCriar, sessao: Session = Depends(obter_sessao)):
    categorias = sessao.query(Categoria).all()
    categoria_id = dados.categoria_id
    if categoria_id is not None and all(c.id != categoria_id for c in categorias):
        raise HTTPException(status_code=400, detail="Categoria inexistente.")
    if categoria_id is None:
        categoria_id = _categoria_sugerida(dados.descricao, categorias)  # chama a IA externa
    item = Item(descricao=dados.descricao, local_encontrado=dados.local_encontrado,
                encontrado_em=dados.encontrado_em, contato_achador=dados.contato_achador,
                categoria_id=categoria_id)
    sessao.add(item)
    sessao.commit()
    sessao.refresh(item)
    return item
```

## Prompt enviado ao ChatHub
Colar exatamente este texto em todos os modelos:

> Contexto: API FastAPI (Python 3.12) com PostgreSQL (Supabase), hospedada no plano gratuito do
> Render, numa única instância. Projeto acadêmico de achados e perdidos. O endpoint POST /itens é
> público (sem login) e, quando a categoria não vem preenchida, chama uma API de IA externa com
> cota gratuita. Problema: não há limite de requisições, então um uso abusivo pode lotar o banco e
> esgotar a cota da IA. Restrições: MVP simples, custo zero, sem infraestrutura nova (sem Redis),
> e os testes pytest existentes devem continuar passando. Código atual: [colar o trecho acima].
> Peço: proponha 3 alternativas DIFERENTES (não só uma). Para cada uma: como funciona, código ou
> configuração, pontos fortes, riscos e limitações, e o que mudaria nos testes. No fim, diga qual
> escolheria e diga o que você não tem certeza.

## Modelos consultados
(Anotar o plano do ChatHub usado e quantos modelos couberam por rodada.)

| Modelo | Resumo da proposta | Pontos fortes | Pontos fracos |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |

## Pontos para conferir nas respostas (análise nossa, feita ANTES de consultar os modelos)
Não é saída do ChatHub: serve para avaliar se os modelos esqueceram algo importante.
- Atrás do proxy do Render, o IP do visitante pode chegar no cabeçalho `X-Forwarded-For`. Um
  limite por IP que ignora isso bloqueia todo mundo junto, ou ninguém.
- Limite guardado na memória do processo zera a cada reinício (o plano gratuito dorme e acorda) e
  não vale se houver mais de uma instância.
- O custo real a proteger é a cota da IA: limitar só as chamadas à IA (com fallback sem categoria)
  pode ser mais barato do que limitar o endpoint inteiro.
- Qualquer solução precisa devolver 429 com mensagem clara, e o frontend (`api.js`) precisa mostrar.
- Dá para testar com pytest? Como?

## Comparação
Notas de 1 a 5 por critério, justificadas em uma frase quando a nota for extrema.

| Critério | Peso | Alternativa A | Alternativa B | Alternativa C |
|---|---|---|---|---|
| Resolve a causa raiz | 30% |  |  |  |
| Segurança | 25% |  |  |  |
| Mudança pequena | 15% |  |  |  |
| Passa na esteira | 15% |  |  |  |
| Segue o padrão do projeto | 10% |  |  |  |
| Esforço | 5% |  |  |  |
| **Total (soma ponderada)** | 100% |  |  |  |

## Onde os modelos discordaram
Se discordaram, provavelmente a especificação estava ambígua. Anotar o que foi esclarecido.

## Decisão
Qual alternativa foi escolhida, por quê e o que ficou de fora.

## Validação (preencher depois de aplicar)
- Testes novos/alterados: ________
- Resultado da esteira no PR (link): ________
- Tempo gasto, do alerta até o PR verde: ________ (compare com a estimativa sem IA: ________)
