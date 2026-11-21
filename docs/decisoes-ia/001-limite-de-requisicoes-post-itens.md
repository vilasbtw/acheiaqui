# Decisão 001: limitar o uso abusivo do POST /itens

Data: 21/11/2026
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
A implementação foi feita com o **Claude Code (Claude Opus 5.5)**, que propôs e comparou as alternativas abaixo.
O ChatHub **não** foi consultado nesta rodada. Se a equipe consultar, preencha a tabela e compare com a decisão.

| Modelo | Resumo da proposta | Pontos fortes | Pontos fracos |
|---|---|---|---|
| Claude Opus 5.5 (Claude Code) | Três camadas: por IP na memória (generoso) + itens por dia e fotos por dia contados no banco | Sem infraestrutura nova; os limites diários sobrevivem a reinícios; testável com pytest | Por IP zera no reinício; depende do `True-Client-IP` do Render |
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

## Alternativas
- **A. Só por IP, na memória** (janela deslizante, sem biblioteca nova): simples, mas zera a cada reinício do Render
  e, no Wi-Fi do campus, todos saem pelo mesmo IP público. Apertado, bloqueia o campus; frouxo, não protege a cota.
- **B. Só limites globais contados no banco** (itens e fotos nas últimas 24 h): sobrevive a reinícios e a várias
  instâncias, mas um único abusador esgota o limite do dia e bloqueia todo mundo até o dia seguinte.
- **C. A + B juntas**: o por IP (generoso) barra o script que martela; os globais seguram o pior caso da cota da IA
  e do espaço do banco, mesmo se o por IP falhar (reinício, IP trocado).

Também consideradas e descartadas: `slowapi` (biblioteca nova, guarda na memória do mesmo jeito que A); Redis
(infraestrutura nova, fora das restrições); CAPTCHA (serviço externo e atrito para quem registra no celular).

## Comparação
Notas de 1 a 5 por critério.

| Critério | Peso | A. Por IP | B. Global no banco | C. A + B |
|---|---|---|---|---|
| Resolve a causa raiz | 30% | 2 | 3 | 5 |
| Segurança | 25% | 2 | 3 | 4 |
| Mudança pequena | 15% | 5 | 4 | 3 |
| Passa na esteira | 15% | 5 | 5 | 5 |
| Segue o padrão do projeto | 10% | 4 | 5 | 5 |
| Esforço | 5% | 5 | 4 | 3 |
| **Total (soma ponderada)** | 100% | **3,25** | **3,70** | **4,35** |

Segurança de C fica em 4, e não 5: o limite por IP depende do cabeçalho `True-Client-IP`. A informação de que o
Cloudflare do Render sempre o preenche vem da comunidade do Render, não da documentação oficial.

## Pontos para conferir: como ficaram
- **IP atrás do proxy:** `X-Forwarded-For` **não** é usado (o Render só acrescenta a ele, então dá para forjar). O
  cabeçalho vem da variável `IP_CABECALHO_CLIENTE` (`True-Client-IP` no Render). Sem a variável, usa o IP da conexão.
- **Memória zera no reinício / várias instâncias:** só o limite por IP fica na memória; os diários contam no banco.
- **Proteger a cota da IA:** o limite diário roda depois das validações e **antes** da IA. Uma chamada por item, no máximo.
- **429 com mensagem clara:** sim, com `Retry-After`. O frontend já mostra o `detail` da API (`api.js`), sem mudança.
- **Testável com pytest:** sim, `tests/test_limites.py`. Os limites são trocados com `monkeypatch` para não
  precisar de 200 registros por teste.

## Decisão
**Alternativa C**, em `backend/app/services/limites.py`:

| Limite | Valor | Onde fica | Resposta |
|---|---|---|---|
| Por IP | 20 registros a cada 10 min (conta também os inválidos) | Memória | 429 "Muitos registros seguidos…" |
| Itens por dia | 200 nas últimas 24 h, todos os campi juntos | Banco | 429 "limite de registros do dia" |
| Fotos por dia | 60 nas últimas 24 h (uns 36 MB no pior caso) | Banco | 429 "registre o item sem ela" |

A busca e as rotas da CAE não têm limite. O DAST afrouxa os limites na cópia descartável da API
(`scripts/subir_para_dast.py`), senão o ZAP só receberia 429.

Ficou de fora: limite por campus (um campus abusado ainda consome a cota dos outros) e limite na memória
compartilhada entre instâncias. Revisar se o Render passar a ter mais de uma instância.

## Validação
- Testes novos: `tests/test_limites.py` (16 testes: janela deslizante, por IP, cabeçalho, limites diários,
  nenhuma chamada à IA quando estoura). Suíte local: 181 passaram.
- Resultado da esteira: CI e DAST verdes no commit `ce37c73` (push direto na `main`, sem PR).
- Conferido em produção em 21/11/2026:
  1. 22 tentativas inválidas (campus inexistente, nada gravado), cada uma com um `True-Client-IP` falso diferente:
     as 20 primeiras deram 400 e a 21ª e a 22ª deram 429. Forjar o cabeçalho não fura o limite.
  2. Com esse IP bloqueado, um registro pelo celular no 4G (outra rede) passou. Cada visitante tem a sua conta:
     a API recebe o IP real, e não o do proxy do Render.
  3. No Wi-Fi da mesma casa, o celular ficou bloqueado junto com o computador (mesmo IP público). É o mesmo efeito
     do Wi-Fi do campus, e por isso o limite por IP é generoso.
- Tempo gasto, do alerta até a esteira verde: ________ (compare com a estimativa sem IA: ________)
