"""
Busca por palavras-chave (D1, D24): sem extensão do banco e sem API externa.

Um item é encontrado se ALGUMA palavra da busca aparece na descrição, no local ou no
nome da categoria. Quanto mais palavras batem, mais acima ele aparece.
Ignora acentos e maiúsculas: "eletronico" encontra "Eletrônico". A descrição e o local ficam
normalizados na coluna `itens.texto_busca` (migração 0006); a palavra buscada passa pela mesma regra.
Limitação conhecida: não entende sinônimos além do nome da categoria.
"""
import operator
import re
import unicodedata
from functools import reduce

from sqlalchemy import case, false, func, or_

from app.models.categoria import Categoria
from app.models.item import Item

MIN_LETRAS = 3
MAX_PALAVRAS = 6


def normalizar(texto: str) -> str:
    """Minúsculas e sem acento. A migração 0006 aplica a mesma regra aos itens antigos (com `translate`)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def texto_de_busca(descricao: str, local_encontrado: str) -> str:
    """O que vai para itens.texto_busca. Mesmo formato da migração 0006: descrição, espaço, local."""
    return normalizar(f"{descricao} {local_encontrado}")


def extrair_palavras(texto: str) -> list[str]:
    """Palavras com letras/números (sem _ nem símbolos), normalizadas, sem repetir."""
    palavras: list[str] = []
    for palavra in re.findall(r"[^\W_]{%d,}" % MIN_LETRAS, normalizar(texto)):
        if palavra not in palavras:
            palavras.append(palavra)
    return palavras[:MAX_PALAVRAS]


def aplicar_busca(consulta, texto: str, categorias: list[Categoria]):
    """`consulta` precisa ter outerjoin com Categoria. Filtra e ordena por relevância.
    `categorias`: todas as categorias, para comparar o nome sem acento (são poucas, então é em Python)."""
    palavras = extrair_palavras(texto)
    if not palavras:
        return consulta.filter(false())

    # Item gravado pelo código antigo, entre a migração 0006 e o deploy, tem texto_busca nulo:
    # nesse caso compara com o texto original (só ignora maiúsculas).
    texto_do_item = func.coalesce(Item.texto_busca, func.lower(Item.descricao + " " + Item.local_encontrado))
    pontos = []
    for palavra in palavras:
        ids_de_categoria = [c.id for c in categorias if palavra in normalizar(c.nome)]
        condicoes = [texto_do_item.like(f"%{palavra}%")]
        if ids_de_categoria:
            condicoes.append(Item.categoria_id.in_(ids_de_categoria))
        pontos.append(case((or_(*condicoes), 1), else_=0))

    total = reduce(operator.add, pontos)
    return consulta.filter(total > 0).order_by(total.desc(), Item.criado_em.desc(), Item.id.desc())
